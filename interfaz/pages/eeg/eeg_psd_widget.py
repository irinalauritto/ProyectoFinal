"""Grafico de PSD (Densidad Espectral de Potencia) en vivo.

Reemplaza a `ssvep.app.psd_widget.PSDWidget` en esta pantalla: ese widget
autoescala el eje Y al min/max exacto de cada frame, que con la amplitud
cruda de la senal puede quedar enorme (o, si la senal esta casi plana,
recortado a una ventana minuscula que amplifica el ruido visualmente).
Este widget mantiene el eje Y numerico pero lo ajusta solo a la banda de
frecuencias visible (min y max reales de esa banda, con un piso minimo de
rango y margen arriba reservado para las etiquetas de frecuencia) -- ver
`_y_range_for`.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QWidget

_TRACE_COLOR = "#2f6690"
_FILL_COLOR = "#2f6690"
_BG_COLOR = "#f8f9fa"
_GRID_COLOR = "#e3e6ea"
_DASH_COLOR = "#c7cdd6"
_LABEL_COLOR = "#9aa1ab"

EMA_ALPHA = 0.2  # suavizado temporal, igual que ssvep.app.psd_widget.PSDWidget

# Piso minimo de rango visible en el eje Y, por modo -- solo para evitar un
# rango degenerado (todo el eje colapsado) sobre una señal perfectamente
# plana; no debe ser grande o vuelve a tapar la curva de azul (ver
# _y_range_for). 0=Absoluto, 1=dB, 2=Normalizado.
_MIN_SPAN_DB = 6.0
_MIN_SPAN_NORMALIZADO = 0.15


class EegPsdWidget(QWidget):
    """Modos de visualizacion, igual numeracion que PSDWidget original:
    0 = Absoluto, 1 = Decibeles, 2 = Normalizado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = 1
        self._enabled = True
        self._raw_freqs: np.ndarray | None = None
        self._raw_psd: np.ndarray | None = None
        self._smooth_psd: np.ndarray | None = None
        self._target_freqs: list[float] = []
        self._freq_markers: list = []
        self._x_range = (0.0, 40.0)  # ver set_target_frequencies/_y_range_for

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot_widget = pg.PlotWidget(background=_BG_COLOR)
        plot_item = self._plot_widget.getPlotItem()
        plot_item.getAxis("left").enableAutoSIPrefix(False)
        left_axis = plot_item.getAxis("left")
        left_axis.setPen(pg.mkPen(color=_GRID_COLOR))
        left_axis.setTextPen(pg.mkPen(color=_LABEL_COLOR))
        plot_item.showAxis("bottom")
        bottom_axis = plot_item.getAxis("bottom")
        bottom_axis.setPen(pg.mkPen(color=_GRID_COLOR))
        bottom_axis.setTextPen(pg.mkPen(color=_LABEL_COLOR))
        plot_item.setLabel("bottom", "Frecuencia", units="Hz")
        self._update_y_label()
        plot_item.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.setXRange(0, 40)
        self._plot_widget.setYRange(0, 1, padding=0)
        layout.addWidget(self._plot_widget)

        fill_color = pg.mkColor(_FILL_COLOR)
        fill_color.setAlphaF(0.15)
        fill_brush = pg.mkBrush(fill_color)
        self._curve = self._plot_widget.plot(
            [], [], pen=pg.mkPen(color=_TRACE_COLOR, width=1.4), fillLevel=0, brush=fill_brush
        )

    # ------------------------------------------------------------------
    def add_psd(self, freqs, psd_data) -> None:
        self._raw_freqs = np.asarray(freqs, dtype=float)
        self._raw_psd = np.asarray(psd_data, dtype=float)
        if self._enabled:
            self._redraw()

    def set_psd_mode(self, mode: int) -> None:
        self._display_mode = mode
        self._smooth_psd = None  # reinicia el suavizado al cambiar de escala
        self._update_y_label()
        if self._enabled and self._raw_psd is not None:
            self._redraw()

    def set_psd_unit(self, unit: int) -> None:
        # Se conserva el metodo solo para no romper la interfaz publica que
        # ya usaba el widget reusado antes; no afecta el rango mostrado.
        pass

    def _update_y_label(self) -> None:
        plot = self._plot_widget.getPlotItem()
        if self._display_mode == 1:
            plot.setLabel("left", "PSD", units="dB")
        elif self._display_mode == 2:
            plot.setLabel("left", "Potencia", units="")
        else:
            plot.setLabel("left", "PSD", units="µV²/Hz")

    def set_target_frequencies(self, frequencies) -> None:
        for item in self._freq_markers:
            self._plot_widget.removeItem(item)
        self._freq_markers.clear()
        self._target_freqs = list(frequencies)

        if not self._target_freqs:
            self._x_range = (0.0, 40.0)
            self._plot_widget.setXRange(*self._x_range)
            return

        # El extremo superior siempre llega como minimo a 17Hz (frecuencia
        # ancla de la calibracion, ver frequency_calibrator.py) aunque las
        # frecuencias asignadas actuales sean todas mas bajas -- asi se
        # puede comparar contra el ancla o candidatas no asignadas sin
        # perder el rango normal alrededor de las frecuencias en uso.
        self._x_range = (min(self._target_freqs) - 3, max(max(self._target_freqs) + 3, 17.0))
        self._plot_widget.setXRange(*self._x_range)

        # Las frecuencias objetivo estan a 0,5Hz una de otra: con "8,5 Hz" en
        # cada linea se pisaban entre si. Se muestra solo el numero (chico) y
        # las etiquetas se alternan en dos alturas, asi entran sin superponerse.
        for i, freq in enumerate(sorted(self._target_freqs)):
            freq_text = f"{freq:g}".replace(".", ",")
            line = pg.InfiniteLine(
                pos=freq,
                angle=90,
                pen=pg.mkPen(color=_DASH_COLOR, width=1, style=Qt.PenStyle.DashLine),
                label=freq_text,
                labelOpts={
                    "color": _LABEL_COLOR,
                    "position": 0.96 if i % 2 == 0 else 0.86,
                    "fill": None,
                    "anchors": [(0.5, 0.5), (0.5, 0.5)],
                },
            )
            line.label.setFont(QFont("Segoe UI", 7))
            self._plot_widget.addItem(line)
            self._freq_markers.append(line)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._enabled = enabled
        if enabled:
            if self._raw_psd is not None:
                self._redraw()
        else:
            self._curve.setData([], [])

    # ------------------------------------------------------------------
    def _redraw(self) -> None:
        psd = self._processed_psd()
        if psd is None or self._raw_freqs is None:
            return

        if self._smooth_psd is None or self._smooth_psd.shape != psd.shape:
            self._smooth_psd = psd.copy()
        else:
            self._smooth_psd = (self._smooth_psd * (1 - EMA_ALPHA)) + (psd * EMA_ALPHA)

        self._curve.setData(self._raw_freqs, self._smooth_psd)

        y_lo, y_hi = self._y_range_for(self._visible_psd_slice())
        self._curve.setFillLevel(y_lo)
        self._plot_widget.setYRange(y_lo, y_hi, padding=0)

    def _visible_psd_slice(self) -> np.ndarray:
        """Solo la parte de la PSD dentro del rango de frecuencias visible
        (banda de los estimulos +/-3Hz, ver set_target_frequencies) -- si
        se calculara sobre todo el espectro, valores bajos fuera de esa
        banda (ej. caida hacia 0Hz) estiran el eje Y mucho mas de lo que
        hace falta para ver la curva realmente en pantalla, dejando la
        mayor parte del panel pintada de azul sin poder apreciar cambios."""
        x_lo, x_hi = self._x_range
        mask = (self._raw_freqs >= x_lo) & (self._raw_freqs <= x_hi)
        if not np.any(mask):
            return self._smooth_psd
        return self._smooth_psd[mask]

    def _y_range_for(self, psd: np.ndarray) -> tuple[float, float]:
        """Rango Y ajustado a la banda visible (ver _visible_psd_slice): min y
        max reales de esa banda -- nunca se recorta el maximo -- mas un piso
        minimo de ancho para no des-zoomear sobre ruido casi plano."""
        p_lo, p_hi = float(np.min(psd)), float(np.max(psd))
        span = p_hi - p_lo

        if self._display_mode == 1:  # Decibeles: piso fijo, ya es una escala comprimida
            min_span = _MIN_SPAN_DB
        elif self._display_mode == 2:  # Normalizado: ya esta en [0, ~1]
            min_span = _MIN_SPAN_NORMALIZADO
        else:  # Absoluto: piso relativo a la magnitud actual (unidad arbitraria)
            magnitude = max(abs(p_hi), abs(p_lo), 1.0)
            min_span = magnitude * 0.25

        if span < min_span:
            center = (p_hi + p_lo) / 2.0
            p_lo, p_hi = center - min_span / 2.0, center + min_span / 2.0
            span = min_span

        # Abajo un margen chico; arriba uno mas grande, reservado para las
        # etiquetas de frecuencia (van dentro del grafico, sobre la curva).
        return p_lo - span * 0.08, p_hi + span * 0.30

    def _processed_psd(self) -> np.ndarray | None:
        if self._raw_psd is None:
            return None
        if self._display_mode == 1:  # Decibeles
            return 10 * np.log10(self._raw_psd + 1e-12)
        if self._display_mode == 2:  # Normalizado
            max_val = np.max(self._raw_psd)
            return self._raw_psd / max_val if max_val > 0 else self._raw_psd
        return self._raw_psd  # Absoluto
