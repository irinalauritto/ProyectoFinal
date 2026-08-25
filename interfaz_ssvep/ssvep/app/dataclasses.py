"""
Módulo de modelos de datos (Dataclasses y Enums).

Este módulo define las estructuras de datos principales utilizadas para 
configurar los estímulos visuales, los métodos de clasificación y las 
preferencias globales del usuario en la aplicación.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple

# ==============================================================================
# Enums (Constantes y Tipos)
# ==============================================================================
# Se definen primero para que estén disponibles conceptualmente antes 
# que los dataclasses que los referencian.

class ClassificationMethods(Enum):
    """
    Enumeración de los métodos de clasificación de señales disponibles.

    Attributes:
        eTRCA: Extended Task-Related Component Analysis.
        CCA: Canonical Correlation Analysis.
    """
    CCA = 0
    eTRCA = 1
    


class StimulusTypes(Enum):
    """
    Enumeración de los tipos de estímulos visuales soportados.

    Attributes:
        flic: Estímulo tipo flicker (parpadeo).
        check: Estímulo tipo checkerboard (tablero de ajedrez).
    """
    flic = 0
    check = 1


# ==============================================================================
# Dataclasses (Modelos de Datos)
# ==============================================================================

@dataclass
class Stimulus:
    """
    Representa la configuración de un estímulo visual individual.

    Attributes:
        freq: Frecuencia del estímulo en Hz.
        theta: Fase del estímulo.
        stim_type: Tipo de estímulo. Se espera que sea el nombre (`.name`) 
            de un valor válido de `StimulusTypes` (ej. `'flic'`, `'check'`).
        shape_type: Forma geométrica del estímulo (ej. `'circle'`, `'square', 'arrow'`).
        direction: Dirección del movimiento del estímulo (ej. `'up','down', 'right', 'lefth'`), si aplica. 
            `None` si el estímulo es estático o no tiene dirección.
    """
    freq: float
    theta: float
    stim_type: str
    shape_type: str
    direction: str | None = None


@dataclass
class UserPreferences:
    """
    Almacena la configuración global y las preferencias del usuario 
    para una sesión experimental.

    Attributes:
        classification_method: Método de clasificación a utilizar. 
            Se espera que sea el nombre (`.name`) de `ClassificationMethods` 
            (ej. `'eTRCA'`, `'CCA'`).
        time_window: Ventana de tiempo (en segundos) utilizada para 
            el análisis o clasificación de la señal.
        channels: Diccionario que mapea el índice del canal (int) 
            a su nombre o etiqueta (str). Por defecto está vacío.
        stimulus: Lista de objetos `Stimulus` que componen la 
            configuración visual del experimento.
        stimulus_on: Lista de booleanos que indica el estado (encendido/apagado) 
            de cada estímulo correspondiente en la lista `stimulus`.
    """
    classification_method: str
    time_window: float
    channels: dict[int, str] = field(default_factory=dict)
    stimulus: list[Stimulus] = field(default_factory=list)
    stimulus_on: list[bool] = field(default_factory=list)
    

@dataclass
class StimulusConfig:
    """
    Estructura de datos para transmitir la configuración de los estímulos 
    al proceso de renderizado en segundo plano (multiprocessing).
    
    Attributes:
        screen_height: Alto de la pantalla en píxeles.
        screen_width: Ancho de la pantalla en píxeles.
        stimulus_data: Diccionario con la configuración de cada estímulo.
        stimulus_positions: Lista de posiciones (x, y) para cada estímulo.
        stimulus_size: Tamaño base de los estímulos en píxeles.
        height_margin: Margen vertical para el cálculo de posiciones.
        width_margin: Margen horizontal para el cálculo de posiciones.
        monitor_index: Índice del monitor donde se mostrarán los estímulos.
    """
    screen_height: int
    screen_width: int
    stimulus_data: Dict[int, Any]
    stimulus_positions: List[Tuple[int, int]]
    stimulus_size: int
    height_margin: int
    width_margin: int
    monitor_index: int