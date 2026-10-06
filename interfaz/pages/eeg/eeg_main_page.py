"""Pantalla principal de EEG/SSVEP (mockup: Pantalla3_EEG.dc.html).

Arma la UI de cero con la estetica "Comando AAC" y la conecta a un
EegSession ya con un usuario cargado (ver interfaz/eeg/session.py). No usa
nada de la UI de interfaz_ssvep (UserUI/AppController) -- los unicos
widgets que se reusan de ssvep son PSDWidget (pyqtgraph puro) y los
popups del evaluador (BCIEvaluatorOperator/User/SequenceWidget), que ya
son ventanas flotantes propias y no rompen la estetica de esta pantalla.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interfaz.eeg.session import NULL_STIMULUS_INDEX
from interfaz.pages.eeg.eeg_live_widget import EegLiveWidget
from interfaz.pages.eeg.eeg_psd_widget import EegPsdWidget

# Orden fijo de estimulos -> (nombre, tecla). Coincide con
# Settings.__stimuli_config y KeyboardController.__actions en interfaz_ssvep
# (indice 0..5): no es configurable en esta pantalla.
# Ojo: el indice 1 manda VK_SPACE (Espacio), no Enter -- ver
# KeyboardController.__actions en interfaz_ssvep (no se toca ese archivo,
# solo se lee para que esta etiqueta sea fiel al mapeo real).
# El indice 0 ("Nulo", Escape en Settings) NO manda ninguna tecla: es el
# estimulo nulo, que solo inicia el periodo refractario (ver
# NULL_STIMULUS_INDEX en session.py). Siempre esta activo, en todos los modos.
STIMULUS_LABELS = ["Nulo", "Espacio", "Derecha", "Arriba", "Izquierda", "Abajo"]
# Forma de cada estimulo (Settings.__stimuli_config en interfaz_ssvep, mismo
# orden/indice), como glifos lisos (no emoji con color) para que combinen
# con la estetica del artefacto en vez de verse como stickers de Windows.
# Las flechas se dibujan como triangulos en el estimulador real
# (StimulusViewer.__arrow_mask) -- estos glifos se actualizaron igual, para
# que combinen.
STIMULUS_ICONS = ["■", "●", "▶", "▲", "◀", "▼"]
# Nombre por forma/direccion (no por la tecla que dispara, a diferencia de
# STIMULUS_LABELS) -- se usa para anunciar por voz el estimulo que hay que
# MIRAR durante la prueba de validacion (ver _on_iniciar_prueba).
STIMULUS_SPOKEN_NAMES = ["Cuadrado", "Círculo", "Derecha", "Arriba", "Izquierda", "Abajo"]

# Canales que se pueden sumar a los fijos (O1/Oz/O2): son los mismos
# electrodos que ofrece ElectrodeHeadWidget en vision. El total esta acotado
# por SETTINGS.max_channels (5 en vision).
EXTRA_CHANNELS = ["PO3", "PO4", "POz", "PO7", "PO8"]

# Modos de entrada preseteados (para uso con software de barrido/entrada
# externo, ej. AsTeRICS): cada uno define qué subconjunto de los 6
# estímulos queda activo (`UserPreferences.stimulus_on`). Las posiciones en
# pantalla de cada estímulo NO cambian entre modos -- StimulusViewer ya
# calcula la posición sobre el conjunto completo de 6 posibles, no sobre
# los activos (ver su propio docstring de load_stimulus_use), así que
# desactivar unos no reacomoda a los demás.
# El estímulo Nulo (índice 0) está activo en TODOS los modos. Además de
# servir para hacer entrar en período refractario sin mandar tecla, cumple
# lo que necesita el clasificador CCA: al menos 2 estímulos activos (si no,
# su fórmula de umbral da 0/0 -- ver frequency_calibrator.py), lo que en
# "Barrido" (que solo necesita Espacio) lo hace imprescindible.
# "frequency_order": orden en que la calibración reparte las frecuencias
# seleccionadas (de mayor a menor exactitud) entre los 6 estímulos -- la
# primera va al primer índice de la tupla, la segunda al siguiente, etc.
# Primero los estímulos activos del modo, por orden de importancia, con el
# Nulo en último lugar entre ellos (segundo en Barrido); los inactivos
# reciben el resto.
INPUT_MODES: dict[str, dict] = {
    "barrido": {  # Nulo + Espacio
        "label": "Barrido",
        "active_indices": (0, 1),
        "frequency_order": (1, 0, 2, 4, 3, 5),
    },
    "secuencial": {  # Nulo + Espacio, Derecha, Izquierda
        "label": "Secuencial",
        "active_indices": (0, 1, 2, 4),
        "frequency_order": (1, 2, 4, 0, 3, 5),
    },
    "direccional": {  # Nulo + Espacio + 4 flechas (los 6)
        "label": "Direccional",
        "active_indices": (0, 1, 2, 3, 4, 5),
        "frequency_order": (1, 2, 4, 3, 5, 0),
    },
}
# Modo por defecto para un paciente sin modo elegido todavía (ej. un
# `stimulus_on` que no calza con ningún modo).
DEFAULT_INPUT_MODE = "direccional"


def _stimulus_on_for_mode(mode_key: str) -> list[bool]:
    active = set(INPUT_MODES[mode_key]["active_indices"])
    return [i in active for i in range(len(STIMULUS_LABELS))]


def _mode_for_stimulus_on(stimulus_on) -> str | None:
    """Modo que corresponde a un `stimulus_on` guardado, o None si no calza
    con ninguno. También reconoce la variante anterior, guardada cuando el
    Nulo (Escape) todavía no estaba siempre activo (ej. [F,T,T,F,T,F] era
    "Secuencial"), para migrarla sin perder el modo que se había elegido."""
    activos = {i for i, on in enumerate(stimulus_on) if on}
    for key, info in INPUT_MODES.items():
        del_modo = set(info["active_indices"])
        if activos == del_modo or (activos | {NULL_STIMULUS_INDEX}) == del_modo:
            return key
    return None


def _frequency_assignment_for_mode(mode_key: str, selected_by_accuracy) -> dict[int, float]:
    """`{índice de estímulo: frecuencia}` según el orden de asignación del
    modo (ver INPUT_MODES). `selected_by_accuracy` viene ordenada de mayor a
    menor exactitud; si hay menos frecuencias que estímulos, solo se asignan
    las primeras (el resto de los estímulos conserva la que ya tenía)."""
    return dict(zip(INPUT_MODES[mode_key]["frequency_order"], selected_by_accuracy))


class EegMainPage(QWidget):
    """Pantalla principal: señal en vivo, canales, calibración, estimulación,
    validación y PSD/retroalimentación. Recibe un EegSession con un usuario
    ya cargado (`session.load_user(user_id)` ya hecho por quien la crea)."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session = session
        self._eval_widgets = None  # se crea al abrir "Iniciar prueba"
        self._head_dialog = None
        self._head_widget = None
        self._test_connections: list = []
        self._test_waiting_for_stimulator = False
        self._enable_control_before_test = False
        self._calibrator = None  # se crea al abrir "Iniciar calibración"
        self._calibration_viewer = None
        self._enable_control_before_calibracion = False
        self._calib_current_freq = 0.0
        self._calib_candidate_num = 0
        self._calib_n_candidates = 0
        self._calib_n_repeats = 0
        self._calib_trials_done = 0

        # Todo el contenido va dentro de un QScrollArea: con las 3 columnas
        # completas (canales+calibracion, estimulacion+validacion, señal+PSD)
        # la pantalla puede no entrar en alto en monitores mas chicos o con
        # escalado de DPI alto -- sin esto, las tarjetas de abajo quedaban
        # cortadas sin forma de verlas. Mismo criterio que InicioPage.
        self_layout = QVBoxLayout(self)
        self_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        outer.addLayout(self._build_header())
        outer.addWidget(self._build_signal_panel())

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(self._build_left_column(), 9)
        columns.addWidget(self._build_stim_validation_column(), 8)
        columns.addWidget(self._build_feedback_column(), 13)
        outer.addLayout(columns, 1)

        self._session.stimuli_ready.connect(self._on_stimuli_ready)
        self._session.filtered_data.connect(self._eeg_widget.append_samples)
        self._session.psd_data.connect(self._psd_widget.add_psd)
        self._session.error_occurred.connect(self._on_session_error)
        self._session.stream_started.connect(self._on_stream_started)

        self._load_from_preferences()

    # ------------------------------------------------------------------
    # Construccion de secciones
    # ------------------------------------------------------------------
    def _build_header(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(2)
        title = QLabel("Control por EEG")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        #subtitle = QLabel("Potenciales evocados de estado estacionario")
        #subtitle.setObjectName("MutedLabel")
        #layout.addWidget(subtitle)
        return layout

    def _build_signal_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        label = QLabel("SEÑAL DE ELECTROENCEFALOGRAFÍA")
        label.setObjectName("SectionLabel")
        header.addWidget(label)
        header.addStretch(1)
        # Aclara si lo que se ve es una grabación (paciente de prueba, ej.
        # "Guille") o el BioAmp real por puerto serie -- sin esto no hay
        # forma de distinguir a simple vista una señal simulada de una real.
        self._lbl_fuente = QLabel("")
        self._lbl_fuente.setObjectName("MutedLabel")
        header.addWidget(self._lbl_fuente)
        self._lbl_channels_count = QLabel("0 canales activos")
        self._lbl_channels_count.setObjectName("MutedLabel")
        header.addWidget(self._lbl_channels_count)
        layout.addLayout(header)

        self._eeg_widget = EegLiveWidget()
        # Fija (no solo minima): al agregar el QScrollArea el panel dejo de
        # estar apretado por el alto de la ventana y crecia sin limite,
        # cambiando el tamaño de la señal en pantalla respecto a como se
        # veia antes -- se fija en el mismo valor para que no vuelva a pasar.
        self._eeg_widget.setFixedHeight(160)
        layout.addWidget(self._eeg_widget)
        return card

    def _build_left_column(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_channels_card())
        layout.addWidget(self._build_calibration_card(), 1)
        return container

    def _build_channels_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Canales EEG")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_help = QPushButton("?")
        btn_help.setObjectName("HelpButton")
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help.setToolTip("Ver la ubicación de los electrodos")
        btn_help.clicked.connect(self._open_head_dialog)
        header.addWidget(btn_help)
        layout.addLayout(header)

        lbl_fixed = QLabel("Fijos (occipitales)")
        lbl_fixed.setObjectName("MutedLabel")
        layout.addWidget(lbl_fixed)
        self._fixed_badges_row = QHBoxLayout()
        self._fixed_badges_row.setSpacing(6)
        layout.addLayout(self._fixed_badges_row)

        self._lbl_extra = QLabel("Adicionales")
        self._lbl_extra.setObjectName("MutedLabel")
        layout.addWidget(self._lbl_extra)
        self._extra_chips_row = QHBoxLayout()
        self._extra_chips_row.setSpacing(6)
        self._channel_chips: dict[str, QPushButton] = {}
        for name in EXTRA_CHANNELS:
            chip = QPushButton(name)
            chip.setObjectName("ChannelChip")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked, n=name: self._on_channel_requested(n, checked))
            self._extra_chips_row.addWidget(chip)
            self._channel_chips[name] = chip
        self._extra_chips_row.addStretch(1)
        layout.addLayout(self._extra_chips_row)

        self._lbl_channels_footer = QLabel("")
        self._lbl_channels_footer.setObjectName("MutedLabel")
        layout.addWidget(self._lbl_channels_footer)
        layout.addStretch(1)
        return card

    def _build_calibration_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Calibración")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_help = QPushButton("?")
        btn_help.setObjectName("HelpButton")
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help.setToolTip("Qué es cada estímulo")
        btn_help.clicked.connect(self._mostrar_ayuda_calibracion)
        header.addWidget(btn_help)
        layout.addLayout(header)

        self._btn_calibrar = QPushButton("Iniciar calibración")
        self._btn_calibrar.setObjectName("PrimaryButton")
        self._btn_calibrar.clicked.connect(self._on_iniciar_calibracion)
        layout.addWidget(self._btn_calibrar)

        self._barra_calibracion = QProgressBar()
        self._barra_calibracion.setObjectName("CalibrationBar")
        self._barra_calibracion.setRange(0, 1)
        self._barra_calibracion.setTextVisible(False)
        self._barra_calibracion.setVisible(False)
        layout.addWidget(self._barra_calibracion)

        lbl_freqs = QLabel("Frecuencias asignadas (editable)")
        lbl_freqs.setObjectName("MutedLabel")
        layout.addWidget(lbl_freqs)

        self._freq_grid = QGridLayout()
        self._freq_grid.setSpacing(6)
        self._freq_spins: list[QDoubleSpinBox] = []
        self._freq_tiles: list[QFrame] = []
        for i, name in enumerate(STIMULUS_LABELS):
            tile = QFrame()
            tile.setObjectName("FreqTile")
            self._freq_tiles.append(tile)
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(8, 5, 8, 5)
            lbl_name = QLabel(f"{STIMULUS_ICONS[i]} {name}")
            lbl_name.setObjectName("FreqTileLabel")
            tile_layout.addWidget(lbl_name)
            tile_layout.addStretch(1)
            # Mientras no este la calibracion automatica (barrido), se puede
            # ajustar la frecuencia de cada estimulo a mano aca.
            spin_value = QDoubleSpinBox()
            spin_value.setObjectName("FreqTileValue")
            spin_value.setDecimals(1)
            spin_value.setRange(4.0, 30.0)
            spin_value.setSingleStep(0.5)
            spin_value.setSuffix(" Hz")
            spin_value.setFixedWidth(80)
            # editingFinished (no valueChanged): cambiar la frecuencia recarga
            # clasificador/filtros/estimulador -- no conviene hacerlo en cada
            # tick mientras se escribe o se mantiene apretada la flechita.
            spin_value.editingFinished.connect(lambda idx=i: self._on_frecuencia_changed(idx))
            tile_layout.addWidget(spin_value)
            self._freq_spins.append(spin_value)
            self._freq_grid.addWidget(tile, i // 2, i % 2)
        layout.addLayout(self._freq_grid)

        self._lbl_calibracion_footer = QLabel("Sin calibrar todavía.")
        self._lbl_calibracion_footer.setObjectName("MutedLabel")
        self._lbl_calibracion_footer.setWordWrap(True)
        layout.addWidget(self._lbl_calibracion_footer)
        layout.addStretch(1)
        return card

    def _build_stim_validation_column(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Estimulación")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        lbl_modo = QLabel("Método de entrada")
        lbl_modo.setObjectName("MutedLabel")
        layout.addWidget(lbl_modo)
        self._combo_modo_entrada = QComboBox()
        self._combo_modo_entrada.setToolTip(
            "Qué subconjunto de estímulos queda activo, para usar con software de barrido/entrada "
            "externo (ej. AsTeRICS). Las posiciones en pantalla no cambian entre modos."
        )
        for key, info in INPUT_MODES.items():
            self._combo_modo_entrada.addItem(info["label"], key)
        self._combo_modo_entrada.currentIndexChanged.connect(self._on_modo_entrada_changed)
        layout.addWidget(self._combo_modo_entrada)

        self._btn_estimulador = QPushButton("Abrir estimulador")
        self._btn_estimulador.setObjectName("PrimaryButton")
        self._btn_estimulador.clicked.connect(self._on_abrir_estimulador)
        layout.addWidget(self._btn_estimulador)

        self._chk_enviar_teclas = QCheckBox("Enviar teclas")
        self._chk_enviar_teclas.setToolTip(
            "Al detectarse un estímulo, envía la tecla asignada (ver ayuda de Calibración) "
            "a la aplicación activa. Solo actúa con el estimulador abierto. \"Nulo\" no envía "
            "ninguna tecla: solo inicia el tiempo refractario. Apagado por defecto para no "
            "interferir mientras se prueba."
        )
        self._chk_enviar_teclas.toggled.connect(self._session.set_enable_control)
        layout.addWidget(self._chk_enviar_teclas)

        lbl_refractario = QLabel("Tiempo refractario")
        lbl_refractario.setObjectName("MutedLabel")
        layout.addWidget(lbl_refractario)
        self._spin_refractario = QDoubleSpinBox()
        self._spin_refractario.setToolTip(
            "Tiempo mínimo entre una tecla enviada y la próxima, para que clasificaciones "
            "seguidas no disparen acciones en cadena mientras se sigue mirando el mismo estímulo."
        )
        self._spin_refractario.setRange(0.0, 30.0)
        self._spin_refractario.setSingleStep(0.5)
        self._spin_refractario.setDecimals(1)
        self._spin_refractario.setValue(5.0)
        self._spin_refractario.setSuffix(" s")
        self._spin_refractario.valueChanged.connect(self._session.set_refractory_period)
        layout.addWidget(self._spin_refractario)

        lbl_validacion = QLabel("VALIDACIÓN")
        lbl_validacion.setObjectName("SectionLabel")
        layout.addWidget(lbl_validacion)

        self._btn_prueba = QPushButton("Iniciar prueba")
        self._btn_prueba.setObjectName("SecondaryButton")
        self._btn_prueba.clicked.connect(self._on_iniciar_prueba)
        layout.addWidget(self._btn_prueba)

        lbl_umbral = QLabel("Umbral CCA")
        lbl_umbral.setObjectName("MutedLabel")
        layout.addWidget(lbl_umbral)
        umbral_row = QHBoxLayout()
        self._slider_umbral = QSlider(Qt.Orientation.Horizontal)
        self._slider_umbral.setRange(0, 100)
        self._slider_umbral.setValue(10)
        self._slider_umbral.valueChanged.connect(self._on_umbral_changed)
        umbral_row.addWidget(self._slider_umbral, 1)
        self._lbl_umbral_value = QLabel("0.10")
        umbral_row.addWidget(self._lbl_umbral_value)
        layout.addLayout(umbral_row)

        lbl_duracion = QLabel("Duración de la pulsación")
        lbl_duracion.setObjectName("MutedLabel")
        layout.addWidget(lbl_duracion)
        self._spin_duracion = QSpinBox()
        self._spin_duracion.setRange(100, 5000)
        self._spin_duracion.setSingleStep(50)
        self._spin_duracion.setValue(250)
        self._spin_duracion.setSuffix(" ms")
        self._spin_duracion.valueChanged.connect(self._on_duracion_changed)
        layout.addWidget(self._spin_duracion)

        self._lbl_evaluacion_footer = QLabel("Última evaluación: sin registrar")
        self._lbl_evaluacion_footer.setObjectName("MutedLabel")
        self._lbl_evaluacion_footer.setWordWrap(True)
        layout.addWidget(self._lbl_evaluacion_footer)
        layout.addStretch(1)
        return card

    def _build_feedback_column(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Señal y retroalimentación")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self._chk_psd = QCheckBox("Graficar PSD")
        self._chk_psd.setChecked(True)
        self._chk_psd.toggled.connect(self._on_psd_toggled)
        layout.addWidget(self._chk_psd)

        combos_row = QHBoxLayout()
        canal_col = QVBoxLayout()
        lbl_canal = QLabel("Canal")
        lbl_canal.setObjectName("MutedLabel")
        canal_col.addWidget(lbl_canal)
        self._combo_canal = QComboBox()
        self._combo_canal.currentIndexChanged.connect(self._on_canal_changed)
        canal_col.addWidget(self._combo_canal)
        combos_row.addLayout(canal_col)

        vis_col = QVBoxLayout()
        lbl_vis = QLabel("Visualización")
        lbl_vis.setObjectName("MutedLabel")
        vis_col.addWidget(lbl_vis)
        self._combo_modo = QComboBox()
        self._combo_modo.addItems(["Valor absoluto", "Decibeles [dB]", "Normalizado"])
        self._combo_modo.setCurrentIndex(1)
        self._combo_modo.currentIndexChanged.connect(self._on_psd_mode_changed)
        vis_col.addWidget(self._combo_modo)
        combos_row.addLayout(vis_col)
        layout.addLayout(combos_row)

        self._psd_widget = EegPsdWidget()
        self._psd_widget.setEnabled(True)
        self._psd_widget.set_psd_mode(1)
        # Panel corto y ancho, como en el artefacto (Pantalla3_EEG.dc.html
        # define el grafico de PSD con relacion de aspecto ~5.8:1, no
        # cuadrado) -- sin stretch, para que no se estire a ocupar todo el
        # alto disponible de la columna.
        self._psd_widget.setMinimumHeight(110)
        self._psd_widget.setMaximumHeight(160)
        layout.addWidget(self._psd_widget)

        self._chk_audio = QCheckBox("Retroalimentación auditiva")
        self._chk_audio.setToolTip("Anuncia por voz el estímulo detectado. Solo actúa con el estimulador abierto.")
        self._chk_audio.toggled.connect(self._session.set_audio_feedback)
        layout.addWidget(self._chk_audio)
        layout.addStretch(1)
        return card

    # ------------------------------------------------------------------
    # Carga de datos desde las preferencias del usuario
    # ------------------------------------------------------------------
    def _load_from_preferences(self) -> None:
        self._ensure_modo_entrada_default()
        prefs = self._session.current_preferences
        self._actualizar_fuente_label()

        # Se muestran SIEMPRE todos los canales configurados en prefs
        # (nunca se ocultan): si alguno no tiene datos reales para la
        # fuente actual (ej. una grabacion de prueba que no lo incluye),
        # se etiqueta como "sin señal" y su traza queda plana -- eso es
        # honesto (refleja que no hay info), ocultarlo no lo es.
        missing = self._session.missing_channel_names
        channel_names = list(prefs.channels.values())
        display_names = [f"{name} (sin señal)" if name in missing else name for name in channel_names]

        self._eeg_widget.set_channel_labels(display_names)
        self._lbl_channels_count.setText(f"{len(channel_names)} canales activos")

        locked = self._locked_channel_names()
        self._clear_layout(self._fixed_badges_row)
        for name, display_name in zip(channel_names, display_names):
            if name in locked:
                badge = QLabel(display_name)
                badge.setObjectName("BadgeFixed")
                self._fixed_badges_row.addWidget(badge)
        self._fixed_badges_row.addStretch(1)
        self._sync_channel_widgets()

        for i, stim in enumerate(prefs.stimulus):
            if i < len(self._freq_spins):
                self._freq_spins[i].blockSignals(True)
                self._freq_spins[i].setValue(stim.freq)
                self._freq_spins[i].blockSignals(False)

        modo_actual = _mode_for_stimulus_on(prefs.stimulus_on)
        self._combo_modo_entrada.blockSignals(True)
        if modo_actual is not None:
            self._combo_modo_entrada.setCurrentIndex(self._combo_modo_entrada.findData(modo_actual))
        self._combo_modo_entrada.blockSignals(False)
        self._sync_freq_tiles()

        self._combo_canal.blockSignals(True)
        self._combo_canal.clear()
        for idx, name in prefs.channels.items():
            self._combo_canal.addItem(name, idx)
        self._combo_canal.blockSignals(False)

        self._psd_widget.set_target_frequencies([stim.freq for stim in prefs.stimulus])

        self._slider_umbral.blockSignals(True)
        self._slider_umbral.setValue(10)
        self._slider_umbral.blockSignals(False)
        self._on_umbral_changed(10)

    # ------------------------------------------------------------------
    # Seleccion de canales (chips + cabeza de electrodos, como en vision)
    # ------------------------------------------------------------------
    @staticmethod
    def _locked_channel_names() -> list[str]:
        import builtins

        return list(builtins.SETTINGS.locked_channels.values())

    @staticmethod
    def _max_channels() -> int:
        import builtins

        return builtins.SETTINGS.max_channels

    def _current_extras(self) -> list[str]:
        locked = set(self._locked_channel_names())
        return [n for n in self._session.current_preferences.channels.values() if n not in locked]

    def _sync_channel_widgets(self) -> None:
        """Refleja los canales realmente activos en los chips, el contador y
        (si esta abierta) la cabeza de electrodos."""
        extras = set(self._current_extras())
        total = len(self._locked_channel_names()) + len(extras)
        full = total >= self._max_channels()
        test_running = self._eval_widgets is not None
        for name, chip in self._channel_chips.items():
            chip.blockSignals(True)
            chip.setChecked(name in extras)
            chip.blockSignals(False)
            chip.setEnabled(not test_running and (name in extras or not full))
        self._lbl_extra.setText(f"Adicionales (hasta {self._max_channels() - len(self._locked_channel_names())})")
        self._lbl_channels_footer.setText(f"{total} canales activos")
        if self._head_widget is not None:
            active = self._locked_channel_names() + self._current_extras()
            self._head_widget.set_active_channels(active)
            self._head_widget.set_channels_display({i + 1: n for i, n in enumerate(active)})

    def _on_channel_requested(self, name: str, active: bool) -> None:
        extras = self._current_extras()
        if active and name not in extras:
            if len(self._locked_channel_names()) + len(extras) >= self._max_channels():
                QMessageBox.information(
                    self, "Canales EEG", f"No se pueden seleccionar más de {self._max_channels()} canales."
                )
                self._sync_channel_widgets()
                return
            extras.append(name)
        elif not active and name in extras:
            extras.remove(name)
        self._apply_channel_selection(extras)

    def _apply_channel_selection(self, extras: list[str]) -> None:
        prefs = self._session.current_preferences
        new_channels = dict(enumerate(self._locked_channel_names() + extras))
        if new_channels == prefs.channels:
            self._sync_channel_widgets()
            return
        # Cambiar los canales cambia el ancho de la señal que viaja por todo
        # el pipeline (filtros/PSD/clasificador), asi que se corta el stream,
        # se guarda el perfil del usuario (queda para proximas sesiones, como
        # en vision) y se recarga todo antes de volver a arrancar.
        self._session.stop_streaming()
        prefs.channels = new_channels
        self._session.save_preferences(prefs)
        self._load_from_preferences()
        self._session.start_streaming()

    def _open_head_dialog(self) -> None:
        if self._head_dialog is not None:
            self._head_dialog.raise_()
            self._head_dialog.activateWindow()
            return

        from ssvep.app.electrode_head_widget import ElectrodeHeadWidget

        dialog = QDialog(self.window())
        dialog.setWindowTitle("Ubicación de electrodos")
        dialog.resize(520, 620)
        dlg_layout = QVBoxLayout(dialog)
        head = ElectrodeHeadWidget()
        head.set_locked_channels(self._locked_channel_names())
        dlg_layout.addWidget(head)
        head.channel_toggled.connect(self._on_channel_requested)
        dialog.finished.connect(self._on_head_dialog_closed)
        self._head_dialog = dialog
        self._head_widget = head
        self._sync_channel_widgets()
        dialog.show()

    def _on_head_dialog_closed(self) -> None:
        self._head_dialog = None
        self._head_widget = None

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _actualizar_fuente_label(self, texto: str | None = None, es_error: bool = False) -> None:
        """Sin `texto`: muestra si la señal es una grabación de prueba o el
        BioAmp real (ver EegSession.is_simulated_source). Con `texto`: lo
        usa tal cual (para el aviso de error de conexión, ver
        _on_session_error) -- se vuelve a limpiar solo al reconectar
        (_on_stream_started)."""
        if texto is None:
            if self._session.is_simulated_source():
                texto = "Fuente: grabación de prueba"
            else:
                texto = "Fuente: BioAmp (puerto serie)"
        self._lbl_fuente.setText(texto)
        self._lbl_fuente.setObjectName("WarningLabel" if es_error else "MutedLabel")
        self._lbl_fuente.style().unpolish(self._lbl_fuente)
        self._lbl_fuente.style().polish(self._lbl_fuente)

    def _on_session_error(self, mensaje: str) -> None:
        self._actualizar_fuente_label(f"⚠ {mensaje}", es_error=True)

    def _on_stream_started(self, iniciado: bool) -> None:
        if iniciado:
            self._actualizar_fuente_label()

    def _on_umbral_changed(self, value: int) -> None:
        umbral = value / 100.0
        self._lbl_umbral_value.setText(f"{umbral:.2f}")
        self._session.set_threshold(umbral)

    def _on_duracion_changed(self, value: int) -> None:
        self._session.keyboard.set_press_duration(value)

    def _on_canal_changed(self, index: int) -> None:
        if index < 0:
            return
        channel_index = self._combo_canal.itemData(index)
        if channel_index is not None:
            self._session.set_psd_channel_index(channel_index)

    def _on_psd_mode_changed(self, index: int) -> None:
        self._psd_widget.set_psd_mode(index)

    def _on_psd_toggled(self, checked: bool) -> None:
        self._psd_widget.setEnabled(checked)

    def _on_iniciar_calibracion(self) -> None:
        if self._calibrator is not None and self._calibrator.is_running():
            self._cancelar_calibracion()
            return

        if self._eval_widgets is not None:
            QMessageBox.warning(self, "Calibración", "Terminá la prueba de validación antes de calibrar.")
            return

        respuesta = QMessageBox.question(
            self,
            "Calibración",
            "La calibración recorre 9 frecuencias candidatas (8 a 16 Hz) con 3 repeticiones "
            "cada una y dura varios minutos. Al terminar reasigna las frecuencias según el "
            "método de entrada elegido: las de mayor exactitud van primero a Espacio y a los "
            "demás estímulos del método, y Nulo recibe la última de ellas (la segunda en Barrido).\n\n"
            "Mientras corre no se puede usar el control por teclado, abrir el estimulador "
            "manual ni iniciar una prueba de validación.\n\n¿Iniciar calibración ahora?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        import builtins

        from ssvep.app.frequency_calibrator import FrequencyCalibrator
        from ssvep.app.stimulus_viewer_calibration import StimulusViewerCalibration

        # Solo puede haber un visor de estimulos abierto a la vez -- si el
        # estimulador manual estaba corriendo, se cierra antes de abrir el
        # propio de la calibracion.
        self._session.stimulus_viewer.stop_stim()
        self._actualizar_boton_estimulador()

        prefs = self._session.current_preferences
        self._calibration_viewer = StimulusViewerCalibration()
        self._calibrator = FrequencyCalibrator(
            stimulus_viewer=self._calibration_viewer,
            channels=prefs.channels,
            time_window=prefs.time_window,
            sample_rate=builtins.SAMPLE_RATE,
            harmonics=builtins.SETTINGS.f_bands,
        )

        self._enable_control_before_calibracion = self._session.enable_control
        self._session.set_enable_control(False)
        self._session.use_classifier(self._calibrator.classifier)
        self._session.classification_result.connect(self._calibrator.receive_classification)

        self._calib_current_freq = 0.0
        self._calib_candidate_num = 0
        self._calib_n_candidates = 0
        self._calib_n_repeats = 0
        self._calib_trials_done = 0

        self._calibrator.candidate_started.connect(self._on_calibracion_candidata)
        self._calibrator.trial_started.connect(self._on_calibracion_trial)
        self._calibrator.resting.connect(self._on_calibracion_descanso)
        self._calibrator.time_elapsed.connect(self._on_calibracion_tiempo)
        self._calibrator.trial_finished.connect(self._on_calibracion_trial_finalizado)
        self._calibrator.calibration_finished.connect(self._on_calibracion_finalizada)
        self._calibrator.calibration_failed.connect(self._on_calibracion_fallida)

        self._set_calibracion_controles_habilitados(False)
        self._btn_calibrar.setText("Cancelar calibración")
        self._barra_calibracion.setRange(0, 1)
        self._barra_calibracion.setValue(0)
        self._barra_calibracion.setVisible(True)
        self._lbl_calibracion_footer.setText("Preparando calibración…")

        self._calibrator.start()

    def _cancelar_calibracion(self) -> None:
        # FrequencyCalibrator.cancel() corta sin emitir calibration_finished
        # (ver docstring), asi que la limpieza de UI/sesion se hace aca
        # directamente en vez de esperar una señal que no va a llegar.
        if self._calibrator is not None:
            self._calibrator.cancel()
        self._lbl_calibracion_footer.setText("Calibración cancelada.")
        self._finalizar_calibracion()

    def _finalizar_calibracion(self) -> None:
        """Limpieza comun a cancelar y a terminar la calibracion: restaura el
        clasificador principal, el control por teclado y los controles que
        se habian deshabilitado. No toca prefs ni el footer (cada llamador
        decide ese mensaje)."""
        if self._calibrator is not None:
            try:
                self._session.classification_result.disconnect(self._calibrator.receive_classification)
            except (RuntimeError, TypeError):
                pass
        self._session.restore_main_classifier()
        self._session.set_enable_control(self._enable_control_before_calibracion)

        if self._calibration_viewer is not None and self._calibration_viewer.is_running():
            self._calibration_viewer.stop_stim()
        self._calibration_viewer = None
        self._calibrator = None

        self._btn_calibrar.setText("Iniciar calibración")
        self._barra_calibracion.setVisible(False)
        self._set_calibracion_controles_habilitados(True)

    def _ensure_modo_entrada_default(self) -> None:
        """Deja `stimulus_on` exactamente como lo define el modo guardado:
        si corresponde a un modo guardado con el formato anterior (sin el
        Nulo activo), se agrega el Nulo y se conserva el modo; si no calza
        con ninguno de los 3 modos, se aplica DEFAULT_INPUT_MODE
        ("Direccional") como punto de partida."""
        prefs = self._session.current_preferences
        modo = _mode_for_stimulus_on(prefs.stimulus_on) or DEFAULT_INPUT_MODE
        esperado = _stimulus_on_for_mode(modo)
        if list(prefs.stimulus_on) == esperado:
            return
        prefs.stimulus_on = esperado
        self._session.save_preferences(prefs)

    def _sync_freq_tiles(self, extra_lock: bool = False) -> None:
        """Atenúa visualmente (opacidad, no deshabilita) la casilla de
        frecuencia de los estímulos que no están activos en el modo de
        entrada actual -- se puede seguir editando igual la frecuencia de
        un estímulo inactivo (ej. "Arriba" en modo Secuencial), para poder
        asignarle de antemano una buena frecuencia por si se lo activa más
        adelante. Solo se deshabilita la EDICIÓN (las 6 por igual, sin
        importar el modo) durante calibración (`extra_lock=True`) o
        mientras corre la prueba de validación."""
        prefs = self._session.current_preferences
        activos = prefs.stimulus_on
        probando = self._eval_widgets is not None
        for i, tile in enumerate(self._freq_tiles):
            effect = tile.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(tile)
                tile.setGraphicsEffect(effect)
            effect.setOpacity(1.0 if activos[i] else 0.45)
            tile.setEnabled(not extra_lock and not probando)

    def _on_modo_entrada_changed(self, index: int) -> None:
        if index < 0:
            return
        if self._eval_widgets is not None or (self._calibrator is not None and self._calibrator.is_running()):
            return
        modo_key = self._combo_modo_entrada.itemData(index)
        if modo_key is None:
            return
        prefs = self._session.current_preferences
        nuevo_stimulus_on = _stimulus_on_for_mode(modo_key)
        if nuevo_stimulus_on == prefs.stimulus_on:
            return
        self._session.stop_streaming()
        prefs.stimulus_on = nuevo_stimulus_on
        self._session.save_preferences(prefs)
        self._load_from_preferences()
        self._session.start_streaming()

    def _set_calibracion_controles_habilitados(self, habilitado: bool) -> None:
        """Mientras corre la calibración, se bloquean los controles que
        competirían por el clasificador/estimulador (prueba de validación,
        estimulador manual, envío de teclas, método de entrada, canales y
        frecuencias asignadas). "Enviar teclas" en particular: durante la
        calibración las clasificaciones corresponden a candidata/ancla, no a
        los estímulos reales -- dejarlo prendido mandaría teclas sueltas sin
        sentido."""
        self._btn_prueba.setEnabled(habilitado)
        self._btn_estimulador.setEnabled(habilitado)
        self._chk_enviar_teclas.setEnabled(habilitado)
        self._combo_modo_entrada.setEnabled(habilitado)
        self._sync_freq_tiles(extra_lock=not habilitado)
        if habilitado:
            # Reaplica las reglas normales (limite de canales, prueba activa)
            # en vez de simplemente habilitar todos los chips.
            self._sync_channel_widgets()
        else:
            for chip in self._channel_chips.values():
                chip.setEnabled(False)

    def _on_calibracion_candidata(self, freq: float, candidate_num: int, n_candidates: int) -> None:
        self._calib_current_freq = freq
        self._calib_candidate_num = candidate_num
        self._calib_n_candidates = n_candidates

    def _on_calibracion_trial(self, repeat_num: int, n_repeats: int) -> None:
        self._calib_n_repeats = n_repeats
        total = max(self._calib_n_candidates * n_repeats, 1)
        self._barra_calibracion.setRange(0, total)
        self._actualizar_footer_calibracion(f"intento {repeat_num}/{n_repeats}: preparando…")

    def _on_calibracion_descanso(self, segundos_restantes: int) -> None:
        self._actualizar_footer_calibracion(f"descanso, arranca en {segundos_restantes}s")

    def _on_calibracion_tiempo(self, segundos: int) -> None:
        self._actualizar_footer_calibracion(f"midiendo… {segundos}s")

    def _actualizar_footer_calibracion(self, sufijo: str) -> None:
        freq_text = f"{self._calib_current_freq:g}".replace(".", ",")
        self._lbl_calibracion_footer.setText(
            f"Candidata {self._calib_candidate_num}/{self._calib_n_candidates} "
            f"({freq_text} Hz) — {sufijo}"
        )

    def _on_calibracion_trial_finalizado(self, freq: float, hits: int, n: int) -> None:
        self._calib_trials_done += 1
        self._barra_calibracion.setValue(self._calib_trials_done)

    def _on_calibracion_finalizada(self, result: dict) -> None:
        # _finalizar_calibracion() pone self._calibrator en None -- se guarda
        # la referencia antes para poder generar el reporte con ella.
        calibrator = self._calibrator
        self._finalizar_calibracion()

        # `result["selected"]` viene ordenada de mayor a menor exactitud: se
        # reparte según el método de entrada actual (ver INPUT_MODES), no
        # en orden creciente de frecuencia como antes.
        prefs = self._session.current_preferences
        modo = _mode_for_stimulus_on(prefs.stimulus_on) or DEFAULT_INPUT_MODE
        asignacion = _frequency_assignment_for_mode(modo, result["selected"])
        for stim_index, freq in asignacion.items():
            prefs.stimulus[stim_index].freq = freq
        self._session.save_preferences(prefs)
        self._load_from_preferences()

        try:
            self._session.calibration_repository().save(self._session.current_user_id, result)
        except Exception:
            pass

        report_path = None
        try:
            import os

            os.makedirs(self._session.reports_dir(), exist_ok=True)
            user_name = self._session.user_manager.get_user(self._session.current_user_id)["name"]
            report_path = os.path.join(self._session.reports_dir(), f"calibracion-{user_name}.pdf")
            calibrator.generate_report(report_path, result)
        except Exception:
            report_path = None

        accs = result["accuracies"]
        accs_text = ", ".join(f"{f:g}Hz: {accs[f]:.0f}%" for f in sorted(accs))
        asignadas_text = "\n".join(
            f"{STIMULUS_ICONS[i]} {STIMULUS_LABELS[i]}: {f:g} Hz ({accs[f]:.0f}%)" for i, f in asignacion.items()
        )
        self._lbl_calibracion_footer.setText(f"Calibración lista para el método {INPUT_MODES[modo]['label']}.")

        mensaje = (
            f"Calibración terminada.\n\nExactitud por candidata:\n{accs_text}\n\n"
            f"Frecuencias asignadas (método {INPUT_MODES[modo]['label']}):\n{asignadas_text}"
        )
        sin_asignar = [STIMULUS_LABELS[i] for i in INPUT_MODES[modo]["frequency_order"] if i not in asignacion]
        if sin_asignar:
            mensaje += (
                "\n\nSin reasignar (no hubo suficientes frecuencias sin colisión armónica, "
                f"conservan la anterior): {', '.join(sin_asignar)}"
            )
        if report_path:
            mensaje += f"\n\nReporte: {report_path}"
        QMessageBox.information(self, "Calibración", mensaje)

    def _on_calibracion_fallida(self, motivo: str) -> None:
        # El propio FrequencyCalibrator/StimulusViewerCalibration ya se
        # detuvieron solos al emitir esta señal -- acá solo queda restaurar
        # la UI/sesion (igual que al cancelar) y avisar del error.
        self._finalizar_calibracion()
        self._lbl_calibracion_footer.setText("La calibración falló. Ver detalle.")
        QMessageBox.critical(self, "Calibración", f"La calibración no pudo continuar:\n\n{motivo}")

    def _on_frecuencia_changed(self, index: int) -> None:
        prefs = self._session.current_preferences
        nueva_freq = round(self._freq_spins[index].value(), 1)
        if prefs.stimulus[index].freq == nueva_freq:
            return
        self._session.stop_streaming()
        prefs.stimulus[index].freq = nueva_freq
        self._session.save_preferences(prefs)
        self._load_from_preferences()
        self._session.start_streaming()

    def _mostrar_ayuda_calibracion(self) -> None:
        leyenda = "\n".join(
            f"{STIMULUS_ICONS[i]}  {name}" + ("  (no envía ninguna tecla: solo inicia el tiempo refractario)" if i == 0 else "")
            for i, name in enumerate(STIMULUS_LABELS)
        )
        QMessageBox.information(
            self,
            "Calibración",
            "Cada estímulo parpadea en la pantalla del estimulador a la frecuencia "
            "que se le asigne acá. Al detectarse, se envía la tecla correspondiente:\n\n"
            f"{leyenda}\n\n"
            "\"Iniciar calibración\" recorre un barrido de frecuencias candidatas y las "
            "reasigna según el método de entrada elegido: las de mayor exactitud van "
            "primero a Espacio y a los demás estímulos del método, y Nulo recibe la "
            "última de ellas (la segunda en Barrido). También se puede ajustar la frecuencia de "
            "cada estímulo a mano, sin calibrar, en \"Frecuencias asignadas\".",
        )

    def _on_stimuli_ready(self, hwnd: int) -> None:
        # La ventana del estimulador termino de abrirse: si hay una prueba
        # esperando, arranca la prueba; si no, solo parpadea (boton
        # "Abrir estimulador"). Mismo criterio que AppController.__on_stimuli_ready.
        if self._test_waiting_for_stimulator:
            self._test_waiting_for_stimulator = False
            self._begin_test()
        else:
            self._session.stimulus_viewer.start_flicker()

    def _on_abrir_estimulador(self) -> None:
        viewer = self._session.stimulus_viewer
        if viewer.is_running():
            viewer.stop_stim()
        else:
            viewer.start_stim()
        self._actualizar_boton_estimulador()

    def _actualizar_boton_estimulador(self) -> None:
        corriendo = self._session.stimulus_viewer.is_running()
        self._btn_estimulador.setText("Cerrar estimulador" if corriendo else "Abrir estimulador")

    def _begin_test(self) -> None:
        if self._eval_widgets is None:
            return
        eval_op = self._eval_widgets[0]
        eval_op.enable_buttons()
        self._session.stimulus_viewer.start_flicker()

    # ------------------------------------------------------------------
    # Validacion (prueba de desempeño) -- reusa BCIEvaluator + sus widgets
    # ------------------------------------------------------------------
    def _on_iniciar_prueba(self) -> None:
        if self._eval_widgets is not None:
            return

        from ssvep.app.bci_evaluator_widgets import BCIEvaluatorOperator, BCIEvaluatorUser, SequenceWidget

        sequence = self._session.evaluation_sequence()
        self._session.evaluator.set_sequence(sequence)

        eval_op = BCIEvaluatorOperator()
        eval_user = BCIEvaluatorUser()
        seq_op = SequenceWidget()
        seq_user = SequenceWidget()
        eval_op.load_sequence_widget(seq_op)
        seq_user.hide_detected_sequence(False)
        eval_user.load_sequence_widget(seq_user)
        seq_op.add_sequence(sequence)
        seq_user.add_sequence(sequence)
        self._eval_widgets = (eval_op, eval_user, seq_op, seq_user)

        ev = self._session.evaluator
        self._test_connections = [
            (ev.index_hit, self._make_hit_handler(eval_op, seq_op)),
            (ev.index_miss, self._make_miss_handler(eval_op, seq_op)),
            (ev.index_sequence, seq_op.highlight_expected_index),
            (ev.index_sequence, seq_user.highlight_expected_index),
            (ev.index_sequence, self._make_anuncio_handler(sequence)),
            (ev.finished, self._on_prueba_finalizada),
            (ev.send_time, eval_op.set_time),
            (eval_op.stop_test_request, self._on_stop_test_request),
            (eval_op.start_test_request, ev.start),
            (eval_user.window_closed, self._on_stop_test_request),
        ]
        for signal, slot in self._test_connections:
            signal.connect(slot)

        self._enable_control_before_test = self._session.enable_control
        self._session.set_enable_control(False)
        self._session.set_add_test_data(True)
        self._btn_prueba.setEnabled(False)
        self._chk_enviar_teclas.setEnabled(False)
        self._combo_modo_entrada.setEnabled(False)
        self._btn_estimulador.setEnabled(False)
        self._sync_freq_tiles()

        eval_op.show()
        eval_user.show()

        # El estimulador se abre recien aca, al correr la prueba (no antes):
        # los botones del operador se habilitan y empieza el parpadeo cuando
        # su ventana termina de abrirse (ver _on_stimuli_ready/_begin_test).
        viewer = self._session.stimulus_viewer
        if viewer.is_running():
            self._begin_test()
        else:
            self._test_waiting_for_stimulator = True
            viewer.start_stim()
        self._actualizar_boton_estimulador()

    def _make_hit_handler(self, eval_op, seq_op):
        def _handler(index: int) -> None:
            eval_op.register_hit()
            seq_op.add_hit(index)

        return _handler

    def _make_anuncio_handler(self, sequence: list):
        # ev.index_sequence manda la POSICION dentro de la secuencia (no el
        # tipo de estimulo -- a diferencia de index_hit/index_miss, que sí
        # mandan el tipo), asi que hay que resolverla contra `sequence` para
        # saber que forma anunciar.
        def _handler(position: int) -> None:
            if position < 0 or position >= len(sequence):
                return
            stim_index = sequence[position]
            if 0 <= stim_index < len(STIMULUS_SPOKEN_NAMES):
                self._session.announce_text(STIMULUS_SPOKEN_NAMES[stim_index])

        return _handler

    def _make_miss_handler(self, eval_op, seq_op):
        def _handler(index: int) -> None:
            eval_op.register_miss()
            seq_op.add_miss(index)

        return _handler

    def _on_stop_test_request(self) -> None:
        # Boton "Detener" del operador, o cierre de la ventana de usuario:
        # dispara evaluator.stop(), que a su vez emite `finished` --
        # _on_prueba_finalizada es quien hace la limpieza real (ver abajo).
        # No limpiar aca directamente: evaluator.stop() ya lo va a disparar.
        self._session.evaluator.stop()

    def _on_prueba_finalizada(self) -> None:
        # Conectado a evaluator.finished, que se dispara tanto al completar
        # la secuencia como al llamar stop() manualmente -- por eso esto
        # solo hace limpieza de UI/estado, nunca vuelve a llamar stop()
        # (si no, stop() volveria a emitir finished -> recursion infinita).
        accuracy = self._session.evaluator.accuracy()
        self._lbl_evaluacion_footer.setText(f"Última evaluación: {accuracy:.0f}% de exactitud")
        self._cerrar_ventanas_prueba()

    def _cerrar_ventanas_prueba(self) -> None:
        """Solo cierra ventanas/restaura estado -- NUNCA llama
        evaluator.stop() (ver _on_stop_test_request/_on_prueba_finalizada)."""
        if self._eval_widgets is None:
            return
        eval_op, eval_user, _seq_op, _seq_user = self._eval_widgets
        for signal, slot in self._test_connections:
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        self._test_connections = []
        self._test_waiting_for_stimulator = False
        self._session.set_enable_control(self._enable_control_before_test)
        self._session.set_add_test_data(False)
        eval_op.stop()
        eval_user.stop()
        self._eval_widgets = None
        self._btn_prueba.setEnabled(True)
        self._chk_enviar_teclas.setEnabled(True)
        self._combo_modo_entrada.setEnabled(True)
        self._btn_estimulador.setEnabled(True)
        self._sync_freq_tiles()
        # Igual que el AppController original: al terminar la prueba se cierra el estimulador.
        self._session.stimulus_viewer.stop_stim()
        self._actualizar_boton_estimulador()

    # ------------------------------------------------------------------
    def liberar_recursos(self) -> None:
        self._cerrar_ventanas_prueba()
        if self._calibrator is not None and self._calibrator.is_running():
            self._cancelar_calibracion()
