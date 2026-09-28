"""Estado compartido entre las paginas del shell (paciente activo, etc.)."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


@dataclass
class PatientInfo:
    nombre: str
    apellido: str = ""
    observaciones: str = ""

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()


class SharedAppState(QObject):
    """Datos que varias paginas necesitan leer/escuchar en comun."""

    patient_changed = Signal(object)  # PatientInfo | None

    def __init__(self):
        super().__init__()
        self.patient: PatientInfo | None = None
        # Solo tiene sentido cuando la modalidad activa es EEG: id del
        # usuario de SSVEP ya resuelto/creado en InicioPage (ver
        # inicio_page.py) -- EegPage lo recibe directo, nunca vuelve a
        # preguntar quien es.
        self.ssvep_user_id: int | None = None

    def set_patient(self, patient: PatientInfo) -> None:
        self.patient = patient
        self.patient_changed.emit(patient)
