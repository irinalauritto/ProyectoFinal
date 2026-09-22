"""Punto de entrada de la interfaz unificada (shell + EMG + EEG/SSVEP embebidos)."""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
_EMG_DIR = _REPO_ROOT / "interfaz_emg"
_SSVEP_DIR = _REPO_ROOT / "interfaz_ssvep"

# interfaz_emg/ e interfaz_ssvep/ no se mueven de lugar (siguen siendo
# ejecutables sueltas para depurar cada modulo de forma aislada) -- solo se
# agregan al sys.path para poder importar `emg.interfazEmg` y
# `ssvep.app...` tal cual desde aca.
for _path in (_REPO_ROOT, _EMG_DIR, _SSVEP_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

import pyqtgraph as pg  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from interfaz.shell.main_window import MainShell  # noqa: E402
from interfaz.shell.style import STYLESHEET  # noqa: E402

# Fondo/trazo por defecto de pyqtgraph, seteado antes de construir
# cualquier PlotWidget en la app (propios o reusados de interfaz_ssvep,
# como PSDWidget). El default real de pyqtgraph es negro; sin esto,
# cualquier PlotWidget que no fije su propio fondo explicito (como
# PSDWidget) queda oscuro y no combina con la paleta Comando AAC. Se
# ubica aca -- no en interfaz_emg/interfaz_ssvep -- para no depender de
# que un modulo se importe antes que otro.
pg.setConfigOption("background", "#f8f9fa")
pg.setConfigOption("foreground", "#69707b")


def _paleta_clara() -> QPalette:
    # Misma paleta que arma interfazEmg.py en su propio main() (probada:
    # con Windows en modo oscuro, sin esto Fusion toma el tema oscuro del
    # sistema para todo lo que el QSS no cubre explicitamente -- botones,
    # groupbox, popups de combobox, etc). Se necesita aca tambien porque en
    # emg_page.py se instancia VentanaEmg directo, sin pasar por ese main().
    paleta = QPalette()
    paleta.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    paleta.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
    paleta.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    paleta.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
    paleta.setColor(QPalette.ColorRole.Text, QColor("#000000"))
    paleta.setColor(QPalette.ColorRole.Button, QColor("#f0f0f0"))
    paleta.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
    paleta.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    paleta.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
    return paleta


def main() -> None:
    app = QApplication(sys.argv)
    # Sin esto, Windows usa su estilo nativo, que ignora buena parte del
    # QSS (bordes, fondos, padding de botones con contenido propio como las
    # tarjetas de modalidad) y puede terminar solapando texto. Fusion es el
    # estilo que ya usan interfazEmg.py y vision.py por la misma razon.
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(_paleta_clara())
    app.setStyleSheet(STYLESHEET)

    window = MainShell()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
