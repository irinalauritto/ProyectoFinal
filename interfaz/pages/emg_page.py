"""Pagina EMG del shell: embebe VentanaEmg (interfaz_emg/emg/interfazEmg.py).

No se copia ni se reescribe la logica de interfazEmg.py -- se importa tal
cual (con interfaz_emg/ agregado a sys.path en interfaz/main.py) y se la
embebe como widget en vez de mostrarla como ventana top-level.
"""

import serial

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from emg.interfazEmg import BAUD_RATE, VentanaEmg, _detectar_puerto_esp32, _elegir_puerto_manualmente

from interfaz.shell.app_state import SharedAppState


class EmgPage(QWidget):
    def __init__(self, state: SharedAppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.ventana_emg: VentanaEmg | None = None
        self._serial_conn: serial.Serial | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Todavía no hay una sesión EMG activa.")
        self._placeholder.setObjectName("MutedCenteredLabel")
        self._layout.addWidget(self._placeholder)

    def tiene_sesion_activa(self) -> bool:
        return self.ventana_emg is not None

    def iniciar_sesion(self, nombre_paciente: str) -> bool:
        """Detecta/abre el puerto de la ESP32 y embebe VentanaEmg.

        Devuelve False (y muestra un aviso) si no se pudo abrir el puerto,
        para que el shell no navegue a una pantalla EMG vacía.
        """
        if self.ventana_emg is not None:
            self.ventana_emg.establecer_paciente(nombre_paciente)
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

        self.ventana_emg = VentanaEmg(self._serial_conn)
        self._layout.removeWidget(self._placeholder)
        self._placeholder.hide()
        self._layout.addWidget(self.ventana_emg)
        self.ventana_emg.establecer_paciente(nombre_paciente)
        return True

    def liberar_recursos(self) -> None:
        if self.ventana_emg is not None:
            self.ventana_emg.liberar_recursos()
