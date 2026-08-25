
import threading
from typing import Optional

import numpy as np
import builtins
from scipy.signal import welch
from PySide6.QtCore import QObject, Signal


class PSDEstimator(QObject):
    """
    Estimador de Densidad Espectral de Potencia (PSD) utilizando el método de Welch.

    Gestiona un buffer de muestras de señal, aplica ventanas de Hann y calcula la PSD
    en intervalos configurables. Los resultados se emiten a través de una señal de Qt.

    Signals:
        psd_ready (tuple): Señal que emite `(freqs, power)` cuando el cálculo de la PSD está listo.
            - `freqs` (numpy.ndarray): Array de frecuencias.
            - `power` (numpy.ndarray): Array de densidades espectrales de potencia.
    """

    psd_ready = Signal(object, object)

    BUFFER_TIME_WINDOW: float = 4.5  # Segundos, fijo, no cambia en runtime
    MIN_TIME_WINDOW: float = 1.0
    MAX_TIME_WINDOW: float = 4.0

    def __init__(self) -> None:
        """Inicializa el estimador PSD con los parámetros por defecto."""
        super().__init__()

        self.__sample_rate: float = builtins.SAMPLE_RATE

        # Configuración de ventana y paso de cálculo
        self.__time_windows_welch: float = 1.0  # Segundos, cantidad que se toma del buffer
        self.__windows_welch: int = int(self.__time_windows_welch * self.__sample_rate)
        self.__step_size: int = int(1.0 * self.__sample_rate)  # Muestras nuevas entre cada cálculo

        # Buffer y estado del canal
        self.__buffer: Optional[np.ndarray] = None
        self.__buffer_size: Optional[tuple[int, int]] = None  # (n_channels, n_samples)
        self.__channel_index: int = 0

        # Parámetros de Welch
        self.__overlap: int = self.__windows_welch // 2
        self.__han_window: np.ndarray = np.hanning(self.__windows_welch)

        # Control de concurrencia y estado
        self.__lock = threading.Lock()
        self.__samples_since_calc: int = 0
        self.__started: bool = False
        self.__is_processing: bool = False

        # Cambios pendientes para aplicar después del procesamiento
        self.__pending_time_window: Optional[float] = None
        self.__pending_overlap: Optional[int] = None

        # Configuración de escala de amplitud
        self.__amplitude_unit: int = 1  # 0: mV, 1: µV, 2: nV
        self.__amplitude_factors: dict[int, float] = {
            0: 1e-3,  # µV -> mV
            1: 1.0,   # µV -> µV
            2: 1e3    # µV -> nV
        }

    # =========================================================================
    # Configuración Pública
    # =========================================================================

    def load_buffer_size(self, n_channels: int) -> None:
        """
        Inicializa o reinicializa el tamaño del buffer.

        El buffer siempre guarda `BUFFER_TIME_WINDOW` (4.5s) de muestras.

        Args:
            n_channels: Número de canales de la señal.
        """
        n_samples = int(self.BUFFER_TIME_WINDOW * self.__sample_rate)
        with self.__lock:
            self.__buffer_size = (n_channels, n_samples)
            self.__buffer = np.zeros(self.__buffer_size)
            self.__samples_since_calc = 0
            if self.__channel_index >= n_channels:
                self.__channel_index = 0

    def load_calc_interval(self, time_step: float) -> None:
        """
        Define cada cuánto tiempo (en segundos) se dispara un cálculo de Welch.

        Args:
            time_step: Intervalo de tiempo en segundos (se acota entre 1.0 y 4.0s).

        Raises:
            RuntimeError: Si se intenta modificar después de haber iniciado el procesamiento.
        """
        if self.__started:
            raise RuntimeError("Ya iniciado, no se puede cambiar el intervalo de cálculo.")
        time_step = max(self.MIN_TIME_WINDOW, min(self.MAX_TIME_WINDOW, time_step))
        self.__step_size = int(time_step * self.__sample_rate)

    def load_time_windows(self, time_windows: float) -> None:
        """
        Define la cantidad de tiempo (en segundos) que se toma del buffer para calcular la PSD.

        Este valor se puede cambiar en runtime. Si hay un procesamiento en curso,
        el cambio se aplica de forma pendiente al finalizar el cálculo actual.

        Args:
            time_windows: Longitud de la ventana de tiempo en segundos (se acota entre 1.0 y 4.0s).
        """
        if self.__is_processing:
            self.__pending_time_window = time_windows
        else:
            self.__update_time_window(time_windows)

    def load_overlap(self, overlap: int) -> None:
        """
        Define el solapamiento (overlap) para el cálculo de Welch.

        Si hay un procesamiento en curso, el cambio se aplica de forma pendiente
        al finalizar el cálculo actual.

        Args:
            overlap: Cantidad de muestras de solapamiento.
        """
        if self.__is_processing:
            self.__pending_overlap = overlap
        else:
            self.__overlap = overlap

    def set_channel_index(self, channel_index: int) -> None:
        """
        Establece el índice del canal que se utilizará para el cálculo de la PSD.

        Args:
            channel_index: Índice del canal en el buffer.
        """
        self.__channel_index = channel_index

    def load_amplitude_unit(self, unit: int) -> None:
        """
        Define la unidad de amplitud de salida para la PSD.

        Args:
            unit: Código de la unidad (0: mV, 1: µV, 2: nV).

        Raises:
            ValueError: Si la unidad no es 0, 1 o 2.
        """
        with self.__lock:
            if unit in (0, 1, 2):
                self.__amplitude_unit = unit
            else:
                raise ValueError("Unidad de amplitud inválida. Use 0 (mV), 1 (µV) o 2 (nV).")

    # =========================================================================
    # Métodos Internos de Configuración
    # =========================================================================

    def __update_time_window(self, time_windows: float) -> None:
        """
        Actualiza internamente los parámetros de la ventana de tiempo para Welch.

        Args:
            time_windows: Longitud de la ventana en segundos.
        """
        time_windows = max(self.MIN_TIME_WINDOW, min(self.MAX_TIME_WINDOW, time_windows))
        n_samples = int(time_windows * self.__sample_rate)

        self.__time_windows_welch = time_windows
        self.__windows_welch = n_samples
        self.__han_window = np.hanning(self.__windows_welch)

    # =========================================================================
    # Procesamiento de Señal
    # =========================================================================

    def add_sample(self, sample: np.ndarray) -> None:
        """
        Añade nuevas muestras al buffer y evalúa si es momento de calcular la PSD.

        Args:
            sample: Array numpy de nuevas muestras con forma `(n_channels, n_samples)`.
        """
        data = np.asarray(sample)

        with self.__lock:
            self.__started = True
            self.__update_buffer(data)
            self.__samples_since_calc += data.shape[1]

            ready = self.__samples_since_calc >= self.__step_size
            if ready:
                ch = self.__channel_index
                # Copiamos los datos para evitar condiciones de carrera durante el cálculo
                samples = self.__buffer[ch, -self.__windows_welch:].copy()
                self.__samples_since_calc = 0

        if ready:
            self.__welch_psd(samples)

    def __update_buffer(self, sample: np.ndarray) -> None:
        """
        Actualiza el buffer circular con las nuevas muestras.

        Args:
            sample: Array numpy de nuevas muestras con forma `(n_channels, n_samples)`.
        """
        _, n_new = sample.shape  # '_' reemplaza a 'n_ch' ya que no se utilizaba
        if n_new == 0:
            return

        buffer_len = self.__buffer.shape[1]

        if n_new >= buffer_len:
            self.__buffer[:] = sample[:, -buffer_len:]
        else:
            self.__buffer[:, :-n_new] = self.__buffer[:, n_new:]
            self.__buffer[:, -n_new:] = sample

    def clear_buffer(self) -> None:
        """Limpia el buffer y reinicia el contador de muestras desde el último cálculo."""
        with self.__lock:
            if self.__buffer is not None:
                self.__buffer[:] = 0
            self.__samples_since_calc = 0

    def __welch_psd(self, samples: np.ndarray) -> None:
        """
        Calcula y emite la Densidad Espectral de Potencia (PSD) para las muestras dadas.

        Args:
            samples: Array 1D de muestras del canal seleccionado.
        """
        self.__is_processing = True

        scale_factor = self.__amplitude_factors.get(self.__amplitude_unit, 1.0)
        scaled_samples = samples * scale_factor

        freqs, power = welch(
            scaled_samples,
            fs=self.__sample_rate,
            nperseg=self.__windows_welch,
            noverlap=self.__overlap,
            window=self.__han_window.copy(),
        )

        self.psd_ready.emit(freqs, power)

        self.__is_processing = False
        self.__apply_pending_changes()

    def __apply_pending_changes(self) -> None:
        """Aplica cualquier cambio de configuración que haya quedado pendiente durante el procesamiento."""
        if self.__pending_time_window is not None:
            self.__update_time_window(self.__pending_time_window)
            self.__pending_time_window = None

        if self.__pending_overlap is not None:
            self.__overlap = self.__pending_overlap
            self.__pending_overlap = None

    def stop(self) -> None:
        """
        Detiene el procesamiento, limpia el buffer y reinicia todos los estados internos.
        """
        with self.__lock:
            self.__started = False
            self.__buffer = None
            self.__buffer_size = None
            self.__samples_since_calc = 0
            self.__pending_time_window = None
            self.__pending_overlap = None
            self.__is_processing = False
