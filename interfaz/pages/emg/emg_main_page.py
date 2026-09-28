"""Pantalla principal de EMG (mockup: Pantalla2_EMG.dc.html).

Arma la UI de cero con la estetica "Comando AAC" y la conecta a un
EmgEngine (ver interfaz_emg/emg/interfazEmg.py -- la logica de lectura
serie/filtrado/calibracion/deteccion se separo de VentanaEmg en un
refactor propio; esta pantalla no reusa VentanaEmg ni su UI, solo
`EmgEngine` y las funciones/constantes sueltas de ese modulo).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interfaz.pages.emg.emg_live_widget import EmgLiveWidget


class EmgMainPage(QWidget):
    """Pantalla principal: señal en vivo, calibración, prueba de validación
    guiada y parámetros. Recibe un `EmgEngine` ya arrancado."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine

        import emg.interfazEmg as emgmod

        self._emgmod = emgmod

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        outer.addLayout(self._build_header())
        outer.addWidget(self._build_signal_panel())

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(self._build_calibracion_card(), 1)
        columns.addWidget(self._build_prueba_card(), 1)
        columns.addWidget(self._build_parametros_card(), 1)
        outer.addLayout(columns, 1)

        self._connect_engine()
        self._sync_parametros_iniciales()

    # ------------------------------------------------------------------
    # Construccion de secciones
    # ------------------------------------------------------------------
    def _build_header(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(2)
        title = QLabel("Control por EMG")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        #subtitle = QLabel("Switch de accionamiento por contracción muscular")
        #subtitle.setObjectName("MutedLabel")
        #layout.addWidget(subtitle)
        return layout

    def _build_signal_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        label = QLabel("SEÑAL DE ELECTROMIOGRAFÍA")
        label.setObjectName("SectionLabel")
        layout.addWidget(label)

        inner = QFrame()
        inner.setObjectName("SignalInner")
        inner.setStyleSheet("#SignalInner { background: #f8f9fa; border: 1px solid #dfe3e8; border-radius: 6px; }")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(10, 10, 10, 6)
        inner_layout.setSpacing(2)

        self._signal_widget = EmgLiveWidget(buffer_size=self._emgmod.BUFFER_SIZE)
        self._signal_widget.setMinimumHeight(180)
        inner_layout.addWidget(self._signal_widget)

        ventana_s = self._emgmod.BUFFER_SIZE / self._emgmod.FS_HZ
        lbl_escala = QLabel(f"Escala: ventana de {ventana_s:.0f} s")
        lbl_escala.setObjectName("MutedLabel")
        lbl_escala.setStyleSheet("font-size: 10px;")
        inner_layout.addWidget(lbl_escala)

        layout.addWidget(inner)
        return card

    def _card_header(self, layout: QVBoxLayout, titulo: str, ayuda_callback) -> None:
        row = QHBoxLayout()
        title = QLabel(titulo)
        title.setObjectName("SectionTitle")
        title.setWordWrap(True)
        row.addWidget(title, 1)
        btn_help = QPushButton("?")
        btn_help.setObjectName("HelpButton")
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help.clicked.connect(ayuda_callback)
        row.addWidget(btn_help, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row)

    def _build_calibracion_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        dur = self._emgmod.CALIBRACION_DURACION_S
        self._card_header(layout, f"Calibración ({dur} s en reposo)", self._mostrar_ayuda_calibracion)

        self._btn_calibrar = QPushButton("Iniciar calibración")
        self._btn_calibrar.setObjectName("PrimaryButton")
        self._btn_calibrar.clicked.connect(self._on_iniciar_calibracion)
        layout.addWidget(self._btn_calibrar)

        barra_row = QVBoxLayout()
        barra_row.setSpacing(4)
        self._barra_calibracion = QProgressBar()
        self._barra_calibracion.setObjectName("CalibrationBar")
        self._barra_calibracion.setRange(0, dur)
        self._barra_calibracion.setTextVisible(False)
        barra_row.addWidget(self._barra_calibracion)
        self._lbl_progreso = QLabel(f"0 / {dur} s")
        self._lbl_progreso.setObjectName("MutedLabel")
        self._lbl_progreso.setAlignment(Qt.AlignmentFlag.AlignRight)
        barra_row.addWidget(self._lbl_progreso)
        layout.addLayout(barra_row)

        self._lbl_calibracion = QLabel("Sin calibrar")
        self._lbl_calibracion.setWordWrap(True)
        layout.addWidget(self._lbl_calibracion)

        layout.addStretch(1)
        self._lbl_umbral = QLabel("Umbral de disparo: —")
        self._lbl_umbral.setObjectName("MutedLabel")
        self._lbl_umbral.setWordWrap(True)
        layout.addWidget(self._lbl_umbral)
        return card

    def _build_prueba_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._card_header(layout, "Prueba de validación (3 contracciones)", self._mostrar_ayuda_prueba)

        botones_row = QHBoxLayout()
        botones_row.setSpacing(8)
        self._btn_prueba = QPushButton("Iniciar prueba")
        self._btn_prueba.setObjectName("SecondaryButton")
        self._btn_prueba.setEnabled(False)
        self._btn_prueba.clicked.connect(self._on_iniciar_prueba)
        botones_row.addWidget(self._btn_prueba)
        self._btn_omitir = QPushButton("Omitir prueba")
        self._btn_omitir.setObjectName("GhostButton")
        self._btn_omitir.setEnabled(False)
        self._btn_omitir.clicked.connect(self._on_omitir_prueba)
        botones_row.addWidget(self._btn_omitir)
        layout.addLayout(botones_row)

        self._btn_siguiente_intento = QPushButton("Registrar intento y continuar")
        self._btn_siguiente_intento.setObjectName("PrimaryButton")
        self._btn_siguiente_intento.setEnabled(False)
        self._btn_siguiente_intento.clicked.connect(self._engine.registrar_intento_actual)
        layout.addWidget(self._btn_siguiente_intento)

        self._lbl_prueba = QLabel("Requiere calibración previa")
        self._lbl_prueba.setWordWrap(True)
        layout.addWidget(self._lbl_prueba)
        layout.addStretch(1)
        return card

    def _build_parametros_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Parámetros")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        m = self._emgmod

        lbl_sens = QLabel("Sensibilidad")
        lbl_sens.setObjectName("MutedLabel")
        layout.addWidget(lbl_sens)
        sens_row = QHBoxLayout()
        # Slider entero (x10) para representar el rango [K_MIN, K_MAX] con
        # un paso de 0.1, igual resolucion que el QDoubleSpinBox original.
        self._slider_sens = QSlider(Qt.Orientation.Horizontal)
        self._slider_sens.setRange(int(m.K_MIN * 10), int(m.K_MAX * 10))
        self._slider_sens.valueChanged.connect(self._on_sensibilidad_changed)
        sens_row.addWidget(self._slider_sens, 1)
        self._lbl_sens_valor = QLabel("—")
        sens_row.addWidget(self._lbl_sens_valor)
        layout.addLayout(sens_row)

        lbl_refr = QLabel("Refractario")
        lbl_refr.setObjectName("MutedLabel")
        layout.addWidget(lbl_refr)
        self._spin_refractario = QSpinBox()
        self._spin_refractario.setRange(m.REFRACTARIO_MIN_MS, m.REFRACTARIO_MAX_MS)
        self._spin_refractario.setSingleStep(50)
        self._spin_refractario.setValue(m.REFRACTARIO_DEFAULT_MS)
        self._spin_refractario.setSuffix(" ms")
        self._spin_refractario.valueChanged.connect(self._on_refractario_changed)
        layout.addWidget(self._spin_refractario)

        lbl_tecla = QLabel("Tecla enviada")
        lbl_tecla.setObjectName("MutedLabel")
        layout.addWidget(lbl_tecla)
        self._combo_tecla = QComboBox()
        self._combo_tecla.addItems(list(m.TECLAS_DISPONIBLES.keys()))
        self._combo_tecla.currentIndexChanged.connect(self._on_tecla_changed)
        layout.addWidget(self._combo_tecla)

        lbl_duracion = QLabel("Duración de la pulsación")
        lbl_duracion.setObjectName("MutedLabel")
        layout.addWidget(lbl_duracion)
        self._spin_duracion = QSpinBox()
        self._spin_duracion.setRange(m.DURACION_TECLA_MIN_MS, m.DURACION_TECLA_MAX_MS)
        self._spin_duracion.setSingleStep(50)
        self._spin_duracion.setValue(m.DURACION_TECLA_DEFAULT_MS)
        self._spin_duracion.setSuffix(" ms")
        self._spin_duracion.valueChanged.connect(self._on_duracion_changed)
        layout.addWidget(self._spin_duracion)

        layout.addStretch(1)
        self._lbl_aviso = QLabel("")
        self._lbl_aviso.setObjectName("WarningLabel")
        self._lbl_aviso.setWordWrap(True)
        self._lbl_aviso.setVisible(False)
        layout.addWidget(self._lbl_aviso)
        return card

    # ------------------------------------------------------------------
    def _sync_parametros_iniciales(self) -> None:
        # Mismo valor por defecto que VentanaEmg: K_DEFAULT espejado.
        self._slider_sens.blockSignals(True)
        self._slider_sens.setValue(round(self._emgmod._espejar_escala_k(self._emgmod.K_DEFAULT) * 10))
        self._slider_sens.blockSignals(False)
        self._lbl_sens_valor.setText(f"{self._slider_sens.value() / 10:.1f}")
        self._engine.set_tecla(self._combo_tecla.currentText())
        self._engine.set_duracion_tecla_ms(self._spin_duracion.value())

    def _connect_engine(self) -> None:
        e = self._engine
        e.samples_ready.connect(self._signal_widget.append_samples)
        e.calibration_progress.connect(self._on_calibration_progress)
        e.calibration_finished.connect(self._on_calibration_finished)
        e.calibration_failed.connect(self._on_calibration_failed)
        e.validation_attempt_started.connect(self._on_validation_attempt_started)
        e.validation_attempt_progress.connect(self._on_validation_attempt_progress)
        e.validation_finished.connect(self._on_validation_finished)
        e.parametros_modificados.connect(self._mostrar_aviso_repetir_prueba)

    # ------------------------------------------------------------------
    # Ayuda
    # ------------------------------------------------------------------
    def _mostrar_ayuda_calibracion(self) -> None:
        dur = self._emgmod.CALIBRACION_DURACION_S
        QMessageBox.information(
            self,
            "Ayuda — Calibración",
            f"La calibración mide durante {dur} segundos el nivel de la señal cuando el paciente "
            "está relajado, y lo usa como referencia de reposo. A partir de esa referencia, calcula "
            "automáticamente el umbral: el nivel que la señal tiene que superar para considerarse "
            "una contracción.\n\n"
            "La Sensibilidad regula qué tan intensa debe ser la contracción para disparar un evento. "
            "Se puede modificar en cualquier momento sin repetir la calibración; tras cada cambio "
            "conviene repetir la prueba de validación.",
        )

    def _mostrar_ayuda_prueba(self) -> None:
        QMessageBox.information(
            self,
            "Ayuda — Prueba de validación",
            "Confirma que el umbral calibrado es adecuado.\n\n"
            "Se piden 3 intentos: en cada uno, el paciente contrae y relaja el músculo una vez, y "
            "quien opera presiona \"Registrar intento y continuar\" cuando termina.\n\n"
            "Lo esperable es un evento por intento. Si no se detecta ninguno, o se detecta más de "
            "uno, conviene ajustar la sensibilidad y/o el refractario en \"Parámetros\" y repetir.",
        )

    def _mostrar_aviso_repetir_prueba(self) -> None:
        self._lbl_aviso.setText("⚠ Parámetros modificados: se recomienda repetir la prueba de validación.")
        self._lbl_aviso.setVisible(True)

    def _ocultar_aviso_repetir_prueba(self) -> None:
        self._lbl_aviso.setVisible(False)

    def _avisar_si_no_calibrado(self) -> None:
        if not self._engine.esta_calibrado() and not self._engine.calibrando:
            QMessageBox.warning(
                self,
                "Calibración requerida",
                "Antes de usar el control por EMG es necesario calibrar el umbral de activación. "
                "Presione \"Iniciar calibración\" para comenzar.",
            )

    def avisar_calibracion_requerida(self) -> None:
        """Llamado desde `EmgPage` al (re)confirmar paciente -- misma
        advertencia que `VentanaEmg.establecer_paciente` mostraba siempre."""
        self._avisar_si_no_calibrado()

    # ------------------------------------------------------------------
    # Calibracion
    # ------------------------------------------------------------------
    def _on_iniciar_calibracion(self) -> None:
        self._engine.iniciar_calibracion()
        self._btn_calibrar.setEnabled(False)
        self._barra_calibracion.setValue(0)
        self._lbl_calibracion.setText("Calibrando… mantenga el músculo relajado.")

    def _on_calibration_progress(self, transcurrido: float, total: float) -> None:
        self._barra_calibracion.setValue(min(int(transcurrido), int(total)))
        self._lbl_progreso.setText(f"{transcurrido:.0f} / {total:.0f} s")
        restante = max(0.0, total - transcurrido)
        self._lbl_calibracion.setText(f"Calibrando… manténgase relajado. Quedan {restante:.0f} s")

    def _on_calibration_finished(self, umbral: float, media: float, sd: float) -> None:
        dur = self._emgmod.CALIBRACION_DURACION_S
        self._btn_calibrar.setEnabled(True)
        self._barra_calibracion.setValue(dur)
        self._lbl_progreso.setText(f"{dur} / {dur} s")
        self._lbl_calibracion.setText("Calibración lista.")
        self._signal_widget.set_umbral(umbral)
        sensibilidad = self._emgmod._espejar_escala_k(self._engine.k)
        self._lbl_umbral.setText(f"Umbral de disparo: {umbral:.1f}\n(media={media:.1f}, SD={sd:.1f}, sensibilidad={sensibilidad:.1f})")
        self._btn_prueba.setEnabled(True)
        self._btn_omitir.setEnabled(True)
        self._lbl_prueba.setText("Calibración lista. Puede iniciar la prueba de validación.")

    def _on_calibration_failed(self, motivo: str) -> None:
        self._btn_calibrar.setEnabled(True)
        self._lbl_calibracion.setText("Calibración fallida — reintentar")
        QMessageBox.critical(self, "Calibración fallida", motivo)

    # ------------------------------------------------------------------
    # Parametros
    # ------------------------------------------------------------------
    def _on_sensibilidad_changed(self, valor_x10: int) -> None:
        sensibilidad = valor_x10 / 10.0
        self._lbl_sens_valor.setText(f"{sensibilidad:.1f}")
        self._engine.set_k(sensibilidad)
        if self._engine.media_reposo is None:
            self._avisar_si_no_calibrado()
            return
        self._signal_widget.set_umbral(self._engine.umbral)
        self._lbl_umbral.setText(
            f"Umbral de disparo: {self._engine.umbral:.1f}\n"
            f"(media={self._engine.media_reposo:.1f}, SD={self._engine.sd_reposo:.1f}, sensibilidad={sensibilidad:.1f})"
        )

    def _on_refractario_changed(self, valor: int) -> None:
        self._engine.set_refractario_ms(valor)
        if self._engine.umbral is None:
            self._avisar_si_no_calibrado()

    def _on_tecla_changed(self, _index: int) -> None:
        self._engine.set_tecla(self._combo_tecla.currentText())
        self._avisar_si_no_calibrado()

    def _on_duracion_changed(self, valor: int) -> None:
        self._engine.set_duracion_tecla_ms(valor)
        self._avisar_si_no_calibrado()

    # ------------------------------------------------------------------
    # Prueba de validacion
    # ------------------------------------------------------------------
    def _on_iniciar_prueba(self) -> None:
        if not self._engine.esta_calibrado():
            QMessageBox.warning(self, "Falta calibrar", "Debe completar la calibración antes de ejecutar la prueba.")
            return
        self._btn_prueba.setEnabled(False)
        self._btn_omitir.setEnabled(False)
        self._ocultar_aviso_repetir_prueba()
        self._engine.iniciar_prueba_validacion()

    def _on_validation_attempt_started(self, intento: int, total: int) -> None:
        self._btn_siguiente_intento.setEnabled(True)
        self._lbl_prueba.setText(
            f"Intento {intento}/{total}: contraiga y relaje el músculo, luego presione "
            f"\"Registrar intento y continuar\" (0 evento(s) detectado(s))"
        )

    def _on_validation_attempt_progress(self, eventos: int) -> None:
        self._lbl_prueba.setText(
            f"Intento {self._engine.intento_actual}/{self._engine.N_INTENTOS_VALIDACION}: contraiga y relaje el "
            f"músculo, luego presione \"Registrar intento y continuar\" ({eventos} evento(s) detectado(s))"
        )

    def _on_validation_finished(self, eventos_por_intento: list) -> None:
        self._btn_siguiente_intento.setEnabled(False)
        correcta = all(n == 1 for n in eventos_por_intento)
        resumen = " | ".join(f"Intento {i + 1}: {n} evento(s)" for i, n in enumerate(eventos_por_intento))
        icono = "✔" if correcta else "⚠"
        self._lbl_prueba.setText(f"{icono} Prueba finalizada — {resumen}")
        self._btn_prueba.setEnabled(True)
        self._btn_omitir.setEnabled(True)

    def _on_omitir_prueba(self) -> None:
        self._engine.omitir_prueba()
        self._ocultar_aviso_repetir_prueba()

    # ------------------------------------------------------------------
    def liberar_recursos(self) -> None:
        pass
