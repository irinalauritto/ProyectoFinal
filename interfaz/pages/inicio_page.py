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

from interfaz.shell import asterics_config as asterics_cfg
from interfaz.shell.app_state import PatientInfo, SharedAppState
from interfaz.shell.asterics_setup import AstericsSetup, is_supported
from interfaz.shell.patient_store import (
    find_by_name,
    full_name,
    get_patient,
    link_ssvep_user,
    load_patients,
    save_patient,
    set_asterics_configured,
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

        # Preparación de AsTeRICS (usuario y tablero del paciente). Cada
        # paciente tiene su perfil de navegador; el de un paciente sin ficha
        # es temporal (ver asterics_config.py).
        self._setup = AstericsSetup(self)
        self._setup.finished.connect(self._on_setup_finished)
        self._setup_token: str | None = None  # paciente cuya preparación terminó en esta ejecución
        self._setup_pending_token: str | None = None  # paciente cuya preparación está en curso
        self._setup_key: str | None = None  # clave del perfil usado en la preparación
        self._setup_patient_id: str | None = None
        self._temp_key: str | None = None  # perfil temporal del paciente nuevo
        self._temp_token: str | None = None

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
        self.txt_apellido.textChanged.connect(self._refresh_start_button)
        form.addRow("Apellido", self.txt_apellido)
        self.txt_observaciones = QPlainTextEdit()
        self.txt_observaciones.setFixedHeight(58)
        self.txt_observaciones.setPlaceholderText("Notas adicionales sobre la sesión… (opcional)")
        form.addRow("Observaciones", self.txt_observaciones)
        self.chk_guardar = QCheckBox("Guardar este paciente para usarlo después")
        self.chk_guardar.setChecked(True)
        form.addRow(self.chk_guardar)
        self.tab_stack.addWidget(nuevo_widget)

        # --- AsTeRICS (primero, antes de elegir la modalidad) ---
        asterics_row = QHBoxLayout()
        asterics_row.setSpacing(14)
        self.btn_asterics = QPushButton("Configurar AsTeRICS AAC")
        self.btn_asterics.setObjectName("SecondaryButton")
        self.btn_asterics.setToolTip(
            "Abre AsTeRICS para iniciar sesión, cargar el usuario del paciente y seleccionar su "
            "tablero. Al terminar, presione «Continuar con la interfaz» (botón rojo dentro de AsTeRICS)."
        )
        self.btn_asterics.clicked.connect(self._on_configurar_asterics)
        asterics_row.addWidget(self.btn_asterics)
        self.lbl_asterics = QLabel("")
        self.lbl_asterics.setObjectName("MutedLabel")
        self.lbl_asterics.setWordWrap(True)
        asterics_row.addWidget(self.lbl_asterics, 1)
        content.addLayout(asterics_row)

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
                "Configure AsTeRICS para continuar.",
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

    # ------------------------------------------------------------------
    # Preparación de AsTeRICS (obligatoria antes de elegir la modalidad)
    # ------------------------------------------------------------------
    @staticmethod
    def _token(patient: PatientInfo) -> str:
        """Identidad del paciente para saber si ya se preparó AsTeRICS: su
        ficha, o su nombre si todavía no tiene."""
        return patient.id or "nombre:" + " ".join(patient.nombre_completo.lower().split())

    def _asterics_listo(self) -> bool:
        patient = self._patient_seleccionado()
        if patient is None:
            return False
        if self._setup_token == self._token(patient):
            return True
        if patient.id:
            entry = get_patient(patient.id)
            if entry and entry.get("asterics_configurado") and asterics_cfg.profile_exists(patient.id):
                return True
        return False

    def _profile_key_for(self, patient: PatientInfo) -> str:
        """Perfil de navegador del paciente: su ficha o, si todavía no tiene,
        uno temporal (estable mientras no cambie el nombre)."""
        if patient.id:
            return patient.id
        token = self._token(patient)
        if self._temp_key is None or self._temp_token != token:
            self._temp_key, self._temp_token = asterics_cfg.new_temp_key(), token
        return self._temp_key

    def _clear_modalidad(self) -> None:
        grupo = self._modalidad_group
        grupo.setExclusive(False)
        for boton in grupo.buttons():
            boton.setChecked(False)
        grupo.setExclusive(True)
        self._modalidad = None

    def _on_configurar_asterics(self) -> None:
        patient = self._patient_seleccionado()
        if patient is None or self._setup.is_running():
            return
        key = self._profile_key_for(patient)
        asterics_cfg.set_active_profile(key)
        token = self._token(patient)

        if not is_supported():
            # Sin Chromium no hay forma de acompañar la preparación: se la
            # deja a mano en el navegador y se habilita el resto del flujo.
            QMessageBox.information(
                self,
                "AsTeRICS",
                "La preparación guiada de AsTeRICS requiere Chrome, Edge, Brave o Vivaldi como navegador "
                "predeterminado.\n\nPuede continuar: prepare AsTeRICS a mano desde su navegador.",
            )
            self._setup_key = key
            self._setup_token = token
            self._refresh_start_button()
            return

        self._setup_pending_token, self._setup_key, self._setup_patient_id = token, key, patient.id
        # AsTeRICS se abre en el monitor del terapeuta: el de esta aplicación.
        if not self._setup.start(anchor_hwnd=int(self.window().winId())):
            QMessageBox.warning(self, "AsTeRICS", "No se pudo abrir AsTeRICS en el navegador predeterminado.")
            return
        self._refresh_start_button()

    def _on_setup_finished(self, ok: bool, message: str) -> None:
        if ok:
            self._setup_token = self._setup_pending_token
            if self._setup_patient_id:
                set_asterics_configured(self._setup_patient_id, True)
        else:
            QMessageBox.warning(self, "AsTeRICS", message)
        self._refresh_start_button()
        ventana = self.window()
        ventana.raise_()
        ventana.activateWindow()

    def _refresh_start_button(self) -> None:
        patient = self._patient_seleccionado()
        listo = self._asterics_listo()
        en_curso = self._setup.is_running()

        self.btn_asterics.setEnabled(patient is not None and not en_curso)
        self.btn_asterics.setText("Reconfigurar AsTeRICS AAC" if listo else "Configurar AsTeRICS AAC")
        if patient is None:
            self.lbl_asterics.setText("Complete los datos del paciente para configurar AsTeRICS.")
        elif en_curso:
            self.lbl_asterics.setText(
                "AsTeRICS está abierta: inicie sesión (o use «sin registrarse»), cargue y seleccione el "
                "tablero del paciente y presione «Continuar con la interfaz» (botón rojo, abajo a la derecha)."
            )
        elif listo:
            self.lbl_asterics.setText("✔ AsTeRICS configurada para este paciente.")
        else:
            self.lbl_asterics.setText(
                "Primero configure AsTeRICS: cargue el usuario y el tablero del paciente."
            )

        # El orden es obligatorio: sin AsTeRICS preparada no se elige modalidad.
        for card in (self.card_emg, self.card_eeg):
            card.setEnabled(listo)
        if not listo and self._modalidad is not None:
            self._clear_modalidad()

        habilitado = patient is not None and listo and self._modalidad is not None
        self.btn_comenzar.setEnabled(habilitado)
        if patient is None:
            self.lbl_hint.setText("Complete los datos del paciente para continuar.")
        elif not listo:
            self.lbl_hint.setText("Configure AsTeRICS para continuar.")
        elif self._modalidad is None:
            self.lbl_hint.setText("Seleccione una modalidad para continuar.")
        else:
            self.lbl_hint.setText("Todo listo.")

    def cancelar_asterics(self) -> None:
        """Al cerrar la aplicación: abandona una preparación en curso."""
        self._setup.cancel()

    def _on_comenzar_clicked(self) -> None:
        patient = self._patient_seleccionado()
        if patient is None or self._modalidad is None:
            return

        token_previo = self._token(patient)

        # Un paciente nuevo se guarda en la lista si se lo pidió. En EEG
        # siempre: su usuario de SSVEP se persiste en la base de todos modos
        # (lo exige su modelo de datos) y la ficha tiene que acompañarlo.
        if self.btn_tab_nuevo.isChecked() and (self.chk_guardar.isChecked() or self._modalidad == "eeg"):
            entry = save_patient(patient.nombre, patient.apellido, patient.observaciones)
            patient.id = entry["id"]

        # Perfil de AsTeRICS de la sesión. Si el paciente era nuevo y recién se
        # guardó, el perfil temporal que preparó pasa a ser el de su ficha.
        if self._setup_token == token_previo and self._setup_key:
            clave = self._setup_key
            if patient.id and asterics_cfg.is_temp(clave):
                if asterics_cfg.promote_profile(clave, patient.id):
                    set_asterics_configured(patient.id, True)
                    clave = patient.id
                self._setup_key = clave
            self._setup_token = self._token(patient)
        else:
            clave = self._profile_key_for(patient)
        asterics_cfg.set_active_profile(clave)

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
