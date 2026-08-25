from ssvep.app.config import crear_engine
from ssvep.app.repositories import UserRepositorySQLAlchemy, PreferencesRepositorySQLAlchemy, TrainingWeightsRepositorySQLAlchemy

def create_repositories():
    """
    Inicializa el motor de la base de datos (Session) y construye las 
    tres instancias de los repositorios concretos listos para usar.
    """
    # 1. Obtenemos el creador de sesiones de tu archivo config
    session_factory = crear_engine()
    
    # 2. Instanciamos una sesión activa de SQLAlchemy
    session = session_factory()
    
    # 3. Construimos los repositorios inyectándoles la sesión abierta
    user_repo = UserRepositorySQLAlchemy(session)
    preferences_repo = PreferencesRepositorySQLAlchemy(session)
    weights_repo = TrainingWeightsRepositorySQLAlchemy(session)
    
    # Devuelve la tupla con los tres repositorios listos
    return user_repo, preferences_repo, weights_repo