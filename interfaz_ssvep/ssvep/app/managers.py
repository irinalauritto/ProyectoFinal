"""
Módulo de gestores de dominio (Managers).

Este módulo contiene las clases responsables de orquestar la lógica de negocio, 
validar reglas de dominio y coordinar las operaciones entre los casos de uso 
y los repositorios de persistencia (AbstractRepository).
"""

from typing import Any

from ssvep.app.abstract_repository import AbstractRepository
from ssvep.app.dataclasses import Stimulus, UserPreferences
from ssvep.app.domain import Preferences, TrainingWeights, User


# ==============================================================================
# UserManager
# ==============================================================================

class UserManager:
    """
    Gestiona las operaciones de dominio relacionadas con los usuarios.

    Se encarga de la creación, recuperación y eliminación de usuarios, 
    asegurando la integridad de los datos (ej. evitar nombres duplicados) 
    antes de delegar la persistencia al repositorio.
    """

    def __init__(self, user_repo: AbstractRepository) -> None:
        """
        Inicializa el UserManager.

        Args:
            user_repo: Implementación concreta de AbstractRepository para usuarios.
        """
        self.__user_repo = user_repo

    def register_new_user(self, name: str) -> User:
        """
        Crea un nuevo sujeto de prueba en el sistema.

        Valida que el nombre no esté duplicado y delega la creación de la 
        entidad de dominio (que realiza su propia validación interna).

        Args:
            name: Nombre del nuevo usuario.

        Returns:
            User: La entidad de usuario recién creada y guardada.

        Raises:
            ValueError: Si ya existe un usuario con ese nombre exacto.
        """
        clean_name = name.strip()
        
        if self.__user_repo.get_by_filter("name", clean_name):
            raise ValueError(f"El usuario '{clean_name}' ya existe en el sistema.")
            
        # Se usan los nombres de parámetros refactorizados en el paso anterior
        new_user = User(user_id=None, user_name=clean_name)
        self.__user_repo.save(new_user)
        
        return new_user
    
    def get_all_users(self) -> list[User]:
        """
        Recupera todos los usuarios registrados en el sistema.

        Returns:
            list[User]: Lista de todas las entidades de usuario.
        """
        return self.__user_repo.get_all()

    def remove_user(self, user_id: int) -> None:
        """
        Elimina un usuario del sistema por su ID.

        Args:
            user_id: Identificador único del usuario a eliminar.
        """
        self.__user_repo.delete(user_id)
    
    def get_user(self, user_id: int) -> dict[str, Any]:
        """
        Busca un usuario por su ID y devuelve sus datos serializados.

        Args:
            user_id: Identificador único del usuario.

        Returns:
            dict[str, Any]: Diccionario con los datos del usuario.

        Raises:
            ValueError: Si no se encuentra el usuario.
        """
        user = self.__user_repo.get_by_filter("id", user_id)
        if not user:
            raise ValueError("Sujeto de prueba no encontrado.")
        return user.to_dict()
    

# ==============================================================================
# PreferencesManager
# ==============================================================================

class PreferencesManager:
    """
    Gestiona las operaciones de dominio relacionadas con las preferencias 
    experimentales del usuario.

    Traduce entre los objetos de transferencia de datos (Dataclasses) usados 
    en la capa de presentación y las entidades de dominio persistentes.
    """

    def __init__(self, prefs_repo: AbstractRepository) -> None:
        """
        Inicializa el PreferencesManager.

        Args:
            prefs_repo: Implementación concreta de AbstractRepository para preferencias.
        """
        self.__prefs_repo = prefs_repo

    def save_or_update_preferences(self, user_id: int, user_prefs: UserPreferences) -> Preferences:
        """
        Guarda o actualiza las preferencias de un usuario.

        Transforma la dataclass `UserPreferences` en la entidad de dominio 
        `Preferences` para ejecutar las validaciones de tipo, y luego decide 
        si realizar una inserción o una actualización en la base de datos.

        Args:
            user_id: Identificador del usuario.
            user_prefs: Objeto UserPreferences con la configuración deseada.

        Returns:
            Preferences: La entidad de preferencias persistida.
        """
        # 1. Creación de la entidad de dominio (se ejecutan las validaciones de los setters)
        preferences_entity = Preferences(
            user_id=user_id,
            classification_method=user_prefs.classification_method,
            time_windows=user_prefs.time_window,
            stimulus_frequency=[stim.freq for stim in user_prefs.stimulus],
            stimulus_shape=[stim.shape_type for stim in user_prefs.stimulus],
            channels=user_prefs.channels,  
            stimulus_on=user_prefs.stimulus_on,
            stimulus_type=[stim.stim_type for stim in user_prefs.stimulus],
            stimulus_theta=[stim.theta for stim in user_prefs.stimulus],
            stimulus_direction=[stim.direction for stim in user_prefs.stimulus]
        )

        # 2. Decisión de persistencia (Upsert)
        existing_prefs = self.__prefs_repo.get_by_filter("user_id", user_id)

        if existing_prefs:
            self.__prefs_repo.update(preferences_entity)
        else:
            self.__prefs_repo.save(preferences_entity)
            
        return preferences_entity

    def get_user_preferences(self, user_id: int) -> UserPreferences:
        """
        Recupera y reconstruye las preferencias de un usuario específico.

        Transforma la entidad de dominio plana de vuelta a la estructura 
        anidada de dataclasses (`UserPreferences` y `Stimulus`) para su 
        consumo en la capa de presentación.

        Args:
            user_id: Identificador del usuario.

        Returns:
            UserPreferences: Objeto con la configuración reconstruida.

        Raises:
            ValueError: Si no se encuentran preferencias para el usuario.
        """
        prefs = self.__prefs_repo.get_by_filter("user_id", user_id)

        if prefs is None:
            raise ValueError("No se encontraron las preferencias de este usuario.")

        # Reconstrucción de la lista de estímulos anidados
        stimulus = [
            Stimulus(
                freq=freq,
                theta=theta,
                stim_type=stim_type,
                shape_type=shape,
                direction=direction,
            )
            for freq, theta, stim_type, shape, direction in zip(
                prefs.stimulus_frequency,
                prefs.stimulus_theta,
                prefs.stimulus_type,
                prefs.stimulus_shape,
                prefs.stimulus_direction,
            )
        ]

        return UserPreferences(
            classification_method=prefs.classification_method,
            time_window=prefs.time_windows,
            channels=prefs.channels,
            stimulus=stimulus,
            stimulus_on=prefs.stimulus_on,
        )

    def remove_user_preferences(self, user_id: int) -> None:
        """
        Elimina las preferencias asociadas a un usuario.

        Args:
            user_id: Identificador del usuario.
        """
        self.__prefs_repo.delete(user_id)


# ==============================================================================
# TrainingWeightsManager
# ==============================================================================

class TrainingWeightsManager:
    """
    Gestiona las operaciones de dominio relacionadas con los pesos y 
    datos de entrenamiento de los modelos de clasificación (ej. eTRCA).
    """

    def __init__(self, weights_repo: AbstractRepository) -> None:
        """
        Inicializa el TrainingWeightsManager.

        Args:
            weights_repo: Implementación concreta de AbstractRepository para pesos.
        """
        self.__weights_repo = weights_repo

    def save_or_update_weights(self, user_id: int, training_result: dict[str, Any]) -> TrainingWeights:
        """
        Guarda o actualiza los pesos de entrenamiento calculados.

        Args:
            user_id: Identificador del usuario.
            training_result: Diccionario con las claves 'trains', 'w', 
                             'num_fbs' y 'num_targets' (ej. salida de _ensembled_TRCA).

        Returns:
            TrainingWeights: La entidad de pesos persistida.
        """
        weights_entity = TrainingWeights(
            user_id=user_id,
            trains=training_result.get('trains'),
            w=training_result.get('w'),
            num_fbs=training_result.get('num_fbs'),
            num_targets=training_result.get('num_targets')
        )

        existing_weights = self.__weights_repo.get_by_filter("user_id", user_id)

        if existing_weights:
            self.__weights_repo.update(weights_entity)
        else:
            self.__weights_repo.save(weights_entity)

        return weights_entity

    def get_user_weights(self, user_id: int) -> dict[str, Any] | None:
        """
        Recupera los pesos de entrenamiento de un usuario en formato diccionario.

        Mantiene el mismo contrato de salida que el calculador de pesos 
        (ej. `CalculeTRCAWeights.get_weights()`).

        Args:
            user_id: Identificador del usuario.

        Returns:
            dict[str, Any] | None: Diccionario con 'trains', 'w', 'num_fbs', 
                                   'num_targets', o None si no existen.
        """
        weights = self.__weights_repo.get_by_filter("user_id", user_id)
        if not weights:
            return None
            
        return {
            'trains': weights.trains,
            'w': weights.w,
            'num_fbs': weights.num_fbs,
            'num_targets': weights.num_targets
        }

    def remove_user_weights(self, user_id: int) -> None:
        """
        Elimina los pesos de entrenamiento asociados a un usuario.

        Args:
            user_id: Identificador del usuario.
        """
        self.__weights_repo.delete(user_id)