"""
envioTeclas.py

Interfaz simple para enviar manualmente un evento de tecla (Enter, Espacio o
Flecha derecha) con una duración de pulsación configurable. Sirve para
probar que Asterics Grid (u otro software) responde correctamente al switch
antes de conectar la señal EMG real.

"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QSpinBox,
)
from pynput.keyboard import Controller as ControladorTeclado, Key

DURACION_MIN_MS, DURACION_MAX_MS, DURACION_DEFAULT_MS = 50, 5000, 200
PAUSA_MIN_MS, PAUSA_MAX_MS, PAUSA_DEFAULT_MS = 50, 10000, 300
RETRASO_MIN_S, RETRASO_MAX_S, RETRASO_DEFAULT_S = 0, 15, 3

TECLAS_DISPONIBLES = {
    "Enter": Key.enter,
    "Espacio": Key.space,
    "Flecha derecha": Key.right,
}


class VentanaEnvioTeclas(QWidget):
    """Ventana simple para enviar una tecla simulada con duración de pulsación configurable."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Envío de tecla — prueba de switch")
        self.resize(380, 180)

        self.teclado = ControladorTeclado()
        self.tecla_activa = None  # tecla actualmente "presionada", o None si no hay envío en curso
        self.en_loop = False      # True mientras el envío repetido está activo

        # --- Cuenta regresiva antes de empezar a enviar, para dar tiempo a
        # cambiar el foco a la ventana destino (p. ej. Asterics Grid): el
        # envío de tecla en sí llega a nivel de sistema operativo a la
        # ventana que tenga el foco en ese momento, no necesariamente a esta. ---
        self._en_cuenta_regresiva = False
        self._segundos_restantes = 0
        self._callback_cuenta_regresiva = None
        self.timer_cuenta_regresiva = QTimer(self)
        self.timer_cuenta_regresiva.timeout.connect(self._tick_cuenta_regresiva)

        self._armar_ui()

    def _armar_ui(self):
        layout = QVBoxLayout(self)
        formulario = QFormLayout()

        self.combo_tecla = QComboBox()
        self.combo_tecla.addItems(list(TECLAS_DISPONIBLES.keys()))
        formulario.addRow("Tecla:", self.combo_tecla)

        self.spin_duracion = QSpinBox()
        self.spin_duracion.setRange(DURACION_MIN_MS, DURACION_MAX_MS)
        self.spin_duracion.setSingleStep(50)
        self.spin_duracion.setValue(DURACION_DEFAULT_MS)
        self.spin_duracion.setSuffix(" ms")
        formulario.addRow("Duración de la pulsación:", self.spin_duracion)

        self.spin_pausa = QSpinBox()
        self.spin_pausa.setRange(PAUSA_MIN_MS, PAUSA_MAX_MS)
        self.spin_pausa.setSingleStep(50)
        self.spin_pausa.setValue(PAUSA_DEFAULT_MS)
        self.spin_pausa.setSuffix(" ms")
        formulario.addRow("Pausa entre envíos (loop):", self.spin_pausa)

        self.spin_retraso = QSpinBox()
        self.spin_retraso.setRange(RETRASO_MIN_S, RETRASO_MAX_S)
        self.spin_retraso.setValue(RETRASO_DEFAULT_S)
        self.spin_retraso.setSuffix(" s")
        formulario.addRow("Retraso antes de empezar:", self.spin_retraso)

        layout.addLayout(formulario)

        self.btn_enviar = QPushButton("Enviar tecla")
        self.btn_enviar.clicked.connect(self._solicitar_envio_manual)
        layout.addWidget(self.btn_enviar)

        self.btn_loop = QPushButton("Iniciar loop")
        self.btn_loop.clicked.connect(self._alternar_loop)
        layout.addWidget(self.btn_loop)

        self.lbl_estado = QLabel("Listo")
        layout.addWidget(self.lbl_estado)

    def _enviar_tecla(self):
        if self.tecla_activa is not None:
            return  # ya hay un envío en curso

        nombre = self.combo_tecla.currentText()
        tecla = TECLAS_DISPONIBLES.get(nombre, Key.enter)
        duracion_ms = self.spin_duracion.value()

        self.tecla_activa = tecla
        self.teclado.press(tecla)
        self.btn_enviar.setEnabled(False)
        self.lbl_estado.setText(f"Tecla \"{nombre}\" presionada ({duracion_ms} ms)...")

        # Se usa QTimer.singleShot en vez de time.sleep para no bloquear la
        # interfaz mientras se mantiene la tecla "pulsada".
        QTimer.singleShot(duracion_ms, self._soltar_tecla)

    def _soltar_tecla(self):
        if self.tecla_activa is not None:
            self.teclado.release(self.tecla_activa)
            self.tecla_activa = None

        if self.en_loop:
            # Encadena el próximo envío tras la pausa configurada, en vez de
            # usar un QTimer periódico: así cada vuelta toma la duración y
            # la pausa actuales de los spinbox, aunque se cambien en caliente.
            pausa_ms = self.spin_pausa.value()
            self.lbl_estado.setText(f"En loop... próximo envío en {pausa_ms} ms")
            QTimer.singleShot(pausa_ms, self._enviar_tecla)
        else:
            self.btn_enviar.setEnabled(True)
            self.lbl_estado.setText("Listo")

    def _solicitar_envio_manual(self):
        if self._en_cuenta_regresiva or self.tecla_activa is not None:
            return
        self._iniciar_cuenta_regresiva(self._enviar_tecla)

    def _alternar_loop(self):
        if self.en_loop:
            self._detener_loop()
        elif not self._en_cuenta_regresiva:
            self._iniciar_cuenta_regresiva(self._iniciar_loop)

    def _iniciar_cuenta_regresiva(self, callback_al_terminar):
        self._callback_cuenta_regresiva = callback_al_terminar
        self.btn_enviar.setEnabled(False)
        self.btn_loop.setEnabled(False)

        retraso_s = self.spin_retraso.value()
        if retraso_s <= 0:
            self._finalizar_cuenta_regresiva()
            return

        self._en_cuenta_regresiva = True
        self._segundos_restantes = retraso_s
        self.lbl_estado.setText(f"Cambie a la ventana destino... comienza en {self._segundos_restantes} s")
        self.timer_cuenta_regresiva.start(1000)

    def _tick_cuenta_regresiva(self):
        self._segundos_restantes -= 1
        if self._segundos_restantes <= 0:
            self.timer_cuenta_regresiva.stop()
            self._finalizar_cuenta_regresiva()
        else:
            self.lbl_estado.setText(f"Cambie a la ventana destino... comienza en {self._segundos_restantes} s")

    def _finalizar_cuenta_regresiva(self):
        self._en_cuenta_regresiva = False
        self.btn_loop.setEnabled(True)
        callback = self._callback_cuenta_regresiva
        self._callback_cuenta_regresiva = None
        callback()

    def _iniciar_loop(self):
        self.en_loop = True
        self.btn_loop.setText("Detener loop")
        self.btn_enviar.setEnabled(False)
        self._enviar_tecla()

    def _detener_loop(self):
        self.en_loop = False
        self.btn_loop.setText("Iniciar loop")
        if self.tecla_activa is None:
            self.btn_enviar.setEnabled(True)
            self.lbl_estado.setText("Listo")
        # Si hay una tecla presionada en este momento, se suelta sola al
        # cumplirse su duración (en _soltar_tecla), que ya no volverá a
        # encadenar un envío porque en_loop pasó a False.

    def closeEvent(self, event):
        # Evita dejar una tecla "pegada" si se cierra la ventana con el loop
        # activo, en medio de una cuenta regresiva o de una pulsación.
        self.en_loop = False
        self.timer_cuenta_regresiva.stop()
        if self.tecla_activa is not None:
            self.teclado.release(self.tecla_activa)
            self.tecla_activa = None
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    # Interfaz clara, consistente con interfazEmg.py
    app.setStyle("Fusion")
    paleta_clara = QPalette()
    paleta_clara.setColor(QPalette.Window, QColor("#ffffff"))
    paleta_clara.setColor(QPalette.WindowText, QColor("#000000"))
    paleta_clara.setColor(QPalette.Base, QColor("#ffffff"))
    paleta_clara.setColor(QPalette.Text, QColor("#000000"))
    paleta_clara.setColor(QPalette.Button, QColor("#f0f0f0"))
    paleta_clara.setColor(QPalette.ButtonText, QColor("#000000"))
    app.setPalette(paleta_clara)

    ventana = VentanaEnvioTeclas()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
