Vision - Control de Videojuegos y Experimentacion BCI mediante SSVEP
====================================================================

Vision es una aplicacion de interfaz cerebro-computadora (BCI) desarrollada en Python, disenada tanto para el control de videojuegos mediante senales EEG como para la experimentacion e investigacion en potenciales evocados visuales de estado estacionario (SSVEP).

El sistema permite al usuario controlar aplicaciones compatibles con teclado o participar en experimentos BCI fijando la mirada en estimulos visuales parpadeantes. La respuesta cerebral asociada es procesada en tiempo real para inferir la accion deseada o evaluar el desempeno del sistema.


CARACTERISTICAS PRINCIPALES
---------------------------

- Control de videojuegos por atencion visual: mapeo de estimulos SSVEP a comandos de teclado virtuales.
- Clasificacion de senales EEG: soporte para algoritmos CCA (Canonical Correlation Analysis) y eTRCA (Extended Task-Related Component Analysis).
- Procesamiento en tiempo real: filtrado digital (bandpass, notch, media, filterbank), estimacion de Densidad Espectral de Potencia (PSD) y acondicionamiento de senal.
- Gestion de usuarios y preferencias: persistencia de datos, configuracion de canales, ventanas de tiempo y estimulos mediante base de datos SQLite.
- Evaluacion y reportes: modulo de evaluacion BCI con calculo de metricas (accuracy, matriz de confusion) y generacion de reportes en PDF.
- Interfaz grafica desarrollada con PySide6 (Qt).


CONTEXTO Y AUTORIA
------------------

El desarrollo se realiza en el Centro de Ingenieria en Rehabilitacion e Investigacion Neuromusculares y Sensoriales (CIRINS), Laboratorio 3 de la Facultad de Ingenieria de la Universidad Nacional de Entre Rios (UNER).



ARQUITECTURA Y FLUJO DE FUNCIONAMIENTO
--------------------------------------

El sistema esta separado en capas: Interfaz (UI), Control, Dominio, Persistencia y Procesamiento.

Estimulos visuales (StimulusViewer)
         |
         v
Respuesta SSVEP del usuario
         |
         v
Dispositivo EEG / Archivo Binario --> Adquisicion (EEGSerialIface)
         |
         v
Filtrado, PSD y Procesamiento (SignalFilters, PSDEstimator)
         |
         v
Clasificacion del estimulo (CCA / eTRCA)
         |
         +---> [Modo Juego] KeyboardController --> Videojuego / App
         |
         +---> [Modo Evaluacion] BCIEvaluator --> Reporte PDF / Metricas

La clase AppController coordina este flujo general, conectando la UI, la adquisicion EEG, el entrenamiento, el clasificador y el control externo.


Flujo detallado:

1. Inicio: main.py crea QApplication, instancia AppController y llama a start_app().
2. Carga de configuracion: al importar ssvep/app/__init__.py se cargan constantes globales en builtins (frecuencia de muestreo, canales, estimulos, etc.). La clase Settings lee config.ini para ajustes persistentes.
3. Usuarios y preferencias: cada usuario tiene nombre, metodo de clasificacion, ventana de tiempo, canales activos, estimulos habilitados, tipo y frecuencia de cada estimulo.
4. Adquisicion y filtrado: la senal pasa por filtro media -> filtro notch -> filtro bandpass -> calculo de PSD -> clasificacion.
5. Entrenamiento (eTRCA): se registran marcas temporales, se segmentan epocas EEG, se construyen tensores de entrenamiento y se calculan pesos TRCA con filterbank.
6. Evaluacion: BCIEvaluator compara la secuencia esperada con las clasificaciones obtenidas, calcula accuracy, arma matriz de confusion y genera PDF.


INTEGRACION CON VIDEOJUEGOS
---------------------------

El sistema no controla la logica interna de los juegos, sino que emula pulsaciones de teclado en Windows.

Configuracion del juego:
GameManager busca archivos en la carpeta "MiCarpeta" ubicada en el Escritorio de Windows. Al seleccionarlo, lo abre y ajusta su ventana para compartir pantalla con los estimulos visuales.

Mapeo de comandos:
La asignacion entre clases SSVEP y teclas se gestiona en ssvep/app/keyboard_controller.py:

  Clase  | Tecla emulada   | Accion habitual
  -------|-----------------|---------------------------
  0      | Escape          | Pausa, cancelar o salir
  1      | Espacio         | Accion principal
  2      | Flecha derecha  | Movimiento a la derecha
  3      | Flecha arriba   | Movimiento hacia arriba
  4      | Flecha izquierda| Movimiento a la izquierda
  5      | Flecha abajo    | Movimiento hacia abajo

Nota: Espacio puede configurarse como sostenida o momentanea. Las flechas son momentaneas.


BASE DE DATOS Y PERSISTENCIA
----------------------------

La aplicacion utiliza SQLite a traves de SQLAlchemy para gestionar el estado de la aplicacion.

- Ubicacion: data/user_database.db
- Tablas principales: users, preferences, training_weights.


Archivos y recursos importantes:

  Ruta                              | Descripcion
  ----------------------------------|---------------------------------------------
  eeg_bin.bin                       | Senal binaria para pruebas sin hardware
  res/ui/                           | Archivos .ui de Qt
  res/images/                       | Recursos graficos
  res/info/info.html                | Pantalla informativa dentro de la app
  mis_seniales/                     | Senales de entrenamiento guardadas en .mat
  res/electrodes_placement/         | Material de referencia para colocacion de electrodos


ESTRUCTURA DEL REPOSITORIO
--------------------------

.
|-- main.py                     # Punto de entrada de la aplicacion Qt
|-- config.ini                  # Configuracion general (puertos, baudrate, etc.)
|-- eeg_bin.bin                 # Senal binaria para pruebas sin hardware
|-- requirements.txt            # Dependencias de Python
|-- ssvep/
|   |-- app/                    # Logica de dominio, procesamiento y control
|   |   |-- app_controller.py   # Orquestador principal
|   |   |-- user_ui.py          # Interfaz grafica (PySide6)
|   |   |-- stimulus_viewer.py  # Presentacion de estimulos SSVEP
|   |   |-- eeg_serial_iface.py # Adquisicion (Serial real y File Interface)
|   |   |-- eeg_signal_procesor.py # Procesamiento en segundo plano
|   |   |-- signal_filters.py   # Filtros (bandpass, notch, media, filterbank)
|   |   |-- psd_estimator.py    # Estimacion de densidad espectral
|   |   |-- eeg_signal_clasifier.py # Clasificadores CCA y eTRCA
|   |   |-- training_manager.py # Logica de entrenamiento eTRCA
|   |   |-- bci_evaluator.py    # Evaluacion, metricas y reporte PDF
|   |   |-- game_manager.py     # Gestion de ventanas de juegos en Windows
|   |   |-- keyboard_controller.py # Emulacion de teclado
|   |   |-- models.py           # Modelos SQLAlchemy
|   |   |-- repositories.py     # Persistencia SQLAlchemy
|   |   |-- managers.py         # Capa de negocio sobre repositorios
|   |   |-- settings.py         # Configuracion general desde config.ini
|   |   |-- dataclasses.py      # Estructuras de datos simples
|   `-- ui/                     # Componentes visuales auxiliares
|-- data/                       # Base de datos SQLite persistente
|-- res/                        # Recursos (UI, imagenes, info, electrodos)
`-- mis_seniales/               # Senales de entrenamiento guardadas (.mat)


REQUISITOS E INSTALACION
------------------------

Requisitos del sistema:
- Sistema operativo: Windows (obligatorio por el uso de APIs de ventanas y emulacion de teclado).
- Python: 3.x
- Hardware: dispositivo EEG (BioAmp) configurado para comunicacion serie.

Instalacion de dependencias:

  python -m pip install -r requirements.txt

Paquetes principales incluidos:
- PySide6: Interfaz grafica
- SQLAlchemy: Persistencia de datos
- NumPy, SciPy: Procesamiento numerico y cientifico
- Matplotlib: Visualizacion
- pyserial: Comunicacion serie con hardware EEG
- Flask, Flask-Session: Servicios web (si aplica)

Instalacion manual (si no hay requirements.txt):

  python -m pip install PySide6 SQLAlchemy numpy scipy matplotlib pyserial Flask Flask-Session


EJECUCION
---------

1. Iniciar la aplicacion:

     python main.py

2. Seleccionar o crear un usuario:
   Al iniciar, la interfaz permite seleccionar un usuario existente o crear uno nuevo. Cada usuario mantiene sus propias preferencias y configuraciones guardadas en la base de datos.

3. Configurar el usuario:
   Una vez seleccionado el usuario, se deben configurar los siguientes parametros:
   
   - Tiempo de respuesta: define el tiempo que el sistema toma para clasificar cada estimulo. Valores mas cortos permiten respuestas mas rapidas (mayor velocidad), mientras que valores mas largos mejoran la exactitud de la clasificacion.
   
   - Canales activos: seleccionar cuales canales EEG se utilizaran para el procesamiento y clasificacion.
   
   - Metodo de deteccion: elegir entre CCA (Canonical Correlation Analysis) o eTRCA (Extended Task-Related Component Analysis). Si se selecciona eTRCA, sera necesario realizar una etapa de entrenamiento antes de usar el sistema.
   
   - Frecuencias de estimulos: configurar las frecuencias de parpadeo de cada estimulo visual que se utilizara.

4. Entrenamiento (si es necesario):
   Si el metodo de clasificacion seleccionado es eTRCA, el sistema requiere una etapa de entrenamiento previa. Durante el entrenamiento, el usuario debe fijar la mirada en cada estimulo visual mientras el sistema registra las respuestas EEG y calcula los pesos del clasificador. Los resultados se guardan en la base de datos para su reutilizacion.
   
   Si el metodo es CCA, no se requiere entrenamiento previo.

5. Seleccionar modo de uso:
   Una vez configurado el usuario (y realizado el entrenamiento, si corresponde), se puede elegir entre:
   
   - Jugar: seleccionar un videojuego de la lista disponible. El sistema abrira el juego y presentara los estimulos visuales para controlarlo mediante la atencion visual.
   
   - Evaluacion BCI: ejecutar una prueba controlada donde el sistema presenta una secuencia de estimulos esperada, compara con las clasificaciones obtenidas, calcula metricas de desempeno (accuracy, matriz de confusion) y genera un reporte en PDF.

IMPORTANTE: Para que los videojuegos aparezcan en la lista y puedan ser seleccionados, se deben colocar sus ejecutables (.exe), accesos directos (.lnk) en la carpeta "MiCarpeta" ubicada en el Escritorio de Windows.

SALIDA GENERADA
---------------

Segun el flujo ejecutado, la aplicacion puede crear:
- Registros en data/user_database.db (usuarios, preferencias, pesos de entrenamiento).
- Archivos de entrenamiento .mat en mis_seniales/.
- Reportes PDF de evaluacion BCI con metricas de desempeno.


ALCANCE Y LIMITACIONES
----------------------

- Entorno controlado: las evaluaciones experimentales estan planteadas para participantes sanos en condiciones de laboratorio (CIRINS).
- Poblacion reducida: la cantidad de participantes es reducida y no representa una poblacion clinica amplia.
- Hardware especifico: el funcionamiento con hardware real depende del amplificador EEG disponible en el laboratorio y su conexion serie.
- Juegos simples: los videojuegos de prueba deben ser capaces de ejecutarse en ventana y aceptar comandos basicos de teclado.
- Dependencia de Windows: la apertura, posicionamiento de ventanas y emulacion de teclado utilizan APIs exclusivas de Windows.
- Consentimiento: las evaluaciones con voluntarios requieren informacion previa del procedimiento y firma de consentimiento informado.


NOTAS PARA MANTENIMIENTO
------------------------

- Mapeo de teclas: si se agregan estimulos o se desea adaptar la aplicacion a otro juego, la asignacion entre clases SSVEP y teclas debe modificarse centralizadamente en ssvep/app/keyboard_controller.py.
- Configuracion global: al importar ssvep/app/__init__.py se cargan constantes globales en builtins (frecuencia de muestreo, canales, estimulos). Modificar estos valores afecta el comportamiento general de la app.


MODULOS PRINCIPALES
-------------------

  Modulo                          | Responsabilidad
  --------------------------------|-------------------------------------------------
  main.py                         | Punto de entrada. Crea la aplicacion Qt y arranca AppController.
  ssvep/app/app_controller.py       | Orquesta el funcionamiento general y conecta senales, interfaz, EEG, estimulos, clasificador y control del juego.
  ssvep/app/user_ui.py              | Implementa la interfaz grafica utilizada por la persona operadora o usuaria.
  ssvep/app/stimulus_viewer.py      | Presenta los estimulos visuales utilizados para provocar respuestas SSVEP.
  ssvep/app/eeg_serial_iface.py     | Gestiona la comunicacion serie con el dispositivo de adquisicion EEG y el flujo de muestras.
  ssvep/app/eeg_signal_procesor.py  | Procesa las senales adquiridas antes de su analisis.
  ssvep/app/signal_filters.py       | Define filtros y operaciones de acondicionamiento de senal.
  ssvep/app/psd_estimator.py        | Estimacion de densidad espectral de potencia.
  ssvep/app/eeg_signal_clasifier.py | Contiene la logica para clasificar la respuesta EEG asociada a los estimulos (CCA y eTRCA).
  ssvep/app/training_manager.py     | Gestiona la etapa de entrenamiento y la generacion de datos para el detector.
  ssvep/app/bci_evaluator.py        | Evalua el desempeno del sistema BCI durante pruebas controladas y genera reportes.
  ssvep/app/game_manager.py         | Busca, abre, posiciona y cierra videojuegos o aplicaciones externas en Windows.
  ssvep/app/keyboard_controller.py  | Convierte la clase detectada en eventos de teclado virtuales enviados al juego.
  ssvep/app/models.py               | Modelos SQLAlchemy.
  ssvep/app/repositories.py         | Persistencia SQLAlchemy.
  ssvep/app/managers.py             | Capa de negocio sobre repositorios.
  ssvep/app/settings.py             | Configuracion general desde config.ini.
  ssvep/app/dataclasses.py          | Estructuras de datos simples.