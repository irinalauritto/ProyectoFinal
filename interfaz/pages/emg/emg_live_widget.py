"""Grafico de señal EMG (envolvente) en vivo, estetica "Comando AAC".

Reemplaza al grafico de `interfazEmg.py` (pyqtgraph con fondo blanco/negro,
sin la estetica del artefacto) -- se alimenta de las mismas señales que
emite `EmgEngine.samples_ready(valores, eventos)` (ver interfaz_emg/emg/
interfazEmg.py, que no se toca en su UI, solo se le separo la logica).
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

_TRACE_COLOR = "#2f6690"
_THRESHOLD_COLOR = "#b5533f"
_BG_COLOR = "#f8f9fa"
_GRID_COLOR = "#e3e6ea"
_LABEL_COLOR = "#9aa1ab"

# Piso minimo del rango Y (en mV): evita "des-zoomear" sobre ruido de reposo
# casi plano (mismo criterio usado en eeg_psd_widget.py).
_MIN_SPAN_MV = 0.5


class EmgLiveWidget(QWidget):
    def __init__(self, parent=None, buffer_size: int = 2000):
        super().__init__(parent)
        self._buffer_size = buffer_size
        self._buffer = np.zeros(buffer_size)
        self._marker_x: list[int] = []
        self._marker_y: list[float] = []
        self._umbral: float | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot_widget = pg.PlotWidget(background=_BG_COLOR)
        plot_item = self._plot_widget.getPlotItem()
        plot_item.hideAxis("bottom")
        left_axis = plot_item.getAxis("left")
        left_axis.setPen(pg.mkPen(color=_GRID_COLOR))
        left_axis.setTextPen(pg.mkPen(color=_LABEL_COLOR))
        plot_item.setLabel("left", "Amplitud", units="mV")
        plot_item.showGrid(x=False, y=True, alpha=0.2)
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.setXRange(0, buffer_size, padding=0)
        layout.addWidget(self._plot_widget)

        self._curve = self._plot_widget.plot(pen=pg.mkPen(color=_TRACE_COLOR, width=1.2), antialias=True)
        self._curve.setDownsampling(auto=True, method="peak")
        self._curve.setClipToView(True)
        self._scatter = pg.ScatterPlotItem(
            size=9, brush=pg.mkBrush(_THRESHOLD_COLOR), pen=pg.mkPen(_THRESHOLD_COLOR)
        )
        self._plot_widget.addItem(self._scatter)
        self._linea_umbral: pg.InfiniteLine | None = None
        self._umbral_label: pg.TextItem | None = None

    # ------------------------------------------------------------------
    def set_umbral(self, valor: float | None) -> None:
        self._umbral = valor
        if valor is None:
            if self._linea_umbral is not None:
                self._plot_widget.removeItem(self._linea_umbral)
                self._linea_umbral = None
            if self._umbral_label is not None:
                self._plot_widget.removeItem(self._umbral_label)
                self._umbral_label = None
            return
        if self._linea_umbral is None:
            self._linea_umbral = pg.InfiniteLine(
                pos=valor,
                angle=0,
                pen=pg.mkPen(color=_THRESHOLD_COLOR, width=1.3, style=Qt.PenStyle.DashLine),
            )
            self._plot_widget.addItem(self._linea_umbral)
            # Un TextItem propio en vez del label incorporado de InfiniteLine:
            # ese ubica el texto por fraccion de posicion sobre la linea, que
            # para una linea horizontal cerca del extremo izquierdo lo deja
            # pegado (y cortado) contra el eje Y. Con anchor=(0, 1) el texto
            # crece hacia la derecha desde el punto, nunca hacia afuera del panel.
            self._umbral_label = pg.TextItem("Umbral de disparo", color=_THRESHOLD_COLOR, anchor=(0, 1))
            self._plot_widget.addItem(self._umbral_label)
            self._umbral_label.setPos(self._buffer_size * 0.02, valor)
        else:
            self._linea_umbral.setValue(valor)
            self._umbral_label.setPos(self._buffer_size * 0.02, valor)

    def append_samples(self, valores: list[float], eventos: list[bool]) -> None:
        n_new = len(valores)
        if n_new <= 0:
            return
        n_new = min(n_new, self._buffer_size)
        valores = valores[-n_new:]
        eventos = eventos[-n_new:]

        # Los marcadores existentes se corren a la izquierda junto con el
        # buffer (mismo criterio que _desplazar_marcadores en interfazEmg.py).
        self._marker_x = [x - n_new for x in self._marker_x]
        keep = [i for i, x in enumerate(self._marker_x) if x >= 0]
        self._marker_x = [self._marker_x[i] for i in keep]
        self._marker_y = [self._marker_y[i] for i in keep]

        self._buffer = np.roll(self._buffer, -n_new)
        self._buffer[-n_new:] = valores
        base = self._buffer_size - n_new
        for i, (valor, es_evento) in enumerate(zip(valores, eventos)):
            if es_evento:
                self._marker_x.append(base + i)
                self._marker_y.append(valor)

        self._redraw()

    def _redraw(self) -> None:
        self._curve.setData(self._buffer)
        self._scatter.setData(x=self._marker_x, y=self._marker_y)

        # Min/max reales (no percentiles): a diferencia del ruido de fondo en
        # la PSD, un pico de contraccion ES la señal de interes aca -- nunca
        # se debe recortar, aunque sea un solo pico aislado en la ventana.
        lo, hi = float(np.min(self._buffer)), float(np.max(self._buffer))
        span = hi - lo
        if self._umbral is not None:
            hi = max(hi, self._umbral)
            span = hi - lo
        if span < _MIN_SPAN_MV:
            center = (hi + lo) / 2.0
            lo, hi = center - _MIN_SPAN_MV / 2.0, center + _MIN_SPAN_MV / 2.0
            span = _MIN_SPAN_MV
        margin = span * 0.15
        self._plot_widget.setYRange(lo - margin, hi + margin, padding=0)

    def clear(self) -> None:
        self._buffer[:] = 0
        self._marker_x = []
        self._marker_y = []
        self._redraw()
