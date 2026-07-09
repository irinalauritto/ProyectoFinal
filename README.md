# Proyecto Final - Control de un sistema de comunicación aumentativa y alternativa con señales electrofisiológicas

Proyecto final de la carrera de Bioingeniería para el control de un sistema de comunicación aumentativa y alternativa (AsTeRICS AAC) a partir de señales de electroencefalografía y electromiografía.

**Autora:** Irina E. Lauritto
**Directora:** L. Carolina Carrere

## Estructura 

- `firmware/emg_esp32/` – Firmware cargado en la  ESP32, el mismo lee la salida ENV del sensor MyoWare 2.0 por ADC.
- `interfaz_emg/src/` – Aplicación en Python: adquisición serie, filtrado, detección
  de activación muscular y disparo del evento de teclado para la activación de AsTeRICS Grid.
- `interfaz_eeg/` – Reservado para el módulo de EEG (aun no desarrollado).

## Arquitectura del pipeline EMG

ESP32 + MyoWare 2.0 (ENV) → serie → interfaz Python (filtrado, envolvente,
umbral con antirrebote) → evento de teclado simulado (pynput) → AsTeRICS Grid
(input method "keypress") → avance del escaneo en el tablero en modo barrido.
