"""Almacén unificado de pacientes (EMG y EEG/SSVEP).

Un solo archivo JSON con UNA ficha por paciente. Todo lo que la aplicación
guarda de un paciente queda acá y no se genera además en otros documentos
(sin PDF ni bitácoras por sesión). Cada ficha tiene:

  * su identidad y datos básicos;
  * `config`: los últimos ajustes de cada modalidad (no se pueden mezclar: el
    refractario es 500 ms en EMG y 5 s en EEG);
  * `historial`: UNA lista cronológica general con las sesiones, calibraciones
    y validaciones de cualquier modalidad (campo `modalidad` en cada una).

    {
      "version": 3,
      "patients": [
        {
          "id": "…", "nombre": "…", "apellido": "…", "observaciones": "…",
          "creado": "…", "ultima_sesion": "…", "ultima_modalidad": "emg"|"eeg"|null,
          "ssvep_user_id": 5 | null,          # vínculo con la base SQLite de SSVEP
          "config": {"emg": {…}, "eeg": {…}},
          "historial": [
            {"fecha": "…", "tipo": "sesion", "modalidad": "eeg", "fin": "…", "duracion_s": 1800},
            {"fecha": "…", "tipo": "calibracion", "modalidad": "emg", "umbral": …},
            {"fecha": "…", "tipo": "validacion", "modalidad": "eeg", "umbral": …}
          ]
        }
      ]
    }

La configuración de EEG que manda sigue siendo la de la base SQLite de
interfaz_ssvep (modo de entrada, frecuencias, canales, umbral): acá se la
REFLEJA para que quede en la ficha y se guardan además los ajustes que SQLite
no tiene (pulsación, refractario, tiempo de barrido).

El archivo vive fuera del repositorio (`%LOCALAPPDATA%\\ComandoAAC`): contiene
datos de pacientes y no debe subirse a git. Si no existe y hay uno viejo en
`interfaz/data/patients.json` (lista simple de EMG), se importa una sola vez.
También se migran las fichas del esquema 2 (bloques `emg`/`eeg` separados).
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

SCHEMA_VERSION = 3
MODALIDADES = ("emg", "eeg")
TIPOS_REGISTRO = ("calibracion", "validacion")
MAX_HISTORIAL = 500  # por paciente: los más viejos se descartan

APP_DIR = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "ComandoAAC"
PATIENTS_FILE = APP_DIR / "patients.json"
LEGACY_FILE = Path(__file__).resolve().parent.parent / "data" / "patients.json"

_lock = threading.RLock()


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _norm(text: str) -> str:
    return " ".join(str(text or "").split()).lower()


def full_name(entry: dict) -> str:
    return f"{entry.get('nombre', '')} {entry.get('apellido', '')}".strip()


def _blank_entry(nombre: str, apellido: str = "", observaciones: str = "") -> dict:
    now = _now()
    return {
        "id": uuid.uuid4().hex,
        "nombre": nombre.strip(),
        "apellido": apellido.strip(),
        "observaciones": observaciones,
        "creado": now,
        "fecha": now,  # última modificación de los datos básicos
        "ultima_sesion": None,
        "ultima_modalidad": None,
        "ssvep_user_id": None,
        "config": {m: {} for m in MODALIDADES},
        "historial": [],
    }


def _normalize(entry: dict) -> dict:
    """Lleva una ficha (de la lista simple vieja o del esquema 2) al esquema
    actual, sin perder nada de lo que ya tiene."""
    base = _blank_entry(entry.get("nombre", ""), entry.get("apellido", ""), entry.get("observaciones", ""))
    fecha = entry.get("fecha") or base["fecha"]
    base["creado"] = entry.get("creado") or fecha
    base["fecha"] = fecha
    for key in ("id", "ultima_sesion", "ultima_modalidad", "ssvep_user_id"):
        if entry.get(key) is not None:
            base[key] = entry[key]

    # --- configuración por modalidad
    config = entry.get("config")
    if isinstance(config, dict):
        for m in MODALIDADES:
            if isinstance(config.get(m), dict):
                base["config"][m] = dict(config[m])
    for m in MODALIDADES:  # esquema 2: bloque por modalidad
        bloque = entry.get(m)
        if isinstance(bloque, dict) and isinstance(bloque.get("config"), dict) and not base["config"][m]:
            base["config"][m] = dict(bloque["config"])

    # --- historial general
    historial = entry.get("historial")
    if isinstance(historial, list):
        base["historial"] = [dict(r) for r in historial if isinstance(r, dict)]
    else:  # esquema 2: calibraciones, validaciones y sesiones sueltas
        registros = []
        for m in MODALIDADES:
            bloque = entry.get(m)
            if not isinstance(bloque, dict):
                continue
            for tipo in TIPOS_REGISTRO:
                dato = bloque.get(tipo)
                if isinstance(dato, dict):
                    resto = {k: v for k, v in dato.items() if k != "fecha"}
                    registros.append({"fecha": dato.get("fecha", fecha), "tipo": tipo, "modalidad": m, **resto})
        for sesion in entry.get("sesiones", []) or []:
            if isinstance(sesion, dict):
                registros.append({
                    "fecha": sesion.get("inicio", fecha), "tipo": "sesion",
                    "modalidad": sesion.get("modalidad"), "fin": sesion.get("fin"),
                    "duracion_s": sesion.get("duracion_s"),
                })
        base["historial"] = sorted(registros, key=lambda r: str(r.get("fecha", "")))
    return base


# ----------------------------------------------------------------------
# Lectura y escritura (atómica)
# ----------------------------------------------------------------------
def _read_legacy() -> list[dict]:
    try:
        with open(LEGACY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data if isinstance(e, dict) and e.get("nombre")]
    except (OSError, ValueError):
        return []


def _write(data: dict) -> None:
    PATIENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATIENTS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PATIENTS_FILE)  # nunca queda un archivo a medio escribir


def _read() -> dict:
    with _lock:
        if not PATIENTS_FILE.exists():
            patients = []
            for old_entry in _read_legacy():
                entry = _normalize(old_entry)
                # La lista vieja solo guardaba pacientes de EMG.
                entry["ultima_modalidad"] = entry.get("ultima_modalidad") or "emg"
                patients.append(entry)
            data = {"version": SCHEMA_VERSION, "patients": patients}
            if patients:
                try:
                    _write(data)  # migración única de la lista vieja
                except OSError:
                    pass
            return data
        try:
            with open(PATIENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):  # por si alguien dejó una lista simple acá
                data = {"patients": data}
            patients = [_normalize(e) for e in data.get("patients", []) if isinstance(e, dict)]
            return {"version": SCHEMA_VERSION, "patients": patients}
        except (OSError, ValueError):
            # Archivo dañado: se lo conserva aparte (no se pierde) y se empieza limpio.
            try:
                PATIENTS_FILE.replace(PATIENTS_FILE.with_name(f"patients.corrupto-{int(time.time())}.json"))
            except OSError:
                pass
            return {"version": SCHEMA_VERSION, "patients": []}


def _mutate(patient_id: Optional[str], change: Callable[[dict], None]) -> bool:
    """Aplica `change(ficha)` a la ficha `patient_id` y guarda. False si no existe."""
    if not patient_id:
        return False
    with _lock:
        data = _read()
        for entry in data["patients"]:
            if entry["id"] == patient_id:
                change(entry)
                _write(data)
                return True
    return False


def _append(entry: dict, registro: dict) -> None:
    entry["historial"].append(registro)
    del entry["historial"][:-MAX_HISTORIAL]


# ----------------------------------------------------------------------
# Lista de pacientes
# ----------------------------------------------------------------------
def load_patients() -> list[dict]:
    return _read()["patients"]


def get_patient(patient_id: Optional[str]) -> Optional[dict]:
    if not patient_id:
        return None
    return next((e for e in load_patients() if e["id"] == patient_id), None)


def find_by_name(nombre: str, apellido: str = "") -> Optional[dict]:
    target = _norm(f"{nombre} {apellido}")
    return next((e for e in load_patients() if _norm(full_name(e)) == target), None)


def save_patient(nombre: str, apellido: str, observaciones: str) -> dict:
    """Crea la ficha, o actualiza las observaciones si ya hay un paciente con
    el mismo nombre y apellido (sin importar mayúsculas)."""
    with _lock:
        data = _read()
        target = _norm(f"{nombre} {apellido}")
        for entry in data["patients"]:
            if _norm(full_name(entry)) == target:
                entry["observaciones"] = observaciones
                entry["fecha"] = _now()
                _write(data)
                return entry
        entry = _blank_entry(nombre, apellido, observaciones)
        data["patients"].append(entry)
        _write(data)
        return entry


def modalities_of(entry: dict) -> list[str]:
    """Modalidades que el paciente ya usó."""
    usadas = []
    for modalidad in MODALIDADES:
        if (
            entry.get("config", {}).get(modalidad)
            or entry.get("ultima_modalidad") == modalidad
            or any(r.get("modalidad") == modalidad for r in entry.get("historial", []))
        ):
            usadas.append(modalidad)
    if entry.get("ssvep_user_id") is not None and "eeg" not in usadas:
        usadas.append("eeg")
    return usadas


# ----------------------------------------------------------------------
# Vínculo con la base SQLite de SSVEP
# ----------------------------------------------------------------------
def link_ssvep_user(patient_id: Optional[str], user_id: int) -> None:
    _mutate(patient_id, lambda e: e.__setitem__("ssvep_user_id", int(user_id)))


def sync_ssvep_users(users: Iterable[tuple[int, str]]) -> int:
    """Unifica la lista: cada usuario de la base SSVEP queda vinculado a una
    ficha (por vínculo previo o por nombre) y los que no tienen ficha se
    agregan. Devuelve cuántas fichas se agregaron."""
    users = list(users)
    if not users:
        return 0
    added = 0
    with _lock:
        data = _read()
        changed = False
        for user_id, name in users:
            target = _norm(name)
            entry = next((e for e in data["patients"] if e.get("ssvep_user_id") == user_id), None)
            if entry is None:
                entry = next(
                    (e for e in data["patients"] if _norm(full_name(e)) == target and e.get("ssvep_user_id") is None),
                    None,
                )
                if entry is not None:
                    entry["ssvep_user_id"] = int(user_id)
                    changed = True
            if entry is None:
                entry = _blank_entry(str(name))
                entry["ssvep_user_id"] = int(user_id)
                data["patients"].append(entry)
                added += 1
                changed = True
        if changed:
            _write(data)
    return added


# ----------------------------------------------------------------------
# Configuración por modalidad
# ----------------------------------------------------------------------
def get_config(patient_id: Optional[str], modalidad: str) -> dict:
    entry = get_patient(patient_id)
    return dict(((entry or {}).get("config") or {}).get(modalidad) or {})


def update_config(patient_id: Optional[str], modalidad: str, config: dict) -> bool:
    """Mezcla `config` con la configuración guardada de esa modalidad."""

    def change(entry: dict) -> None:
        entry["config"].setdefault(modalidad, {}).update(config)
        entry["config"][modalidad]["actualizado"] = _now()

    return _mutate(patient_id, change)


# ----------------------------------------------------------------------
# Historial general
# ----------------------------------------------------------------------
def add_record(patient_id: Optional[str], modalidad: str, tipo: str, data: dict) -> bool:
    """Agrega al historial un resultado ("calibracion" o "validacion")."""
    if tipo not in TIPOS_REGISTRO:
        raise ValueError(f"Tipo de registro desconocido: {tipo!r}")

    def change(entry: dict) -> None:
        _append(entry, {"fecha": _now(), "tipo": tipo, "modalidad": modalidad, **data})

    return _mutate(patient_id, change)


set_result = add_record  # nombre usado por las pantallas


def last_record(entry: dict, tipo: str, modalidad: Optional[str] = None) -> Optional[dict]:
    """Último registro de ese tipo (y modalidad, si se indica)."""
    for registro in reversed(entry.get("historial", [])):
        if registro.get("tipo") == tipo and (modalidad is None or registro.get("modalidad") == modalidad):
            return registro
    return None


def _close_open_sessions(entry: dict) -> None:
    now = datetime.now()
    for registro in entry["historial"]:
        if registro.get("tipo") == "sesion" and registro.get("fin") is None:
            registro["fin"] = now.isoformat(timespec="seconds")
            try:
                registro["duracion_s"] = max(0, round((now - datetime.fromisoformat(registro["fecha"])).total_seconds()))
            except (KeyError, ValueError):
                registro["duracion_s"] = None


def start_session(patient_id: Optional[str], modalidad: str) -> bool:
    def change(entry: dict) -> None:
        _close_open_sessions(entry)
        now = _now()
        _append(entry, {"fecha": now, "tipo": "sesion", "modalidad": modalidad, "fin": None, "duracion_s": None})
        entry["ultima_sesion"] = now
        entry["ultima_modalidad"] = modalidad

    return _mutate(patient_id, change)


def end_session(patient_id: Optional[str]) -> bool:
    return _mutate(patient_id, _close_open_sessions)
