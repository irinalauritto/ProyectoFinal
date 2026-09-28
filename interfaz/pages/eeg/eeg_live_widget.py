"""Grafico de señal EEG multicanal en vivo.

Reemplaza a `ssvep.app.eeg_widget.EEGWidget` (que depende de un .ui propio
con su estetica) -- este es pyqtgraph puro, estilizado para calzar con el
artefacto "Comando AAC" (fondo claro, trazo azul, un canal por banda
horizontal con su nombre a la izquierda, como en Pantalla3_EEG.dc.html).
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

BUFFER_SECONDS = 6
DEFAULT_SAMPLE_RATE = 250
# Al (re)arrancar el stream, los filtros arrastran un transitorio enorme (el
# salto desde 0 al offset DC de la señal cruda) que dura ~1s: no es EEG, y
# aplasta la escala de todo lo demas mientras siga dentro del buffer. Se
# descartan esos primeros segundos filtrados.
WARMUP_SECONDS = 1.5

_TRACE_COLOR = "#2f6690"
_LABEL_COLOR = "#262c34"
_BG_COLOR = "#f8f9fa"
_GRID_COLOR = "#e3e6ea"


class EegLiveWidget(QWidget):
    def __init__(self, parent=None, sample_rate: int = DEFAULT_SAMPLE_RATE):
        super().__init__(parent)
        self._sample_rate = sample_rate
        self._buffer_size = int(BUFFER_SECONDS * sample_rate)
        self._channel_names: list[str] = []
        self._buffers: list[np.ndarray] = []
        self._curves: list = []
        self._labels: list = []
        self._filled = 0  # cuantas muestras reales (no relleno inicial en 0) hay en el buffer
        self._warmup_left = int(WARMUP_SECONDS * sample_rate)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot_widget = pg.PlotWidget(background=_BG_COLOR)
        plot_item = self._plot_widget.getPlotItem()
        plot_item.hideAxis("left")
        plot_item.hideAxis("bottom")
        plot_item.showGrid(x=False, y=False)
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        self._plot_widget.setMenuEnabled(False)
        layout.addWidget(self._plot_widget)

    def set_channel_labels(self, names: list[str]) -> None:
        """(Re)inicializa el grafico para esta lista de canales (mismo orden
        que las filas de la señal filtrada que va a llegar en `append_samples`)."""
        self._channel_names = list(names)
        self._buffers = [np.zeros(self._buffer_size) for _ in names]
        self._filled = 0
        self._warmup_left = int(WARMUP_SECONDS * self._sample_rate)
        self._plot_widget.clear()
        self._curves = []
        self._labels = []

        n = len(names)
        for i, name in enumerate(names):
            curve = self._plot_widget.plot(pen=pg.mkPen(color=_TRACE_COLOR, width=1.1), antialias=True)
            # Con ~1500 muestras dibujadas en ~1200px de ancho, sin esto la
            # linea se ve "solida"/dentada (una muestra por pixel o mas) --
            # 'peak' conserva los picos en vez de promediar, para no
            # perder informacion real de la señal al reducir puntos.
            curve.setDownsampling(auto=True, method="peak")
            curve.setClipToView(True)
            self._curves.append(curve)
            label = pg.TextItem(name, color=_LABEL_COLOR, anchor=(0, 0.5))
            label.setPos(0, self._offset_for(i, n))
            self._plot_widget.addItem(label)
            self._labels.append(label)
            if i > 0:
                sep_y = self._offset_for(i, n) + 0.5
                sep = pg.InfiniteLine(
                    pos=sep_y, angle=0, pen=pg.mkPen(color=_GRID_COLOR, width=1, style=Qt.PenStyle.DashLine)
                )
                self._plot_widget.addItem(sep)

        self._plot_widget.setYRange(-0.6, (n - 1) + 0.6, padding=0)
        self._plot_widget.setXRange(0, self._buffer_size, padding=0)

    @staticmethod
    def _offset_for(index: int, n: int) -> float:
        # Canal 0 arriba, ultimo canal abajo (igual orden que la lista de canales).
        return float(n - 1 - index)

    def append_samples(self, sample_block) -> None:
        """Agrega un bloque nuevo de señal filtrada: lista/array shape
        (n_channels, n_samples), mismo formato que `EegSession.filtered_data`."""
        if not self._buffers:
            return
        block = np.asarray(sample_block, dtype=float)
        if block.ndim == 1:
            block = block[None, :]
        if self._warmup_left > 0:
            dropped = min(self._warmup_left, block.shape[1])
            self._warmup_left -= dropped
            block = block[:, dropped:]
        n_new = block.shape[1]
        if n_new <= 0:
            return
        n_new = min(n_new, self._buffer_size)
        for i in range(min(len(self._buffers), block.shape[0])):
            self._buffers[i] = np.roll(self._buffers[i], -n_new)
            self._buffers[i][-n_new:] = block[i, -n_new:]
        self._filled = min(self._filled + n_new, self._buffer_size)
        self._redraw()

    def _redraw(self) -> None:
        n = len(self._buffers)
        # Mientras el buffer rotativo no se lleno una vez (arranque de la
        # sesion), el resto sigue en su relleno inicial en 0 -- normalizar
        # con eso adentro exagera muchisimo la escala (el salto entre 0 y
        # el valor real de la señal domina el rango) y toda la señal real
        # se ve chata/plana en comparacion. Se recorta a la parte con
        # datos reales, tanto para la normalizacion como para lo dibujado.
        start = self._buffer_size - self._filled
        for i, buf in enumerate(self._buffers):
            real = buf[start:]
            normalized = np.full(self._buffer_size, np.nan)
            if real.size:
                # Escala robusta (percentiles 5-95 en vez de min-max): al
                # (re)arrancar el stream, los filtros dejan un transitorio
                # enorme por el offset DC que, con min-max, aplasta el resto
                # de la señal durante los ~6s que tarda en salir del buffer.
                # Lo que se pasa de la banda se recorta para no pisar a los
                # canales vecinos.
                lo, hi = np.percentile(real, [5, 95])
                spread = float(hi - lo)
                if spread < 1e-9:
                    spread = 1.0
                scaled = (real - float(np.median(real))) / spread * 0.6
                normalized[start:] = np.clip(scaled, -0.48, 0.48)
            y = normalized + self._offset_for(i, n)
            self._curves[i].setData(y)

    def clear(self) -> None:
        for buf in self._buffers:
            buf[:] = 0
        self._filled = 0
        self._warmup_left = int(WARMUP_SECONDS * self._sample_rate)
        self._redraw()
