"""
Módulo de configuración de la aplicación Flask y la base de datos.
"""

import datetime
import os
from typing import Callable, Optional

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ==============================================================================
# Inicialización de la Aplicación
# ==============================================================================

app = Flask(__name__)

app.config['SECRET_KEY'] = '9zK7mN2wX4pQ8vB1rT5sY3eW6uJ0xL9a'
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(hours=2)
app.config.from_object(__name__)

# ==============================================================================
# Configuración de la Base de Datos (se resuelve en tiempo de ejecución)
# ==============================================================================

DATABASE_URL: Optional[str] = None
_engine = None


def init_database(base_dir: str) -> None:
    """
    Configura la ubicación de la base de datos a partir de la carpeta base de la app.

    Debe llamarse una única vez antes de usar `crear_engine()`.

    Args:
        base_dir: Carpeta base de la aplicación (ej: la que devuelve get_app_dir()).
    """
    global DATABASE_URL

    db_dir = os.path.join(base_dir, "data")
    os.makedirs(db_dir, exist_ok=True)

    db_path = os.path.join(db_dir, "user_database.db")
    DATABASE_URL = f'sqlite:///{db_path}'


def crear_engine() -> Callable[[], Session]:
    """
    Crea y devuelve un generador de sesiones de SQLAlchemy (sessionmaker).

    Requiere que `init_database(base_dir)` haya sido llamado previamente.

    Returns:
        Callable[[], Session]: Un `sessionmaker` que devuelve nuevas sesiones.

    Raises:
        RuntimeError: Si se llama antes de inicializar la base de datos.
    """
    global _engine

    if DATABASE_URL is None:
        raise RuntimeError(
            "La base de datos no fue inicializada. Llamá a init_database(base_dir) primero."
        )

    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False)

    return sessionmaker(bind=_engine)
