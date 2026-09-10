"""Pantalla de Inicio: datos de paciente + eleccion de modalidad (EMG/EEG).

Basada en el mockup Main.dc.html del artefacto "Comando AAC".
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from interfaz.shell.app_state import PatientInfo, SharedAppState
from interfaz.shell.patient_store import load_patients, save_patient

# Los logos institucionales ya existen como recursos del modulo SSVEP; se
# reutilizan tal cual (solo lectura del archivo, sin importar codigo de
# ssvep) para no duplicar assets.
_LOGOS_DIR = Path(__file__).resolve().parent.parent.parent / "interfaz_ssvep" / "res" / "images"


def _logo_label(filename: str, height: int) -> QLabel:
    label = QLabel()
    pixmap = QPixmap(str(_LOGOS_DIR / filename))
    if not pixmap.isNull():
        label.setPixmap(pixmap.scaledToHeight(height, mode=Qt.TransformationMode.SmoothTransformation))
    return label


class ModalityCard(QPushButton):
    """Tarjeta seleccionable (EMG o EEG) con titulo y descripcion."""

    def __init__(self, titulo: str, descripcion: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModalityCard")
        self.setCheckable(True)
        self.setMinimumHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel(titulo)
        title.setObjectName("ModalityCardTitle")
        layout.addWidget(title)

        desc = QLabel(descripcion)
        desc.setObjectName("ModalityCardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addStretch(1)


class InicioPage(QWidget):
    """Pagina inicial: elegir/crear paciente y modalidad de control."""

    session_started = Signal(str)  # "emg" | "eeg"

    def __init__(self, state: SharedAppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._modalidad: str | None = None
        self._pacientes_guardados: list[dict] = []

        # Todo el contenido va dentro de un QScrollArea: en pantallas mas
        # bajas o con escalado de DPI alto, el formulario completo (logos +
        # toggle + tarjetas + boton) puede no entrar en alto sin esto, y las
        # tarjetas de modalidad terminaban recortadas/ilegibles.
        self_layout = QVBoxLayout(self)
        self_layout.setContentsMargins(0, 0, 0, 0)
        # OJO: no usar scroll.setStyleSheet(...)/scroll_content.setStyleSheet(...)
        # aca -- un stylesheet puesto directamente sobre un widget corta la
        # cascada del QSS de la app para sus descendientes (asi se rompieron
        # los bordes/fondos de las tarjetas y el segmented control la primera
        # vez). La transparencia del QScrollArea se resuelve en el QSS
        # global (ver QScrollArea > QWidget > QWidget en shell/style.py).
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self_layout.addWidget(scroll)

        scroll_content = QWidget()
        scroll.setWidget(scroll_content)

        outer = QVBoxLayout(scroll_content)
        outer.setContentsMargins(40, 40, 40, 28)

        container = QWidget()
        container.setObjectName("InicioContainer")
        container.setMaximumWidth(620)
        outer.addWidget(container, 0)
        outer.setAlignment(container, Qt.AlignmentFlag.AlignHCenter)

        content = QVBoxLayout(container)
        content.setSpacing(22)

        logos_row = QHBoxLayout()
        logos_row.setSpacing(28)
        logos_row.addStretch(1)
        logos_row.addWidget(_logo_label("logo_gir.png", 50))
        logos_row.addWidget(_logo_label("logo_ingenieria.svg", 50))
        logos_row.addStretch(1)
        content.addLayout(logos_row)

        subtitle = QLabel("Grupo de Investigación en Rehabilitación · Facultad de Ingeniería, UNER")
        subtitle.setObjectName("MutedCenteredLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        content.addWidget(subtitle)

        title = QLabel("Nueva sesión")
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        content.addWidget(title)

        desc = QLabel("Complete los datos del paciente para comenzar.")
        desc.setObjectName("MutedCenteredLabel")
        desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        content.addWidget(desc)

        # --- Toggle "Elegir guardado" / "Guardar nuevo" ---
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(0)
        self.btn_tab_guardado = QPushButton("Elegir paciente guardado")
        self.btn_tab_nuevo = QPushButton("Guardar paciente nuevo")
        for btn in (self.btn_tab_guardado, self.btn_tab_nuevo):
            btn.setObjectName("SegmentButton")
            btn.setCheckable(True)
            toggle_row.addWidget(btn)
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_group.addButton(self.btn_tab_guardado, 0)
        self._tab_group.addButton(self.btn_tab_nuevo, 1)
        self.btn_tab_nuevo.setChecked(True)
        self._tab_group.idClicked.connect(self._on_tab_changed)
        content.addLayout(toggle_row)

        # --- Paginas del toggle ---
        self.tab_stack = QStackedWidget()
        content.addWidget(self.tab_stack)

        guardado_widget = QWidget()
        guardado_layout = QVBoxLayout(guardado_widget)
        guardado_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_pacientes = QComboBox()
        self.combo_pacientes.currentIndexChanged.connect(self._refresh_start_button)
        guardado_layout.addWidget(self.combo_pacientes)
        self.tab_stack.addWidget(guardado_widget)

        nuevo_widget = QFrame()
        nuevo_widget.setObjectName("Card")
        form = QFormLayout(nuevo_widget)
        form.setSpacing(10)
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej. Juan")
        self.txt_nombre.textChanged.connect(self._refresh_start_button)
        form.addRow("Nombre", self.txt_nombre)
        self.txt_apellido = QLineEdit()
        self.txt_apellido.setPlaceholderText("Ej. Fernández")
        form.addRow("Apellido", self.txt_apellido)
        self.txt_observaciones = QPlainTextEdit()
        self.txt_observaciones.setFixedHeight(58)
        self.txt_observaciones.setPlaceholderText("Notas adicionales sobre la sesión… (opcional)")
        form.addRow("Observaciones", self.txt_observaciones)
        self.tab_stack.addWidget(nuevo_widget)

        # --- Modalidad ---
        modalidad_label = QLabel("MODALIDAD DE CONTROL")
        modalidad_label.setObjectName("SectionLabel")
        content.addWidget(modalidad_label)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.card_emg = ModalityCard("EMG", "Comando por contracción muscular (electromiografía de superficie).")
        self.card_eeg = ModalityCard("EEG", "Comando por estimulación visual (SSVEP).")
        self._modalidad_group = QButtonGroup(self)
        self._modalidad_group.setExclusive(True)
        self._modalidad_group.addButton(self.card_emg, 0)
        self._modalidad_group.addButton(self.card_eeg, 1)
        self._modalidad_group.idClicked.connect(self._on_modalidad_changed)
        cards_row.addWidget(self.card_emg)
        cards_row.addWidget(self.card_eeg)
        content.addLayout(cards_row)

        # --- Confirmar ---
        bottom_row = QHBoxLayout()
        self.lbl_hint = QLabel("Seleccioná una modalidad para continuar.")
        self.lbl_hint.setObjectName("MutedLabel")
        bottom_row.addWidget(self.lbl_hint)
        bottom_row.addStretch(1)
        self.btn_comenzar = QPushButton("Comenzar sesión")
        self.btn_comenzar.setObjectName("PrimaryButton")
        self.btn_comenzar.setEnabled(False)
        self.btn_comenzar.clicked.connect(self._on_comenzar_clicked)
        bottom_row.addWidget(self.btn_comenzar)
        content.addLayout(bottom_row)

        outer.addStretch(1)

        self._reload_pacientes_guardados()
        self._on_tab_changed(1)

    # ------------------------------------------------------------------
    def _on_tab_changed(self, tab_id: int) -> None:
        self.tab_stack.setCurrentIndex(tab_id)
        self._refresh_start_button()

    def _on_modalidad_changed(self, modality_id: int) -> None:
        self._modalidad = "emg" if modality_id == 0 else "eeg"
        self._refresh_start_button()

    def _reload_pacientes_guardados(self) -> None:
        self._pacientes_guardados = load_patients()
        self.combo_pacientes.blockSignals(True)
        self.combo_pacientes.clear()
        if not self._pacientes_guardados:
            self.combo_pacientes.addItem("No hay pacientes guardados todavía")
        else:
            for entry in self._pacientes_guardados:
                nombre_completo = f"{entry['nombre']} {entry.get('apellido', '')}".strip()
                self.combo_pacientes.addItem(nombre_completo)
        self.combo_pacientes.blockSignals(False)

    def _patient_seleccionado(self) -> PatientInfo | None:
        if self.btn_tab_guardado.isChecked():
            index = self.combo_pacientes.currentIndex()
            if index < 0 or index >= len(self._pacientes_guardados):
                return None
            entry = self._pacientes_guardados[index]
            return PatientInfo(
                nombre=entry["nombre"],
                apellido=entry.get("apellido", ""),
                observaciones=entry.get("observaciones", ""),
            )
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            return None
        return PatientInfo(
            nombre=nombre,
            apellido=self.txt_apellido.text().strip(),
            observaciones=self.txt_observaciones.toPlainText().strip(),
        )

    def _refresh_start_button(self) -> None:
        habilitado = self._patient_seleccionado() is not None and self._modalidad is not None
        self.btn_comenzar.setEnabled(habilitado)
        if self._modalidad is None:
            self.lbl_hint.setText("Seleccioná una modalidad para continuar.")
        elif self._patient_seleccionado() is None:
            self.lbl_hint.setText("Completá los datos del paciente para continuar.")
        else:
            self.lbl_hint.setText("Todo listo.")

    def _on_comenzar_clicked(self) -> None:
        patient = self._patient_seleccionado()
        if patient is None or self._modalidad is None:
            return

        if self.btn_tab_nuevo.isChecked():
            save_patient(patient.nombre, patient.apellido, patient.observaciones)
            self._reload_pacientes_guardados()

        self._state.set_patient(patient)
        self.session_started.emit(self._modalidad)

    def notificar_sesion_no_disponible(self) -> None:
        QMessageBox.information(
            self,
            "Sesión EMG",
            "Todavía no inició una sesión EMG. Complete los datos del paciente y elija"
            " la modalidad EMG en Inicio.",
        )
