"""Ventana principal del shell: sidebar + pantallas (Inicio/EMG/EEG)."""

import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from interfaz.pages.eeg_page import EegPage
from interfaz.pages.emg_page import EmgPage
from interfaz.pages.inicio_page import InicioPage
from interfaz.shell import asterics_config, patient_store
from interfaz.shell.app_state import SharedAppState
from interfaz.shell.sidebar import Sidebar


class MainShell(QMainWindow):
    # Perfil de AsTeRICS con el que se abrió la última sesión (None: ninguno todavía).
    _asterics_profile: str | None = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control AAC")
        # Tamaño "normal"/restaurado (el que queda si despues se desmaximiza
        # la ventana). main.py ya se encarga de mostrar la ventana antes de
        # maximizarla (show() y recien despues showMaximized(), no al reves)
        # para que Windows resuelva el DPI/tamaño de pantalla real antes de
        # calcular el maximizado -- este resize() de aca no interfiere con eso.
        self.resize(1300, 900)

        self.state = SharedAppState()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate_requested.connect(self._on_nav_requested)
        self.sidebar.collapse_requested.connect(lambda: self._set_sidebar_visible(False))
        layout.addWidget(self.sidebar)

        # Boton para volver a mostrar la barra lateral cuando esta oculta.
        # Vive fuera del Sidebar (que se oculta entero) para poder
        # recuperarla; solo se ve mientras el sidebar esta colapsado.
        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(8, 8, 8, 0)
        self.btn_expand = QPushButton("☰")
        self.btn_expand.setObjectName("SidebarExpandButton")
        self.btn_expand.setFixedSize(28, 28)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setToolTip("Mostrar barra lateral")
        self.btn_expand.clicked.connect(lambda: self._set_sidebar_visible(True))
        top_bar_layout.addWidget(self.btn_expand)
        top_bar_layout.addStretch(1)
        right_layout.addWidget(top_bar)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)
        layout.addWidget(right_side, 1)

        self.inicio_page = InicioPage(self.state)
        self.emg_page = EmgPage(self.state)
        self.eeg_page = EegPage(self.state)
        for page in (self.inicio_page, self.emg_page, self.eeg_page):
            self.stack.addWidget(page)

        self.inicio_page.session_started.connect(self._on_session_started)
        self.state.patient_changed.connect(self._on_patient_changed)

        # Arranca en Inicio, centrada y sin barra lateral.
        self._show(self.inicio_page, "inicio")

        # Mantenimiento de los perfiles de AsTeRICS (temporales y caché).
        threading.Thread(target=self._mantener_perfiles_asterics, name="asterics-perfiles", daemon=True).start()

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
            if self.eeg_page.tiene_sesion_activa():
                self._show(self.eeg_page, key)
            else:
                self.sidebar.set_active("inicio")
                self.inicio_page.notificar_sesion_no_disponible("EEG")

    def _on_session_started(self, modalidad: str) -> None:
        if modalidad == "emg":
            patient = self.state.patient
            nombre_completo = patient.nombre_completo if patient else ""
            if not self.emg_page.iniciar_sesion(nombre_completo):
                return
            self._abrir_ficha(self.emg_page, "emg")
            self._show(self.emg_page, "emg")
        else:
            if self.state.ssvep_user_id is None:
                return
            if not self.eeg_page.iniciar_sesion(self.state.ssvep_user_id):
                return
            self._abrir_ficha(self.eeg_page, "eeg")
            self._show(self.eeg_page, "eeg")

    def _abrir_ficha(self, page, modalidad: str) -> None:
        """Asocia la pantalla a la ficha del paciente (restaura su configuración y
        guarda lo que cambie) y registra el inicio de la sesión en su historial."""
        patient = self.state.patient
        patient_id = patient.id if patient else None

        # AsTeRICS es de un paciente: si cambió el perfil, se cierra la ventana
        # que haya quedado abierta del paciente anterior.
        perfil = asterics_config.active_profile()
        if self._asterics_profile is not None and perfil != self._asterics_profile:
            self.emg_page.cerrar_asterics()
            self.eeg_page.cerrar_asterics()
        self._asterics_profile = perfil

        page.vincular_ficha(patient_id)
        patient_store.start_session(patient_id, modalidad)

    def _on_patient_changed(self, patient) -> None:
        texto = patient.nombre_completo if patient else "(sin definir)"
        self.sidebar.set_patient_label(texto)

    def _show(self, page: QWidget, nav_key: str) -> None:
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(nav_key)
        # Inicio arranca centrada y sin distracciones; al entrar a una
        # sesion (EMG/EEG) la barra lateral vuelve para poder navegar.
        # El boton de colapsar/expandir sigue disponible en cualquier
        # pantalla si se quiere mas espacio.
        self._set_sidebar_visible(nav_key != "inicio")

    def _set_sidebar_visible(self, visible: bool) -> None:
        self.sidebar.setVisible(visible)
        self.btn_expand.setVisible(not visible)

    # ------------------------------------------------------------------
    @staticmethod
    def _mantener_perfiles_asterics() -> None:
        """Borra perfiles temporales que hayan quedado y la caché regenerable
        de los perfiles (cada paciente ocupa unas pocas decenas de MB)."""
        try:
            asterics_config.purge_temporary_profiles()
            asterics_config.clean_all_caches()
        except Exception:
            pass  # es solo limpieza: nunca debe molestar al arrancar

    def closeEvent(self, event) -> None:
        patient = self.state.patient
        patient_store.end_session(patient.id if patient else None)
        self.inicio_page.cancelar_asterics()
        self.emg_page.liberar_recursos()
        self.eeg_page.liberar_recursos()
        # Si AsTeRICS sigue abierta el perfil está en uso y no se toca: la
        # próxima vez que arranque la aplicación se limpia.
        try:
            asterics_config.purge_temporary_profiles()
            asterics_config.clean_cache()
        except Exception:
            pass
        super().closeEvent(event)
