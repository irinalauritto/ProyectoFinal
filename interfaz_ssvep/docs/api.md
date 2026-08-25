# Referencia de la API

## Configuración y Estructuras de Datos

### Configuración General
Gestiona la configuración general de la aplicación leyendo y escribiendo el archivo `config.ini`.
::: src.app.settings
    options:
      show_root_heading: true
      members_order: source

### Estructuras de Datos
Define las estructuras de datos simples (dataclasses) utilizadas a lo largo de la aplicación.
::: src.app.dataclasses
    options:
      show_root_heading: true
      members_order: source

---

## Control y Orquestación

### Controlador Principal
Orquesta el funcionamiento general y conecta las señales, la interfaz, el EEG, los estímulos, el clasificador y el control del juego.
::: src.app.app_controller
    options:
      show_root_heading: true
      members_order: source

---

## Interfaz y Estímulos Visuales

### Interfaz de Usuario
Implementa la interfaz gráfica principal utilizada por la persona operadora o usuaria.
::: src.app.user_ui
    options:
      show_root_heading: true
      members_order: source

### Visor de Estímulos
Presenta los estímulos visuales utilizados para provocar respuestas SSVEP en el usuario.
::: src.app.stimulus_viewer
    options:
      show_root_heading: true
      members_order: source

---

## Adquisición y Procesamiento EEG

### Interfaz Serie
Gestiona la comunicación serie con el dispositivo de adquisición EEG y el flujo de muestras.
::: src.app.eeg_serial_iface
    options:
      show_root_heading: true
      members_order: source

### Procesamiento de Señal
Procesa las señales adquiridas antes de su análisis (ventanas, segmentación, etc.).
::: src.app.eeg_signal_procesor
    options:
      show_root_heading: true
      members_order: source

### Filtros de Señal
Define los filtros y operaciones de acondicionamiento de señal (Notch, Bandpass, etc.).
::: src.app.signal_filters
    options:
      show_root_heading: true
      members_order: source

### Estimación PSD
Realiza la estimación de la densidad espectral de potencia (Power Spectral Density) de la señal.
::: src.app.psd_estimator
    options:
      show_root_heading: true
      members_order: source

---

## Clasificación, Entrenamiento y Evaluación

### Clasificador EEG
Contiene la lógica para clasificar la respuesta EEG asociada a los estímulos (implementaciones de CCA y eTRCA).
::: src.app.eeg_signal_classifier
    options:
      show_root_heading: true
      members_order: source

### Gestor de Entrenamiento
Gestiona la etapa de entrenamiento del sistema y la generación de datos para el detector.
::: src.app.training_manager
    options:
      show_root_heading: true
      members_order: source

### Evaluador BCI
Evalúa el desempeño del sistema BCI durante pruebas controladas y genera reportes de rendimiento.
::: src.app.bci_evaluator
    options:
      show_root_heading: true
      members_order: source

---

## Integración con Videojuegos

### Gestor de Juegos
Busca, abre, posiciona y cierra videojuegos o aplicaciones externas en el sistema operativo Windows.
::: src.app.game_manager
    options:
      show_root_heading: true
      members_order: source

### Controlador de Teclado
Convierte la clase detectada por el clasificador en eventos de teclado virtuales enviados al juego.
::: src.app.keyboard_controller
    options:
      show_root_heading: true
      members_order: source

---

## Capa de Datos y Persistencia

### Modelos de Base de Datos
Define los modelos de datos utilizando SQLAlchemy.
::: src.app.models
    options:
      show_root_heading: true
      members_order: source

### Repositorios
Implementa la capa de persistencia de datos utilizando SQLAlchemy.
::: src.app.repositories
    options:
      show_root_heading: true
      members_order: source

### Gestores de Negocio
Implementa la capa de lógica de negocio que opera sobre los repositorios.
::: src.app.managers
    options:
      show_root_heading: true
      members_order: source