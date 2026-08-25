import builtins
from typing import List, Optional, Tuple

import numpy as np
from scipy.signal import (
    butter, bessel, cheby1,
    iirnotch, tf2sos,
    sosfilt, sosfilt_zi, sosfiltfilt, buttord
)


class SignalFilters:
    """
    Procesador de señales EEG para aplicaciones en tiempo real.

    Gestiona el filtrado de señales multicanal utilizando un buffer circular,
    filtro de media móvil, filtro notch (para ruido de red) y filtro pasa-bandas.
    También incluye soporte para Filterbank (descomposición en sub-bandas).
    """

    def __init__(self) -> None:
        """
        Inicializa el procesador de EEG con valores por defecto.
        
        Las frecuencias de muestreo y número de bandas se obtienen automáticamente
        de las variables globales `builtins.SAMPLE_RATE` y `builtins.SETTINGS.f_bands`.
        """
        # --- Parámetros del sistema ---
        self.__fs: float = float(builtins.SAMPLE_RATE)
        self.__n_fbands: int = int(builtins.SETTINGS.f_bands)
        self.__n_channels: Optional[int] = None
        self.__configure_ready: bool = False

        # --- Parámetros del filtro pasa-bandas ---
        self.__lowcut: float = 1.0
        self.__highcut: float = 100.0
        self.__low_freq: Optional[float] = None
        self.__order: int = 6
        self.__filter_type: str = 'butter'  # 'butter', 'bessel', 'cheb'
        self.__rp_bp: float = 0.3            # Ripple en banda de paso (solo Chebyshev)
        
        self.__bandpass_enabled: Optional[bool] = None
        self.__sosband: Optional[np.ndarray] = None
        self.__ziband: Optional[List[np.ndarray]] = None
        
        # Variables para Filterbank
        self.__passband: Optional[np.ndarray] = None
        self.__stopband: Optional[np.ndarray] = None

        # --- Parámetros del filtro notch ---
        self.__notch_enabled: Optional[bool] = None
        self.__f0: float = 50.0      # Frecuencia a atenuar (Hz)
        self.__fcalidad: float = 30.0 # Factor de calidad
        self.__sosnotch: Optional[np.ndarray] = None
        self.__zinotch: Optional[List[np.ndarray]] = None
        
        # --- Parámetros del filtro de media (DC offset removal) ---
        self.__media_enabled: Optional[bool] = None
        self.__samples_media: int = 100
        self.__buffer: Optional[np.ndarray] = None

    # =========================================================================
    # Interfaz Pública: Configuración
    # =========================================================================

    def add_parameters(
        self,
        order: Optional[int] = None,
        low_freq: Optional[float] = None,
        high_freq: Optional[float] = None,
        notch_enabled: Optional[bool] = None,
        media_enabled: Optional[bool] = None,
        bandpass_enabled: Optional[bool] = None,
        filter_type: Optional[str] = None
    ) -> None:
        """
        Configura o actualiza los parámetros de los filtros.

        Args:
            order: Orden del filtro pasa-bandas.
            low_freq: Frecuencia de corte inferior del filtro pasa-bandas.
            high_freq: Frecuencia de corte superior del filtro pasa-bandas
            notch_enabled: Habilita o deshabilita el filtro notch.
            media_enabled: Habilita o deshabilita la sustracción de media (DC).
            bandpass_enabled: Habilita o deshabilita el filtro pasa-bandas.
            filter_type: Tipo de filtro ('butter', 'bessel', 'cheb').
        """
        if high_freq is not None and low_freq is not None:
            self.__low_freq = low_freq
            self.__highcut = (high_freq * self.__n_fbands) + 3.0
            self.__lowcut = max(0.5, low_freq - 3.0)  # Evita frecuencias <= 0

        if order is not None:
            self.__order = order
        if notch_enabled is not None:
            self.__notch_enabled = notch_enabled
        if media_enabled is not None:
            self.__media_enabled = media_enabled
        if bandpass_enabled is not None:
            self.__bandpass_enabled = bandpass_enabled
        if filter_type is not None and filter_type in ('butter', 'bessel', 'cheb'):
            self.__filter_type = filter_type

        self.__configure_filters()

    def get_parameters(self) -> Tuple[float, float, int, Optional[bool], Optional[bool], Optional[bool]]:
        """
        Obtiene los parámetros actuales de configuración del filtrado.

        Returns:
            Tupla con: (lowcut, highcut, order, notch_enabled, media_enabled, bandpass_enabled).
        """
        return (
            self.__lowcut, 
            self.__highcut, 
            self.__order, 
            self.__notch_enabled, 
            self.__media_enabled, 
            self.__bandpass_enabled
        )

    def stop(self) -> None:
        """
        Detiene el procesamiento y limpia los estados internos (buffers y estados de filtro).
        """
        self.__n_channels = None
        self.__buffer = None
        self.__ziband = None
        self.__zinotch = None
        self.__configure_ready = False

    # =========================================================================
    # Interfaz Pública: Procesamiento de Señal
    # =========================================================================

    def eeg_stream_filter(self, sample: List[List[float]] | np.ndarray) -> np.ndarray:
        """
        Procesa un bloque de muestras de EEG a través de la cadena de filtros configurada.

        Args:
            sample: Datos de entrada con forma `(n_channels, n_samples)`.

        Returns:
            Array numpy con las muestras filtradas. Retorna array vacío si la entrada está vacía.

        Raises:
            ValueError: Si se llama antes de configurar los parámetros con `add_parameters`.
        """
        if not self.__configure_ready:
            raise ValueError("Primero se deben cargar los parámetros del filtro usando add_parameters()")

        data = self.__list_array(sample)
        
        if data.shape[1] == 0:
            return np.array([], dtype=np.float64)  # Retorna array vacío para no romper el flujo
        
        # Inicialización del buffer en la primera ejecución
        if self.__n_channels is None:
            self.__n_channels = data.shape[0]
            self.__buffer = np.zeros((self.__n_channels, self.__samples_media), dtype=np.float64)
            
        self.__update_buffer(data)
        
        # Cadena de filtrado
        y = self.__media_filter(data, self.__media_enabled)
        y = self.__notch_filter(y, self.__notch_enabled)
        y = self.__bandpass_filter(y, self.__bandpass_enabled)
                
        return y

    def filterbank(self, eeg: np.ndarray, fs: Optional[float] = None, idx_fb: int = 1) -> np.ndarray:
        """
        Diseña y aplica un filtro de una sub-banda específica (Filterbank).

        Basado en: X. Chen et al., "Filter bank canonical correlation analysis for 
        implementing a high-speed SSVEP-based brain-computer interface", J. Neural Eng., 2015.

        Args:
            eeg: Datos EEG de entrada con forma `(num_channels, data_length)`.
            fs: Frecuencia de muestreo. Si es None, usa la configurada en la instancia.
            idx_fb: Índice del filtro en el banco (1 a `n_fbands`).

        Returns:
            Datos EEG filtrados en la sub-banda especificada.

        Raises:
            ValueError: Si `idx_fb` está fuera del rango válido.
        """
        if self.__passband is None or self.__stopband is None:
            raise RuntimeError("El filtro no está configurado. Llama a add_parameters() primero.")
            
        if idx_fb < 1 or idx_fb > self.__n_fbands:
            raise ValueError(f"idx_fb debe estar entre 1 y {self.__n_fbands} (inclusive).")

        current_fs = fs if fs is not None else self.__fs
        num_chans, data_len = eeg.shape
        nyq = current_fs / 2.0

        # Normalizar frecuencias a Nyquist
        Wp = [self.__passband[idx_fb - 1] / nyq, 90.0 / nyq]
        Ws = [self.__stopband[idx_fb - 1] / nyq, 100.0 / nyq]

        # Diseñar orden y corte del filtro Butterworth
        N, Wn = buttord(Wp, Ws, 3, 40)  # 3 dB ripple en banda de paso, 40 dB atenuación en banda de rechazo

        # Usar representación SOS para estabilidad numérica
        sos = butter(N, Wn, btype='band', output='sos', fs=current_fs)

        # Calcular longitud de relleno (padlen) de forma segura para sosfiltfilt
        n_sections = sos.shape[0]
        padlen = 3 * (2 * n_sections - 1)
        if padlen >= data_len:
            padlen = max(0, data_len - 1)
        if padlen == 0:
            padlen = None

        # Aplicar filtrado de fase cero a cada canal
        y = np.zeros_like(eeg, dtype=np.float64)
        for ch_i in range(num_chans):
            y[ch_i, :] = sosfiltfilt(sos, eeg[ch_i, :], padtype='odd', padlen=padlen)

        return y

    # =========================================================================
    # Lógica Interna: Diseño de Filtros
    # =========================================================================

    def __configure_filters(self) -> None:
        """Diseña los coeficientes de los filtros (SOS) según los parámetros actuales."""
        if self.__low_freq is None:
            self.__low_freq = self.__lowcut

        wn = [self.__lowcut, self.__highcut]
        if self.__lowcut >= self.__highcut:
            raise ValueError("lowcut debe ser estrictamente menor que highcut")

        # 1. Filtro Pasa-bandas
        if self.__filter_type == 'bessel':
            self.__sosband = bessel(self.__order, wn, btype='bandpass', analog=False, output='sos', norm='phase', fs=self.__fs)
        elif self.__filter_type == 'cheb':
            self.__sosband = cheby1(self.__order, self.__rp_bp, wn, btype='bandpass', analog=False, output='sos', fs=self.__fs)
        else:  # 'butter' por defecto
            self.__sosband = butter(self.__order, wn, btype='bandpass', analog=False, output='sos', fs=self.__fs)
        
        # 2. Filtro Notch
        b, a = iirnotch(self.__f0, self.__fcalidad, self.__fs)
        self.__sosnotch = tf2sos(b, a)
        
        # 3. Configuración para Filterbank
        passband_list = [self.__low_freq * (1 + i) - 2.0 for i in range(self.__n_fbands)]
        stopband_list = [self.__low_freq * (i + 1) - 3.0 for i in range(self.__n_fbands)]
        
        self.__passband = np.array(passband_list)
        self.__stopband = np.array(stopband_list)
        
        self.__configure_ready = True

    # =========================================================================
    # Lógica Interna: Aplicación de Filtros
    # =========================================================================

    def __bandpass_filter(self, sample: np.ndarray, apply: Optional[bool]) -> np.ndarray:
        """Aplica el filtro pasa-bandas con estado (para continuidad en tiempo real)."""
        if not apply or self.__sosband is None:
            return sample
                        
        if self.__ziband is None or len(self.__ziband) != self.__n_channels:
            self.__ziband = [sosfilt_zi(self.__sosband) for _ in range(self.__n_channels)]

        # Filtrar canal por canal manteniendo el estado
        filtered_sample = np.zeros_like(sample)
        for ch in range(self.__n_channels):
            filtered_sample[ch], self.__ziband[ch] = sosfilt(self.__sosband, sample[ch], zi=self.__ziband[ch])

        return filtered_sample
    
    def __media_filter(self, sample: np.ndarray, apply: Optional[bool]) -> np.ndarray:
        """Elimina el componente de corriente continua (DC) restando la media del buffer."""
        if not apply or self.__buffer is None:
            return sample
            
        return sample - self.__buffer.mean(axis=1, keepdims=True)
    
    def __notch_filter(self, sample: np.ndarray, apply: Optional[bool]) -> np.ndarray:
        """Aplica el filtro notch con estado (para continuidad en tiempo real)."""
        if not apply or self.__sosnotch is None:
            return sample
            
        if self.__zinotch is None or len(self.__zinotch) != self.__n_channels:
            self.__zinotch = [sosfilt_zi(self.__sosnotch) for _ in range(self.__n_channels)]
            
        filtered_sample = np.zeros_like(sample)
        for ch in range(self.__n_channels):
            filtered_sample[ch], self.__zinotch[ch] = sosfilt(self.__sosnotch, sample[ch], zi=self.__zinotch[ch])
            
        return filtered_sample

    # =========================================================================
    # Lógica Interna: Gestión de Datos
    # =========================================================================

    def __update_buffer(self, sample: np.ndarray) -> None:
        """
        Actualiza el buffer circular con las nuevas muestras.
        
        Args:
            sample: Nuevas muestras con forma `(n_channels, n_samples)`.
        """
        _, n_new = sample.shape
        if n_new == 0 or self.__buffer is None:
            return
            
        buffer_len = self.__buffer.shape[1]

        if n_new >= buffer_len:
            # Si llegan más muestras que el tamaño del buffer, sobrescribir con las últimas
            self.__buffer[:] = sample[:, -buffer_len:]
        else:
            # Desplazar hacia la izquierda e insertar las nuevas al final
            self.__buffer[:, :-n_new] = self.__buffer[:, n_new:]
            self.__buffer[:, -n_new:] = sample
    
    def __list_array(self, sample: List | np.ndarray) -> np.ndarray:
        """Convierte la entrada a un array numpy de tipo float64 de forma segura."""
        return np.asarray(sample, dtype=np.float64)