"""EegSession: orquesta el pipeline de SSVEP (adquisicion, filtros, PSD,
clasificador CCA, evaluador, control por teclado, voz, estimulo visual)
sin depender en nada de la UI de interfaz_ssvep (UserUI/AppController).

Reemplaza el rol de AppController para la interfaz nueva: mismas clases de
"logica" de ssvep/app/, importadas e instanciadas tal cual (nunca se edita
ningun archivo de interfaz_ssvep/), orquestadas por esta clase propia.

CCA es el unico clasificador contemplado -- no se orquesta el camino de
entrenamiento eTRCA (TrainingManager) porque esta interfaz no lo necesita.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal


class EegSession(QObject):
    # Señales re-emitidas del pipeline interno, para que la UI se conecte
    # sin conocer las piezas internas (EEGSignalProcessor, EEGFileInterface, etc).
    stream_started = Signal(bool)
    filtered_data = Signal(list)
    psd_data = Signal(object, object)
    classification_result = Signal(int)
    error_occurred = Signal(str)
    stimuli_ready = Signal(int)  # hwnd de la ventana de estimulos

    def __init__(self, data_dir: str, eeg_bin_path: Optional[str] = None, parent=None):
        super().__init__(parent)

        import builtins

        import ssvep.app  # noqa: F401  efecto secundario: carga SAMPLE_RATE/SETTINGS/etc en builtins

        from ssvep.app.bci_evaluator import BCIEvaluator
        from ssvep.app.config import crear_engine, init_database
        from ssvep.app.eeg_serial_iface import EEGFileInterface
        from ssvep.app.eeg_signal_classifier import EEGSignalCCAClassifier
        from ssvep.app.eeg_signal_procesor import EEGSignalProcessor
        from ssvep.app.game_manager import GameManager
        from ssvep.app.keyboard_controller import KeyboardController
        from ssvep.app.managers import PreferencesManager, TrainingWeightsManager, UserManager
        from ssvep.app.models import Base
        from ssvep.app.psd_estimator import PSDEstimator
        from ssvep.app.repositories import (
            PreferencesRepositorySQLAlchemy,
            TrainingWeightsRepositorySQLAlchemy,
            UserRepositorySQLAlchemy,
        )
        from ssvep.app.signal_filters import SignalFilters
        from ssvep.app.stimulus_viewer import StimulusViewer
        from ssvep.app.voice_feedback import VoiceFeedback

        self._data_dir = str(data_dir)
        self._builtins = builtins

        # --- Persistencia (mismo patron que usaba AppController.__initialize_database) ---
        init_database(self._data_dir)
        engine_factory = crear_engine()
        engine = engine_factory.kw["bind"]
        Base.metadata.create_all(bind=engine)
        db_session = engine_factory()
        self.user_manager = UserManager(UserRepositorySQLAlchemy(db_session))
        self.prefs_manager = PreferencesManager(PreferencesRepositorySQLAlchemy(db_session))
        self.weights_manager = TrainingWeightsManager(TrainingWeightsRepositorySQLAlchemy(db_session))

        # --- Pipeline de señal ---
        self._eeg_iface = EEGFileInterface(arch_n=eeg_bin_path or "eeg_bin.bin")
        self._filters = SignalFilters()
        self._psd_estimator = PSDEstimator()
        self._classifier = EEGSignalCCAClassifier()
        self._processing_worker = EEGSignalProcessor(self._filters, self._psd_estimator)
        self._processing_thread = QThread()

        # --- Feedback / evaluacion / estimulo visual ---
        self.keyboard = KeyboardController(press_duration_ms=builtins.SETTINGS.press_duration_ms)
        self.voice = VoiceFeedback()
        self.evaluator = BCIEvaluator(base_dir=self._data_dir)
        self.stimulus_viewer = StimulusViewer()
        self.game_manager = GameManager()

        self.current_user_id: Optional[int] = None
        self.current_preferences = None  # UserPreferences, seteado en load_user()
        self.missing_channel_names: set = set()  # nombres de prefs.channels sin datos reales (ver load_user)
        self.enable_control = False
        self.add_test_data = False
        self.audio_feedback_enabled = False

        # --- Wiring interno ---
        self._eeg_iface.streamStarted.connect(self.stream_started)
        self._eeg_iface.dataDecoded.connect(self._processing_worker.on_data_decoded)
        self._eeg_iface.portException.connect(self.error_occurred)

        self._processing_worker.filteredData.connect(self.filtered_data)
        self._processing_worker.psdData.connect(self.psd_data)
        self._processing_worker.classificationResult.connect(self._on_classification_result)
        self._processing_worker.errorOccurred.connect(self.error_occurred)

        self.stimulus_viewer.stimuli_ready.connect(self.stimuli_ready)

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Mueve el worker de procesamiento a su hilo dedicado y lo arranca.
        Llamar una sola vez, antes de start_streaming()."""
        self._processing_worker.moveToThread(self._processing_thread)
        self._processing_thread.start()

    def load_user(self, user_id: int):
        """Carga las preferencias del usuario y configura filtros/clasificador/evaluador.

        Devuelve el UserPreferences cargado.
        """
        prefs = self.prefs_manager.get_user_preferences(user_id)
        self.current_user_id = user_id
        self.current_preferences = prefs

        # Todos los estimulos quedan siempre activos: todavia no existe la
        # pantalla de "configuracion avanzada" (ver plan de Fase 3) que le
        # permitiria al usuario elegir apagar alguno -- hasta que exista,
        # cualquier `stimulus_on` guardado (de antes, o de otra fuente) se
        # ignora en favor de todos activos. No se persiste este cambio (no
        # se llama save_preferences aca): en cuanto exista esa pantalla,
        # esto se saca y stimulus_on vuelve a reflejar la eleccion real.
        prefs.stimulus_on = [True] * len(prefs.stimulus)

        list_freqs = [stim.freq for stim in prefs.stimulus]
        self._filters.stop()
        # Banda + notch encendidos por defecto (igual que UserUI, que arranca
        # con chk_bandpass y chk_notch tildados); sin esto la señal llega
        # cruda, con el offset DC de millones de cuentas, y se ve pegada al
        # ruido de red en vez de EEG.
        self._filters.add_parameters(
            low_freq=min(list_freqs), high_freq=max(list_freqs), bandpass_enabled=True, notch_enabled=True
        )

        # Igual que AppController al recargar un usuario: sin stop() previo,
        # load_calc_interval falla si el estimador ya proceso datos ("Ya
        # iniciado") -- pasa al cambiar de usuario o de canales.
        self._psd_estimator.stop()
        self._psd_estimator.load_buffer_size(len(prefs.channels))
        self._psd_estimator.load_calc_interval(prefs.time_window)

        self._classifier.load_data(self._builtins.SAMPLE_RATE, prefs, self._builtins.SETTINGS.f_bands)
        self._processing_worker.load_classifier(self._classifier)
        self._processing_worker.set_classifier_ready(True)

        user_name = self.user_manager.get_user(user_id)["name"]
        self.evaluator.set_user_preferences(prefs)
        self.evaluator.set_report_path(f"reporte-bci-{user_name}.pdf")
        self.evaluator.set_auto_generate_report(True)

        self.stimulus_viewer.load_stimulus_use(prefs.stimulus, prefs.stimulus_on)

        # Pacientes de prueba (ej. "Guille") tienen una grabacion SSVEP real
        # guardada -- se reproduce esa en vez del archivo generico, para
        # tener los canales con datos de verdad en vez de huecos en cero.
        # TEST_PATIENTS se importa tal cual de app_controller.py (no se
        # duplica el mapeo, ni se toca ese archivo).
        from ssvep.app.app_controller import TEST_PATIENTS

        relative_path = TEST_PATIENTS.get(user_name)
        self.missing_channel_names = set()
        if hasattr(self._eeg_iface, "set_source_file"):
            if relative_path is not None:
                from pathlib import Path

                abs_path = Path(self._data_dir) / relative_path
                self._eeg_iface.set_source_file(str(abs_path))
                self.missing_channel_names = self._missing_channels_in_recording(abs_path, prefs)
            else:
                self._eeg_iface.set_source_file(None)

        return prefs

    def _missing_channels_in_recording(self, mat_path, prefs) -> set:
        """Nombres de `prefs.channels` que NO estan realmente grabados en
        `mat_path` (lectura propia del .mat, solo para saber que mostrar --
        no se toca `eeg_serial_iface.py`, que igual zero-rellena esos
        canales internamente para no romper el largo fijo del buffer).
        Si no está en la grabación, no se considera un canal real."""
        try:
            from ssvep.app import mat_recording

            data = mat_recording.load_recording(str(mat_path))
            recorded = {str(name).strip() for name in data["info"]["channels"]}
        except Exception:
            return set()
        return {name for name in prefs.channels.values() if name not in recorded}

    def evaluation_sequence(self) -> list:
        """Secuencia de la prueba de desempeño: para pacientes de prueba
        (ej. Guille) es la secuencia realmente pedida al grabar su .mat
        (TEST_PATIENTS_SEQUENCES, igual que AppController); para el resto
        se genera al azar entre los estimulos activos."""
        from ssvep.app.app_controller import TEST_PATIENTS_SEQUENCES

        name = self.user_manager.get_user(self.current_user_id)["name"]
        if name in TEST_PATIENTS_SEQUENCES:
            return list(TEST_PATIENTS_SEQUENCES[name])
        active = [i for i, on in enumerate(self.current_preferences.stimulus_on) if on]
        return self._builtins.SETTINGS.generate_evaluation_sequence(active)

    def save_preferences(self, prefs) -> None:
        """Persiste `prefs` (UserPreferences) para el usuario actual y las
        vuelve a cargar (misma UserPreferences queda activa en el pipeline)."""
        if self.current_user_id is None:
            raise RuntimeError("No hay un usuario cargado (llamar load_user primero)")
        self.prefs_manager.save_or_update_preferences(self.current_user_id, prefs)
        self.load_user(self.current_user_id)

    def set_eeg_source_file(self, path: Optional[str]) -> None:
        """Cambia el archivo fuente de EEGFileInterface (crudo .bin o .mat
        grabado). Solo tiene efecto si la adquisicion configurada es por
        archivo; no aplica con EEGSerialInterface."""
        if hasattr(self._eeg_iface, "set_source_file"):
            self._eeg_iface.set_source_file(path)

    # ------------------------------------------------------------------
    def start_streaming(self) -> None:
        self._processing_worker.start()
        self._eeg_iface.begin_connection(self.current_preferences.channels)
        self._processing_worker.set_psd_enabled(True)

    def stop_streaming(self) -> None:
        self._eeg_iface.end_connection()
        self._processing_worker.stop()
        self._processing_worker.set_psd_enabled(False)
        self.stimulus_viewer.stop_stim()
        self.game_manager.close_game()

    # ------------------------------------------------------------------
    def set_threshold(self, value: float) -> None:
        self._classifier.load_threshold(value)

    def set_psd_channel_index(self, index: int) -> None:
        self._psd_estimator.set_channel_index(index)

    def set_filters(self, *, bandpass=None, notch=None, media=None) -> None:
        self._filters.add_parameters(bandpass_enabled=bandpass, notch_enabled=notch, media_enabled=media)

    def set_enable_control(self, value: bool) -> None:
        self.enable_control = value

    def set_audio_feedback(self, value: bool) -> None:
        self.audio_feedback_enabled = value

    def set_add_test_data(self, value: bool) -> None:
        """Si esta en True, cada clasificacion valida se manda tambien a
        `self.evaluator.add_classification(...)` (usado durante Validacion)."""
        self.add_test_data = value

    def _on_classification_result(self, result: int) -> None:
        self.classification_result.emit(result)
        if result < -1:
            return
        if self.audio_feedback_enabled:
            self.voice.announce(result)
        if self.add_test_data:
            self.evaluator.add_classification(result)
        if self.enable_control:
            self.keyboard.stim_received(result)

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        """Detiene streaming y el hilo de procesamiento. Llamar al cerrar la sesion."""
        self.stop_streaming()
        self._processing_thread.quit()
        self._processing_thread.wait()
