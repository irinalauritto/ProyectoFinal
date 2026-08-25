"""Módulo para gestionar el entrenamiento SSVEP y calcular pesos TRCA.

Este módulo contiene `TrainingManager`, que coordina la adquisición de datos EEG,
el control de estímulos visuales y el guardado de sesiones. También incluye
`CalculeTRCAWeights`, que implementa el algoritmo Task-Related Component Analysis
basado en Nakanishi et al. (2018).

Reference:
    M. Nakanishi et al., "Enhancing Detection of SSVEPs for a High-Speed Brain
    Speller Using Task-Related Component Analysis," IEEE Trans. Biomed. Eng.,
    vol. 65, no. 1, pp. 104-112, Jan. 2018, doi: 10.1109/TBME.2017.2694818.
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import builtins
import math
import random
import time
import os

import numpy as np
from PySide6.QtCore import QObject, Signal
from scipy.io import savemat
from scipy.linalg import eigh

from ssvep.app.dataclasses import UserPreferences

# Constantes de tiempo para la adquisición
TIME_DiSCARD = 0.15  # Segundos de transitorio a descartar al inicio de cada época
TIME_MARGIN = 0.10   # Segundos de margen extra para absorber desfasajes de reloj


class TrainingManager(QObject):
    """Gestiona la adquisición de señales EEG durante una sesión de entrenamiento SSVEP.

    Coordina la presentación de estímulos visuales, la recepción de muestras EEG,
    la sincronización de eventos, la segmentación de épocas, el guardado en `.mat`
    y el cálculo de los pesos TRCA para el clasificador.

    Attributes:
        trial_status (Signal[str]): Emitida al completar cada trial.
        stimulus_indicate (Signal[int]): Indica qué estímulo mostrar a continuación.
        stimulus_on (Signal[None]): Solicita encender el estímulo visual.
        training_finish (Signal[object]): Emitida al finalizar con los resultados del TRCA.
    """

    trial_status = Signal(str)
    stimulus_indicate = Signal(int)
    stimulus_on = Signal()
    training_finish = Signal(object)

    def __init__(self,base_dir, p_filterbank, p_user_preferences: UserPreferences = None):
        """Inicializa el gestor de entrenamiento.

        Args:
            base_dir: Carpeta base de la aplicación, usada como raíz para guardar las sesiones de entrenamiento (.mat).
            p_filterbank: Función de filtrado por bandas utilizada para TRCA.
            p_user_preferences (UserPreferences, optional): Preferencias del usuario. Defaults to None.
        """
        super().__init__()

        self.__base_dir = base_dir
        self.__filterbank = p_filterbank
        self.__delta_t = 1 / builtins.SAMPLE_RATE

        # Banderas de estado
        self.__is_start = False
        self.__is_finish = False
        self.__add_data = False
        self.__mark_count = 0
        self.__stim_index = 0
        self.__n_trials = builtins.SETTINGS.trials_use
        

        # Parámetros de tiempo
        self.__cue_duration_sec = builtins.SETTINGS.cue_duration_sec
        self.__cue_duration_samples = int(self.__cue_duration_sec * builtins.SAMPLE_RATE)

        # Variables de procesamiento
        self.__n_discard_samples = int(TIME_DiSCARD * builtins.SAMPLE_RATE)
        self.__tail_margin_samples = int(TIME_MARGIN * builtins.SAMPLE_RATE)
        self.__collecting_tail = False
        self.__actual_stimulus = 0
        self.__time = None

        # Contadores
        self.__actual_trial = 0
        self.__actual_sample = 0
        self.__time_receive = 0
        self.__time_send = 0
        self.__eeg_time = 0
        self.__all_marks_added = False
        self.__indicate_finish = False
        self.__waiting_for_last_mark = False

        # Buffers
        self.__buffer = []
        self.__stimulus_mark = []

        # Guardado
        self.__ruta = []
        self.__nombre = "Usuario"
        self.__folder_save = str(Path(self.__base_dir) / "mis_seniales")

        # Filtros
        self.__lowcut = None
        self.__highcut = None
        self.__order = None
        self.__notch = None
        self.__media = None
        self.__bandpass = None
        self.__channels_info = None

        self.update_data(p_user_preferences)

    # ------------------------------------------------------------------
    # Métodos públicos (API)
    # ------------------------------------------------------------------

    def update_data(self, p_user_preferences: UserPreferences = None):
        """Actualiza las preferencias del usuario y recalcula parámetros del entrenamiento.

        Args:
            p_user_preferences (UserPreferences, optional): Nuevas preferencias. Defaults to None.
        """
        if p_user_preferences is None:
            return

        self.__channels = p_user_preferences.channels

        self.__stimulus_use = {}
        index = 0
        for i in range(len(p_user_preferences.stimulus)):
            if p_user_preferences.stimulus_on[i]:
                self.__stimulus_use[index] = p_user_preferences.stimulus[i]
                index += 1

        self.__n_stimulus = len(self.__stimulus_use)
        self.__stimulus_order = list(range(self.__n_stimulus))
        self.__signal_windows_time = p_user_preferences.time_window
        self.__signal_windows_samples = int(self.__signal_windows_time * builtins.SAMPLE_RATE)

    def load_name(self, name: str):
        """Carga el nombre del usuario para identificar la sesión.

        Args:
            name (str): Nombre del usuario.
        """
        self.__nombre = name

    def load_channels_info(self, channels_info):
        """Carga la información descriptiva de los canales EEG.

        Args:
            channels_info: Información de los canales (nombres, ubicaciones, etc.).
        """
        self.__channels_info = channels_info

    def add_filter_data(self, p_data: tuple):
        """Añade los parámetros de configuración de los filtros aplicados.

        Args:
            p_data (tuple): `(lowcut, highcut, order, notch, media, bandpass)`.
        """
        (
            self.__lowcut,
            self.__highcut,
            self.__order,
            self.__notch,
            self.__media,
            self.__bandpass,
        ) = p_data

    def add_sample(self, sample):
        """Añade una nueva muestra EEG al buffer de adquisición.

        Es llamado por el adquirente de señales cada vez que llegan nuevas muestras.

        Args:
            sample: Lista o tupla de muestras multicanal.
        """
        if not self.__add_data:
            return

        if self.__time is None:
            if len(sample) > 1:
                self.__time = time.perf_counter() - (len(sample) - 1) * self.__delta_t
            else:
                self.__time = time.perf_counter()

        self.__update_buffer(sample)

    def add_mark(self, mark: float):
        """Registra la marca temporal del encendido de un estímulo visual.

        Sincroniza la marca con la señal EEG y, al completarse todas las marcas,
        inicia la recolección del margen de cola.

        Args:
            mark (float): Timestamp de `time.perf_counter()` del encendido.
        """
        if not self.__add_data:
            return

        self.__time_receive = mark
        dts = int((self.__time_receive - self.__time_send) / self.__delta_t)
        t_start = self.__eeg_time + self.__delta_t * dts
        self.__stimulus_mark.append((t_start, self.__actual_stimulus))
        self.__mark_count += 1

        if self.__mark_count == self.__n_trials * self.__n_stimulus:
            self.__all_marks_added = True
            self.__collecting_tail = True

            buffer_start_time = self.__buffer[0][0]
            idx_event = math.ceil((t_start - buffer_start_time) / self.__delta_t)
            self.__tail_target_len = (
                idx_event
                + self.__n_discard_samples
                + self.__signal_windows_samples
                + self.__tail_margin_samples
            )

    def start_training(self):
        """Inicia la sesión de entrenamiento.

        Crea la carpeta de guardado, baraja el orden de los estímulos, indica
        el primer estímulo y activa las banderas de adquisición.
        """
        self.__create_folder()
        random.shuffle(self.__stimulus_order)
        self.__indicate_stimulus()
        self.__is_start = True
        self.__add_data = True

    def stop(self):
        """Detiene el entrenamiento y reinicia el estado interno."""
        self.__is_start = False
        self.__buffer = []
        self.__is_finish = False
        self.__actual_stimulus = 0
        self.__actual_trial = 0
        self.__mark_count = 0
        self.__stimulus_mark = []

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def __update_buffer(self, sample):
        """Añade cada canal de la muestra al buffer y actualiza el estado."""
        for channels in zip(*sample):
            self.__update_training_state()
            self.__buffer.append((self.__time, *channels))
            self.__time += self.__delta_t
            self.__actual_sample += 1

    def __update_training_state(self):
        """Máquina de estados del entrenamiento (indicación, estímulo, cola)."""
        if not (self.__is_start and self.__add_data):
            return

        if self.__collecting_tail:
            if (len(self.__buffer) + 1) >= self.__tail_target_len and not self.__is_finish:
                self.__is_finish = True
                self.__add_data = False
                self.__save_data_mat()
            return

        if self.__waiting_for_last_mark:
            return

        if self.__actual_sample >= self.__cue_duration_samples and not self.__indicate_finish:
            self.__indicate_finish = True
            self.stimulus_on.emit()
            self.__actual_sample = 0

        if self.__indicate_finish and self.__actual_sample >= self.__signal_windows_samples:
            self.__actual_sample = 0
            self.__stim_index += 1

            if self.__stim_index >= self.__n_stimulus:
                self.__actual_trial += 1
                self.trial_status.emit(f'Se completó el trial {self.__actual_trial}')
                self.__stim_index = 0
                random.shuffle(self.__stimulus_order)

            total_completed = (self.__actual_trial * self.__n_stimulus) + self.__stim_index
            total_required = self.__n_trials * self.__n_stimulus

            if total_completed >= total_required:
                self.__waiting_for_last_mark = True

            if not self.__waiting_for_last_mark:
                self.__eeg_time = self.__time
                self.__time_send = time.perf_counter()
                self.__indicate_stimulus()
                self.__indicate_finish = False

    def __indicate_stimulus(self):
        """Emite la señal para indicar qué estímulo mostrar a continuación."""
        self.__actual_stimulus = self.__stimulus_order[self.__stim_index]
        self.stimulus_indicate.emit(self.__actual_stimulus)

    def __create_folder(self):
        """Crea la carpeta de destino para guardar la sesión."""
        self.__ruta = f"{self.__folder_save}/{self.__nombre}/"
        ruta = Path(self.__ruta)
        ruta.mkdir(parents=True, exist_ok=True)

    def __save_data_mat(self):
        """Guarda los datos crudos en `.mat` y calcula los pesos TRCA."""
        eeg = np.array(self.__buffer)
        events = np.array(self.__stimulus_mark)
        info = self.__create_info()
        file_name = f"ssvep_{info['nombre']}_{info['fecha']}"

        savemat(self.__ruta + file_name + '.mat', {"eeg": eeg, "events": events, "info": info})

        train_tensor, _ = self.__generate_training_tensor()
        print(f"El tamanio del tensor es: {train_tensor.shape}")
        train_data = {
            'fs': builtins.SAMPLE_RATE,
            'n_channels': len(self.__channels),
            'n_samples': train_tensor.shape[2],
            'n_trials': self.__n_trials,
            'n_stimulus': self.__n_stimulus,
            'n_fbands': builtins.SETTINGS.f_bands,
            'signalWindows': train_tensor,
        }
        training_results = CalculeTRCAWeights.get_weights(train_data, self.__filterbank)
        self.training_finish.emit(training_results)
        self.stop()

    def __create_info(self) -> dict:
        """Construye el diccionario de metadatos para el archivo `.mat`.

        Returns:
            dict: Metadatos de la sesión (nombre, fecha, filtros, estímulos, etc.).
        """
        info = {
            "nombre": self.__nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            "formato_eeg": "timestamp, canal1, ..., canalN",
            "formato_events": "timestamp, estimulo encendido",
            "channels": self.__channels_info,
            "n_trials": self.__n_trials,
            "ventana_de_estimulacion": self.__signal_windows_time,
            "duracion_indicacion_visual_sec": self.__cue_duration_sec,
            "filtros": {
                "lowcut": self.__lowcut,
                "highcut": self.__highcut,
                "order": self.__order,
                "notch": "Activado" if self.__notch else "Desactivado",
                "media": "Activado" if self.__media else "Desactivado",
                "bandpass": "Activado" if self.__bandpass else "Desactivado",
            },
            "estimulos": []
        }

        for i in range(self.__n_stimulus):
            stim = self.__stimulus_use[i]
            info["estimulos"].append({
                "index": i,
                "freq": stim.freq,
                "tipo_de_estimulo": stim.stim_type,
                "forma_de_estimulo": stim.shape_type,
                "direccion": stim.direction if stim.direction is not None else ""
            })
        return info

    def __segment_epochs(self, events_list, filtered_signals, timestamps, n_discard_samples, n_window_samples):
        """Segmenta la señal continua en épocas por estímulo.

        Args:
            events_list (list): Lista de `[timestamp, stim_id]`.
            filtered_signals (np.ndarray): `(n_total_samples, n_channels)`.
            timestamps (np.ndarray): `(n_total_samples,)`.
            n_discard_samples (int): Muestras a descartar al inicio de la época.
            n_window_samples (int): Duración fija de cada época en muestras.

        Returns:
            defaultdict: `{stim_id: list[np.ndarray(n_channels, n_window_samples)]}`.
        """
        epochs_by_stimulus = defaultdict(list)

        for t_start, stim_id in events_list:
            stim_id = int(stim_id)
            idx_event = np.searchsorted(timestamps, t_start)
            idx_start = idx_event + n_discard_samples
            idx_end = idx_start + n_window_samples

            epoch = filtered_signals[idx_start:idx_end, :]
            epochs_by_stimulus[stim_id].append(epoch.T)

        return epochs_by_stimulus

    def __build_tensor(self, epochs_by_stimulus):
        """Construye el tensor 4D de épocas para TRCA.

        Args:
            epochs_by_stimulus (defaultdict): Épocas agrupadas por estímulo.

        Returns:
            tuple: `(tensor, stim_ids)` donde tensor es `(N_stim, n_channels, n_samples, n_trials)`.
        """
        stim_ids = sorted(epochs_by_stimulus.keys())
        n_window_samples = self.__signal_windows_samples

        for stim_id in stim_ids:
            for i, epoch in enumerate(epochs_by_stimulus[stim_id]):
                if epoch.shape[1] < n_window_samples:
                    print(
                        f"[TrainingManager] WARNING: stim_id={stim_id} epoch#{i} "
                        f"shape={epoch.shape} < n_window_samples={n_window_samples}"
                    )

        tensor_list = []
        for stim_id in stim_ids:
            epochs = epochs_by_stimulus[stim_id]
            trimmed_epochs = np.stack([e[:, :n_window_samples] for e in epochs], axis=-1)
            tensor_list.append(trimmed_epochs)

        tensor = np.stack(tensor_list, axis=0)
        return tensor, stim_ids

    def __generate_training_tensor(self):
        """Genera el tensor de entrenamiento desde el buffer almacenado.

        Returns:
            tuple: `(tensor, stim_ids)` para procesamiento TRCA.
        """
        buffer_array = np.array(self.__buffer)
        timestamps = buffer_array[:, 0]
        filtered_signals = buffer_array[:, 1:]

        epochs = self.__segment_epochs(
            self.__stimulus_mark, filtered_signals, timestamps,
            self.__n_discard_samples, self.__signal_windows_samples
        )
        return self.__build_tensor(epochs)

class CalculeTRCAWeights:
    """Implementa el cálculo de pesos Task-Related Component Analysis (TRCA).

    Aplica el algoritmo TRCA para mejorar la detección de respuestas SSVEP,
    según Nakanishi et al. (2018).
    """

    @staticmethod
    def _compute_trca_weights(n_channels: int, n_trials: int, signal: np.ndarray) -> np.ndarray:
        """Calcula los pesos espaciales TRCA para un único estímulo.

        Resuelve el problema de autovalores generalizado `S w = λ Q w`.

        Args:
            n_channels (int): Número de canales EEG.
            n_trials (int): Número de trials del estímulo.
            signal (np.ndarray): `(n_channels, n_samples, n_trials)`.

        Returns:
            np.ndarray: Matriz de pesos `W` de forma `(n_channels, n_channels)`.
        """
        num_smpls = signal.shape[1]

        # Matriz S: covarianza inter-trial
        s = np.zeros((n_channels, n_channels))
        for i in range(n_trials - 1):
            trial1 = signal[:, :, i] - np.mean(signal[:, :, i], axis=1, keepdims=True)
            for j in range(i + 1, n_trials):
                trial2 = signal[:, :, j] - np.mean(signal[:, :, j], axis=1, keepdims=True)
                s += trial1 @ trial2.T + trial2 @ trial1.T

        # Matriz Q: covarianza total
        ux = signal.reshape(n_channels, num_smpls * n_trials)
        ux = ux - np.mean(ux, axis=1, keepdims=True)
        q = ux @ ux.T

        eigvals, eigvecs = eigh(s, q)
        idx = np.argsort(eigvals)[::-1]
        return eigvecs[:, idx]

    @staticmethod
    def _ensembled_TRCA(
        n_stimulus: int,
        n_channels: int,
        n_samples: int,
        n_trials: int,
        n_fbands: int,
        fs_signal: int,
        signalWindows: np.ndarray,
        p_filterbank
    ) -> dict:
        """Calcula los pesos TRCA ensemble para todos los estímulos y bandas.

        Args:
            n_stimulus (int): Cantidad de estímulos diferentes.
            n_channels (int): Cantidad de canales EEG.
            n_samples (int): Muestras por época.
            n_trials (int): Trials por estímulo.
            n_fbands (int): Bandas del filterbank.
            fs_signal (int): Frecuencia de muestreo (Hz).
            signalWindows (np.ndarray): `(n_stimulus, n_channels, n_samples, n_trials)`.
            p_filterbank: Función de filtrado `(signal, fs, idx_fb)`.

        Returns:
            dict: `'trains'`, `'w'`, `'num_fbs'`, `'num_targets'`.
        """
        trains = np.zeros((n_stimulus, n_fbands, n_channels, n_samples))
        ens_w = np.zeros((n_fbands, n_stimulus, n_channels))

        for t in range(n_stimulus):
            eeg_tmp = signalWindows[t, :, :, :].copy()

            for fb in range(n_fbands):
                eeg_filtered = np.zeros_like(eeg_tmp)

                for tri in range(n_trials):
                    eeg_filtered[:, :, tri] = p_filterbank(
                        eeg_tmp[:, :, tri], fs=fs_signal, idx_fb=fb + 1
                    )

                trains[t, fb, :, :] = np.mean(eeg_filtered, axis=2)
                w_tmp = CalculeTRCAWeights._compute_trca_weights(n_channels, n_trials, eeg_filtered)
                ens_w[fb, t, :] = w_tmp[:, 0]

        return {
            'trains': trains,
            'w': ens_w,
            'num_fbs': n_fbands,
            'num_targets': n_stimulus
        }

    @staticmethod
    def get_weights(data: dict, p_filterbank) -> dict:
        """Punto de entrada público para calcular los pesos TRCA ensemble.

        Args:
            data (dict): Diccionario con `'fs'`, `'n_channels'`, `'n_samples'`,
                `'n_trials'`, `'n_stimulus'`, `'n_fbands'`, `'signalWindows'`.
            p_filterbank: Función del banco de filtros.

        Returns:
            dict: Resultado con `'trains'`, `'w'`, `'num_fbs'`, `'num_targets'`.
        """
        return CalculeTRCAWeights._ensembled_TRCA(
            n_stimulus=data['n_stimulus'],
            n_channels=data['n_channels'],
            n_samples=data['n_samples'],
            n_trials=data['n_trials'],
            n_fbands=data['n_fbands'],
            fs_signal=data['fs'],
            signalWindows=data['signalWindows'],
            p_filterbank=p_filterbank
        )

       
