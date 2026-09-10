"""Store liviano de pacientes para la pantalla de Inicio.

No hay (todavia) una base compartida entre EMG y EEG/SSVEP: el modulo EEG
sigue con su propia base SQLite (ver interfaz_ssvep), que no se toca en esta
etapa. Para que "Elegir paciente guardado" funcione ya mismo en el shell
unificado, se usa un JSON simple en interfaz/data/patients.json.
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PATIENTS_FILE = DATA_DIR / "patients.json"


def load_patients() -> list[dict]:
    if not PATIENTS_FILE.exists():
        return []
    try:
        with open(PATIENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_patient(nombre: str, apellido: str, observaciones: str) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    patients = load_patients()
    entry = {
        "nombre": nombre,
        "apellido": apellido,
        "observaciones": observaciones,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    patients.append(entry)
    with open(PATIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)
    return entry
