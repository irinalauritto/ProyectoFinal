import json
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from ssvep.app.domain import User, Preferences, TrainingWeights
from ssvep.app.abstract_repository import AbstractRepository
from ssvep.app.models import UserModel, PreferencesModel, TrainingWeightsModel


class UserRepositorySQLAlchemy(AbstractRepository):
    """
    Repositorio para gestionar la persistencia de entidades User en la base de datos.
    
    Implementa el patrón Repository utilizando SQLAlchemy como ORM.
    """

    def __init__(self, session: Session) -> None:
        """
        Inicializa el repositorio con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy para interactuar con la base de datos.
        """
        self.__session = session
        # Asegura la creación de la tabla si no existe (Nota: considerar mover a migraciones en el futuro)
        UserModel.metadata.create_all(self.__session.bind)

    def save(self, user: User) -> None:
        """
        Guarda un nuevo usuario en la base de datos.

        Args:
            user: Entidad de dominio User a guardar.

        Raises:
            ValueError: Si el parámetro no es una instancia de la clase User.
        """
        if not isinstance(user, User):
            raise ValueError("The parameter is not an instance of the User class")
        
        db_user = self.__map_entity_to_model(user)
        self.__session.add(db_user)
        self.__session.commit()
        self.__session.refresh(db_user)
        
        # Sincroniza el ID generado por la BD con la entidad de dominio
        user.id = db_user.id

    def get_all(self) -> Dict[int, str]:
        """
        Obtiene todos los usuarios registrados.

        Returns:
            Un diccionario donde la clave es el ID del usuario y el valor es su nombre.
        """
        db_users = self.__session.query(UserModel).all()
        return {user.id: user.name for user in db_users}
    
    def update(self, updated_user: User) -> None:
        """
        Actualiza la información de un usuario existente.

        Args:
            updated_user: Entidad de dominio User con los datos actualizados.

        Raises:
            ValueError: Si el parámetro no es una instancia de la clase User.
        """
        if not isinstance(updated_user, User):
            raise ValueError("The parameter is not an instance of the User class")
            
        db_user = self.__session.query(UserModel).filter_by(id=updated_user.id).first()
        if db_user:
            db_user.name = updated_user.name
            self.__session.commit()

    def get_by_filter(self, filter_key: str, value: Any) -> Optional[User]:
        """
        Obtiene un usuario filtrando por una columna específica.

        Args:
            filter_key: Nombre de la columna por la que filtrar (ej. 'id', 'name').
            value: Valor a buscar en la columna especificada.

        Returns:
            La entidad de dominio User si se encuentra, de lo contrario None.
        """
        db_user = self.__session.query(UserModel).filter_by(**{filter_key: value}).first()
        return self.__map_model_to_entity(db_user) if db_user else None
    
    def delete(self, entity_id: int) -> None:
        """
        Elimina un usuario de la base de datos por su ID.

        Args:
            entity_id: ID del usuario a eliminar.
        """
        db_user = self.__session.query(UserModel).filter_by(id=entity_id).first()
        if db_user:
            self.__session.delete(db_user)
            self.__session.commit()
    
    def __map_entity_to_model(self, entity: User) -> UserModel:
        """Convierte una entidad de dominio User en un modelo de SQLAlchemy."""
        return UserModel(
            id=entity.id,
            name=entity.name
        )
        
    def __map_model_to_entity(self, model: UserModel) -> User:
        """Convierte un modelo de SQLAlchemy en una entidad de dominio User."""
        return User(
            user_id=model.id,
            user_name=model.name
        )


class PreferencesRepositorySQLAlchemy(AbstractRepository):
    """
    Repositorio para gestionar la persistencia de entidades Preferences.
    
    Maneja la serialización y deserialización automática de listas y diccionarios 
    a formato JSON para su almacenamiento en columnas de texto de la base de datos.
    """

    def __init__(self, session: Session) -> None:
        """
        Inicializa el repositorio con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy.
        """
        self.__session = session
        PreferencesModel.metadata.create_all(self.__session.bind)

    def save(self, preferences: Preferences) -> None:
        """
        Guarda un nuevo registro de preferencias en la base de datos.

        Args:
            preferences: Entidad de dominio Preferences a guardar.

        Raises:
            ValueError: Si el parámetro no es una instancia de la clase Preferences.
        """
        if not isinstance(preferences, Preferences):
            raise ValueError("The parameter is not an instance of the Preferences class")
            
        db_prefs = self.__map_entity_to_model(preferences)
        self.__session.add(db_prefs)
        self.__session.commit()

    def get_all(self) -> List[Preferences]:
        """
        Obtiene todos los registros de preferencias.

        Returns:
            Una lista de entidades de dominio Preferences.
        """
        db_prefs = self.__session.query(PreferencesModel).all()
        return [self.__map_model_to_entity(prefs) for prefs in db_prefs]
    
    def update(self, updated_prefs: Preferences) -> None:
        """
        Actualiza las preferencias de un usuario existente.

        Args:
            updated_prefs: Entidad de dominio Preferences con los datos actualizados.

        Raises:
            ValueError: Si el parámetro no es una instancia de la clase Preferences.
        """
        if not isinstance(updated_prefs, Preferences):
            raise ValueError("The parameter is not an instance of the Preferences class")
            
        db_prefs = self.__session.query(PreferencesModel).filter_by(user_id=updated_prefs.user_id).first()

        if db_prefs:
            db_prefs.time_windows = updated_prefs.time_windows
            db_prefs.classification_method = updated_prefs.classification_method
            # Serialización de estructuras de datos a JSON String
            db_prefs.stim_frequency = json.dumps(updated_prefs.stimulus_frequency)
            db_prefs.stim_shape = json.dumps(updated_prefs.stimulus_shape)
            db_prefs.channels = json.dumps(updated_prefs.channels)
            db_prefs.stim_on = json.dumps(updated_prefs.stimulus_on)
            db_prefs.stim_theta = json.dumps(updated_prefs.stimulus_theta)
            db_prefs.stim_type = json.dumps(updated_prefs.stimulus_type)
            db_prefs.stim_direction = json.dumps(updated_prefs.stimulus_direction)
            self.__session.commit()

    def get_by_filter(self, filter_key: str, value: Any) -> Optional[Preferences]:
        """
        Obtiene preferencias filtrando por una columna específica.

        Args:
            filter_key: Nombre de la columna por la que filtrar (ej. 'user_id').
            value: Valor a buscar.

        Returns:
            La entidad de dominio Preferences si se encuentra, de lo contrario None.
        """
        db_prefs = self.__session.query(PreferencesModel).filter_by(**{filter_key: value}).first()
        return self.__map_model_to_entity(db_prefs) if db_prefs else None
    
    def delete(self, entity_id: int) -> None:
        """
        Elimina las preferencias asociadas a un ID de usuario.

        Args:
            entity_id: ID del usuario cuyas preferencias se eliminarán.
        """
        db_prefs = self.__session.query(PreferencesModel).filter_by(user_id=entity_id).first()
        if db_prefs:
            self.__session.delete(db_prefs)
            self.__session.commit()
            
    def __map_entity_to_model(self, entity: Preferences) -> PreferencesModel:
        """Convierte una entidad de dominio Preferences en un modelo de SQLAlchemy."""
        return PreferencesModel(
            user_id=entity.user_id,
            time_windows=entity.time_windows,
            classification_method=entity.classification_method,
            stim_frequency=json.dumps(entity.stimulus_frequency),
            stim_shape=json.dumps(entity.stimulus_shape),
            channels=json.dumps(entity.channels),
            stim_on=json.dumps(entity.stimulus_on),
            stim_theta=json.dumps(entity.stimulus_theta),
            stim_type=json.dumps(entity.stimulus_type),
            stim_direction=json.dumps(entity.stimulus_direction)
        )
    
    def __map_model_to_entity(self, model: PreferencesModel) -> Preferences:
        """
        Convierte un modelo de SQLAlchemy en una entidad de dominio Preferences.
        Deserializa las cadenas JSON a sus tipos de datos originales (listas, dicts, bools).
        """
        return Preferences(
            user_id=int(model.user_id),
            classification_method=model.classification_method,
            time_windows=float(model.time_windows),
            stimulus_frequency=[float(f) for f in json.loads(model.stim_frequency)],
            stimulus_shape=json.loads(model.stim_shape),
            channels={int(k): v for k, v in json.loads(model.channels).items()},
            stimulus_on=[bool(x) for x in json.loads(model.stim_on)],
            stimulus_type=json.loads(model.stim_type),
            stimulus_theta=[float(t) for t in json.loads(model.stim_theta)],
            stimulus_direction=json.loads(model.stim_direction)
        )


class TrainingWeightsRepositorySQLAlchemy(AbstractRepository):
    """
    Repositorio para gestionar la persistencia de entidades TrainingWeights.
    
    Maneja la serialización de arrays de NumPy a formato JSON para su 
    almacenamiento en la base de datos.
    """

    def __init__(self, session: Session) -> None:
        """
        Inicializa el repositorio con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy.
        """
        self.__session = session
        TrainingWeightsModel.metadata.create_all(self.__session.bind)

    def save(self, weights: TrainingWeights) -> None:
        """
        Guarda un nuevo registro de pesos de entrenamiento.

        Args:
            weights: Entidad de dominio TrainingWeights a guardar.

        Raises:
            ValueError: Si el parámetro no es una instancia de la clase TrainingWeights.
        """
        if not isinstance(weights, TrainingWeights):
            raise ValueError("The parameter is not an instance of the TrainingWeights class")
            
        db_weights = self.__map_entity_to_model(weights)
        self.__session.add(db_weights)
        self.__session.commit()

    def get_all(self) -> List[TrainingWeights]:
        """
        Obtiene todos los registros de pesos de entrenamiento.

        Returns:
            Una lista de entidades de dominio TrainingWeights.
        """
        db_weights = self.__session.query(TrainingWeightsModel).all()
        return [self.__map_model_to_entity(w) for w in db_weights]

    def update(self, updated_weights: TrainingWeights) -> None:
        """
        Actualiza los pesos de entrenamiento de un usuario existente.

        Args:
            updated_weights: Entidad de dominio TrainingWeights con los datos actualizados.

        Raises:
            ValueError: Si el parámetro no es una instancia de la clase TrainingWeights.
        """
        if not isinstance(updated_weights, TrainingWeights):
            raise ValueError("The parameter is not an instance of the TrainingWeights class")
            
        db_weights = self.__session.query(TrainingWeightsModel).filter_by(user_id=updated_weights.user_id).first()
        if db_weights:
            db_weights.trains = json.dumps(updated_weights.trains.tolist())
            db_weights.w = json.dumps(updated_weights.w.tolist())
            db_weights.num_fbs = updated_weights.num_fbs
            db_weights.num_targets = updated_weights.num_targets
            self.__session.commit()

    def get_by_filter(self, filter_key: str, value: Any) -> Optional[TrainingWeights]:
        """
        Obtiene pesos de entrenamiento filtrando por una columna específica.

        Args:
            filter_key: Nombre de la columna por la que filtrar (ej. 'user_id').
            value: Valor a buscar.

        Returns:
            La entidad de dominio TrainingWeights si se encuentra, de lo contrario None.
        """
        db_weights = self.__session.query(TrainingWeightsModel).filter_by(**{filter_key: value}).first()
        return self.__map_model_to_entity(db_weights) if db_weights else None

    def delete(self, entity_id: int) -> None:
        """
        Elimina los pesos de entrenamiento asociados a un ID de usuario.

        Args:
            entity_id: ID del usuario cuyos pesos se eliminarán.
        """
        db_weights = self.__session.query(TrainingWeightsModel).filter_by(user_id=entity_id).first()
        if db_weights:
            self.__session.delete(db_weights)
            self.__session.commit()

    def __map_entity_to_model(self, entity: TrainingWeights) -> TrainingWeightsModel:
        """Convierte una entidad de dominio TrainingWeights en un modelo de SQLAlchemy."""
        return TrainingWeightsModel(
            user_id=entity.user_id,
            trains=json.dumps(entity.trains.tolist()),
            w=json.dumps(entity.w.tolist()),
            num_fbs=entity.num_fbs,
            num_targets=entity.num_targets
        )

    def __map_model_to_entity(self, model: TrainingWeightsModel) -> TrainingWeights:
        """
        Convierte un modelo de SQLAlchemy en una entidad de dominio TrainingWeights.
        Deserializa las cadenas JSON a arrays de NumPy de tipo float.
        """
        return TrainingWeights(
            user_id=model.user_id,
            trains=np.array(json.loads(model.trains), dtype=float),
            w=np.array(json.loads(model.w), dtype=float),
            num_fbs=int(model.num_fbs),
            num_targets=int(model.num_targets)
        )