# Diagramas de flujo — Control por EMG

Basados en el código actual de:

- `firmware/emg_esp32/main/emg_esp32.c` (adquisición)
- `interfaz/pages/emg_page.py` (inicio de sesión)
- `interfaz_emg/emg/interfazEmg.py` → `EmgEngine` (lógica)
- `interfaz/pages/emg/emg_main_page.py` y `emg_live_widget.py` (pantalla)

Se pueden pegar en [mermaid.live](https://mermaid.live) para exportarlos como PNG/SVG.

---

## 1. Flujo general de la sesión EMG

```mermaid
flowchart TD
    A([Inicio: el operador elige EMG para el paciente]) --> B{¿Ya hay una<br/>sesión EMG activa?}
    B -- Sí --> B1[Mostrar aviso de<br/>calibración requerida] --> P
    B -- No --> C[Detección automática del puerto:<br/>probar cada puerto serie y buscar<br/>≥2 líneas numéricas de la ESP32]
    C --> D{¿Se encontró<br/>la ESP32?}
    D -- No --> E[Diálogo: elegir puerto<br/>manualmente]
    E --> F{¿Puerto<br/>elegido?}
    F -- No --> X([Fin: no se abre la pantalla EMG])
    D -- Sí --> G
    F -- Sí --> G[Abrir puerto serie<br/>115200 baudios]
    G --> H{¿Se pudo<br/>abrir?}
    H -- No --> H1[Mensaje de error] --> X
    H -- Sí --> I[Crear EmgEngine y EmgMainPage]
    I --> J["Vincular ficha del paciente:<br/>restaurar sensibilidad, refractario,<br/>tecla, duración y barrido<br/>(no el umbral)"]
    J --> K[Aviso: calibración requerida]
    K --> L[Arrancar timer de lectura<br/>cada 20 ms]
    L --> P

    P[Pantalla EMG: señal en vivo] --> Q[/Operador: Iniciar calibración/]
    Q --> R[Calibración 30 s en reposo<br/>ver diagrama 3]
    R --> S{¿Calibración<br/>exitosa?}
    S -- No --> Q
    S -- Sí --> T[Umbral calculado:<br/>se dibuja en el gráfico<br/>y se guarda en la ficha]
    T --> U{¿Prueba de<br/>validación?}
    U -- Omitir --> W
    U -- Iniciar --> V[Prueba de 3 contracciones<br/>ver diagrama 4]
    V --> V1{¿1 evento en<br/>cada intento?}
    V1 -- No --> V2[Ajustar sensibilidad<br/>y/o refractario] --> U
    V1 -- Sí --> W
    W[/Operador: Abrir AsTeRICS/] --> W1[Abrir AsTeRICS maximizado en el<br/>monitor del paciente y enviarle<br/>modo barrido, tiempo de barrido<br/>y duración de pulsación]
    W1 --> Y[Uso: cada contracción detectada<br/>envía una tecla a AsTeRICS]
    Y --> Z{¿Se cambian<br/>parámetros?}
    Z -- Sí --> Z1[Recalcular umbral, guardar en ficha<br/>y avisar: repetir validación] --> U
    Z -- No --> Y
    Y --> FIN([Cierre: detener timer, soltar tecla,<br/>cerrar puerto y AsTeRICS])
```

---

## 2. Adquisición y procesamiento de cada muestra

```mermaid
flowchart TD
    subgraph ESP32 [ESP32-C6 · firmware]
        E1([app_main]) --> E2[Configurar ADC1 canal 1 · GPIO1<br/>12 bits · atenuación 12 dB]
        E2 --> E3[Leer ADC 0–4095]
        E3 --> E4[Enviar por serie<br/>valor + salto de línea]
        E4 --> E5[Esperar 2 ms<br/>≈500 Hz]
        E5 --> E3
    end

    E4 -. USB serie .-> T1

    subgraph PC [PC · EmgEngine._tick cada 20 ms]
        T1([Tick del timer]) --> T2{¿Hay datos en<br/>el buffer serie?}
        T2 -- No --> T9
        T2 -- Sí --> T3[Leer una línea]
        T3 --> T4{¿Es un<br/>número?}
        T4 -- No --> T2
        T4 -- Sí --> T5[Convertir ADC → mV<br/>valor · 3300 / 4095]
        T5 --> F1[Pasaaltos 1 Hz<br/>quita la continua]
        F1 --> F2[Notch 50 Hz<br/>quita la red eléctrica]
        F2 --> F3[Rectificado de<br/>onda completa]
        F3 --> F4[Pasabajos 4 Hz<br/>= envolvente]
        F4 --> T6{Estado}
        T6 -- Calibrando --> T7[Guardar muestra para<br/>la calibración]
        T6 -- Calibrado --> T8[Detección de evento<br/>ver diagrama 5]
        T6 -- Sin calibrar --> T7b[Solo se grafica]
        T7 --> T2
        T8 --> T2
        T7b --> T2
        T9{¿Se leyeron<br/>muestras?} -- Sí --> T10[Emitir samples_ready:<br/>actualizar gráfico, marcar eventos]
        T9 -- No --> T11
        T10 --> T11{¿Calibrando?}
        T11 -- Sí --> T12[Actualizar progreso<br/>de calibración]
        T11 -- No --> T13([Fin del tick])
        T12 --> T13
    end
```

---

## 3. Calibración

```mermaid
flowchart TD
    C1([Iniciar calibración]) --> C2[calibrando = True<br/>vaciar muestras<br/>guardar hora de inicio]
    C2 --> C3[En cada tick: acumular<br/>muestras de envolvente]
    C3 --> C4[Informar progreso<br/>barra y segundos restantes]
    C4 --> C5{¿Pasaron<br/>30 s?}
    C5 -- No --> C3
    C5 -- Sí --> C6[calibrando = False]
    C6 --> C7{¿Hay al menos<br/>2 muestras?}
    C7 -- No --> C8([Calibración fallida:<br/>revisar conexión serie])
    C7 -- Sí --> C9[media = promedio de las muestras<br/>SD = desvío estándar]
    C9 --> C10["umbral = media + k · SD<br/>k = espejo de la sensibilidad<br/>(1 a 3)"]
    C10 --> C11["umbral de reactivación =<br/>umbral − 0,5 · (umbral − media)"]
    C11 --> C12([Calibración lista:<br/>mostrar umbral, habilitar prueba,<br/>guardar en ficha])
```

---

## 4. Prueba de validación (3 contracciones)

```mermaid
flowchart TD
    V1([Iniciar prueba]) --> V2{¿Está<br/>calibrado?}
    V2 -- No --> V3([Aviso: falta calibrar])
    V2 -- Sí --> V4[intento = 0<br/>lista de eventos vacía]
    V4 --> V5[intento = intento + 1]
    V5 --> V6{¿intento > 3?}
    V6 -- No --> V7[Eventos del intento = 0<br/>esperar contracción]
    V7 --> V8[Paciente contrae y relaja;<br/>cada evento detectado suma 1<br/>y se muestra en pantalla]
    V8 --> V9[/Operador: Registrar intento<br/>y continuar/]
    V9 --> V10[Guardar cantidad de eventos<br/>del intento]
    V10 --> V5
    V6 -- Sí --> V11{¿Exactamente 1 evento<br/>en cada intento?}
    V11 -- Sí --> V12([✔ Prueba correcta])
    V11 -- No --> V13([⚠ Prueba con fallas:<br/>ajustar sensibilidad/refractario])
    V12 --> V14[Guardar resultado en la ficha]
    V13 --> V14
```

---

## 5. Detección de eventos (comparador con histéresis + refractario)

```mermaid
flowchart TD
    D1([Nueva muestra de envolvente]) --> D2{¿Detector<br/>armado?}
    D2 -- Sí --> D3{¿valor ≥ umbral?}
    D3 -- No --> DN([No hay evento])
    D3 -- Sí --> D4[Desarmar detector]
    D4 --> D5{¿Pasó el tiempo<br/>refractario desde el<br/>último evento?}
    D5 -- No --> DN
    D5 -- Sí --> D6[EVENTO]
    D2 -- No --> D7{¿valor ≤ umbral<br/>de reactivación?}
    D7 -- Sí --> D8[Rearmar detector] --> DN
    D7 -- No --> DN

    D6 --> K1[Guardar hora del evento]
    K1 --> K2{¿Hay una tecla<br/>todavía presionada?}
    K2 -- Sí --> K3[Soltarla] --> K4
    K2 -- No --> K4[Traer AsTeRICS al frente<br/>y presionar la tecla elegida<br/>Enter / Espacio / Flecha derecha]
    K4 --> K5[Programar soltar la tecla<br/>tras la duración configurada]
    K5 --> K6[Beep de confirmación]
    K6 --> K7{¿Prueba de validación<br/>en curso?}
    K7 -- Sí --> K8[Sumar evento al intento]
    K7 -- No --> K9([Evento marcado en el gráfico])
    K8 --> K9
```
