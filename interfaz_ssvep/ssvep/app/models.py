"""
Módulo de modelos de base de datos (SQLAlchemy ORM).

Este módulo define la estructura de las tablas en la base de datos SQLite,
mapeando las entidades de dominio (User, Preferences, TrainingWeights) 
a sus respectivas representaciones persistentes.
"""

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ==============================================================================
# Base ORM
# ==============================================================================

class Base(DeclarativeBase):
    """
    Clase base declarativa para todos los modelos ORM de la aplicación.
    
    Heredar de esta clase permite que SQLAlchemy registre automáticamente 
    los metadatos de las tablas definidas.
    """
    pass


# ==============================================================================
# Modelos de Base de Datos
# ==============================================================================

class UserModel(Base):
    """
    Representación en base de datos de la entidad User.

    Attributes:
        id: Identificador único y clave primaria del usuario (autoincremental).
        name: Nombre del usuario (máximo 255 caracteres, no nulo).
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class PreferencesModel(Base):
    """
    Representación en base de datos de las preferencias experimentales de un usuario.

    Nota:
        Los campos que representan listas (ej. `stim_frequency`, `channels`) 
        se almacenan como cadenas de texto (`String(1000)`). Se asume que 
        estos datos se serializan (ej. mediante JSON o CSV) antes de guardarse 
        y se deserializan al recuperarse.

    Attributes:
        user_id: Clave primaria y clave foránea a la tabla 'users' (con borrado en cascada).
        classification_method: Método de clasificación seleccionado (ej. 'eTRCA', 'CCA').
        time_windows: Longitud de la ventana de tiempo en segundos.
        stim_frequency: Frecuencias de los estímulos (serializado).
        stim_shape: Formas geométricas de los estímulos (serializado).
        channels: Canales de EEG seleccionados (serializado).
        stim_on: Estado de activación de cada estímulo (serializado).
        stim_theta: Fases o ángulos de los estímulos (serializado).
        stim_type: Tipos de estímulos (serializado).
        stim_direction: Direcciones de movimiento de los estímulos (serializado).
    """
    __tablename__ = "preferences"

    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    classification_method: Mapped[str] = mapped_column(String(50), nullable=False)
    time_windows: Mapped[float] = mapped_column(Float, nullable=False)
    
    stim_frequency: Mapped[str] = mapped_column(String(1000), nullable=False)
    stim_shape: Mapped[str] = mapped_column(String(1000), nullable=False)
    channels: Mapped[str] = mapped_column(String(1000), nullable=False)
    stim_on: Mapped[str] = mapped_column(String(1000), nullable=False)
    stim_theta: Mapped[str] = mapped_column(String(1000), nullable=False)
    stim_type: Mapped[str] = mapped_column(String(1000), nullable=False)
    stim_direction: Mapped[str] = mapped_column(String(1000), nullable=False)


class TrainingWeightsModel(Base):
    """
    Representación en base de datos de los pesos y datos de entrenamiento (TRCA).

    Attributes:
        user_id: Clave primaria y clave foránea a la tabla 'users' (con borrado en cascada).
        trains: Datos de entrenamiento (matriz serializada).
        w: Matriz de pesos calculada (serializada).
        num_fbs: Número de bandas de frecuencia utilizadas.
        num_targets: Número de objetivos (targets) del paradigma experimental.
    """
    __tablename__ = "training_weights"

    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    
    # Se usa Text en lugar de String para las matrices, ya que su representación 
    # en texto (ej. JSON) puede superar fácilmente los límites de un String estándar.
    trains: Mapped[str] = mapped_column(Text, nullable=False)
    w: Mapped[str] = mapped_column(Text, nullable=False)
    num_fbs: Mapped[int] = mapped_column(Integer, nullable=False)
    num_targets: Mapped[int] = mapped_column(Integer, nullable=False)