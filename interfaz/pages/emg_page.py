"""Pagina EMG del shell: EmgEngine (logica de interfazEmg.py, sin UI) mas
EmgMainPage (UI propia, estetica Comando AAC).

`interfaz_emg/emg/interfazEmg.py` se refactorizo para separar la logica
(EmgEngine: lectura serie, filtrado, calibracion, deteccion de eventos,
tecla) de su UI original (VentanaEmg, que sigue funcionando igual en modo
standalone) -- esta pagina no embebe VentanaEmg, arma su propia UI sobre
EmgEngine, igual criterio que interfaz/pages/eeg_page.py con ssvep.
"""

import serial

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from emg.interfazEmg import BAUD_RATE, EmgEngine, _detectar_puerto_esp32, _elegir_puerto_manualmente

from interfaz.shell.app_state import SharedAppState


class EmgPage(QWidget):
    def __init__(self, state: SharedAppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._engine: EmgEngine | None = None
        self._main_page = None
        self._serial_conn: serial.Serial | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Todavía no hay una sesión EMG activa.")
        self._placeholder.setObjectName("MutedCenteredLabel")
        self._layout.addWidget(self._placeholder)

    def tiene_sesion_activa(self) -> bool:
        return self._engine is not None

    def iniciar_sesion(self, nombre_paciente: str) -> bool:
        """Detecta/abre el puerto de la ESP32 y arma la pantalla EMG propia.

        Devuelve False (y muestra un aviso) si no se pudo abrir el puerto,
        para que el shell no navegue a una pantalla EMG vacía.
        """
        if self._engine is not None:
            self._engine.establecer_paciente(nombre_paciente)
            self._main_page.avisar_calibracion_requerida()
            return True

        puerto = _detectar_puerto_esp32()
        if puerto is None:
            puerto = _elegir_puerto_manualmente()
            if puerto is None:
                return False

        try:
            self._serial_conn = serial.Serial(puerto, BAUD_RATE, timeout=0)
        except serial.SerialException as exc:
            QMessageBox.critical(self, "Puerto serie", f"No se pudo abrir el puerto {puerto}:\n{exc}")
            return False

        from interfaz.pages.emg.emg_main_page import EmgMainPage

        self._engine = EmgEngine(self._serial_conn)
        self._main_page = EmgMainPage(self._engine)

        self._layout.removeWidget(self._placeholder)
        self._placeholder.hide()
        self._layout.addWidget(self._main_page)

        self._engine.establecer_paciente(nombre_paciente)
        self._main_page.avisar_calibracion_requerida()
        self._engine.start()
        return True

    def liberar_recursos(self) -> None:
        if self._main_page is not None:
            self._main_page.liberar_recursos()
        if self._engine is not None:
            self._engine.liberar_recursos()
