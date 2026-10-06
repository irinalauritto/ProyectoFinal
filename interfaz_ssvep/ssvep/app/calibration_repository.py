"""Persistencia opcional del detalle completo de una corrida de
`FrequencyCalibrator` (accuracy por candidata, semilla, fecha, refresh
rate) -- para poder comparar corridas de distintas sesiones.

Archivo nuevo: no modifica `models.py` ni `repositories.py`. Define su
propia tabla reusando la misma `Base`/engine declarativa de `models.py`
(mismo patrón de `TrainingWeightsModel`, importado tal cual, no duplicado)
para que quede en la misma base SQLite sin tocar ningún archivo existente.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from ssvep.app.models import Base


class CalibrationRunModel(Base):
    """Una fila por corrida de calibración completa de un usuario.

    Attributes:
        id: Identificador autoincremental de la corrida.
        user_id: Usuario al que pertenece (borrado en cascada con el usuario).
        date: Fecha/hora ISO de la corrida.
        seed: Semilla de aleatorización usada (reproducibilidad).
        refresh_rate: Tasa de refresco (Hz) detectada del monitor.
        anchor_freq: Frecuencia del estímulo ancla usado como referencia.
        accuracies_json: `{frecuencia: accuracy}` de todas las candidatas, serializado.
        selected_json: Lista de las frecuencias finalmente seleccionadas, serializada.
    """

    __tablename__ = "calibration_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[str] = mapped_column(String(50), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    refresh_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_freq: Mapped[float] = mapped_column(Float, nullable=False)
    accuracies_json: Mapped[str] = mapped_column(Text, nullable=False)
    selected_json: Mapped[str] = mapped_column(Text, nullable=False)


class CalibrationRunRepository:
    """Repositorio simple (no implementa `AbstractRepository`: esta tabla
    es de solo agregar/consultar historial, no un recurso CRUD de dominio
    como User/Preferences) para guardar y listar corridas de calibración."""

    def __init__(self, session: Session) -> None:
        self.__session = session
        CalibrationRunModel.metadata.create_all(self.__session.bind)

    def save(self, user_id: int, result: Dict[str, Any]) -> None:
        """Guarda el resultado de una corrida (ver `FrequencyCalibrator._finish`
        para las claves esperadas: date, seed, refresh_rate, anchor_freq,
        accuracies, selected)."""
        row = CalibrationRunModel(
            user_id=user_id,
            date=result["date"],
            seed=int(result["seed"]),
            refresh_rate=int(result["refresh_rate"]),
            anchor_freq=float(result["anchor_freq"]),
            accuracies_json=json.dumps(result["accuracies"]),
            selected_json=json.dumps(result["selected"]),
        )
        self.__session.add(row)
        self.__session.commit()

    def get_all_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Corridas guardadas para un usuario, más reciente primero."""
        rows = (
            self.__session.query(CalibrationRunModel)
            .filter_by(user_id=user_id)
            .order_by(CalibrationRunModel.id.desc())
            .all()
        )
        return [
            {
                "date": row.date,
                "seed": row.seed,
                "refresh_rate": row.refresh_rate,
                "anchor_freq": row.anchor_freq,
                "accuracies": {float(k): v for k, v in json.loads(row.accuracies_json).items()},
                "selected": json.loads(row.selected_json),
            }
            for row in rows
        ]
