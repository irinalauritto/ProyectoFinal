"""
emg_plot.py

Visualización en tiempo real de la señal EMG (ENV) recibida desde la ESP32
por puerto serie.
Adquisición, graficación y  procesamiento  de la señal EMG (ENV) en tiempo real.

"""

# Importación de librerías
import sys
from collections import deque

import serial
import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Definción de constantes globales
SERIAL_PORT = "COM8"   # Ajustar según el puerto asignado a la ESP32 (Administrador de dispositivos de Windows)
BAUD_RATE = 115200
BUFFER_SIZE = 2000    # Cantidad de muestras visibles en el gráfico
UPDATE_MS = 20       # Intervalo de refresco del gráfico (ms)


def main():
    app = QApplication(sys.argv) #Creación de la aplicación Qt

    # Apertura del puerto serie
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
    except serial.SerialException as e:
        print(f"No se pudo abrir el puerto {SERIAL_PORT}: {e}")
        sys.exit(1)

    # Grafico en tiempo real usando PyQtGraph
    win = pg.GraphicsLayoutWidget(show=True, title="Señal EMG en tiempo real")
    win.resize(900, 500)
    plot = win.addPlot(title="MyoWare 2.0 - ENV")
    plot.setLabel("left", "Amplitud (unidades ADC)")
    plot.setLabel("bottom", "Muestras")
    plot.setXRange(0, BUFFER_SIZE - 1, padding=0)
    plot.enableAutoRange(axis="y")
    curve = plot.plot(pen=pg.mkPen(color="g", width=1))

    # Inicialización del buffer circular para almacenar las muestras de la señal EMG
    buffer = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

    def update():
        # Lee todas las líneas disponibles en el buffer serie sin bloquear
        while ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if line.isdigit():
                buffer.append(int(line))
        curve.setData(list(buffer))

    # Configuración del temporizador para actualizar el gráfico
    timer = QTimer()
    timer.timeout.connect(update)
    timer.start(UPDATE_MS)

    exit_code = app.exec()
    ser.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
