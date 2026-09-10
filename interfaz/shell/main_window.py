"""Ventana principal del shell: sidebar + pantallas (Inicio/EMG/EEG)."""

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from interfaz.pages.eeg_placeholder_page import EegPlaceholderPage
from interfaz.pages.emg_page import EmgPage
from interfaz.pages.inicio_page import InicioPage
from interfaz.shell.app_state import SharedAppState
from interfaz.shell.sidebar import Sidebar


class MainShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control AAC")
        self.resize(1300, 900)

        self.state = SharedAppState()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate_requested.connect(self._on_nav_requested)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.inicio_page = InicioPage(self.state)
        self.emg_page = EmgPage(self.state)
        self.eeg_page = EegPlaceholderPage(self.state)
        for page in (self.inicio_page, self.emg_page, self.eeg_page):
            self.stack.addWidget(page)

        self.inicio_page.session_started.connect(self._on_session_started)
        self.state.patient_changed.connect(self._on_patient_changed)

    # ------------------------------------------------------------------
    def _on_nav_requested(self, key: str) -> None:
        if key == "inicio":
            self._show(self.inicio_page, key)
        elif key == "emg":
            if self.emg_page.tiene_sesion_activa():
                self._show(self.emg_page, key)
            else:
                self.sidebar.set_active("inicio")
                self.inicio_page.notificar_sesion_no_disponible()
        elif key == "eeg":
            self._show(self.eeg_page, key)

    def _on_session_started(self, modalidad: str) -> None:
        patient = self.state.patient
        nombre_completo = patient.nombre_completo if patient else ""
        if modalidad == "emg":
            if not self.emg_page.iniciar_sesion(nombre_completo):
                return
            self._show(self.emg_page, "emg")
        else:
            self.eeg_page.iniciar_sesion()
            self._show(self.eeg_page, "eeg")

    def _on_patient_changed(self, patient) -> None:
        texto = patient.nombre_completo if patient else "(sin definir)"
        self.sidebar.set_patient_label(texto)

    def _show(self, page: QWidget, nav_key: str) -> None:
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(nav_key)

    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        self.emg_page.liberar_recursos()
        super().closeEvent(event)
