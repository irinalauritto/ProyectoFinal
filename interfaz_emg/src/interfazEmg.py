"""
interfazEmg.py

Visualización en tiempo real de la señal EMG (ENV) recibida desde la ESP32
por puerto serie, con funcionamiento como switch de accionamiento por EMG
para controlar Asterics Grid.

Incluye: calibración de umbral en reposo, prueba de validación guiada de
3 contracciones, detección de eventos por flanco ascendente con tiempo
refractario, envío de tecla + sonido de retroalimentación por evento, y
registro de sesión en un archivo JSON.

"""

# Importación de librerías
import sys
import os
import json
import time
from collections import deque
from datetime import datetime

import numpy as np
import serial
from scipy.signal import butter, iirnotch, tf2sos, sosfilt, sosfilt_zi
import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QProgressBar,
    QComboBox,
    QMessageBox,
    QDialog,
)
from PySide6.QtGui import QPalette, QColor
from pynput.keyboard import Controller as ControladorTeclado, Key

# Interfaz clara (fondo blanco) en vez del tema oscuro por defecto de pyqtgraph
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")

# Retroalimentación sonora: winsound es de la biblioteca estándar en Windows
# (no agrega dependencias nuevas) y no bloquea el hilo principal.
try:
    import winsound
    _SONIDO_DISPONIBLE = True
except ImportError:  # en plataformas no Windows simplemente se omite el sonido
    _SONIDO_DISPONIBLE = False


# Definición de constantes globales
SERIAL_PORT = "COM8"   # Ajustar según el puerto asignado a la ESP32 (Administrador de dispositivos de Windows)
BAUD_RATE = 115200
BUFFER_SIZE = 2000    # Cantidad de muestras visibles en el gráfico
UPDATE_MS = 20        # Intervalo de refresco del gráfico (ms)

# Modo de la señal recibida por puerto serie:
#   "ENVOLVENTE": se usa tal cual el valor que manda el sensor (salida ENV
#                 del MyoWare 2.0, ya rectificada y filtrada en hardware).
#                 Es el modo que se usó hasta ahora.
#   "RAW": el valor recibido es la señal EMG cruda (sin rectificar). La
#          envolvente se calcula por software en esta interfaz: pasaaltos
#          1 Hz (elimina la continua/bias del ADC) -> notch 50 Hz (elimina
#          la interferencia de la red eléctrica) -> rectificado de onda
#          completa -> pasabajos 6 Hz (genera la envolvente).
# Se elige editando esta constante antes de correr la interfaz, según a qué
# salida del sensor (SIG/ENV o RAW) esté conectado el GPIO de la ESP32.
MODO_SENAL = "RAW"   # "ENVOLVENTE" o "RAW"

FS_HZ = 500.0          # Frecuencia de muestreo aproximada del firmware (SAMPLE_DELAY_MS = 2 ms)
HP_CORTE_HZ = 1.0      # Pasaaltos: elimina la componente continua/bias de la señal cruda
NOTCH_FREQ_HZ = 50.0   # Notch: frecuencia de la red eléctrica en Argentina (usar 60 Hz en países con esa red)
NOTCH_Q = 30.0         # Factor de calidad del notch: cuanto más alto, más angosto (afecta menos a la señal vecina)
LP_CORTE_HZ = 3.0      # Pasabajos: genera la envolvente a partir de la señal rectificada
                       # (bajado de 6 a 3 Hz: con EMG cruda real, 6 Hz + MA de 20 ms dejaba
                       # pasar demasiado temblor; a costa de ~45 ms más de retardo, la
                       # envolvente queda notablemente más limpia — ver conversación)

VENTANA_MA_MUESTRAS = 30   # Tamaño de la ventana del filtro de media móvil (a ~500 Hz, ~60 ms)

# Histéresis del detector: el umbral de "reactivación" (para volver a poder
# disparar) queda esta fracción por debajo del umbral de disparo, dentro del
# margen (umbral - media_reposo). Sin esto, el ruido de una señal real puede
# hacer que la envolvente oscile alrededor del umbral durante una misma
# contracción y dispare varias veces seguidas.
HISTERESIS_FRACCION = 0.5

# Conversión ADC -> mV: ESP32-C6, ADC de 12 bits (0-4095) con atenuación de
# 12 dB, rango completo 0-3.3 V (ver emg_esp32.c).
ADC_RESOLUCION = 4095
ADC_VREF_MV = 3300.0


def _adc_a_mv(valor_adc):
    return valor_adc * ADC_VREF_MV / ADC_RESOLUCION

CALIBRACION_DURACION_S = 30     # Duración de la ventana de calibración en reposo

K_MIN, K_MAX, K_DEFAULT = 1.0, 3.0, 3.0
REFRACTARIO_MIN_MS, REFRACTARIO_MAX_MS, REFRACTARIO_DEFAULT_MS = 100, 2500, 500
DURACION_TECLA_MIN_MS, DURACION_TECLA_MAX_MS, DURACION_TECLA_DEFAULT_MS = 50, 5000, 200

LOGS_DIR = "logs"

TECLAS_DISPONIBLES = {
    "Enter": Key.enter,
    "Espacio": Key.space,
    "Flecha derecha": Key.right,
}


class RegistroSesion:
    """Registra en un archivo JSON los eventos de una sesión (calibración,
    cambios de parámetros, pruebas de validación y activaciones)."""

    def __init__(self, nombre_paciente):
        os.makedirs(LOGS_DIR, exist_ok=True)
        ahora = datetime.now()
        nombre_sanitizado = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in nombre_paciente.strip()
        ) or "paciente"
        self.ruta = os.path.join(
            LOGS_DIR, f"{nombre_sanitizado}_{ahora.strftime('%Y%m%d_%H%M%S')}.json"
        )
        self.datos = {
            "paciente": nombre_paciente,
            "inicio_sesion": ahora.isoformat(timespec="seconds"),
            "eventos": [],
        }
        self._guardar()

    def registrar(self, tipo, **campos):
        evento = {"tipo": tipo, "timestamp": datetime.now().isoformat(timespec="seconds")}
        evento.update(campos)
        self.datos["eventos"].append(evento)
        self._guardar()

    def _guardar(self):
        # Se reescribe el archivo completo en cada registro: las sesiones son
        # cortas y esto evita dejar el JSON a medio escribir ante un cierre abrupto.
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(self.datos, f, ensure_ascii=False, indent=2)


class DialogoDatosPaciente(QDialog):
    """Ventana emergente inicial: pide el nombre del paciente/voluntario antes
    de abrir la interfaz principal. La fecha y hora se toman automáticamente."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Datos del paciente")
        self.setModal(True)
        self.nombre_paciente = ""

        layout = QVBoxLayout(self)
        formulario = QFormLayout()

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del paciente/voluntario")
        formulario.addRow("Paciente:", self.txt_nombre)
        formulario.addRow("Fecha y hora:", QLabel(datetime.now().strftime("%d/%m/%Y %H:%M")))
        layout.addLayout(formulario)

        botones = QHBoxLayout()
        botones.addStretch()
        btn_continuar = QPushButton("Continuar")
        btn_continuar.clicked.connect(self._confirmar)
        botones.addWidget(btn_continuar)
        layout.addLayout(botones)

    def _confirmar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Falta el nombre", "Ingrese el nombre del paciente/voluntario.")
            self.txt_nombre.setFocus()
            return
        self.nombre_paciente = nombre
        self.accept()


class VentanaEmg(QWidget):
    """Ventana principal: gráfico en tiempo real + panel de control del switch EMG."""

    def __init__(self, ser, nombre_paciente):
        super().__init__()
        self.nombre_paciente = nombre_paciente
        self.setWindowTitle(f"Switch EMG — MyoWare 2.0 — {nombre_paciente}")
        self.resize(1100, 700)

        self.ser = ser
        self.teclado = ControladorTeclado()
        self.tecla_activa = None  # tecla actualmente "presionada" por un evento, o None

        # --- Buffer de la señal y marcadores de eventos sobre el gráfico ---
        self.buffer = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
        self.marcadores_x = []
        self.marcadores_y = []

        # --- Generación de envolvente por software (sólo si MODO_SENAL == "RAW") ---
        if MODO_SENAL == "RAW":
            self._sos_pasaaltos = butter(2, HP_CORTE_HZ, btype="highpass", fs=FS_HZ, output="sos")
            self._sos_notch = tf2sos(*iirnotch(NOTCH_FREQ_HZ, NOTCH_Q, fs=FS_HZ))
            self._sos_pasabajos = butter(2, LP_CORTE_HZ, btype="lowpass", fs=FS_HZ, output="sos")
            # El estado inicial del pasaaltos se fija recién con la primera
            # muestra real (ver _generar_envolvente): si se asumiera un
            # historial en 0, el bias del ADC (~2000 counts) generaría un
            # escalón artificial y un transitorio espurio de casi 1 s al
            # arrancar la aplicación. El notch y el pasabajos no tienen ese
            # problema porque reciben una señal ya centrada en 0 (la salida
            # del pasaaltos), así que su estado inicial puede quedar en 0.
            self._zi_pasaaltos = None
            self._zi_notch = sosfilt_zi(self._sos_notch)
            self._zi_pasabajos = sosfilt_zi(self._sos_pasabajos)

        # --- Filtro de media móvil aplicado a cada muestra (tras generar la envolvente si corresponde) ---
        self.ventana_ma = deque(maxlen=VENTANA_MA_MUESTRAS)

        # --- Diagnóstico: frecuencia de muestreo real medida ---
        # FS_HZ es una suposición (2 ms de delay en el firmware = ~500 Hz
        # nominales); si la tasa real difiere, los filtros quedan diseñados
        # para un corte real distinto del que dicen sus constantes. Se mide
        # la tasa real cada 1 s a partir de las muestras efectivamente
        # recibidas, para poder comparar contra FS_HZ.
        self._contador_muestras_fs = 0
        self._tiempo_ultima_medicion_fs = time.monotonic()

        # --- Parámetros configurables ---
        self.k = K_DEFAULT
        self.refractario_ms = REFRACTARIO_DEFAULT_MS

        # --- Estado de calibración ---
        self.calibrando = False
        self.calibracion_muestras = []
        self.calibracion_inicio = None
        self.media_reposo = None
        self.sd_reposo = None
        self.umbral = None
        self.umbral_reactivacion = None

        # --- Estado de detección de eventos (flanco ascendente + histéresis + refractario) ---
        # armado=True: la señal está en zona de reposo, lista para detectar
        # un nuevo cruce ascendente. Se desarma apenas cruza el umbral hacia
        # arriba, y sólo vuelve a armarse cuando la señal cae por debajo del
        # umbral de reactivación (más bajo que el de disparo).
        self.armado = True
        self.ultimo_evento_tiempo = None

        # --- Estado de la prueba de validación guiada ---
        # El avance de intento lo decide el terapeuta a mano (botón "Registrar
        # intento"), no un temporizador: cada paciente contrae y relaja a su
        # propio ritmo.
        self.validando = False
        self.esperando_intento = False
        self.intento_actual = 0
        self.eventos_intento_actual = 0
        self.eventos_por_intento = []

        # El nombre ya se pidió en el diálogo inicial: la sesión arranca a
        # registrarse desde que se abre la ventana, no recién en la primera
        # calibración.
        self.registro = RegistroSesion(nombre_paciente)

        self._armar_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(UPDATE_MS)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _armar_ui(self):
        # Layout de dos columnas: gráfico chico a la izquierda, controles
        # (más anchos y prominentes, sobre todo "Parámetros") a la derecha.
        layout_principal = QHBoxLayout(self)

        columna_izquierda = QVBoxLayout()

        # Gráfico en tiempo real (se mantiene la base existente con pyqtgraph)
        self.win = pg.GraphicsLayoutWidget()
        self.win.setBackground("w")
        self.win.setMinimumHeight(280)
        self.win.setMaximumWidth(420)
        self.plot = self.win.addPlot(title="MyoWare 2.0 - ENV")
        self.plot.setLabel("left", "Amplitud (unidades ADC)")
        self.plot.setLabel("bottom", "Muestras")
        self.plot.setXRange(0, BUFFER_SIZE - 1, padding=0)
        self.plot.enableAutoRange(axis="y")  # visualización original: autoescala en cada refresco
        # Intentos de eje Y fijo / en mV (a pedido puntual, luego revertidos): se
        # dejan comentados en vez de borrarlos.
        # self.plot.enableAutoRange(axis="y", enable=False)
        # self.plot.setYRange(0, ADC_VREF_MV, padding=0)  # rango completo del ADC (0-3300 mV)
        # self.plot.setYRange(0, 1000, padding=0)  # acotado a 0-1000 mV para ver mejor la envolvente
        self.curve = self.plot.plot(pen=pg.mkPen(color="b", width=1))
        self.scatter_eventos = pg.ScatterPlotItem(size=10, brush=pg.mkBrush("r"), pen=pg.mkPen("r"))
        self.plot.addItem(self.scatter_eventos)
        self.linea_umbral = None  # se crea recién cuando hay un umbral calculado
        self.linea_reactivacion = None  # ídem, umbral de reactivación (histéresis)
        columna_izquierda.addWidget(self.win)

        # Diagnóstico: frecuencia de muestreo real vs. la asumida en FS_HZ
        self.lbl_fs = QLabel(f"Frecuencia de muestreo real: midiendo... (asumida FS_HZ = {FS_HZ:.0f} Hz)")
        self.lbl_fs.setStyleSheet("color: #555555; font-size: 9pt;")
        self.lbl_fs.setWordWrap(True)
        columna_izquierda.addWidget(self.lbl_fs)
        columna_izquierda.addStretch()

        layout_principal.addLayout(columna_izquierda, 1)

        columna_derecha = QVBoxLayout()

        # --- Paciente (el nombre se pidió en el diálogo inicial) ---
        self.lbl_paciente = QLabel(f"Paciente: {self.nombre_paciente}")
        self.lbl_paciente.setStyleSheet("font-size: 11pt; font-weight: bold;")
        columna_derecha.addWidget(self.lbl_paciente)

        # --- Calibración ---
        grupo_calib = QGroupBox(f"Calibración ({CALIBRACION_DURACION_S} s en reposo)")
        v_calib = QVBoxLayout(grupo_calib)
        self.btn_calibrar = QPushButton("Iniciar calibración")
        self.barra_calibracion = QProgressBar()
        self.barra_calibracion.setRange(0, CALIBRACION_DURACION_S)
        self.lbl_calibracion = QLabel("Sin calibrar")
        self.lbl_umbral = QLabel("Umbral actual: -")
        v_calib.addWidget(self.btn_calibrar)
        v_calib.addWidget(self.barra_calibracion)
        v_calib.addWidget(self.lbl_calibracion)
        v_calib.addWidget(self.lbl_umbral)
        columna_derecha.addWidget(grupo_calib)

        # --- Parámetros ajustables en cualquier momento: grupo destacado, ---
        # --- es el que más va a tocar el terapeuta durante la sesión.     ---
        grupo_param = QGroupBox("Parámetros")
        grupo_param.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 13pt; border: 2px solid #2E5395;
                        border-radius: 6px; margin-top: 12px; padding-top: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #2E5395; }
            QGroupBox QLabel, QGroupBox QComboBox, QGroupBox QSpinBox, QGroupBox QDoubleSpinBox {
                font-size: 11pt; font-weight: normal; }
        """)
        f_param = QFormLayout(grupo_param)
        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(K_MIN, K_MAX)
        self.spin_k.setSingleStep(0.1)
        self.spin_k.setDecimals(1)
        self.spin_k.setValue(K_DEFAULT)
        self.spin_refractario = QSpinBox()
        self.spin_refractario.setRange(REFRACTARIO_MIN_MS, REFRACTARIO_MAX_MS)
        self.spin_refractario.setSingleStep(50)
        self.spin_refractario.setValue(REFRACTARIO_DEFAULT_MS)
        self.combo_tecla = QComboBox()
        self.combo_tecla.addItems(list(TECLAS_DISPONIBLES.keys()))
        self.spin_duracion_tecla = QSpinBox()
        self.spin_duracion_tecla.setRange(DURACION_TECLA_MIN_MS, DURACION_TECLA_MAX_MS)
        self.spin_duracion_tecla.setSingleStep(50)
        self.spin_duracion_tecla.setValue(DURACION_TECLA_DEFAULT_MS)
        self.spin_duracion_tecla.setSuffix(" ms")
        f_param.addRow("k (sensibilidad):", self.spin_k)
        f_param.addRow("Refractario (ms):", self.spin_refractario)
        f_param.addRow("Tecla enviada:", self.combo_tecla)
        f_param.addRow("Duración de la pulsación:", self.spin_duracion_tecla)
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setStyleSheet("color: darkorange; font-weight: bold; font-size: 11pt;")
        self.lbl_aviso.setWordWrap(True)
        self.lbl_aviso.setVisible(False)
        f_param.addRow(self.lbl_aviso)
        columna_derecha.addWidget(grupo_param)

        # --- Prueba de validación guiada ---
        grupo_prueba = QGroupBox("Prueba de validación (3 contracciones)")
        v_prueba = QVBoxLayout(grupo_prueba)
        self.btn_prueba = QPushButton("Iniciar prueba")
        self.btn_prueba.setEnabled(False)
        self.btn_omitir_prueba = QPushButton("Omitir prueba")
        self.btn_omitir_prueba.setEnabled(False)
        self.btn_siguiente_intento = QPushButton("Registrar intento y continuar")
        self.btn_siguiente_intento.setEnabled(False)
        self.lbl_prueba = QLabel("Requiere calibración previa")
        self.lbl_prueba.setWordWrap(True)
        v_prueba.addWidget(self.btn_prueba)
        v_prueba.addWidget(self.btn_omitir_prueba)
        v_prueba.addWidget(self.btn_siguiente_intento)
        v_prueba.addWidget(self.lbl_prueba)
        columna_derecha.addWidget(grupo_prueba)

        columna_derecha.addStretch()

        layout_principal.addLayout(columna_derecha, 2)

        # Conexión de señales
        self.btn_calibrar.clicked.connect(self._iniciar_calibracion)
        self.spin_k.valueChanged.connect(self._on_k_cambiado)
        self.spin_refractario.valueChanged.connect(self._on_refractario_cambiado)
        self.btn_prueba.clicked.connect(self._iniciar_prueba_validacion)
        self.btn_omitir_prueba.clicked.connect(self._omitir_prueba)
        self.btn_siguiente_intento.clicked.connect(self._registrar_intento_actual)

    # ------------------------------------------------------------------
    # Lectura serie + procesamiento de cada muestra (llamado por QTimer)
    # ------------------------------------------------------------------
    def _tick(self):
        # Lee todas las líneas disponibles en el buffer serie sin bloquear
        while self.ser.in_waiting:
            linea = self.ser.readline().decode(errors="ignore").strip()
            if not linea.isdigit():
                continue
            # valor = _adc_a_mv(int(linea))  # conversión a mV (a pedido puntual, luego revertida)
            valor_crudo = int(linea)
            self._contador_muestras_fs += 1

            if MODO_SENAL == "RAW":
                # Señal EMG cruda: se genera la envolvente por software.
                valor_muestra = self._generar_envolvente(valor_crudo)
            else:
                # Señal ya envuelta por el sensor (salida ENV del MyoWare).
                valor_muestra = valor_crudo

            # Filtro de media móvil: suaviza el ruido de muestra a muestra
            # antes de graficar y de usar la señal para calibración/detección.
            self.ventana_ma.append(valor_muestra)
            valor = sum(self.ventana_ma) / len(self.ventana_ma)

            marca_tiempo = time.monotonic()

            self.buffer.append(valor)
            self._desplazar_marcadores()

            if self.calibrando:
                self.calibracion_muestras.append(valor)
            elif self.umbral is not None:
                self._procesar_deteccion(valor, marca_tiempo)

        self.curve.setData(list(self.buffer))
        self.scatter_eventos.setData(x=self.marcadores_x, y=self.marcadores_y)

        if self.calibrando:
            self._actualizar_progreso_calibracion()
        if self.esperando_intento:
            self._actualizar_contador_intento()

        self._actualizar_fs_medida()

    def _actualizar_fs_medida(self):
        ahora = time.monotonic()
        transcurrido = ahora - self._tiempo_ultima_medicion_fs
        if transcurrido >= 1.0:
            fs_medida = self._contador_muestras_fs / transcurrido
            self.lbl_fs.setText(
                f"Frecuencia de muestreo real: {fs_medida:.0f} Hz  (asumida FS_HZ = {FS_HZ:.0f} Hz)"
            )
            self._contador_muestras_fs = 0
            self._tiempo_ultima_medicion_fs = ahora

    def _desplazar_marcadores(self):
        # El buffer tiene largo fijo: la muestra más nueva siempre queda en
        # el índice BUFFER_SIZE-1, por lo que los marcadores previos deben
        # correrse una posición hacia la izquierda en cada muestra nueva.
        nuevos_x, nuevos_y = [], []
        for x, y in zip(self.marcadores_x, self.marcadores_y):
            x -= 1
            if x >= 0:
                nuevos_x.append(x)
                nuevos_y.append(y)
        self.marcadores_x, self.marcadores_y = nuevos_x, nuevos_y

    def _generar_envolvente(self, valor_crudo):
        if self._zi_pasaaltos is None:
            # Primera muestra real: se fija el estado inicial del pasaaltos
            # a partir de este valor para no generar un escalón artificial.
            self._zi_pasaaltos = sosfilt_zi(self._sos_pasaaltos) * valor_crudo

        # Pasaaltos 1 Hz: elimina la continua/bias del ADC y centra la señal
        # cruda en torno a 0 (recién ahí tiene sentido rectificar).
        filtrado_hp, self._zi_pasaaltos = sosfilt(self._sos_pasaaltos, [valor_crudo], zi=self._zi_pasaaltos)
        # Notch 50 Hz: elimina la interferencia de la red eléctrica.
        filtrado_notch, self._zi_notch = sosfilt(self._sos_notch, filtrado_hp, zi=self._zi_notch)
        # Rectificado de onda completa.
        rectificado = abs(filtrado_notch[0])
        # Pasabajos 6 Hz: suaviza el rectificado y genera la envolvente.
        envolvente, self._zi_pasabajos = sosfilt(self._sos_pasabajos, [rectificado], zi=self._zi_pasabajos)
        return envolvente[0]

    # ------------------------------------------------------------------
    # Detección de eventos: flanco ascendente + tiempo refractario
    # ------------------------------------------------------------------
    def _procesar_deteccion(self, valor, marca_tiempo):
        # Seguro de flanco ascendente con histéresis (disparador de Schmitt):
        # mientras self.armado es True la señal está en zona de reposo y se
        # vigila el cruce hacia arriba del umbral de disparo. En cuanto cruza,
        # se desarma de inmediato: ya no se vuelve a evaluar un nuevo evento
        # aunque la señal siga oscilando por encima del umbral (eso evita
        # "rebotes" — varios disparos dentro de una misma contracción por
        # ruido de la señal real). Sólo se rearma cuando la señal cae por
        # debajo del umbral de reactivación, más bajo que el de disparo.
        if self.armado:
            if valor >= self.umbral:
                refractario_cumplido = (
                    self.ultimo_evento_tiempo is None
                    or (marca_tiempo - self.ultimo_evento_tiempo) * 1000.0 >= self.refractario_ms
                )
                if refractario_cumplido:
                    self._aceptar_evento(marca_tiempo, valor)
                self.armado = False
        else:
            if valor <= self.umbral_reactivacion:
                self.armado = True

    def _aceptar_evento(self, marca_tiempo, valor):
        self.ultimo_evento_tiempo = marca_tiempo

        # a) marca visual en el gráfico
        self.marcadores_x.append(BUFFER_SIZE - 1)
        self.marcadores_y.append(valor)

        # b) pulsación de tecla simulada (captada por Asterics Grid como switch)
        tecla = TECLAS_DISPONIBLES.get(self.combo_tecla.currentText(), Key.enter)
        self._enviar_tecla(tecla)

        # c) retroalimentación sonora
        if _SONIDO_DISPONIBLE:
            winsound.MessageBeep(winsound.MB_OK)

        if self.registro is not None:
            # self.registro.registrar("activacion", valor=round(valor, 2), umbral=round(self.umbral, 2))  # variante con valor en mV
            self.registro.registrar("activacion", valor=valor, umbral=round(self.umbral, 2))

        if self.esperando_intento:
            self.eventos_intento_actual += 1

    def _enviar_tecla(self, tecla):
        if self.tecla_activa is not None:
            # Un evento nuevo llegó antes de soltar la tecla del evento
            # anterior (duración configurada mayor que el refractario):
            # se suelta ya la anterior para no dejarla "pegada".
            self.teclado.release(self.tecla_activa)

        self.tecla_activa = tecla
        self.teclado.press(tecla)

        # Se usa QTimer.singleShot en vez de time.sleep para no bloquear la
        # interfaz mientras se mantiene la tecla "pulsada".
        duracion_ms = self.spin_duracion_tecla.value()
        QTimer.singleShot(duracion_ms, self._soltar_tecla)

    def _soltar_tecla(self):
        if self.tecla_activa is not None:
            self.teclado.release(self.tecla_activa)
            self.tecla_activa = None

    # ------------------------------------------------------------------
    # Calibración
    # ------------------------------------------------------------------
    def _iniciar_calibracion(self):
        # El nombre del paciente ya se pidió en el diálogo inicial y el
        # registro de sesión ya está creado (ver __init__).
        self.calibrando = True
        self.calibracion_muestras = []
        self.calibracion_inicio = time.monotonic()
        self.btn_calibrar.setEnabled(False)
        self.barra_calibracion.setValue(0)
        self.lbl_calibracion.setText("Calibrando... mantenga el músculo relajado.")

    def _actualizar_progreso_calibracion(self):
        transcurrido = time.monotonic() - self.calibracion_inicio
        self.barra_calibracion.setValue(min(int(transcurrido), CALIBRACION_DURACION_S))
        restante = max(0, CALIBRACION_DURACION_S - transcurrido)
        self.lbl_calibracion.setText(f"Calibrando... manténgase relajado. Quedan {restante:0.0f} s")
        if transcurrido >= CALIBRACION_DURACION_S:
            self._finalizar_calibracion()

    def _finalizar_calibracion(self):
        self.calibrando = False
        self.btn_calibrar.setEnabled(True)
        self.barra_calibracion.setValue(CALIBRACION_DURACION_S)

        muestras = self.calibracion_muestras
        if len(muestras) < 2:
            QMessageBox.critical(
                self, "Calibración fallida",
                "No se recibieron suficientes muestras durante la calibración. "
                "Verifique la conexión serie e intente nuevamente."
            )
            self.lbl_calibracion.setText("Calibración fallida — reintentar")
            return

        self.media_reposo = float(np.mean(muestras))
        self.sd_reposo = float(np.std(muestras, ddof=1))
        self._recalcular_umbral()

        self.lbl_calibracion.setText(
            f"Calibración completa ({len(muestras)} muestras). "
            f"Media={self.media_reposo:.1f}  SD={self.sd_reposo:.1f}"
        )
        if self.registro is not None:
            self.registro.registrar(
                "calibracion",
                media_reposo=round(self.media_reposo, 2),
                sd_reposo=round(self.sd_reposo, 2),
                k=self.k,
                umbral=round(self.umbral, 2),
                n_muestras=len(muestras),
            )

        self.btn_prueba.setEnabled(True)
        self.btn_omitir_prueba.setEnabled(True)
        self.lbl_prueba.setText("Calibración lista. Puede iniciar la prueba de validación.")

    def _recalcular_umbral(self):
        self.umbral = self.media_reposo + self.k * self.sd_reposo
        margen = self.umbral - self.media_reposo
        self.umbral_reactivacion = self.umbral - HISTERESIS_FRACCION * margen

        if self.linea_umbral is None:
            self.linea_umbral = pg.InfiniteLine(pos=self.umbral, angle=0, pen=pg.mkPen(color="r", width=2))
            self.plot.addItem(self.linea_umbral)
        else:
            self.linea_umbral.setValue(self.umbral)

        if self.linea_reactivacion is None:
            self.linea_reactivacion = pg.InfiniteLine(
                pos=self.umbral_reactivacion, angle=0, pen=pg.mkPen(color="orange", width=1)
            )
            self.plot.addItem(self.linea_reactivacion)
        else:
            self.linea_reactivacion.setValue(self.umbral_reactivacion)

        self.lbl_umbral.setText(
            f"Umbral de disparo: {self.umbral:.1f}  |  Umbral de reactivación: {self.umbral_reactivacion:.1f}  "
            f"(media={self.media_reposo:.1f}, SD={self.sd_reposo:.1f}, k={self.k:.1f})"
        )

    # ------------------------------------------------------------------
    # Ajuste libre de parámetros (k y refractario) durante la sesión
    # ------------------------------------------------------------------
    def _on_k_cambiado(self, valor):
        self.k = valor
        if self.media_reposo is None:
            return  # todavía no hay calibración: nada que recalcular ni registrar
        self._recalcular_umbral()
        if self.registro is not None:
            self.registro.registrar("cambio_parametro", parametro="k", valor=valor, modificado_por="terapeuta")
        self._mostrar_aviso_repetir_prueba()

    def _on_refractario_cambiado(self, valor):
        self.refractario_ms = valor
        if self.umbral is None:
            return  # todavía no hay calibración: nada que registrar
        if self.registro is not None:
            self.registro.registrar(
                "cambio_parametro", parametro="refractario_ms", valor=valor, modificado_por="terapeuta"
            )
        self._mostrar_aviso_repetir_prueba()

    def _mostrar_aviso_repetir_prueba(self):
        self.lbl_aviso.setText("⚠ Parámetros modificados: se recomienda repetir la prueba de validación.")
        self.lbl_aviso.setVisible(True)

    def _ocultar_aviso_repetir_prueba(self):
        self.lbl_aviso.setVisible(False)

    # ------------------------------------------------------------------
    # Prueba de validación guiada (3 contracciones)
    # ------------------------------------------------------------------
    def _iniciar_prueba_validacion(self):
        if self.umbral is None:
            QMessageBox.warning(self, "Falta calibrar", "Debe completar la calibración antes de ejecutar la prueba.")
            return

        self.validando = True
        self.intento_actual = 0
        self.eventos_por_intento = []
        self.btn_prueba.setEnabled(False)
        self.btn_omitir_prueba.setEnabled(False)
        self._ocultar_aviso_repetir_prueba()
        self._siguiente_intento()

    def _siguiente_intento(self):
        self.intento_actual += 1
        if self.intento_actual > 3:
            self._finalizar_prueba_validacion()
            return
        self.eventos_intento_actual = 0
        self.esperando_intento = True
        self.btn_siguiente_intento.setEnabled(True)
        self._actualizar_contador_intento()

    def _actualizar_contador_intento(self):
        # Se refresca en cada tick para que el conteo de eventos en vivo se
        # vea actualizado mientras el paciente contrae el músculo.
        self.lbl_prueba.setText(
            f"Intento {self.intento_actual}/3: contraiga y relaje el músculo, luego presione "
            f"\"Registrar intento y continuar\" ({self.eventos_intento_actual} evento(s) detectado(s))"
        )

    def _registrar_intento_actual(self):
        if not self.esperando_intento:
            return
        self.esperando_intento = False
        self.btn_siguiente_intento.setEnabled(False)
        self.eventos_por_intento.append(self.eventos_intento_actual)
        if self.registro is not None:
            self.registro.registrar(
                "intento_validacion",
                intento=self.intento_actual,
                eventos=self.eventos_intento_actual,
            )
        self._siguiente_intento()

    def _finalizar_prueba_validacion(self):
        self.validando = False
        self.esperando_intento = False
        self.btn_siguiente_intento.setEnabled(False)
        correcta = all(n == 1 for n in self.eventos_por_intento)
        resumen = " | ".join(f"Intento {i + 1}: {n} evento(s)" for i, n in enumerate(self.eventos_por_intento))
        icono = "✔" if correcta else "⚠"
        self.lbl_prueba.setText(f"{icono} Prueba finalizada — {resumen}")

        if self.registro is not None:
            self.registro.registrar(
                "prueba_validacion",
                resultado="completada",
                eventos_por_intento=self.eventos_por_intento,
                correcta=correcta,
                k=self.k,
                refractario_ms=self.refractario_ms,
            )

        self.btn_prueba.setEnabled(True)
        self.btn_omitir_prueba.setEnabled(True)

    def _omitir_prueba(self):
        if self.registro is not None:
            self.registro.registrar(
                "prueba_validacion", resultado="omitida", k=self.k, refractario_ms=self.refractario_ms
            )
        self._ocultar_aviso_repetir_prueba()

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self.timer.stop()
        if self.tecla_activa is not None:
            self.teclado.release(self.tecla_activa)
            self.tecla_activa = None
        if self.ser.is_open:
            self.ser.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)  # Creación de la aplicación Qt

    # Fuerza una paleta clara para toda la interfaz, sin depender de si
    # Windows tiene activado el modo oscuro.
    app.setStyle("Fusion")
    paleta_clara = QPalette()
    paleta_clara.setColor(QPalette.Window, QColor("#ffffff"))
    paleta_clara.setColor(QPalette.WindowText, QColor("#000000"))
    paleta_clara.setColor(QPalette.Base, QColor("#ffffff"))
    paleta_clara.setColor(QPalette.AlternateBase, QColor("#f0f0f0"))
    paleta_clara.setColor(QPalette.Text, QColor("#000000"))
    paleta_clara.setColor(QPalette.Button, QColor("#f0f0f0"))
    paleta_clara.setColor(QPalette.ButtonText, QColor("#000000"))
    app.setPalette(paleta_clara)

    # Ventana emergente inicial: pide el nombre del paciente antes de abrir
    # la interfaz principal (la fecha/hora se toma automáticamente).
    dialogo = DialogoDatosPaciente()
    if dialogo.exec() != QDialog.Accepted:
        sys.exit(0)

    # Apertura del puerto serie
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
    except serial.SerialException as e:
        print(f"No se pudo abrir el puerto {SERIAL_PORT}: {e}")
        sys.exit(1)

    ventana = VentanaEmg(ser, dialogo.nombre_paciente)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
