"""
Pantalla de Inicio
Aquí se guardan los datos del pacientes y se selecciona la modalidad de control (EMG o EEG). 
Se reutiliza el mismo formulario para crear un paciente nuevo o elegir uno guardado, 
y se valida que haya datos completos antes de habilitar el boton "Comenzar sesión".

Autora: Irina Lauritto

"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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
from interfaz.shell.patient_store import (
    find_by_name,
    full_name,
    get_patient,
    link_ssvep_user,
    load_patients,
    save_patient,
    sync_ssvep_users,
)

# Los logos institucionales ya existen como recursos del modulo SSVEP proveniente de vision
_LOGOS_DIR = Path(__file__).resolve().parent.parent.parent / "interfaz_ssvep" / "res" / "images"


def _logo_label(filename: str, height: int) -> QLabel:
    label = QLabel()
    pixmap = QPixmap(str(_LOGOS_DIR / filename))
    if not pixmap.isNull():
        label.setPixmap(pixmap.scaledToHeight(height, mode=Qt.TransformationMode.SmoothTransformation))
    return label


class FixedHeightStack(QStackedWidget):
    """ Widget que mantiene una altura fija basada en el contenido más alto de sus hijos. """

    def sizeHint(self):
        """ Devuelve un tamaño sugerido que tiene la misma anchura que el tamaño sugerido normal, pero con la altura del hijo más alto. """
        hint = super().sizeHint()
        max_h = max((self.widget(i).sizeHint().height() for i in range(self.count())), default=hint.height())
        return hint.expandedTo(hint.__class__(hint.width(), max_h))

    def minimumSizeHint(self):
        """ Devuelve un tamaño mínimo sugerido que tiene la misma anchura que el tamaño mínimo sugerido normal, pero con la altura del hijo más alto. """
        hint = super().minimumSizeHint()
        max_h = max(
            (self.widget(i).minimumSizeHint().height() for i in range(self.count())), default=hint.height()
        )
        return hint.expandedTo(hint.__class__(hint.width(), max_h))


class ModalityCard(QPushButton):
    """Tarjeta seleccionable EMG o EEG con título y descripción."""

    def __init__(self, titulo: str, descripcion: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModalityCard")
        self.setCheckable(True)
        self.setMinimumHeight(120)

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
    """Página inicial: elegir o crear paciente, seleccionar modalidad de control."""

    session_started = Signal(str)  # "emg" | "eeg"

    def __init__(self, state: SharedAppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._modalidad: str | None = None
        self._pacientes_guardados: list[dict] = []
        self._ssvep_users: list[tuple[int, str]] = []
        self._ssvep_user_manager = None
        self._ssvep_prefs_manager = None

        self_layout = QVBoxLayout(self)
        self_layout.setContentsMargins(0, 0, 0, 0)
 
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

        subtitle = QLabel("Grupo de Ingeniería en Rehabilitación · Facultad de Ingeniería, UNER")
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
        self.tab_stack = FixedHeightStack()
        content.addWidget(self.tab_stack)

        guardado_widget = QWidget()
        guardado_layout = QVBoxLayout(guardado_widget)
        guardado_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_pacientes = QComboBox()
      
        self.combo_pacientes.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_pacientes.setMinimumContentsLength(1)
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
        self.chk_guardar = QCheckBox("Guardar este paciente para usarlo después")
        self.chk_guardar.setChecked(True)
        form.addRow(self.chk_guardar)
        self.tab_stack.addWidget(nuevo_widget)

        # --- Modalidad ---
        modalidad_label = QLabel("MODALIDAD DE CONTROL")
        modalidad_label.setObjectName("SectionLabel")
        content.addWidget(modalidad_label)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.card_emg = ModalityCard("EMG", "Comando por electromiografía de superficie.")
        self.card_eeg = ModalityCard("EEG", "Comando por potenciales evocados de estado estacionario (SSVEP).")
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
        self.lbl_hint = QLabel("Seleccione una modalidad para continuar.")
        self.lbl_hint.setObjectName("MutedLabel")
    
        _hint_font_metrics = self.lbl_hint.fontMetrics()
        _hint_min_width = max(
            _hint_font_metrics.horizontalAdvance(texto)
            for texto in (
                "Seleccione una modalidad para continuar.",
                "Complete los datos del paciente para continuar.",
                "Todo listo.",
            )
        )
        self.lbl_hint.setMinimumWidth(_hint_min_width)
        bottom_row.addWidget(self.lbl_hint)
        bottom_row.addStretch(1)
        self.btn_comenzar = QPushButton("Comenzar sesión")
        self.btn_comenzar.setObjectName("PrimaryButton")
        self.btn_comenzar.setEnabled(False)
        self.btn_comenzar.clicked.connect(self._on_comenzar_clicked)
        bottom_row.addWidget(self.btn_comenzar)
        content.addLayout(bottom_row)

        outer.addStretch(1)

        self._sincronizar_con_ssvep()
        self._reload_pacientes_guardados()
        self._on_tab_changed(1)

    # ------------------------------------------------------------------
    # Desde acá lo que está escrito es la lógica de negocio de la página. Lo previo es solo la construcción de la UI.
    def _on_tab_changed(self, tab_id: int) -> None:
        """ Cambia entre la pestaña de paciente guardado y la de paciente nuevo. """
        self.tab_stack.setCurrentIndex(tab_id)
        self._refresh_start_button()

    def _on_modalidad_changed(self, modality_id: int) -> None:
        self._modalidad = "emg" if modality_id == 0 else "eeg"
        # La lista de pacientes es la misma para las dos modalidades (ver
        # patient_store): elegir una no la recarga ni cambia la selección.
        self._refresh_start_button()

    def _ensure_ssvep_connection(self) -> None:
        """Conecta a la base de SSVEP para poder listar/crear sus usuarios."""
        if self._ssvep_user_manager is not None:
            return
        import sys

        ssvep_dir = Path(__file__).resolve().parent.parent.parent / "interfaz_ssvep"
        ssvep_dir_str = str(ssvep_dir)
        if ssvep_dir_str not in sys.path:
            sys.path.insert(0, ssvep_dir_str)

        from ssvep.app.config import crear_engine, init_database
        from ssvep.app.managers import PreferencesManager, UserManager
        from ssvep.app.repositories import PreferencesRepositorySQLAlchemy, UserRepositorySQLAlchemy

        data_dir = ssvep_dir / "vision_data"
        init_database(str(data_dir))
        engine_factory = crear_engine()
        db_session = engine_factory()
        self._ssvep_user_manager = UserManager(UserRepositorySQLAlchemy(db_session)) #en esta línea y en la siguiente se crean los managers de SSVEP para poder acceder a la base de datos de usuarios y preferencias
        self._ssvep_prefs_manager = PreferencesManager(PreferencesRepositorySQLAlchemy(db_session))

    def _sincronizar_con_ssvep(self) -> None:
        """Une la lista con los usuarios de la base SSVEP: cada usuario queda
        vinculado a una ficha y los que no tenían ficha se agregan. Si no hay
        base todavía (nunca se usó EEG), no se conecta a nada."""
        db = Path(__file__).resolve().parent.parent.parent / "interfaz_ssvep" / "vision_data" / "data" / "user_database.db"
        if not db.exists():
            return
        try:
            self._ensure_ssvep_connection()
            sync_ssvep_users(self._ssvep_user_manager.get_all_users().items())
        except Exception:
            # Sin la base de SSVEP la lista de EMG sigue funcionando.
            return

    def _reload_pacientes_guardados(self) -> None:
        """Una sola lista para las dos modalidades (ver patient_store)."""
        # Se conserva el paciente elegido (si sigue en la lista) al recargar.
        previo = self._pacientes_guardados[self.combo_pacientes.currentIndex()]["id"] if (
            0 <= self.combo_pacientes.currentIndex() < len(self._pacientes_guardados)
        ) else None
        self._pacientes_guardados = sorted(load_patients(), key=lambda e: full_name(e).lower())
        self.combo_pacientes.blockSignals(True)
        self.combo_pacientes.clear()
        if not self._pacientes_guardados:
            self.combo_pacientes.addItem("No hay pacientes guardados todavía")
        else:
            for entry in self._pacientes_guardados:
                self.combo_pacientes.addItem(full_name(entry))
            for i, entry in enumerate(self._pacientes_guardados):
                if entry["id"] == previo:
                    self.combo_pacientes.setCurrentIndex(i)
                    break
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
                id=entry["id"],
            )
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            return None
        existente = find_by_name(nombre, self.txt_apellido.text().strip())
        return PatientInfo(
            nombre=nombre,
            apellido=self.txt_apellido.text().strip(),
            observaciones=self.txt_observaciones.toPlainText().strip(),
            id=existente["id"] if existente else None,
        )

    def _resolve_ssvep_user_id(self, patient: PatientInfo) -> int | None:
        """Usuario SSVEP del paciente: el que ya tiene vinculado en su ficha,
        o uno con su mismo nombre (sin distinguir mayúsculas), o uno nuevo con
        las preferencias por defecto. Deja el vínculo guardado en la ficha."""
        self._ensure_ssvep_connection()
        usuarios = dict(self._ssvep_user_manager.get_all_users().items())

        entry = get_patient(patient.id)
        if entry is not None and entry.get("ssvep_user_id") in usuarios:
            return entry["ssvep_user_id"]

        objetivo = patient.nombre_completo.strip().lower()
        for uid, name in usuarios.items():
            if name.strip().lower() == objetivo:
                link_ssvep_user(patient.id, uid)
                return uid

        import builtins

        new_user = self._ssvep_user_manager.register_new_user(patient.nombre_completo)
        self._ssvep_prefs_manager.save_or_update_preferences(
            new_user.id, builtins.SETTINGS.default_user_preferences
        )
        link_ssvep_user(patient.id, new_user.id)
        return new_user.id

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

        # Un paciente nuevo se guarda en la lista si se lo pidió. En EEG
        # siempre: su usuario de SSVEP se persiste en la base de todos modos
        # (lo exige su modelo de datos) y la ficha tiene que acompañarlo.
        if self.btn_tab_nuevo.isChecked() and (self.chk_guardar.isChecked() or self._modalidad == "eeg"):
            entry = save_patient(patient.nombre, patient.apellido, patient.observaciones)
            patient.id = entry["id"]

        if self._modalidad == "eeg":
            user_id = self._resolve_ssvep_user_id(patient)
            if user_id is None:
                return
            self._state.ssvep_user_id = user_id

        self._state.set_patient(patient)
        self.session_started.emit(self._modalidad)
        self._reload_pacientes_guardados()

    def notificar_sesion_no_disponible(self, modalidad: str = "EMG") -> None:
        QMessageBox.information(
            self,
            f"Sesión {modalidad}",
            f"Todavía no inició una sesión {modalidad}. Complete los datos del paciente y elija"
            f" la modalidad {modalidad} en Inicio.",
        )
