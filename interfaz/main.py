"""Punto de entrada de la interfaz unificada (shell + EMG embebido).

La integracion de EEG/SSVEP queda para una etapa posterior; por ahora esa
pantalla es solo estetica (ver interfaz/pages/eeg_placeholder_page.py).
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
_EMG_DIR = _REPO_ROOT / "interfaz_emg"

# interfaz_emg/ no se mueve de lugar (sigue siendo ejecutable suelta para
# depurar EMG de forma aislada) -- solo se agrega al sys.path para poder
# importar `emg.interfazEmg` tal cual desde aca.
for _path in (_REPO_ROOT, _EMG_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from PySide6.QtWidgets import QApplication  # noqa: E402

from interfaz.shell.main_window import MainShell  # noqa: E402
from interfaz.shell.style import STYLESHEET  # noqa: E402


def main() -> None:
    app = QApplication(sys.argv)
    # Sin esto, Windows usa su estilo nativo, que ignora buena parte del
    # QSS (bordes, fondos, padding de botones con contenido propio como las
    # tarjetas de modalidad) y puede terminar solapando texto. Fusion es el
    # estilo que ya usan interfazEmg.py y vision.py por la misma razon.
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainShell()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
