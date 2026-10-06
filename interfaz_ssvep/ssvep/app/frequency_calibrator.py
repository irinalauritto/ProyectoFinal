"""Calibración individual de frecuencias SSVEP.

Mide, para el usuario actual, la exactitud del clasificador CCA en varias
frecuencias candidatas y selecciona las 6 finales evitando colisiones
armónicas entre ellas. Archivo nuevo: no modifica ningún otro archivo de
`ssvep/app/` -- reusa tal cual `EEGSignalCCAClassifier`, `StimulusViewer`,
`Stimulus`/`UserPreferences` y el patrón de reporte PDF de `BCIEvaluator`.

Metodología (ver también Mu et al. 2022 para la nocion de colisión
armónica, y Kozin et al. 2023 / Keihani et al. 2018 para el diseño general
de barrido de frecuencias candidata por candidata, discutidos en el diseño
de este proyecto):

Por cada candidata se arma una configuración de SOLO 2 estímulos activos
(la candidata + un ancla fija fuera de la banda de candidatas) porque el
umbral del clasificador (`BaseEEGClassifier._validate_threshold`) calcula
qué tan por encima está la correlación ganadora *respecto de las demás
candidatas* -- con un solo estímulo activo esa cuenta da 0/0 siempre y el
clasificador nunca puede devolver un resultado válido. Con 2 estímulos (el
umbral en 0.0, decisión cruda por ventana) cada intento es un forzado
"la candidata gana, o gana el ancla", que es justamente la señal que
interesa medir.

La ventana de estímulos es `StimulusViewerCalibration`
(`stimulus_viewer_calibration.py`, archivo nuevo también): candidata y
ancla centradas y bien separadas, con un descanso de `rest_duration_s`
antes de cada trial (candidata resaltada en rojo + mensaje "Debe mirar el
estímulo remarcado") -- ni `stimulus_viewer.py` ni ningún otro archivo
existente de `ssvep/app/` se modifican.
"""

from __future__ import annotations

import builtins
import ctypes
import random
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from ssvep.app.dataclasses import Stimulus, UserPreferences
from ssvep.app.eeg_signal_classifier import EEGSignalCCAClassifier

# Códigos especiales que puede devolver EEGSignalCCAClassifier.update_buffer
# (ver base_classifier.py) -- con threshold=0.0 (ver _run_current_trial)
# -1 ("no supera el umbral") no debería ocurrir nunca, pero se filtra igual
# por robustez.
_NO_ENOUGH_SAMPLES = -2
_NO_THRESHOLD = -1

DEFAULT_CANDIDATE_FREQS: Tuple[float, ...] = tuple(float(f) for f in range(8, 17))  # 8..16 Hz, paso 1
DEFAULT_ANCHOR_FREQ = 17.0
DEFAULT_N_REPEATS = 3
DEFAULT_TRIAL_DURATION_S = 13.0
DEFAULT_DISCARD_S = 4.0
DEFAULT_REST_DURATION_S = 6.0
DEFAULT_N_HARMONICS_COLLISION = 2
DEFAULT_N_FINAL = 6


# =============================================================================
# Funciones puras (testeables sin Qt ni hardware) -- ver tests/test_frequency_calibrator.py
# =============================================================================

def collides(f1: float, f2: float, n_harmonics: int = DEFAULT_N_HARMONICS_COLLISION, tol: float = 1e-6) -> bool:
    """Indica si `f2` es un armónico entero de `f1` (o viceversa), hasta el
    n-ésimo armónico. Un armónico compartido es una fuente real de
    confusión para el clasificador CCA (la respuesta cerebral a f1 tiene
    energía en sus armónicos, que se puede confundir con una respuesta
    genuina a f2 si f2 coincide con uno de ellos).

    Args:
        f1, f2: Frecuencias a comparar, en Hz.
        n_harmonics: Orden máximo de armónico a considerar (2 = hasta el
            2do armónico inclusive).
        tol: Tolerancia absoluta en Hz para considerar una coincidencia.

    Returns:
        True si `f2 == k*f1` o `f1 == k*f2` para algún entero k en
        [1, n_harmonics].
    """
    if f1 <= 0 or f2 <= 0:
        return False
    for k in range(1, n_harmonics + 1):
        if abs(k * f1 - f2) <= tol or abs(k * f2 - f1) <= tol:
            return True
    return False


def compute_candidate_accuracies(decisions: List[Tuple[float, int, int]]) -> Dict[float, float]:
    """Exactitud (0-100) por candidata, a partir de las decisiones registradas.

    Args:
        decisions: Lista de `(candidate_freq, true_label, predicted_label)`.
            `true_label` es siempre 0 (la candidata ocupa la posición 0 en
            cada trial, ver `FrequencyCalibrator._start_trial`) -- se
            conserva igual en la tupla para que el formato sea el mismo
            que `BCIEvaluator.true_labels`/`predicted_labels`.

    Returns:
        `{frecuencia: accuracy}` -- 0.0 para una candidata sin decisiones
        registradas (no debería pasar en una corrida real, pero evita
        división por cero si un trial no llegó a producir ninguna).
    """
    correct: Dict[float, int] = defaultdict(int)
    total: Dict[float, int] = defaultdict(int)
    for freq, true_label, predicted_label in decisions:
        total[freq] += 1
        if predicted_label == true_label:
            correct[freq] += 1
    return {freq: (correct[freq] / total[freq] * 100.0) for freq, n in total.items()}


def select_final_frequencies(
    accuracies: Dict[float, float],
    n_final: int = DEFAULT_N_FINAL,
    n_harmonics: int = DEFAULT_N_HARMONICS_COLLISION,
) -> List[float]:
    """Selecciona hasta `n_final` frecuencias evitando colisión armónica.

    Recorre las candidatas ordenadas por exactitud descendente; una
    candidata se agrega si no colisiona (ver `collides`) con ninguna de
    las ya seleccionadas. Al recorrer en orden descendente, si colisiona
    con una ya seleccionada esa ya-seleccionada tiene exactitud mayor o
    igual -- por construcción, la que se descarta del par es siempre la
    de menor exactitud (la candidata actual).

    Args:
        accuracies: `{frecuencia: accuracy}`, ej. salida de
            `compute_candidate_accuracies`.
        n_final: Cantidad de frecuencias finales a seleccionar.
        n_harmonics: Orden máximo de armónico para `collides`.

    Returns:
        Lista de hasta `n_final` frecuencias seleccionadas, en el orden en
        que fueron aceptadas (descendente por exactitud).
    """
    ordered = sorted(accuracies.keys(), key=lambda f: accuracies[f], reverse=True)
    selected: List[float] = []
    for freq in ordered:
        if any(collides(freq, chosen, n_harmonics) for chosen in selected):
            continue
        selected.append(freq)
        if len(selected) >= n_final:
            break
    return selected


def _detect_refresh_rate() -> int:
    """Tasa de refresco (Hz) del monitor principal, vía la API de Windows
    (GDI `GetDeviceCaps`) -- independiente de `StimulusViewer`/PsychoPy
    (que detectan la suya propia, pero solo la usan puertas adentro del
    proceso de estímulos, sin exponerla). Se usa acá solo para registrarla
    como metadato de la corrida; 60 Hz como valor de respaldo si la
    consulta falla."""
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        try:
            vrefresh_index = 116  # VREFRESH, ver wingdi.h
            rate = gdi32.GetDeviceCaps(hdc, vrefresh_index)
        finally:
            user32.ReleaseDC(0, hdc)
        return int(rate) if rate and rate > 1 else 60
    except Exception:
        return 60


# =============================================================================
# Orquestador (Qt, hardware real) -- no se testea unitariamente, ver arriba
# =============================================================================

class FrequencyCalibrator(QObject):
    """Barrido de frecuencias candidatas + selección final, para un usuario.

    No posee la adquisición de EEG: quien la use debe conectar
    `receive_classification` a la señal de clasificación del pipeline en
    uso (ej. `EegSession.classification_result`) mientras la calibración
    esté corriendo, y cargar `self.classifier` como clasificador activo
    del `EEGSignalProcessor` en uso (ver `EegSession.use_classifier` en
    `interfaz/eeg/session.py`) -- este archivo no asume ninguna interfaz
    de shell en particular.

    `stimulus_viewer` debe ser una instancia de `StimulusViewerCalibration`
    (`stimulus_viewer_calibration.py`): expone `load_stimulus_use(candidata,
    ancla)`, `start_stim()`, `start_rest()`, `start_flicker()`, `stop_stim()`,
    `is_running()` y la señal `stimuli_ready`.

    Cada trial: `start_stim()` -> espera `stimuli_ready` -> `rest_duration_s`
    de descanso (candidata resaltada + mensaje, sin parpadear) ->
    `start_flicker()` -> `trial_duration_s` de parpadeo (se descartan las
    decisiones de los primeros `discard_s`) -> `stop_stim()`.

    Señales:
        candidate_started(freq, candidate_num, n_candidates): nueva candidata.
        trial_started(repeat_num, n_repeats): nuevo intento de la candidata actual.
        resting(segundos_restantes): descanso previo al trial, cuenta regresiva.
        time_elapsed(segundos): segundos transcurridos en el parpadeo del trial actual.
        trial_finished(freq, hits, decisiones_validas): resumen del trial recién terminado.
        calibration_finished(resultado): barrido completo -- ver `_finish`.
        calibration_failed(motivo)
    """

    candidate_started = Signal(float, int, int)
    trial_started = Signal(int, int)
    resting = Signal(int)
    time_elapsed = Signal(int)
    trial_finished = Signal(float, int, int)
    calibration_finished = Signal(dict)
    calibration_failed = Signal(str)

    def __init__(
        self,
        stimulus_viewer: Any,
        channels: Dict[int, str],
        time_window: float,
        sample_rate: Optional[float] = None,
        harmonics: Optional[int] = None,
        candidate_freqs: Tuple[float, ...] = DEFAULT_CANDIDATE_FREQS,
        anchor_freq: float = DEFAULT_ANCHOR_FREQ,
        n_repeats: int = DEFAULT_N_REPEATS,
        trial_duration_s: float = DEFAULT_TRIAL_DURATION_S,
        discard_s: float = DEFAULT_DISCARD_S,
        rest_duration_s: float = DEFAULT_REST_DURATION_S,
        n_harmonics_collision: int = DEFAULT_N_HARMONICS_COLLISION,
        n_final: int = DEFAULT_N_FINAL,
        seed: Optional[int] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._stimulus_viewer = stimulus_viewer
        self._channels = dict(channels)
        self._time_window = time_window
        self._sample_rate = sample_rate if sample_rate is not None else builtins.SAMPLE_RATE
        self._harmonics = harmonics if harmonics is not None else builtins.SETTINGS.f_bands

        self._candidate_freqs = list(candidate_freqs)
        self._anchor_freq = anchor_freq
        self._n_repeats = n_repeats
        self._trial_duration_s = trial_duration_s
        self._discard_s = discard_s
        self._rest_duration_s = rest_duration_s
        self._n_harmonics_collision = n_harmonics_collision
        self._n_final = n_final
        self._seed = seed if seed is not None else random.SystemRandom().randrange(2**31)

        # Clasificador propio, aislado del que usa la sesión en producción
        # (ver docstring de módulo: nunca se le carga más de 2 estímulos).
        self.classifier = EEGSignalCCAClassifier()

        self._trial_specs: List[Tuple[float, int]] = []
        self._trial_index = 0
        self._decisions: List[Tuple[float, int, int]] = []
        self._current_freq: Optional[float] = None
        self._current_trial_decisions: List[Tuple[float, int, int]] = []
        self._trial_elapsed = 0
        self._rest_elapsed = 0
        self._in_discard = True
        self._resting = False
        self._refresh_rate = 60
        self._running = False
        self._waiting_ready = False

        self._trial_timer = QTimer(self)
        self._trial_timer.setInterval(1000)
        self._trial_timer.timeout.connect(self._on_trial_tick)

        self._rest_timer = QTimer(self)
        self._rest_timer.setInterval(1000)
        self._rest_timer.timeout.connect(self._on_rest_tick)

        self._stimulus_viewer.stimuli_ready.connect(self._on_stimuli_ready)
        # Opcional: StimulusViewerCalibration expone stimulus_failed cuando
        # el proceso de la ventana crashea antes de abrir (ver su docstring)
        # -- sin esto, ese fallo deja la calibracion colgada para siempre en
        # "esperando la ventana", sin ningun aviso.
        stimulus_failed = getattr(self._stimulus_viewer, "stimulus_failed", None)
        if stimulus_failed is not None:
            stimulus_failed.connect(self._on_stimulus_failed)

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Arranca el barrido completo (bloquea hasta `calibration_finished`
        o `calibration_failed`, ambas asíncronas vía señales Qt)."""
        if self._running:
            return
        self._running = True

        rng = random.Random(self._seed)
        self._trial_specs = [
            (freq, repeat) for freq in self._candidate_freqs for repeat in range(self._n_repeats)
        ]
        rng.shuffle(self._trial_specs)
        self._trial_index = 0
        self._decisions = []
        self._refresh_rate = _detect_refresh_rate()
        # Se le pasa el refresco ya detectado (GDI, rapido) al visor para que
        # la ventana de estimulos no tenga que medirlo de nuevo con PsychoPy
        # (ver StimulusViewerCalibration.set_refresh_rate).
        set_refresh_rate = getattr(self._stimulus_viewer, "set_refresh_rate", None)
        if set_refresh_rate is not None:
            set_refresh_rate(self._refresh_rate)

        self._advance_trial()

    def cancel(self) -> None:
        """Corta la corrida en curso (si hay una) sin emitir `calibration_finished`."""
        if not self._running:
            return
        self._running = False
        self._waiting_ready = False
        self._resting = False
        self._trial_timer.stop()
        self._rest_timer.stop()
        if self._stimulus_viewer.is_running():
            self._stimulus_viewer.stop_stim()

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    def receive_classification(self, result: int) -> None:
        """Conectar a la señal de clasificación del pipeline en uso mientras
        `is_running()` sea True (ver docstring de la clase)."""
        if not self._running or self._waiting_ready or self._resting or self._in_discard:
            return
        if result in (_NO_ENOUGH_SAMPLES, _NO_THRESHOLD) or result < 0:
            return
        self._current_trial_decisions.append((self._current_freq, 0, result))

    # ------------------------------------------------------------------
    def _advance_trial(self) -> None:
        if self._trial_index >= len(self._trial_specs):
            self._finish()
            return

        freq, repeat = self._trial_specs[self._trial_index]
        self._current_freq = freq
        self._current_trial_decisions = []
        self._trial_elapsed = 0
        self._in_discard = True

        candidate_num = self._candidate_freqs.index(freq) + 1
        self.candidate_started.emit(freq, candidate_num, len(self._candidate_freqs))
        self.trial_started.emit(repeat + 1, self._n_repeats)

        # Config de 2 estimulos: candidata (posicion 0) + ancla fija (posicion 1).
        # Mismo shape_type ("square") para ambos -- el ancla ya no se dibuja
        # como circulo, para que los dos estimulos se vean iguales salvo por
        # la frecuencia.
        stim_candidate = Stimulus(freq=freq, theta=0.0, stim_type="flic", shape_type="square")
        stim_anchor = Stimulus(freq=self._anchor_freq, theta=0.0, stim_type="flic", shape_type="square")
        trial_prefs = UserPreferences(
            classification_method="CCA",
            time_window=self._time_window,
            channels=self._channels,
            stimulus=[stim_candidate, stim_anchor],
            stimulus_on=[True, True],
        )

        self.classifier.load_data(self._sample_rate, trial_prefs, self._harmonics)
        self.classifier.load_threshold(0.0)  # decision cruda, sin voto de continuidad (ver docstring de modulo)
        self.classifier.clear_buffer()

        if self._stimulus_viewer.is_running():
            # La ventana ya esta abierta (no se cierra entre trials, ver
            # _end_trial/_finish) -- se corta el parpadeo del trial anterior,
            # se cambian las frecuencias, y se pasa directo al descanso sin
            # esperar `stimuli_ready` de nuevo (esa señal solo se emite una
            # vez, al abrir la ventana por primera vez).
            self._stimulus_viewer.start_rest()
            self._stimulus_viewer.update_stimulus_use(stim_candidate, stim_anchor)
            self._waiting_ready = False
            self._begin_rest()
        else:
            self._waiting_ready = True
            self._stimulus_viewer.load_stimulus_use(stim_candidate, stim_anchor)
            self._stimulus_viewer.start_stim()

    def _on_stimulus_failed(self, reason: str) -> None:
        if not self._running:
            return
        self._running = False
        self._waiting_ready = False
        self._resting = False
        self._trial_timer.stop()
        self._rest_timer.stop()
        self.calibration_failed.emit(reason)

    def _on_stimuli_ready(self, _hwnd: int) -> None:
        if not self._running or not self._waiting_ready:
            return
        self._waiting_ready = False
        self._begin_rest()

    def _begin_rest(self) -> None:
        # Descanso antes del trial: candidata resaltada + mensaje "Debe
        # mirar el estímulo remarcado" (ver StimulusViewerCalibration),
        # sin parpadear todavía. La ventana ya arranca en este estado
        # (start_stim) o ya se le pidió expresamente con start_rest()
        # (_advance_trial, trials siguientes al primero), asi que alcanza
        # con arrancar el timer.
        self._resting = True
        self._rest_elapsed = 0
        self.resting.emit(int(self._rest_duration_s))
        self._rest_timer.start()

    def _on_rest_tick(self) -> None:
        self._rest_elapsed += 1
        remaining = max(0, int(self._rest_duration_s) - self._rest_elapsed)
        self.resting.emit(remaining)
        if self._rest_elapsed >= self._rest_duration_s:
            self._rest_timer.stop()
            self._resting = False
            self._stimulus_viewer.start_flicker()
            self._trial_timer.start()

    def _on_trial_tick(self) -> None:
        self._trial_elapsed += 1
        self.time_elapsed.emit(self._trial_elapsed)
        if self._in_discard and self._trial_elapsed >= self._discard_s:
            self._in_discard = False
        if self._trial_elapsed >= self._trial_duration_s:
            self._trial_timer.stop()
            self._end_trial()

    def _end_trial(self) -> None:
        self._decisions.extend(self._current_trial_decisions)
        hits = sum(1 for _, true_label, pred in self._current_trial_decisions if pred == true_label)
        self.trial_finished.emit(self._current_freq, hits, len(self._current_trial_decisions))

        # La ventana queda abierta entre trials (ver _advance_trial) -- solo
        # se cierra al terminar todo el barrido, en _finish().
        self._trial_index += 1
        self._advance_trial()

    def _finish(self) -> None:
        self._running = False
        if self._stimulus_viewer.is_running():
            self._stimulus_viewer.stop_stim()
        accuracies = compute_candidate_accuracies(self._decisions)
        selected = select_final_frequencies(accuracies, n_final=self._n_final, n_harmonics=self._n_harmonics_collision)
        result = {
            "date": datetime.now().isoformat(timespec="seconds"),
            "seed": self._seed,
            "refresh_rate": self._refresh_rate,
            "anchor_freq": self._anchor_freq,
            "candidate_freqs": list(self._candidate_freqs),
            "n_repeats": self._n_repeats,
            "trial_duration_s": self._trial_duration_s,
            "discard_s": self._discard_s,
            "accuracies": accuracies,
            "selected": selected,
        }
        self.calibration_finished.emit(result)

    # ------------------------------------------------------------------
    def generate_report(self, filepath: str, result: Dict[str, Any]) -> None:
        """PDF con un gráfico de barras de exactitud por candidata, las 6
        seleccionadas resaltadas -- mismo patrón (matplotlib + PdfPages)
        que `BCIEvaluator.generate_report`."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        accuracies = result["accuracies"]
        selected = set(result["selected"])
        freqs = sorted(accuracies.keys())
        accs = [accuracies[f] for f in freqs]
        colors = ["#2f6690" if f in selected else "#c7cdd6" for f in freqs]
        labels = [f"{f:g}" for f in freqs]

        with PdfPages(filepath) as pdf:
            fig, ax = plt.subplots(figsize=(8.27, 5.5))
            ax.bar(labels, accs, color=colors)
            ax.set_xlabel("Frecuencia candidata (Hz)")
            ax.set_ylabel("Exactitud (%)")
            ax.set_ylim(0, 100)
            ax.set_title("Calibración de frecuencias SSVEP")
            subtitle = (
                f"Semilla: {result['seed']}  |  Refresco monitor: {result['refresh_rate']} Hz  |  "
                f"Ancla: {result['anchor_freq']:g} Hz  |  Seleccionadas: "
                + ", ".join(f"{f:g}" for f in sorted(selected))
            )
            fig.text(0.5, 0.92, subtitle, ha="center", fontsize=8, color="#69707b")
            fig.tight_layout(rect=(0, 0, 1, 0.9))
            pdf.savefig(fig)
            plt.close(fig)
