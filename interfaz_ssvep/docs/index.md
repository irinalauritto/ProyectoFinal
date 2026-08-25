# Vision

## Control de videojuegos mediante SSVEP

Vision es una aplicación de interfaz cerebro-computadora (*Brain-Computer Interface*, BCI) orientada al control de videojuegos y aplicaciones compatibles con teclado. El sistema utiliza potenciales evocados visuales de estado estacionario (*Steady-State Visually Evoked Potentials*, SSVEP): la persona usuaria observa un estímulo visual parpadeante y el sistema analiza la señal EEG para reconocer la acción asociada.

El flujo principal de la aplicación es:

```text
Estímulos visuales -> respuesta SSVEP -> adquisición EEG por serie
-> filtrado y procesamiento -> clasificación -> teclado virtual -> videojuego
```

`AppController` es el componente que coordina los módulos de la interfaz, la adquisición de señal, el procesamiento, la clasificación y el control del juego.

## Uso de la documentación

Esta página está preparada para [mkdocstrings](https://mkdocstrings.github.io/), que extrae la referencia de API directamente desde los docstrings del código fuente. Para generar el sitio se requiere configurar el complemento `mkdocstrings` con el manejador de Python y asegurar que la raíz del repositorio esté incluida en las rutas de búsqueda.

## Punto de entrada y coordinación

### Controlador principal

::: src.app.app_controller
    options:
      show_source: false
      members_order: source

### Creación de componentes

::: src.app.factory
    options:
      show_source: false
      members_order: source

## Interfaz y estímulos visuales

### Interfaz de usuario

::: src.app.user_ui
    options:
      show_source: false
      members_order: source

### Visor de estímulos

::: src.app.stimulus_viewer
    options:
      show_source: false
      members_order: source

### Componentes de visualización EEG

::: src.app.eeg_widget
    options:
      show_source: false
      members_order: source

::: src.app.electrode_head_widget
    options:
      show_source: false
      members_order: source

::: src.app.psd_widget
    options:
      show_source: false
      members_order: source

## Adquisición y procesamiento EEG

### Interfaz serie

::: src.app.eeg_serial_iface
    options:
      show_source: false
      members_order: source

### Procesamiento de señal

::: src.app.eeg_signal_procesor
    options:
      show_source: false
      members_order: source

::: src.app.signal_filters
    options:
      show_source: false
      members_order: source

::: src.app.psd_estimator
    options:
      show_source: false
      members_order: source

## Clasificación, entrenamiento y evaluación

### Clasificadores SSVEP

::: src.app.eeg_signal_classifier
    options:
      show_source: false
      members_order: source

### Entrenamiento

::: src.app.training_manager
    options:
      show_source: false
      members_order: source

### Evaluación BCI

::: src.app.bci_evaluator
    options:
      show_source: false
      members_order: source

::: src.app.bci_evaluator_widgets
    options:
      show_source: false
      members_order: source

## Integración con videojuegos

### Gestión de videojuegos y ventanas

`GameManager` localiza ejecutables, accesos directos o scripts disponibles en la carpeta configurada del Escritorio, abre el juego y posiciona su ventana junto al visor de estímulos. La implementación utiliza APIs de Windows.

::: src.app.game_manager
    options:
      show_source: false
      members_order: source

### Control de teclado

`KeyboardController` transforma la clase SSVEP detectada en eventos de teclado virtuales para que el videojuego reciba la acción solicitada. El mapeo actual contempla `Escape`, `Espacio` y las cuatro flechas direccionales.

::: src.app.keyboard_controller
    options:
      show_source: false
      members_order: source

## Datos, configuración y persistencia

### Estructuras y configuración

::: src.app.dataclasses
    options:
      show_source: false
      members_order: source

::: src.app.domain
    options:
      show_source: false
      members_order: source

::: src.app.config
    options:
      show_source: false
      members_order: source

::: src.app.settings
    options:
      show_source: false
      members_order: source

### Modelos y repositorios

::: src.app.models
    options:
      show_source: false
      members_order: source

::: src.app.abstract_repository
    options:
      show_source: false
      members_order: source

::: src.app.repositories
    options:
      show_source: false
      members_order: source

::: src.app.managers
    options:
      show_source: false
      members_order: source
