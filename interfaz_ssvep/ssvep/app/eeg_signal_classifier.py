import threading
from typing import Any

import numpy as np
from sklearn.cross_decomposition import CCA

from ssvep.app.dataclasses import UserPreferences


class BaseEEGClassifier:
    """Clase base para clasificadores de señales EEG.

    Proporciona la gestión del búfer de datos, el umbral de decisión y la lógica 
    de validación temporal compartida por clasificadores específicos (como TRCA o CCA).
    Gestiona la concurrencia en el acceso al búfer mediante un `threading.Lock`.
    """

    def __init__(self, buffer_size: int = 100, sample_shape: tuple = (1,)):
        """Inicializa el clasificador base.

        Args:
            buffer_size: Tamaño inicial del búfer en número de muestras.
            sample_shape: Forma de cada muestra individual (por defecto, (1,)).
        """
        self._fs: float | None = None
        self._threshold: float = 0.0
        self._lock = threading.Lock()
        
        self._filterbank: Any = None
        self._n_fbands: int | None = None
        self._n_targets: int | None = None
        self._target_labels: list[int] | None = None

        self._buffer = np.zeros((buffer_size, *sample_shape))
        self._class_buffer = [-1, -1, -1, -1]
        self._index = 0
        self._samples_count = 0
        
        self._time_window: float = 0.0 
        self._samples_per_step: int = 0 
        self._s_steps_count: int = 0 

    def clear_buffer(self) -> None:
        """Limpia el búfer de datos y reinicia los contadores de manera segura."""
        with self._lock:
            self._buffer = np.zeros(self._buffer.shape)
            self._samples_count = 0
            self._class_buffer = [-1, -1, -1, -1]
            self._index = 0
            self._s_steps_count = 0

    def load_buffer_size(self, time_window: float, n_channels: int) -> None:
        """Configura el tamaño del búfer en función de la ventana de tiempo y canales.

        Args:
            time_window: Duración de la ventana de tiempo en segundos.
            n_channels: Número de canales de la señal EEG.
        """
        with self._lock:
            self._time_window = time_window
            if self._fs is None:
                raise ValueError("La frecuencia de muestreo (_fs) debe establecerse antes de cargar el tamaño del búfer.")
            
            n_samples = int(time_window * self._fs)
            self._buffer = np.zeros((n_samples, n_channels))
            self._samples_count = 0 
            self._recalculate_steps_under_lock()

    def load_threshold(self, threshold: float) -> None:
        """Establece el umbral de confianza para la validación de la clasificación.

        Args:
            threshold: Valor del umbral. Si es <= 0, se desactiva la validación por ventana móvil.
        """
        with self._lock:
            self._threshold = threshold
            self._recalculate_steps_under_lock()

    def _recalculate_steps_under_lock(self) -> None:
        """Reconfigura el paso de procesamiento según si el umbral está activo o no.
        
        Debe llamarse dentro de un bloque `with self._lock:`.
        """
        if self._fs and self._time_window > 0:
            if self._threshold > 0:
                # Ventanas móviles (pasos del 25% para votación)
                self._samples_per_step = int((self._time_window / 4.0) * self._fs)
            else:
                # Bloque completo del 100% de la ventana
                self._samples_per_step = int(self._time_window * self._fs)
            self._s_steps_count = 0

    def load_filterbank(self, filterbank: Any) -> None:
        """Establece la función o objeto de filtrado por bandas.

        Args:
            filterbank: Callable u objeto que aplica el filtrado por banda.
        """
        self._filterbank = filterbank

    def set_target_labels(self, target_labels: list[int]) -> None:
        """Establece la traducción de posición interna a índice real de estímulo.

        Internamente (en `classify_signal`), cada objetivo se identifica por su
        posición (0..N-1) entre los estímulos activos. Esa posición no coincide
        con el índice real del estímulo en `Settings` cuando los estímulos
        activos no son exactamente los primeros N (ej: solo están activos los
        estímulos 2 y 4). `target_labels[posicion]` debe dar el índice real
        correspondiente, de forma que `classify_signal` devuelva siempre índices
        reales de estímulo, comparables con la secuencia de `BCIEvaluator`.

        Args:
            target_labels: Lista donde `target_labels[i]` es el índice real del
                estímulo que ocupa la posición `i` entre los activos.
        """
        self._target_labels = target_labels

    def _validate_threshold(self, rho: np.ndarray) -> int:
        """Valida las correlaciones (rho) contra el umbral configurado.

        Args:
            rho: Array de valores de correlación o puntuación para cada objetivo.

        Returns:
            int: El ID del estímulo clasificado, -1 si no se alcanza el umbral,
                 o el de mayor valor si el umbral es 0.
        """
        rho = np.asarray(rho)
        stim_id = int(np.argmax(rho))
        if self._target_labels is not None:
            stim_id = self._target_labels[stim_id]

        if self._threshold <= 0:
            return stim_id
            
        max_rho = np.max(rho)
        min_rho = np.min(rho)
        denominator = np.sum(rho) - min_rho
        
        if denominator <= 0:
            with self._lock:
                self._class_buffer[self._index] = -1
                self._index = (self._index + 1) % len(self._class_buffer)
            return -1
            
        sum_rho = (max_rho - min_rho) / denominator
        
        if sum_rho >= self._threshold:
            with self._lock:
                self._class_buffer[self._index] = stim_id
                self._index = (self._index + 1) % len(self._class_buffer)
                
                for candidate_stim in set(self._class_buffer):
                    if candidate_stim != -1 and self._class_buffer.count(candidate_stim) >= 3:
                        return int(candidate_stim)
                return -1
        else:
            with self._lock:
                self._class_buffer[self._index] = -1
                self._index = (self._index + 1) % len(self._class_buffer)
            return -1

    def update_buffer(self, sample: np.ndarray) -> int:
        """Actualiza el búfer con nuevas muestras y procesa si se alcanza el paso requerido.

        Args:
            sample: Nuevas muestras de señal EEG a añadir al búfer.

        Returns:
            int: ID del estímulo clasificado, -1 (no válido), -2 (búfer no lleno) o 
                 -3 (en proceso de acumulación de pasos para votación).
        """
        buffer_to_process = None
        
        # Transponer si la forma coincide con los canales pero no con las muestras
        if sample.ndim > 1 and sample.shape[0] == self._buffer.shape[1]:
            sample = sample.T
            
        n_new_samples = sample.shape[0]

        with self._lock:
            self._buffer[:-n_new_samples] = self._buffer[n_new_samples:]
            self._buffer[-n_new_samples:] = sample
            self._samples_count += n_new_samples 
            
            if self._samples_per_step > 0 and self._samples_count >= self._samples_per_step:
                self._samples_count = 0
                self._s_steps_count += 1 
                buffer_to_process = self._buffer.copy().T 
        
        if buffer_to_process is not None:
            raw_decision = self.classify_signal(buffer_to_process)
            
            if self._threshold <= 0:
                return raw_decision
            
            if self._s_steps_count >= 4:
                self._s_steps_count = 0 
                return raw_decision 
            
            return -3
            
        return -2

    def classify_signal(self, signal_windows: np.ndarray) -> int:
        """Método abstracto para clasificar una ventana de señal.
        
        Debe ser implementado por las clases hijas.

        Args:
            signal_windows: Ventana de señal EEG a clasificar.

        Returns:
            int: ID del estímulo clasificado.
        """
        raise NotImplementedError("Las clases hijas deben implementar el método classify_signal.")


class EEGSignalTRCAClassifier(BaseEEGClassifier):
    """Clasificador EEG basado en Task-Related Component Analysis (TRCA).

    Utiliza pesos preentrenados y plantillas de entrenamiento para maximizar 
    la correlación entre la señal de prueba y los componentes relacionados con la tarea.

    References:
        M. Nakanishi, Y. Wang, X. Chen, Y.-T. Wang, X. Gao, y T.-P. Jung, 
        «Enhancing Detection of SSVEPs for a High-Speed Brain Speller Using 
        Task-Related Component Analysis», *IEEE Trans. Biomed. Eng.*, vol. 65, 
        n.o 1, pp. 104-112, ene. 2018, doi: 10.1109/TBME.2017.2694818.
    """

    def __init__(self):
        """Inicializa el clasificador TRCA."""
        super().__init__()
        self._ensembled_weights: np.ndarray | None = None
        self._train_prom: np.ndarray | None = None
        self._training_ready = False
        
    def load_data(
        self,
        fs_signal: float,
        data: dict,
        n_channels: int,
        time_windows: float,
        target_labels: list[int],
    ) -> None:
        """Carga los datos de entrenamiento y configura el clasificador.

        Args:
            fs_signal: Frecuencia de muestreo de la señal.
            data: Diccionario con las claves 'w' (pesos), 'num_fbs' (bandas),
                  'trains' (plantillas) y 'num_targets' (objetivos).
            n_channels: Número de canales de la señal.
            time_windows: Duración de la ventana de tiempo en segundos.
            target_labels: Índices reales de estímulo, en el mismo orden en que
                fueron entrenados (posición i -> índice real del estímulo i-ésimo
                activo). Ver `set_target_labels`.
        """
        self._ensembled_weights = data['w'].transpose(0, 2, 1)
        self._n_fbands = data['num_fbs']
        self._train_prom = data['trains'].transpose(0, 1, 3, 2)
        self._fs = fs_signal
        self._n_targets = data['num_targets']
        self.set_target_labels(target_labels)

        self.load_buffer_size(time_windows, n_channels)
        self._training_ready = True
 
    def classify_signal(self, signal_windows: np.ndarray) -> int:
        """Clasifica la ventana de señal utilizando el algoritmo TRCA.

        Args:
            signal_windows: Ventana de señal EEG a clasificar (forma: canales x muestras).

        Returns:
            int: ID del estímulo clasificado o -1 si no está entrenado.
        """
        if not self._training_ready or self._ensembled_weights is None or self._train_prom is None:
            return -1
        
        r = np.zeros((self._n_fbands, self._n_targets))
        fb_coefs = (np.arange(1, self._n_fbands + 1) ** (-1.25)) + 0.25
        signal_windows_filt = np.zeros((self._n_fbands, *signal_windows.shape))
        
        for fba in range(self._n_fbands):
            signal_windows_filt[fba, :, :] = self._filterbank(signal_windows, self._fs, fba + 1)
            
        for fb in range(self._n_fbands):
            signal_test = signal_windows_filt[fb, :, :].T 
            W = self._ensembled_weights[fb, :, :]        
            A = signal_test @ W                           
            
            for target in range(self._n_targets):         
                x_prom = self._train_prom[target, fb, :, :] 
                B = x_prom @ W                          
                
                R = np.corrcoef(A.ravel(), B.ravel(), rowvar=False)
                r[fb, target] = R[0, 1]
        
        rho = fb_coefs @ (r ** 2)
        return self._validate_threshold(rho)


class EEGSignalCCAClassifier(BaseEEGClassifier):
    """Clasificador EEG basado en Canonical Correlation Analysis (CCA).

    Genera señales de referencia basadas en armónicos de las frecuencias de los 
    estímulos y calcula la correlación canónica con la señal EEG de prueba.
    """

    def __init__(self):
        """Inicializa el clasificador CCA."""
        super().__init__()
        self._n_harmonics: int | None = None
        self._reference_signals: dict[int, np.ndarray] = {}
        self._cca = CCA(n_components=1)
        
    def load_data(self, fs_signal: float, data: UserPreferences, harmonics: int) -> None:
        """Carga las preferencias del usuario y genera las señales de referencia.

        Args:
            fs_signal: Frecuencia de muestreo de la señal.
            data: Objeto UserPreferences con la configuración de estímulos y canales.
            harmonics: Número de armónicos a considerar para la generación de referencias.
        """
        self._fs = fs_signal
        self._n_harmonics = harmonics
        
        n_channels = len(data.channels)
        self.load_buffer_size(data.time_window, n_channels)
        
        t = np.linspace(0, self._time_window, int(self._fs * self._time_window), endpoint=False)
        
        for stim_index, stim in enumerate(data.stimulus):
            if data.stimulus_on[stim_index]:
                references = []
                for harmonic in range(1, self._n_harmonics + 1):
                    n_harmonic = stim.freq * harmonic
                    references.append(np.sin(2 * np.pi * n_harmonic * t))
                    references.append(np.cos(2 * np.pi * n_harmonic * t))
                
                self._reference_signals[stim_index] = np.array(references).T

        self.set_target_labels(list(self._reference_signals.keys()))

    def classify_signal(self, signal_windows: np.ndarray) -> int:
        """Clasifica la ventana de señal utilizando el algoritmo CCA.

        Args:
            signal_windows: Ventana de señal EEG a clasificar (forma: canales x muestras).

        Returns:
            int: ID del estímulo clasificado.
        """
        keys = list(self._reference_signals.keys())
        signal_t = signal_windows.T 
        coefficients = np.zeros(len(keys))
        
        for i, key in enumerate(keys):
            self._cca.fit(signal_t, self._reference_signals[key])
            eeg_res, ref_res = self._cca.transform(signal_t, self._reference_signals[key])
            
            # Calcular correlación entre los primeros componentes canónicos
            r = np.corrcoef(eeg_res[:, 0], ref_res[:, 0])[0, 1]
            coefficients[i] = r

        return self._validate_threshold(coefficients) 