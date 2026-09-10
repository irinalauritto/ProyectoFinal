# Prompt para Claude Code — Implementación de la interfaz (login + EMG + EEG/SSVEP)

> Copiá este archivo completo y pegalo como primer mensaje a Claude Code, ejecutándolo **desde la raíz de tu proyecto** (`interfaz_ssvep/` o donde esté `ssvep/app/`), para que tenga acceso directo a los archivos reales mencionados.

## Contexto

Este proyecto es una tesina de bioingeniería (UNER) que comanda un tablero AsTeRICS Grid de comunicación aumentativa y alternativa mediante tres señales electrofisiológicas: EMG y EEG/SSVEP (con CCA como clasificador). Ya existe una aplicación PySide6 funcional en `ssvep/app/`, con una arquitectura por capas (dominio / repositorios SQLAlchemy / clasificadores / widgets Qt) y una UI monolítica (`UserUI` en `user_ui.py`) que expone señales Qt para cada acción.

Diseñé, junto con Claude, un mockup de tres pantallas nuevas (login/gestión de paciente, control EMG y control EEG/SSVEP) que busca reemplazar/reordenar la UI actual. El mockup completo (HTML/CSS estático, sin lógica) está publicado como referencia visual acá:

**https://claude.ai/code/artifact/f6781e28-409b-40dd-a60e-c4c7f83f97e2**

Tu tarea es **implementar estas tres pantallas en PySide6, integradas con las clases reales del proyecto** — no truquear datos ni reinventar lógica que ya existe. Priorizá reutilizar y conectar sobre las clases/señales que ya están, y create solo lo que efectivamente falta (sobre todo: la gestión de pacientes guardados/nuevos, que es funcionalidad nueva).

## Principio general de trabajo

1. Antes de escribir código, **leé los archivos reales que se listan abajo** (no asumas sus contenidos a partir de este prompt: puede haber cambiado algo). En particular, **`interfazEmg.py` (o el módulo equivalente que controla la Pantalla 2 de EMG) no fue revisado al armar este prompt** — abrilo primero y usalo como fuente de verdad para los campos y señales reales del panel EMG, por encima de lo que se infiere acá.
2. Cuando un elemento visual del mockup ya tiene una señal Qt, un campo de `Settings` o un método de clase existente que lo cubre, **conectate a eso**, no crees un duplicado.
3. Cuando algo es genuinamente nuevo (la gestión de "paciente guardado / paciente nuevo" de la Pantalla 1, principalmente), diseñalo siguiendo el mismo patrón repositorio/dominio/ORM que ya usa el proyecto para `User`/`Preferences`/`TrainingWeights`.
4. Si encontrás una ambigüedad real entre el mockup y el código existente (ver la sección "Puntos a confirmar" al final), no la resuelvas adivinando: preguntame antes de tocar código que ya funciona.
5. Mantené la paleta y estilo del mockup (ver "Estilo visual") para que las tres pantallas se vean consistentes entre sí y con el resto de la app.

## Inventario de clases/archivos reales relevantes (en `ssvep/app/`)

- **`user_ui.py`** — `UserUI(QMainWindow)`, la ventana principal actual. Ya define señales Qt para casi todo lo que hace falta: `new_user_request(str)`, `request_user_preferences(int)`, `remove_user_request(int)`, `save_user_preferences_request(int, UserPreferences)`, `user_list_request()`, `threshold_request(float)`, `press_duration_request(int)`, `psd_channel_request(int)`, `psd_mode_request(int)`, `eeg_speed_request(float)`, `eeg_scale_request(int)`, `eeg_amplitude_request(int)`, `enable_control_request(bool)`, `enable_classify_request(bool)`, `audio_feedback_request(bool)`, `windows_welch_request(float)`, `overlap_request(float)`, entre otras. Páginas: `page_user_selection`, `page_user_config` (patrón de páginas apilado que probablemente convenga replicar para las 3 pantallas nuevas).
- **`domain.py`** — entidades de dominio `User`, `Preferences`, `TrainingWeights` (capa de negocio, separada del ORM).
- **`models.py`** — ORM SQLAlchemy: `UserModel(id, name)`, `PreferencesModel` (incluye `classification_method`, `time_windows`, `stim_frequency`, `stim_shape`, `channels`, `stim_on`, `stim_theta`, `stim_type`, `stim_direction`, todos serializados como string), `TrainingWeightsModel` (`trains`, `w`, `num_fbs`, `num_targets`).
- **`repositories.py`** — `UserRepositorySQLAlchemy`, `PreferencesRepositorySQLAlchemy`, `TrainingWeightsRepositorySQLAlchemy`. La Pantalla 1 nueva (guardar/elegir paciente) debe usar estos repositorios, no acceso directo a la DB.
- **`dataclasses.py`** — `Stimulus(freq, theta, stim_type, shape_type, direction)` con `shape_type` validado en `'circle' | 'square' | 'arrow'`; `UserPreferences(classification_method, time_window, channels, stimulus, stimulus_on)`; `ClassificationMethods` (CCA=0, eTRCA=1); `StimulusTypes` (flic=0, check=1).
- **`eeg_signal_classifier.py`** — `BaseEEGClassifier` con `load_threshold(threshold: float)`, `_validate_threshold(rho)` (calcula `sum_rho = (max_rho - min_rho) / (Σrho - min_rho)` y lo compara contra `self._threshold`; si `threshold <= 0` no filtra), esquema de votación por mayoría en ventanas solapadas. `EEGSignalCCAClassifier(BaseEEGClassifier)` y `EEGSignalTRCAClassifier(BaseEEGClassifier)`. El slider "Umbral CCA" de la Pantalla 3 debe alimentar esto vía `threshold_request`/`load_threshold`, **no** un valor nuevo desconectado.
- **`bci_evaluator.py`** — `BCIEvaluator(QObject)`: `NO_THRESHOLD = -1`, `NO_ENOUGH_SAMPLES = -2`, `start()`, `stop()`, `add_classification()`, `accuracy`, `calculate_itr()`, `generate_report()`. Esta es la clase que corre la "Prueba de validación"/"Validación" en ambas pantallas (EMG y EEG) — no reimplementar el conteo de aciertos/ITR a mano en la UI.
- **`psd_widget.py`** — `PSDWidget(QWidget)`, basado en pyqtgraph: `add_psd(freqs, psd_data)`, `set_psd_mode(mode)`, `set_psd_unit(unit)`, `set_target_frequencies(frequencies: List[float])` (dibuja las líneas verticales + etiquetas Hz, tal como se ve en el gráfico PSD del mockup). El panel "Señal y retroalimentación" de la Pantalla 3 debe **usar esta clase real**, no un `QChart`/SVG estático — el mockup ya está dibujado para parecerse a su salida real.
- **`psd_estimator.py`** — `PSDEstimator(QObject)`: `load_buffer_size`, `load_time_windows`, `load_overlap`, `set_channel_index`, `add_sample`, cálculo Welch. El selector "Canal" del panel PSD debe llamar `set_channel_index`.
- **`eeg_widget.py`** — `EEGWidget(QWidget, Ui_EEGWidget)`: widget de graficado en vivo multicanal (dibujo por `QPainter`, no pyqtgraph), con `add_filtered_signal`, `setup_channel_labels`, controles de velocidad/amplitud/escala. **Esta es la clase real detrás del gráfico multicanal (O1/Oz/O2/PO3/PO4) que aparece arriba en la Pantalla 3** — conectala en vez de recrear el dibujo a mano.
- **`electrode_head_widget.py`** — `ElectrodeHeadWidget(QGraphicsView)` + `ElectrodeItem`: selector de canales por clic sobre un diagrama de cabeza (no por chips/pills), con `set_channels_display`, `set_active_channels`, `set_locked_channels`, `get_active_channels`, límite dado por `Settings.max_channels`. **Ver "Puntos a confirmar" — el mockup muestra chips, no el diagrama de cabeza real.**
- **`settings.py`** — `Settings`: persiste `intf_name/baudrate/port` (conexión del dispositivo, ej. "COM5 · ESP32" / "COM7 · BioAmp" en el sidebar), `press_duration_ms`, `speed_scale`, `amplitude_scale`, `cue_duration_sec`, `trials_use`, `f_bands`, `default_user_preferences()`, `locked_channels`, `max_channels`. Los campos de "Parámetros" del mockup deben leer/escribir acá, no guardarse sueltos en la UI.

## Especificación de las tres pantallas

### Pantalla 1 — Inicio de sesión (reemplaza el diálogo emergente actual de selección de usuario)

Sidebar fija (se repite en las 3 pantallas): navegación Inicio/EMG/EEG-SSVEP, y al pie el nombre del paciente activo + estado de conexión del dispositivo (punto verde + puerto).

Bloque central:
- Logos institucionales (GIR / Facultad de Ingeniería UNER) + título "Nueva sesión".
- Selector tipo pestañas "Paciente": **"Elegir paciente guardado"** / **"Guardar paciente nuevo"** (esta última activa por defecto).
  - *Elegir paciente guardado*: desplegable con los pacientes ya cargados (listar vía `UserRepositorySQLAlchemy`, equivalente a lo que hoy hace `ql_user_list`/`user_list_request` en `user_ui.py`, pero como combo en vez de lista).
  - *Guardar paciente nuevo*: campos **Nombre** y **Apellido** por separado (hoy `UserModel.name` es un único string — decidir si concatenar "Nombre Apellido" al guardar o si conviene agregar columna; ver "Puntos a confirmar") + **Observaciones** (opcional, texto libre; no existe hoy un campo equivalente en `UserModel`/`PreferencesModel` — si se quiere persistir, es un campo nuevo a agregar, si no, tratarlo como nota de sesión no persistente).
- Tarjetas "Modalidad de control": EMG / EEG (selección única tipo radio) — determina a qué pantalla se navega al continuar.
- Botón "Comenzar sesión" (deshabilitado hasta elegir/crear paciente + modalidad).

### Pantalla 2 — Control por EMG

Encabezado "Control por EMG" + "Switch de accionamiento por contracción muscular".

- Panel "Señal de electromiografía": gráfico en vivo con línea de umbral ("Umbral de disparo") y marcadores de evento — **usar el widget real que ya dibuja esto en `interfazEmg.py`** (no fue leído para este prompt; revisalo antes de tocar este panel).
- Tres tarjetas en fila:
  - **Calibración (30 s en reposo)**: botón "Iniciar calibración", barra de progreso + cuenta regresiva, y al terminar muestra "Umbral de disparo: X (media=…, SD=…, sensibilidad=…)" — sensibilidad es el mismo parámetro que aparece abajo en "Parámetros".
  - **Prueba de validación (3 contracciones)**: botones "Iniciar prueba"/"Omitir prueba", luego "Registrar intento y continuar" con contador de intentos — debe correr sobre `BCIEvaluator` (no reimplementar el conteo).
  - **Parámetros**: Sensibilidad (slider), Refractario (stepper, ms), Tecla enviada (combo — confirmar con `interfazEmg.py` si hay un mapeo de teclas existente o si esto es nuevo), Duración de la pulsación (stepper, ms → `Settings.press_duration_ms` / `press_duration_request`). Al modificar cualquiera, mostrar el aviso "se recomienda repetir la prueba de validación" (ya está en el mockup).

### Pantalla 3 — Control por EEG — SSVEP

Encabezado "Control por EEG — SSVEP" + "Estimulación visual de estado estacionario".

- Panel superior "Señal de electroencefalografía": gráfico multicanal en vivo (canales O1/Oz/O2 fijos + hasta 2 adicionales) — **usar `EEGWidget`** (`eeg_widget.py`), no redibujar a mano.
- Tres columnas:
  - **Columna 1**:
    - *Canales EEG*: canales fijos occipitales (O1/Oz/O2, no deseleccionables) + adicionales seleccionables (POz/PO3/PO4/PO7/PO8, máximo definido por `Settings.max_channels`) con contador "X de Y canales activos". **Ver "Puntos a confirmar": el mockup usa chips/pills, pero la clase real (`ElectrodeHeadWidget`) es un diagrama de cabeza clickeable.**
    - *Calibración*: botón "Iniciar calibración" que corre un barrido de frecuencia 8–16 Hz en pasos de 0,5 Hz (recordar: CCA no requiere entrenamiento previo, a diferencia de eTRCA) y selecciona las 6 frecuencias con mejor exactitud; debajo, "Frecuencias asignadas" muestra la frecuencia elegida para cada uno de los 6 estímulos (Escape=cuadrado, Enter=círculo, 4 flechas=direcciones), consistente con `Stimulus.shape_type` (`'square'`, `'circle'`, `'arrow'` + `direction`).
  - **Columna 2 — Estimulación**: botón "Abrir estimulador" (lanza el proceso de estímulos visuales, `StimulusConfig`/multiprocessing). Debajo, sección **Validación**: botón "Iniciar prueba" (sobre `BCIEvaluator`, igual que en EMG), slider **"Umbral CCA"** (→ `threshold_request`/`BaseEEGClassifier.load_threshold`, recordar que `threshold <= 0` desactiva el filtro de umbral), "Duración de la pulsación" (mismo patrón que en EMG).
  - **Columna 3 — Señal y retroalimentación**: checkbox "Graficar PSD" (→ `psd_graph_request`), combo "Canal" (→ `psd_channel_request`/`PSDEstimator.set_channel_index`), combo "Visualización" (→ `psd_mode_request`/`PSDWidget.set_psd_mode`/`set_psd_unit` — el mockup muestra "Decibeles (dB)"; confirmar qué otros modos expone `PSDWidget`), el propio `PSDWidget` con `set_target_frequencies()` marcando las 6 frecuencias de la calibración, y checkbox "Retroalimentación auditiva" (→ `audio_feedback_request`).

## Estilo visual (para mantener consistencia)

Fuente "Segoe UI" (fallback Ubuntu/system-ui). Paleta: acento `#2f6690` (hover/dark `#204a68`), texto principal `#262c34`, texto secundario `#69707b`, bordes `#dfe3e8`/`#c7cdd6`, fondo de chip `#eef0f3`, fondo de tarjeta/selección tenue `#e7eff4`. Radios de 6–8 px en tarjetas, 999 px en chips/pills. Este esquema debería vivir como QSS centralizado (o tema Qt) reutilizable entre las tres pantallas, no repetido por widget.

## Puntos a confirmar conmigo antes de implementar (no asumir)

1. **Canales EEG**: ¿mantenemos la UI de chips del mockup, o migramos a `ElectrodeHeadWidget` (el diagrama de cabeza clickeable que ya existe)? Son interacciones distintas.
2. **Nombre/Apellido del paciente**: `UserModel` hoy solo tiene `name` (un string). ¿Agregamos columna `apellido`, o concatenamos "Nombre Apellido" en un único campo al guardar?
3. **Observaciones de sesión**: ¿se persiste en algún lado (nueva tabla/columna) o es solo una nota visual de esa sesión?
4. **"Tecla enviada" y "Refractario" en Parámetros de EMG**: confirmar si ya existen como configuración en `interfazEmg.py`/`Settings`, o son campos nuevos.
5. Confirmar con `interfazEmg.py` real cuál es la clase que ya dibuja el gráfico EMG con línea de umbral, para no duplicarla.

## Cómo proceder

Empezá por la Pantalla 1 (es la que tiene más lógica nueva: gestión de pacientes guardados/nuevos). Para las Pantallas 2 y 3, priorizá **reconectar/reskinnear** sobre lo que ya funciona en `interfazEmg.py`/`user_ui.py`/los widgets reales, y dejá para el final los elementos genuinamente nuevos (Calibración por barrido de frecuencia en EEG, slider de Umbral CCA, chips de "Frecuencias asignadas"). Si en algún punto el mockup y el código real entran en conflicto de forma no cubierta en "Puntos a confirmar", parate y preguntame en vez de decidir por tu cuenta.
