import numpy as np
import pyqtgraph as pg
from typing import List, Optional

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout


UPDATE_INTERVAL_MS: int = 40     # 25 FPS
EMA_ALPHA: float = 0.2           # Factor de suavizado temporal (Exponential Moving Average)


class PSDWidget(QWidget):
    """
    Widget para graficar la Densidad Espectral de Potencia (PSD) en tiempo real.

    Gestiona la recepción de datos de frecuencia y potencia, aplica modos de 
    visualización (Absoluto, dB, Normalizado), suavizado temporal (EMA) y 
    marcadores de frecuencias objetivo.

    Attributes:
        __display_mode (int): Modo de visualización (0: Absoluto, 1: dB, 2: Normalizado).
        __amplitude_unit (int): Unidad de amplitud de los datos de entrada (0: mV, 1: µV, 2: nV).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Inicializa el widget de graficado de PSD.

        Args:
            parent: Widget padre opcional.
        """
        super().__init__(parent)

        # Datos de la señal
        self.__freqs: Optional[np.ndarray] = None
        self.__raw_psd: Optional[np.ndarray] = None       # PSD tal cual llega (ya escalada externamente)
        self.__psd: Optional[np.ndarray] = None           # PSD procesada según el modo de visualización
        self.__smooth_psd: Optional[np.ndarray] = None    # PSD con suavizado EMA aplicado

        # Elementos gráficos de marcadores
        self.__freq_markers: List[pg.InfiniteLine] = []
        self.__freq_labels: List[pg.TextItem] = []
        
        # Estados de visualización
        self.__display_mode: int = 0  # 0: Absoluto, 1: dB, 2: Normalizado
        self.__amplitude_unit: int = 1  # 0: mV²/Hz, 1: µV²/Hz, 2: nV²/Hz (Por defecto µV²/Hz)

        # Configuración del gráfico
        self.__setup_plot()

        # Timer de actualización
        self.__timer = QTimer(self)
        self.__timer.timeout.connect(self.__update_plot)
        self.__timer_running: bool = False

        # Inicialmente deshabilitado hasta que se le indique lo contrario
        self.setEnabled(False)

    # =========================================================================
    # Configuración Inicial del Gráfico
    # =========================================================================

    def __setup_plot(self) -> None:
        """Configura el layout, el PlotWidget de pyqtgraph y los estilos iniciales de los ejes."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.__plot_widget = pg.PlotWidget()
        layout.addWidget(self.__plot_widget)

        plot = self.__plot_widget

        # Desactivar prefijos automáticos del eje Y (evita que invente kV, GV, etc.)
        plot.getAxis("left").enableAutoSIPrefix(False)

        # Configuración de etiquetas de ejes
        plot.setLabel("bottom", "Frecuencia", units="Hz")
        self.__update_y_axis_labels() 

        # Rango inicial y cuadrícula
        plot.setXRange(0, 40)
        plot.showGrid(x=True, y=True, alpha=0.3)

        # Curva principal de datos
        self.__curve = plot.plot([], [], pen=pg.mkPen(width=2))

    # =========================================================================
    # Lógica Interna de Procesamiento y Visualización
    # =========================================================================

    def __update_y_axis_labels(self) -> None:
        """
        Actualiza el texto y las unidades del eje Y dinámicamente.
        
        Evita que un cambio de unidad física sobrescriba incorrectamente 
        los modos de visualización dB o Normalizado.
        """
        plot = self.__plot_widget
        unit_strings = {0: "mV²/Hz", 1: "µV²/Hz", 2: "nV²/Hz"}
        current_unit_str = unit_strings.get(self.__amplitude_unit, "µV²/Hz")

        if self.__display_mode == 1:  # Decibelios
            plot.setLabel("left", "PSD", units=f"dB (ref: 1 {current_unit_str})")
        elif self.__display_mode == 2:  # Normalizado
            plot.setLabel("left", "Potencia Normalizada", units="")
        else:  # Absoluto
            plot.setLabel("left", "PSD", units=current_unit_str)

    def __process_psd(self) -> None:
        """
        Aplica la transformación matemática al PSD crudo según el modo de visualización.
        
        Los datos de entrada (__raw_psd) ya deben venir escalados correctamente 
        en su unidad física desde el estimador externo.
        """
        if self.__raw_psd is None:
            return

        if self.__display_mode == 0:  # Absoluto
            self.__psd = self.__raw_psd
        elif self.__display_mode == 1:  # Decibelios
            # Se añade 1e-12 para evitar log10(0)
            self.__psd = 10 * np.log10(self.__raw_psd + 1e-12)
        elif self.__display_mode == 2:  # Normalizado
            max_val = np.max(self.__raw_psd)
            self.__psd = self.__raw_psd / max_val if max_val > 0 else self.__raw_psd

    # =========================================================================
    # Interfaz Pública
    # =========================================================================

    def add_psd(self, freqs: np.ndarray, psd_data: np.ndarray) -> None:
        """
        Recibe nuevos datos de frecuencia y potencia para ser graficados.

        Args:
            freqs: Array 1D de frecuencias.
            psd_data: Array 1D de valores de potencia (PSD).
        """
        self.__freqs = np.asarray(freqs)
        self.__raw_psd = np.asarray(psd_data) 
        
        self.__process_psd()

        if not self.__timer_running:
            self.__start_timer()

    def set_psd_mode(self, mode: int) -> None:
        """
        Cambia el modo de visualización de la PSD.

        Args:
            mode: 0 para Absoluto, 1 para dB, 2 para Normalizado.
        """
        self.__display_mode = mode
        self.__update_y_axis_labels()
        
        if self.__raw_psd is not None:
            self.__process_psd()

    def set_psd_unit(self, unit: int) -> None:
        """
        Informa al widget la unidad física de los datos de entrada.

        Args:
            unit: 0 para mV, 1 para µV, 2 para nV.
        """
        self.__amplitude_unit = unit
        self.__update_y_axis_labels()
        
        # Si estamos en dB o Normalizado, actualizar la etiqueta de referencia
        if self.__raw_psd is not None:
            self.__process_psd()

    def set_target_frequencies(self, frequencies: List[float]) -> None:
        """
        Dibuja líneas verticales y etiquetas para las frecuencias objetivo.

        Args:
            frequencies: Lista de frecuencias (en Hz) a marcar en el gráfico.
        """
        # 1. Limpiar marcadores anteriores
        for item in self.__freq_markers:
            self.__plot_widget.removeItem(item)
        for item in self.__freq_labels:
            self.__plot_widget.removeItem(item)

        self.__freq_markers.clear()
        self.__freq_labels.clear()

        if not frequencies:
            return

        # 2. Optimización: Calcular el rango X una sola vez fuera del bucle
        min_freq = min(frequencies) - 3
        max_freq = max(frequencies) + 3
        self.__plot_widget.setXRange(min_freq, max_freq)

        # 3. Dibujar nuevos marcadores
        for freq in frequencies:
            # Línea vertical
            line = pg.InfiniteLine(pos=freq, angle=90, pen=pg.mkPen(width=1))
            self.__plot_widget.addItem(line)
            self.__freq_markers.append(line)

            # Etiqueta de texto
            label = pg.TextItem(text=f"{freq} Hz", anchor=(0.5, 1))
            label.setPos(freq, 0)
            self.__plot_widget.addItem(label)
            self.__freq_labels.append(label)

    def stop_drawing(self) -> None:
        """Detiene el timer de actualización del gráfico."""
        self.__timer.stop()
        self.__timer_running = False

    @Slot(bool)
    def setEnabled(self, enabled: bool) -> None:
        """
        Habilita o deshabilita el widget y su mecanismo de dibujo.
        Sobrescribe el método nativo de QWidget.
        """
        super().setEnabled(enabled)
        if enabled:
            self.__start_timer()
        else:
            self.stop_drawing()
            self.__clear_plot()

    # =========================================================================
    # Lógica Interna de Actualización
    # =========================================================================

    def __start_timer(self) -> None:
        """Inicia el timer de actualización si no está ya corriendo."""
        if not self.__timer_running:
            self.__timer.start(UPDATE_INTERVAL_MS)
            self.__timer_running = True

    @Slot()
    def __update_plot(self) -> None:
        """
        Slot llamado por el QTimer. Aplica suavizado EMA y actualiza la curva.
        """
        if self.__freqs is None or self.__psd is None:
            return

        # Inicialización o reinicio del filtro si cambió el tamaño del array
        if self.__smooth_psd is None or self.__smooth_psd.shape != self.__psd.shape:
            self.__smooth_psd = self.__psd.copy()
        else:
            # Aplicar Exponential Moving Average (EMA)
            self.__smooth_psd = (self.__smooth_psd * (1 - EMA_ALPHA)) + (self.__psd * EMA_ALPHA)

        # Actualizar datos de la curva
        self.__curve.setData(self.__freqs, self.__smooth_psd)

        # Ajustar el rango del eje Y automáticamente
        if self.__display_mode == 2:  # Normalizado siempre va de 0 a ~1.5
            self.__plot_widget.setYRange(0, 1.5)
        else:
            y_min = np.min(self.__smooth_psd)
            y_max = np.max(self.__smooth_psd)
            margin = abs(y_max - y_min) * 0.1
            
            # Evitar márgenes de 0 si la señal es plana
            if margin == 0:
                margin = 1.0 
                
            self.__plot_widget.setYRange(y_min - margin, y_max + margin)

    def __clear_plot(self) -> None:
        """Limpia todos los datos almacenados y resetea la curva visual."""
        self.__freqs = None
        self.__raw_psd = None
        self.__psd = None
        self.__smooth_psd = None
        self.__curve.setData([], [])
