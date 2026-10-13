"""
Página EEG:
    EegSession es la lógica de ssvep/app/, sin UI. Mientras que EegMainPage se encarga de la UI de la página EEG, con la estética de la aplicación de control de Asterics AAC.

Autora: Irina Lauritto
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

    def vincular_ficha(self, patient_id) -> None:
        """Asocia la pantalla a la ficha del paciente (ver patient_store)."""
        if self._main_page is not None:
            self._main_page.attach_ficha(patient_id)

    def cerrar_asterics(self) -> None:
        """Cierra la ventana de AsTeRICS abierta desde esta pantalla (si hay)."""
        if self._main_page is not None:
            self._main_page.cerrar_asterics()

    def liberar_recursos(self) -> None:
        if self._main_page is not None:
            self._main_page.liberar_recursos()
        if self._session is not None:
            self._session.shutdown()
