"""
Grabación de las señales de una etapa de la sesión EEG o EMG (calibración, validación
o uso online) en un archivo .mat, cuando está marcado "Guardar señales".

Se guarda la señal cruda, tal como sale de la adquisición (sin filtros), junto con lo
que se calculó con ella y los eventos de la etapa. Contenido del .mat (se lee con
`scipy.io.loadmat(ruta, simplify_cells=True)`):

    eeg o emg:      muestra, canal1, ..., canalN (señal cruda).
    ventanas:       solo EEG: muestra, t_s, ventana_completa, ganador, margen, voto.
    ventanas_rho:   solo EEG: correlación de cada estímulo activo, una fila por ventana.
    calculos:       solo EMG: una fila por muestra (ver `formato_calculos`).
    eventos:        lista de {tipo, muestra, t_s, ...} según la etapa.
    info:           paciente, canales, frecuencias, filtros, umbral, etc.
    resultado:      lo que calculó la etapa al terminar.
    estado:         "completa", "cancelada" o "fallida".

La columna `muestra` de ventanas y eventos es el contador de muestras crudas al
momento de registrarlos: vale para ubicarlos en la señal, con la precisión de un
bloque de adquisición.

Las muestras llegan desde el hilo de adquisición y las ventanas desde el de
procesamiento, por eso todo pasa por un lock.

Autora: Irina Lauritto
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
from scipy.io import savemat

WINDOW_COLUMNS = ["muestra", "t_s", "ventana_completa", "ganador", "margen", "voto"]

# Carpeta de las señales. Va fuera de interfaz/datos_pacientes/, que git ignora.
SENALES_DIR = Path(__file__).resolve().parents[2] / "senales"


def session_folder(patient: str, prefix: str = "") -> Path:
    """Carpeta para las señales de una sesión nueva del paciente."""
    return SENALES_DIR / patient / f"{prefix}{datetime.now():%Y-%m-%d_%H-%M-%S}"


def _to_mat(value: Any) -> Any:
    """Convierte `value` a algo que savemat acepta (no admite None ni claves numéricas)."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return {str(key): _to_mat(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        items = [_to_mat(val) for val in value]
        if items and all(isinstance(val, (bool, int, float)) for val in items):
            return np.asarray(items, dtype=float)
        cell = np.empty(len(items), dtype=object)
        for i, item in enumerate(items):
            cell[i] = item
        return cell
    return value


class SignalRecorder:
    """Acumula en memoria una etapa por vez y la escribe al terminar."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self._stage: Optional[str] = None
        self._capturing = False
        self._path: Optional[Path] = None
        self._info: dict = {}
        self._chunks: list[np.ndarray] = []
        self._n_samples = 0
        self._windows: list[list[float]] = []
        self._rhos: list[np.ndarray] = []
        self._events: list[dict] = []
        self._calculations: list[np.ndarray] = []
        self._signal_name = "eeg"
        self._calculation_format = ""
        self._start = 0.0

    @property
    def stage(self) -> Optional[str]:
        return self._stage

    @property
    def capturing(self) -> bool:
        return self._capturing

    def begin(self, stage: str, info: dict, path: Path, signal_name: str = "eeg", calculation_format: str = "") -> None:
        with self._lock:
            self._reset()
            self._stage = stage
            self._signal_name = signal_name
            self._calculation_format = calculation_format
            self._info = dict(info)
            self._path = Path(path)
            self._start = time.monotonic()
            self._capturing = True

    def stop_capture(self) -> None:
        """Deja de acumular, pero la etapa sigue abierta hasta `finish`."""
        with self._lock:
            self._capturing = False

    def add_samples(self, samples: Any) -> None:
        """Recibe un bloque crudo de la interfaz de adquisición: una secuencia por canal."""
        if not self._capturing:
            return
        block = np.asarray(samples)
        if block.ndim != 2 or block.shape[1] == 0:
            return
        with self._lock:
            if self._capturing:
                self._chunks.append(block.T.astype(np.int64))
                self._n_samples += block.shape[1]

    def add_calculations(self, rows: Any) -> None:
        """Registra lo calculado para un bloque de muestras, una fila por muestra."""
        with self._lock:
            if self._capturing:
                self._calculations.append(np.asarray(rows, dtype=float))

    def add_window(self, rho: Any, margin: float, winner: int, vote: int, full: bool) -> None:
        """Registra lo que calculó el clasificador en una ventana (ver `set_window_observer`)."""
        with self._lock:
            if not self._capturing:
                return
            elapsed = time.monotonic() - self._start
            self._windows.append([self._n_samples, elapsed, float(full), winner, margin, vote])
            self._rhos.append(np.asarray(rho, dtype=float))

    def add_event(self, kind: str, **data: Any) -> None:
        with self._lock:
            if not self._capturing:
                return
            elapsed = time.monotonic() - self._start
            self._events.append({"tipo": kind, "muestra": self._n_samples, "t_s": elapsed, **data})

    def finish(self, status: str, result: Optional[dict] = None) -> Optional[Path]:
        """Escribe el .mat y cierra la etapa. Devuelve la ruta, o None si no había etapa abierta."""
        with self._lock:
            if self._stage is None:
                return None
            path, stage, info = self._path, self._stage, self._info
            chunks, n_samples = self._chunks, self._n_samples
            windows, rhos, events = self._windows, self._rhos, self._events
            calculations, signal_name = self._calculations, self._signal_name
            calculation_format = self._calculation_format
            self._reset()

        n_channels = chunks[0].shape[1] if chunks else len(info.get("canales", []))
        raw = np.vstack(chunks) if chunks else np.zeros((0, n_channels), dtype=np.int64)
        eeg = np.column_stack([np.arange(n_samples, dtype=np.int64), raw]) if n_samples else np.zeros((0, n_channels + 1))

        n_targets = max((rho.size for rho in rhos), default=0)
        rho_matrix = np.full((len(rhos), n_targets), np.nan)
        for row, rho in enumerate(rhos):
            rho_matrix[row, : rho.size] = rho

        content = {
            signal_name: eeg,
            f"formato_{signal_name}": "muestra, canal1, ..., canalN",
            "eventos": _to_mat(events),
            "info": _to_mat(info),
            "resultado": _to_mat(result or {}),
            "etapa": stage,
            "estado": status,
        }
        if signal_name == "eeg":
            content["ventanas"] = np.asarray(windows, dtype=float).reshape(-1, len(WINDOW_COLUMNS))
            content["formato_ventanas"] = ", ".join(WINDOW_COLUMNS)
            content["ventanas_rho"] = rho_matrix
        if calculation_format:
            content["calculos"] = np.vstack(calculations) if calculations else np.zeros((0, 0))
            content["formato_calculos"] = calculation_format

        path.parent.mkdir(parents=True, exist_ok=True)
        savemat(str(path), content, do_compression=True)
        return path
