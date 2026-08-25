"""
Módulo de modelos de dominio para la gestión de usuarios, preferencias y pesos de entrenamiento.

Este módulo define las clases principales que representan el estado y la configuración 
del usuario, así como los datos matemáticos resultantes del entrenamiento de los 
modelos de clasificación de señales EEG.
"""

import numpy as np
from typing import Any


# ==============================================================================
# Clase User
# ==============================================================================

class User:
    """
    Representa a un usuario del sistema.

    Valida y encapsula los datos básicos de identificación del usuario, 
    asegurando que el ID sea un entero (o None) y el nombre sea una cadena 
    de texto válida y sin espacios en blanco al inicio o final.
    """

    def __init__(self, user_id: int | None, user_name: str) -> None:
        """
        Inicializa una nueva instancia de User.

        Args:
            user_id: Identificador único del usuario. Puede ser None si aún no se ha asignado.
            user_name: Nombre del usuario. No puede estar vacío.
        """
        # No es necesario pre-inicializar con None, los setters se encargan de la validación
        self.id = user_id
        self.name = user_name

    @property
    def id(self) -> int | None:
        """int | None: Identificador único del usuario."""
        return self.__id

    @id.setter
    def id(self, user_id: int | None) -> None:
        if user_id is not None and not isinstance(user_id, int):
            raise ValueError("El id del usuario debe ser un número entero.")
        self.__id = user_id

    @property
    def name(self) -> str:
        """str: Nombre del usuario, siempre almacenado sin espacios en los extremos."""
        return self.__name

    @name.setter
    def name(self, user_name: str) -> None:
        if not isinstance(user_name, str) or user_name.strip() == "":
            raise ValueError("El nombre del usuario debe ser un string y no debe estar vacío.")
        self.__name = user_name.strip()

    def to_dict(self) -> dict[str, Any]:
        """
        Convierte la instancia del usuario a un diccionario para serialización.

        Returns:
            dict[str, Any]: Diccionario con las claves 'id' y 'name'.
        """
        return {
            "id": self.id,
            "name": self.name,
        }


# ==============================================================================
# Clase Preferences
# ==============================================================================

class Preferences:
    """
    Almacena la configuración experimental y las preferencias de procesamiento 
    de un usuario específico.

    Agrupa parámetros relacionados con la ventana de tiempo, el método de 
    clasificación y las características detalladas de cada estímulo visual.
    """

    def __init__(
        self,
        user_id: int | None,
        classification_method: str,
        time_windows: float | int,
        stimulus_frequency: list[float],
        stimulus_shape: list[str],
        channels: dict[int, str],
        stimulus_on: list[bool],
        stimulus_type: list[str],
        stimulus_theta: list[float],
        stimulus_direction: list[str | None],
    ) -> None:
        """
        Inicializa una nueva instancia de Preferences.

        Args:
            user_id: ID del usuario al que pertenecen estas preferencias.
            classification_method: Nombre del método de clasificación (ej. 'eTRCA', 'CCA').
            time_windows: Longitud de la ventana de tiempo en segundos.
            stimulus_frequency: Lista de frecuencias (Hz) para cada estímulo.
            stimulus_shape: Lista de formas geométricas para cada estímulo.
            channels: Diccionario que mapea índices de canal a sus nombres.
            stimulus_on: Lista de booleanos indicando si cada estímulo está activo.
            stimulus_type: Lista de tipos de estímulo (ej. 'flic', 'check').
            stimulus_theta: Lista de fases o ángulos para cada estímulo.
            stimulus_direction: Lista de direcciones de movimiento (o None si es estático).
        """
        self.user_id = user_id
        self.time_windows = time_windows
        self.classification_method = classification_method
        self.stimulus_frequency = stimulus_frequency
        self.stimulus_shape = stimulus_shape
        self.channels = channels
        self.stimulus_on = stimulus_on
        self.stimulus_type = stimulus_type
        self.stimulus_theta = stimulus_theta
        self.stimulus_direction = stimulus_direction

    # --- Propiedades y Validadores (Getters y Setters agrupados por atributo) ---

    @property
    def user_id(self) -> int | None:
        """int | None: ID del usuario asociado."""
        return self.__user_id

    @user_id.setter
    def user_id(self, value: int | None) -> None:
        if value is not None and not isinstance(value, int):
            raise ValueError("El id del usuario debe ser un número entero.")
        self.__user_id = value

    @property
    def time_windows(self) -> float:
        """float: Longitud de la ventana de tiempo en segundos."""
        return self.__time_windows

    @time_windows.setter
    def time_windows(self, value: float | int) -> None:
        if not isinstance(value, (float, int)):
            raise ValueError("Error de tipo: La longitud de ventana debe ser un número entero o decimal.")
        self.__time_windows = float(value)

    @property
    def classification_method(self) -> str:
        """str: Método de clasificación seleccionado."""
        return self.__classification_method

    @classification_method.setter
    def classification_method(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("Error de tipo: El método de clasificación debe ser un string.")
        self.__classification_method = value

    @property
    def stimulus_frequency(self) -> list[float]:
        """list[float]: Frecuencias de los estímulos."""
        return self.__stimulus_frequency

    @stimulus_frequency.setter
    def stimulus_frequency(self, value: list) -> None:
        if not isinstance(value, list):
            raise ValueError("Error de tipo: La frecuencia del estímulo debe ser una Lista.")
        self.__stimulus_frequency = value

    @property
    def stimulus_shape(self) -> list[str]:
        """list[str]: Formas de los estímulos."""
        return self.__stimulus_shape

    @stimulus_shape.setter
    def stimulus_shape(self, value: list) -> None:
        if not isinstance(value, list):
            raise ValueError("Error de tipo: La forma del estímulo debe ser una Lista.")
        self.__stimulus_shape = value

    @property
    def channels(self) -> dict[int, str]:
        """dict[int, str]: Mapeo de índices de canales a sus nombres."""
        return self.__channels

    @channels.setter
    def channels(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("Error de tipo: Los canales deben ser un diccionario.")  # <-- CORREGIDO: decía "Lista"
        self.__channels = value

    @property
    def stimulus_on(self) -> list[bool]:
        """list[bool]: Estado de activación de cada estímulo."""
        return self.__stimulus_on

    @stimulus_on.setter
    def stimulus_on(self, value: list) -> None:
        if not isinstance(value, list):
            raise ValueError("Error de tipo: El parámetro stim_on debe ser una Lista.")
        self.__stimulus_on = value

    @property
    def stimulus_type(self) -> list[str]:
        """list[str]: Tipos de estímulos."""
        return self.__stimulus_type

    @stimulus_type.setter
    def stimulus_type(self, value: list) -> None:
        if not isinstance(value, list):
            raise ValueError("Error de tipo: El tipo de estímulo debe ser una Lista.")
        self.__stimulus_type = value

    @property
    def stimulus_theta(self) -> list[float]:
        """list[float]: Fases o ángulos de los estímulos."""
        return self.__stimulus_theta

    @stimulus_theta.setter
    def stimulus_theta(self, value: list) -> None:
        if not isinstance(value, list):
            raise ValueError("Error de tipo: El parámetro stimulus_theta debe ser una Lista.")
        self.__stimulus_theta = value

    @property
    def stimulus_direction(self) -> list[str | None]:
        """list[str | None]: Direcciones de los estímulos."""
        return self.__stimulus_direction

    @stimulus_direction.setter
    def stimulus_direction(self, value: list) -> None:
        if not isinstance(value, list):
            raise ValueError("Error de tipo: El parámetro stimulus_direction debe ser una Lista.")
        self.__stimulus_direction = value


# ==============================================================================
# Clase TrainingWeights
# ==============================================================================

class TrainingWeights:
    """
    Almacena los pesos y datos de entrenamiento resultantes del procesamiento 
    de señales EEG para un usuario específico.

    Contiene las matrices de pesos (W), los datos de entrenamiento (trains) 
    y metadatos sobre la configuración del modelo (número de bandas de frecuencia 
    y número de objetivos).
    """

    def __init__(
        self,
        user_id: int | None,
        trains: np.ndarray | None = None,
        w: np.ndarray | None = None,
        num_fbs: int | None = None,
        num_targets: int | None = None,
    ) -> None:
        """
        Inicializa una nueva instancia de TrainingWeights.

        Args:
            user_id: ID del usuario al que pertenecen estos pesos.
            trains: Array de numpy con los datos de entrenamiento. 
                    Por defecto, un array vacío.
            w: Array de numpy con la matriz de pesos calculada. 
               Por defecto, un array vacío.
            num_fbs: Número de bandas de frecuencia utilizadas. Por defecto, 0.
            num_targets: Número de objetivos (targets) del paradigma. Por defecto, 0.
        """
        self.user_id = user_id
        self.trains = trains if trains is not None else np.array([])
        self.w = w if w is not None else np.array([])
        self.num_fbs = num_fbs if num_fbs is not None else 0
        self.num_targets = num_targets if num_targets is not None else 0

    @property
    def user_id(self) -> int | None:
        """int | None: ID del usuario asociado a estos pesos."""
        return self.__user_id

    @user_id.setter
    def user_id(self, value: int | None) -> None:
        if value is not None and not isinstance(value, int):
            raise ValueError("El id del usuario debe ser un número entero.")
        self.__user_id = value

    @property
    def trains(self) -> np.ndarray:
        """np.ndarray: Datos de entrenamiento."""
        return self.__trains

    @trains.setter
    def trains(self, value: np.ndarray) -> None:
        if not isinstance(value, np.ndarray):
            raise ValueError("Error de tipo: 'trains' debe ser un np.ndarray.")
        self.__trains = value

    @property
    def w(self) -> np.ndarray:
        """np.ndarray: Matriz de pesos del modelo."""
        return self.__w

    @w.setter
    def w(self, value: np.ndarray) -> None:
        if not isinstance(value, np.ndarray):
            raise ValueError("Error de tipo: 'w' debe ser un np.ndarray.")
        self.__w = value

    @property
    def num_fbs(self) -> int:
        """int: Número de bandas de frecuencia."""
        return self.__num_fbs

    @num_fbs.setter
    def num_fbs(self, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError("Error de tipo: 'num_fbs' debe ser un entero.")
        self.__num_fbs = value

    @property
    def num_targets(self) -> int:
        """int: Número de objetivos (targets)."""
        return self.__num_targets

    @num_targets.setter
    def num_targets(self, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError("Error de tipo: 'num_targets' debe ser un entero.")
        self.__num_targets = value