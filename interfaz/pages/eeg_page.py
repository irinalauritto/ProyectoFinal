"""Pagina EEG/SSVEP del shell: EegSession (logica de ssvep/app/, sin UI)
mas EegMainPage (UI propia, estetica Comando AAC).

No embebe nada de la UI de interfaz_ssvep (UserUI/AppController) y no
modifica ningun archivo de interfaz_ssvep/ -- ver interfaz/eeg/session.py.
"""

from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from interfaz.shell.app_state import SharedAppState

_SSVEP_DIR = Path(__file__).resolve().parent.parent.parent / "interfaz_ssvep"


class EegPage(QWidget):
    def __init__(self, state: SharedAppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._session = None
        self._main_page = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Todavía no hay una sesión EEG activa.")
        self._placeholder.setObjectName("MutedCenteredLabel")
        self._layout.addWidget(self._placeholder)

    def tiene_sesion_activa(self) -> bool:
        return self._session is not None

    def iniciar_sesion(self, user_id: int) -> bool:
        """Arranca EegSession la primera vez y carga `user_id`.

        `user_id` ya viene resuelto desde InicioPage (elegido/creado ahi,
        ver pages/inicio_page.py) -- esta pagina no vuelve a preguntar
        quien es.
        """
        if self._session is None:
            from interfaz.eeg.session import EegSession
            from interfaz.pages.eeg.eeg_main_page import EegMainPage

            data_dir = _SSVEP_DIR / "vision_data"
            eeg_bin_path = _SSVEP_DIR / "eeg_bin.bin"
            self._session = EegSession(data_dir=str(data_dir), eeg_bin_path=str(eeg_bin_path))
            self._session.start()

            self._session.load_user(user_id)
            self._main_page = EegMainPage(self._session)

            self._layout.removeWidget(self._placeholder)
            self._placeholder.hide()
            self._layout.addWidget(self._main_page)

            self._session.start_streaming()
        else:
            self._session.stop_streaming()
            self._session.load_user(user_id)
            self._main_page._load_from_preferences()
            self._session.start_streaming()

        return True

    def liberar_recursos(self) -> None:
        if self._main_page is not None:
            self._main_page.liberar_recursos()
        if self._session is not None:
            self._session.shutdown()
