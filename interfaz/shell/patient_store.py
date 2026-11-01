"""Almacén unificado de pacientes (EMG y EEG/SSVEP).

Un archivo JSON por paciente (su ficha). Todo lo que la aplicación guarda de
un paciente queda en su archivo y no se genera además en otros documentos
(sin PDF ni bitácoras por sesión). Cada ficha tiene:

  * su identidad y datos básicos;
  * `config`: los últimos ajustes de cada modalidad (no se pueden mezclar: el
    refractario es 500 ms en EMG y 5 s en EEG);
  * `historial`: UNA lista cronológica general con las sesiones, calibraciones
    y validaciones de cualquier modalidad (campo `modalidad` en cada una).

    datos_pacientes/Ana_Evequoz_1a2b3c4d.json:
    {
      "version": 3,
      "id": "…", "nombre": "…", "apellido": "…", "observaciones": "…",
      "creado": "…", "ultima_sesion": "…", "ultima_modalidad": "emg"|"eeg"|null,
      "ssvep_user_id": 5 | null,          # vínculo con la base SQLite de SSVEP
      "asterics_configurado": "…" | null, # cuándo se preparó su perfil de AsTeRICS
      "config": {"emg": {…}, "eeg": {…}},
      "historial": [
        {"fecha": "…", "tipo": "sesion", "modalidad": "eeg", "fin": "…", "duracion_s": 1800},
        {"fecha": "…", "tipo": "calibracion", "modalidad": "emg", "umbral": …},
        {"fecha": "…", "tipo": "validacion", "modalidad": "eeg", "umbral": …}
      ]
    }

La configuración de EEG que manda sigue siendo la de la base SQLite de
interfaz_ssvep (modo de entrada, frecuencias, canales, umbral): acá se la
REFLEJA para que quede en la ficha y se guardan además los ajustes que SQLite
no tiene (pulsación, refractario, tiempo de barrido).

Los archivos viven en `interfaz/datos_pacientes/` (ignorada por git: contiene
datos de pacientes y el repositorio es público). Si la carpeta todavía no tiene
fichas, se separa una sola vez la lista única que usaban las versiones
anteriores: `datos_pacientes/patients.json` (que queda renombrado como
`patients.migrado.json`), o si no `%LOCALAPPDATA%\\ComandoAAC\\patients.json`,
o si no la lista simple de EMG de `interfaz/data/patients.json`.
También se migran las fichas del esquema 2 (bloques `emg`/`eeg` separados).
"""

from __future__ import annotations

import json
import os
import re
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

_INTERFAZ_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = _INTERFAZ_DIR / "datos_pacientes"
# Listas únicas de versiones anteriores: se separan en fichas la primera vez.
SINGLE_FILE = PATIENTS_DIR / "patients.json"
OLD_APP_FILE = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "ComandoAAC" / "patients.json"
LEGACY_FILE = _INTERFAZ_DIR / "data" / "patients.json"

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
        "asterics_configurado": None,
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
    for key in ("id", "ultima_sesion", "ultima_modalidad", "ssvep_user_id", "asterics_configurado"):
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
def _read_list(path: Path) -> list[dict]:
    """Fichas de una lista única vieja (esquema 3 `{"patients": [...]}` o lista simple)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("patients", [])
    return [e for e in data if isinstance(e, dict) and e.get("nombre")]


def patient_file(entry: dict) -> Path:
    """Archivo de la ficha: nombre legible + comienzo del id (por si se repite el nombre)."""
    nombre = re.sub(r"[^\w-]+", "_", full_name(entry)).strip("_") or "paciente"
    return PATIENTS_DIR / f"{nombre}_{entry['id'][:8]}.json"


def _write_entry(entry: dict) -> None:
    path = patient_file(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": SCHEMA_VERSION, **entry}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # nunca queda un archivo a medio escribir


def _write(data: dict) -> None:
    for entry in data["patients"]:
        _write_entry(entry)


def _migrate_single_list() -> None:
    """Separa en fichas la lista única de versiones anteriores (una sola vez)."""
    if SINGLE_FILE.exists():
        old = _read_list(SINGLE_FILE)
    elif OLD_APP_FILE.exists():
        old = _read_list(OLD_APP_FILE)  # el original queda como respaldo
    else:
        # La lista vieja de interfaz/data solo guardaba pacientes de EMG.
        old = [{**e, "ultima_modalidad": e.get("ultima_modalidad") or "emg"} for e in _read_list(LEGACY_FILE)]
    if not old:
        return
    try:
        for e in old:
            _write_entry(_normalize(e))
        if SINGLE_FILE.exists():
            SINGLE_FILE.replace(SINGLE_FILE.with_name("patients.migrado.json"))
    except OSError:
        pass


def _read() -> dict:
    with _lock:
        if not any(PATIENTS_DIR.glob("*.json")) or SINGLE_FILE.exists():
            _migrate_single_list()
        patients = []
        for path in PATIENTS_DIR.glob("*.json"):
            if path.name.startswith("patients."):  # respaldos de la lista única
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("nombre"):
                    patients.append(_normalize(data))
            except (OSError, ValueError):
                # Archivo dañado: se lo conserva aparte (no se pierde) y se sigue con los demás.
                try:
                    path.replace(path.with_suffix(f".corrupto-{int(time.time())}"))
                except OSError:
                    pass
        patients.sort(key=lambda e: str(e.get("creado", "")))
        return {"version": SCHEMA_VERSION, "patients": patients}


def _mutate(patient_id: Optional[str], change: Callable[[dict], None]) -> bool:
    """Aplica `change(ficha)` a la ficha `patient_id` y guarda. False si no existe."""
    if not patient_id:
        return False
    with _lock:
        data = _read()
        for entry in data["patients"]:
            if entry["id"] == patient_id:
                change(entry)
                _write_entry(entry)
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
                _write_entry(entry)
                return entry
        entry = _blank_entry(nombre, apellido, observaciones)
        _write_entry(entry)
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
# Perfil de AsTeRICS del paciente
# ----------------------------------------------------------------------
def set_asterics_configured(patient_id: Optional[str], configured: bool = True) -> bool:
    """Marca (o desmarca) que el perfil de AsTeRICS del paciente ya tiene su
    usuario y su tablero cargados (ver asterics_config.profile_dir)."""
    return _mutate(patient_id, lambda e: e.__setitem__("asterics_configurado", _now() if configured else None))


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
