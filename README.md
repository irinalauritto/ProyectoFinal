# Tesis - Control de tablero de comunicación AsTeRICS AAC mediante EMG y EEG

Trabajo de tesis para el control de un tablero de comunicación aumentativa y
alternativa (AsTeRICS AAC / AsTeRICS Grid) a partir de señales bioeléctricas.
Los módulos de EMG y EEG se desarrollan de forma independiente. Primera etapa: EMG.

## Estructura

- `firmware/emg_esp32/` – Sketch de la ESP32 que lee el MyoWare 2.0 (salida ENV) por ADC.
- `interfaz_emg/src/` – Aplicación en Python: adquisición serie, filtrado, detección
  de activación muscular y disparo del evento de teclado hacia AsTeRICS Grid.
- `interfaz_emg/data/` – Registros crudos de EMG para el análisis de la tesis.
- `interfaz_eeg/` – Reservado para el módulo de EEG (etapa posterior).
- `docs/` – Notas, diagramas y material de la tesis.

## Arquitectura del pipeline EMG

ESP32 + MyoWare 2.0 (ENV) → serie/BLE → interfaz Python (filtrado, envolvente,
umbral con antirrebote) → evento de teclado simulado (pynput) → AsTeRICS Grid
(input method "keypress") → avance del escaneo en el tablero.

## Entorno de desarrollo

```powershell
cd interfaz_emg
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
