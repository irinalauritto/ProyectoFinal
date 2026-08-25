"""Carga de grabaciones SSVEP guardadas por TrainingManager (.mat)."""

from scipy.io import loadmat


def load_recording(path: str) -> dict:
    """
    Carga un archivo .mat de sesión SSVEP.

    Args:
        path (str): Ruta al archivo .mat.

    Returns:
        dict: Diccionario con las claves 'eeg', 'events' e 'info'
            (ver `TrainingManager.__save_data_mat`).
    """
    return loadmat(path, simplify_cells=True)
