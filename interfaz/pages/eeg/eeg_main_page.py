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
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interfaz.pages.eeg.eeg_live_widget import EegLiveWidget
from interfaz.pages.eeg.eeg_psd_widget import EegPsdWidget

# Orden fijo de estimulos -> (nombre, tecla). Coincide con
# Settings.__stimuli_config y KeyboardController.__actions en interfaz_ssvep
# (indice 0..5): no es configurable en esta pantalla.
STIMULUS_LABELS = ["Escape", "Enter", "Derecha", "Arriba", "Izquierda", "Abajo"]

# Canales que se pueden sumar a los fijos (O1/Oz/O2): son los mismos
# electrodos que ofrece ElectrodeHeadWidget en vision. El total esta acotado
# por SETTINGS.max_channels (5 en vision).
EXTRA_CHANNELS = ["PO3", "PO4", "POz", "PO7", "PO8"]


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

        outer = QVBoxLayout(self)
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
        self._lbl_channels_count = QLabel("0 canales activos")
        self._lbl_channels_count.setObjectName("MutedLabel")
        header.addWidget(self._lbl_channels_count)
        layout.addLayout(header)

        self._eeg_widget = EegLiveWidget()
        self._eeg_widget.setMinimumHeight(160)
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

        title = QLabel("Calibración")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self._btn_calibrar = QPushButton("Iniciar calibración")
        self._btn_calibrar.setObjectName("PrimaryButton")
        self._btn_calibrar.clicked.connect(self._on_iniciar_calibracion)
        layout.addWidget(self._btn_calibrar)

        lbl_freqs = QLabel("Frecuencias asignadas")
        lbl_freqs.setObjectName("MutedLabel")
        layout.addWidget(lbl_freqs)

        self._freq_grid = QGridLayout()
        self._freq_grid.setSpacing(6)
        self._freq_tiles: list[QLabel] = []
        for i, name in enumerate(STIMULUS_LABELS):
            tile = QFrame()
            tile.setObjectName("FreqTile")
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(8, 5, 8, 5)
            lbl_name = QLabel(name)
            lbl_name.setObjectName("FreqTileLabel")
            tile_layout.addWidget(lbl_name)
            tile_layout.addStretch(1)
            lbl_value = QLabel("—")
            lbl_value.setObjectName("FreqTileValue")
            tile_layout.addWidget(lbl_value)
            self._freq_tiles.append(lbl_value)
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

        self._btn_estimulador = QPushButton("Abrir estimulador")
        self._btn_estimulador.setObjectName("PrimaryButton")
        self._btn_estimulador.clicked.connect(self._on_abrir_estimulador)
        layout.addWidget(self._btn_estimulador)

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
        self._chk_audio.toggled.connect(self._session.set_audio_feedback)
        layout.addWidget(self._chk_audio)
        layout.addStretch(1)
        return card

    # ------------------------------------------------------------------
    # Carga de datos desde las preferencias del usuario
    # ------------------------------------------------------------------
    def _load_from_preferences(self) -> None:
        prefs = self._session.current_preferences

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
            if i < len(self._freq_tiles):
                freq_text = f"{stim.freq:g}".replace(".", ",")
                self._freq_tiles[i].setText(f"{freq_text} Hz")

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
        # La logica del barrido de frecuencias se agrega en la etapa
        # siguiente (interfaz/eeg/calibration.py); este boton ya existe
        # segun el mockup pero todavia no dispara nada real.
        QMessageBox.information(
            self,
            "Calibración",
            "La calibración de frecuencias se implementa en la próxima etapa.",
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
            viewer.start_flicker()
        else:
            viewer.start_stim()

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

    def _make_hit_handler(self, eval_op, seq_op):
        def _handler(index: int) -> None:
            eval_op.register_hit()
            seq_op.add_hit(index)

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
        # Igual que el AppController original: al terminar la prueba se cierra el estimulador.
        self._session.stimulus_viewer.stop_stim()

    # ------------------------------------------------------------------
    def liberar_recursos(self) -> None:
        self._cerrar_ventanas_prueba()
