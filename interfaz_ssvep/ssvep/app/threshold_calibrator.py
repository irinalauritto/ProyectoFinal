"""Validación: cálculo automático del umbral de aceptación (T) del usuario.

Mide, con los estímulos finales reales del usuario (las frecuencias que
seleccionó la Calibración, ver `frequency_calibrator.py`; solo los que están
activos en su método de entrada), qué tan confiable es cada
ventana del clasificador CCA según su margen normalizado, y elige el umbral
que se va a usar en producción en vez de que un operador lo ajuste a mano.

Metodología (misma idea que la Calibración: decisión cruda por ventana, con
el umbral del clasificador en 0.0):

Los estímulos activos parpadean en simultáneo durante toda la corrida, sin
apagarse entre ítems -- por eso acá no hay descanso entre ítems. Por cada
ítem (en orden aleatorio) se anuncia por voz cuál hay que mirar, se da una
ventana de aviso (`cue_duration_s`) y después se registran
`trial_duration_s` segundos, descartando las ventanas de los primeros
`discard_s`. De cada ventana del tramo limpio se guarda
`(margen, fue_correcta)`, donde el margen es el mismo valor que
`BaseEEGClassifier._validate_threshold` compara contra el umbral (ver
`compute_margin` en `eeg_signal_classifier.py`).

El umbral final se elige con el criterio de Wang et al. (2020): se
descartan los T que dejan sin resolver a más del 20% de los ítems y, entre
los que quedan, se elige el de mayor exactitud (ver `sweep_thresholds`).
"""

from __future__ import annotations

import builtins
import random
from dataclasses import replace
from datetime import datetime
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from ssvep.app.bci_evaluator import calculate_itr
from ssvep.app.dataclasses import DEFAULT_THRESHOLD, UserPreferences
from ssvep.app.eeg_signal_classifier import EEGSignalCCAClassifier, compute_margin  # noqa: F401  (compute_margin se re-exporta)
from ssvep.app.frequency_calibrator import (
    DEFAULT_DISCARD_S,
    DEFAULT_TRIAL_DURATION_S,
    DEFAULT_WINDOW_ALIGN_MARGIN_S,
)

# Misma estructura de trial que la Calibración (Rejer & Cieszyński 2017: 2 s
# de aviso + 11 s de estimulación, se analizan los últimos 10), salvo que acá
# los estímulos siguen parpadeando también durante el aviso.
DEFAULT_CUE_DURATION_S = 2.0
# Cantidad mínima de ítems de una corrida: con menos estímulos activos
# (Barrido: 2, Secuencial: 4) se repiten hasta llegar, para que la Validación
# dure lo mismo en todos los métodos de entrada.
DEFAULT_MIN_ITEMS = 6
DEFAULT_MAX_UNRESOLVED_FRACTION = 0.2
DEFAULT_T_VALUES: Tuple[float, ...] = tuple(i / 100.0 for i in range(0, 101))  # 0.00..1.00, paso 0.01
DEFAULT_READY_TIMEOUT_S = 60.0

# Por ítem (clave: su posición en la secuencia de la corrida, no el estímulo
# -- un mismo estímulo puede aparecer en más de un ítem), la lista en orden
# temporal de (margen, fue_correcta) de cada ventana de su tramo limpio.
RecordsByItem = Dict[int, List[Tuple[float, bool]]]


# =============================================================================
# Funciones puras (testeables sin Qt ni hardware) -- ver tests/test_threshold_calibrator.py
# =============================================================================

def build_item_sequence(active_indices: Sequence[int], min_items: int, rng: random.Random) -> List[int]:
    """Arma la secuencia de estímulos a pedir en una corrida.

    Cada estímulo activo aparece al menos una vez. Si hay menos estímulos
    que `min_items`, se repiten de la forma más pareja posible hasta llegar
    exactamente a `min_items` (los que sobran al repartir se eligen al
    azar). El orden es aleatorio, evitando -- cuando se puede -- pedir el
    mismo estímulo dos veces seguidas.

    Args:
        active_indices: Índices de los estímulos activos.
        min_items: Cantidad mínima de ítems de la secuencia.
        rng: Generador aleatorio (con semilla, para que sea reproducible).

    Returns:
        Lista de índices de estímulo, de largo `max(min_items, len(active_indices))`.
    """
    active = list(active_indices)
    if not active:
        return []
    n_items = max(min_items, len(active))
    full_rounds, extra = divmod(n_items, len(active))
    sequence = active * full_rounds + rng.sample(active, extra)

    rng.shuffle(sequence)
    for _ in range(200):
        if all(a != b for a, b in zip(sequence, sequence[1:])):
            break
        rng.shuffle(sequence)
    return sequence


def replace_null_threshold(threshold: float, default: float = DEFAULT_THRESHOLD) -> float:
    """Devuelve `default` si el umbral calculado es 0 (o menor); si no, el mismo umbral.

    El barrido da 0 cuando la primera ventana de todos los ítems acierta:
    todos los T bajos empatan y gana el más bajo. Pero la corrida solo mide
    momentos en que el usuario mira un estímulo, y con umbral 0 el
    clasificador acepta cualquier ventana y nunca responde "sin detección"
    cuando no mira ninguno -- por eso ese resultado se reemplaza por el
    umbral por defecto.
    """
    return default if threshold <= 0 else threshold


class ThresholdOutcome(NamedTuple):
    """Resultado de simular un umbral T sobre los registros de una corrida.

    Attributes:
        unresolved_fraction: Fracción (0-1) de ítems sin ninguna ventana con
            margen >= T.
        accuracy: Exactitud (0-100) entre los ítems resueltos; 0.0 si no se
            resolvió ninguno.
        mean_windows_to_decision: Promedio, entre los ítems resueltos, de la
            cantidad de ventanas que hicieron falta hasta la primera aceptada
            (1 = se aceptó la primera); 0.0 si no se resolvió ninguno.
    """

    unresolved_fraction: float
    accuracy: float
    mean_windows_to_decision: float


def evaluate_threshold(records_by_item: RecordsByItem, t: float) -> ThresholdOutcome:
    """Simula el comportamiento real del clasificador con umbral `t`.

    Para cada ítem se recorren sus ventanas en orden temporal y la decisión
    del ítem es la de la PRIMERA ventana con margen >= `t` (no un promedio de
    todas las ventanas sueltas): eso es lo que vería el usuario, que recibe
    una acción apenas una ventana supera el umbral. Si ninguna ventana del
    ítem lo supera, el ítem queda sin resolver.

    Args:
        records_by_item: `{ítem: [(margen, fue_correcta), ...]}` en orden temporal.
        t: Umbral a simular.

    Returns:
        ThresholdOutcome con la fracción de ítems sin resolver, la exactitud
        entre los resueltos y las ventanas promedio hasta decidir.
    """
    n_items = len(records_by_item)
    if n_items == 0:
        return ThresholdOutcome(1.0, 0.0, 0.0)

    resolved = 0
    correct = 0
    windows_used = 0
    for windows in records_by_item.values():
        for position, (margin, was_correct) in enumerate(windows):
            if margin >= t:
                resolved += 1
                correct += 1 if was_correct else 0
                windows_used += position + 1
                break

    unresolved_fraction = (n_items - resolved) / n_items
    if resolved == 0:
        return ThresholdOutcome(unresolved_fraction, 0.0, 0.0)
    return ThresholdOutcome(unresolved_fraction, correct / resolved * 100.0, windows_used / resolved)


def sweep_thresholds(
    records_by_item: RecordsByItem,
    t_values: Iterable[float],
    max_unresolved_fraction: float = DEFAULT_MAX_UNRESOLVED_FRACTION,
) -> float:
    """Elige el umbral de aceptación según el criterio de Wang et al. (2020).

    Se descartan los T que dejan sin resolver a más de
    `max_unresolved_fraction` de los ítems y, entre los que quedan, se
    devuelve el de mayor exactitud (ver `evaluate_threshold`).

    Args:
        records_by_item: `{ítem: [(margen, fue_correcta), ...]}` en orden temporal.
        t_values: Umbrales candidatos.
        max_unresolved_fraction: Fracción máxima (0-1) de ítems sin resolver
            que se tolera para un T.

    Returns:
        El umbral elegido.

    Raises:
        ValueError: Si no hay registros, o si ningún T candidato deja
            resueltos a suficientes ítems.
    """
    if not records_by_item:
        raise ValueError("No hay ventanas registradas para calcular el umbral.")

    best_t: Optional[float] = None
    best_accuracy = -1.0
    # Decisión explícita de desempate: se recorre de menor a mayor y solo se
    # reemplaza al mejor con una exactitud ESTRICTAMENTE mayor, así que ante
    # un empate queda el T más bajo -- decide más rápido (acepta antes la
    # primera ventana) sin perder exactitud.
    for t in sorted(set(t_values)):
        outcome = evaluate_threshold(records_by_item, t)
        if outcome.unresolved_fraction > max_unresolved_fraction + 1e-9:
            continue
        if outcome.accuracy > best_accuracy:
            best_accuracy = outcome.accuracy
            best_t = t

    if best_t is None:
        raise ValueError(
            "Ningún umbral candidato resuelve suficientes ítems "
            f"(se tolera hasta {max_unresolved_fraction:.0%} sin resolver)."
        )
    return best_t


def summarize_threshold(
    records_by_item: RecordsByItem,
    t: float,
    window_s: float,
    n_classes: Optional[int] = None,
) -> Dict[str, float]:
    """Exactitud e ITR que se obtienen con el umbral `t` sobre una corrida.

    El tiempo por selección que entra al ITR es el promedio, entre los ítems
    resueltos, del tiempo hasta la primera ventana aceptada dentro del tramo
    limpio (ventanas necesarias x `window_s`); los ítems sin resolver no
    suman tiempo ni cuentan en la exactitud.

    Args:
        records_by_item: `{ítem: [(margen, fue_correcta), ...]}` en orden temporal.
        t: Umbral a evaluar.
        window_s: Duración (s) de cada ventana del clasificador.
        n_classes: Cantidad de clases N para el ITR; por defecto, la cantidad
            de ítems de `records_by_item`.

    Returns:
        `{"threshold", "accuracy" (0-100), "unresolved_fraction" (0-1),
        "mean_decision_time_s", "itr" (bits/min)}`.
    """
    outcome = evaluate_threshold(records_by_item, t)
    n = n_classes if n_classes is not None else len(records_by_item)
    decision_time_s = outcome.mean_windows_to_decision * window_s
    itr = calculate_itr(outcome.accuracy / 100.0, n, decision_time_s) if n >= 2 else 0.0
    return {
        "threshold": t,
        "accuracy": outcome.accuracy,
        "unresolved_fraction": outcome.unresolved_fraction,
        "mean_decision_time_s": decision_time_s,
        "itr": itr,
    }


# =============================================================================
# Orquestador (Qt, hardware real) -- no se testea unitariamente, ver arriba
# =============================================================================

class ThresholdCalibrator(QObject):
    """Corrida de Validación + cálculo del umbral T*, para un usuario.

    Igual que `FrequencyCalibrator`, no posee la adquisición de EEG: quien la
    use debe conectar `receive_classification` a la señal de clasificación
    del pipeline en uso (ej. `EegSession.classification_result`) mientras la
    corrida esté en curso, y cargar `self.classifier` como clasificador
    activo del `EEGSignalProcessor` (ver `EegSession.use_classifier`).

    `stimulus_viewer` debe ser un `StimulusViewer` (`stimulus_viewer.py`, el
    de siempre -- no `StimulusViewerCalibration`, que está armado para
    exactamente 2 estímulos): se le cargan los estímulos activos del usuario
    (`user_preferences.stimulus_on`: 2 en Barrido, 4 en Secuencial, 6 en
    Direccional) y quedan parpadeando toda la corrida. Solo esos son ítems de
    la corrida: el margen depende de cuántos estímulos compiten, así que el
    umbral vale para ese conjunto y hay que volver a validar si cambia.

    La secuencia tiene al menos `min_items` ítems (ver `build_item_sequence`):
    con menos estímulos activos, se repiten.

    Cada ítem: anuncio por voz -> `cue_duration_s` de aviso -> `trial_duration_s`
    de registro (se descartan las ventanas de los primeros `discard_s`). Sin
    descanso entre ítems.

    Señales:
        item_started(item_index, item_num, n_items): nuevo ítem a mirar
            (`item_index` es el índice del estímulo; `item_num`, su posición 1..n).
        cueing(segundos_restantes): aviso previo al registro, cuenta regresiva.
        time_elapsed(segundos): segundos transcurridos en el registro del ítem actual.
        window_classified(item_index, predicho, margen, fue_correcta): ventana registrada.
        item_finished(item_index, hits, ventanas_validas): resumen del ítem recién terminado.
        calibration_finished(resultado): corrida completa -- ver `_finish`.
        calibration_failed(motivo)
    """

    item_started = Signal(int, int, int)
    cueing = Signal(int)
    time_elapsed = Signal(int)
    window_classified = Signal(int, int, float, bool)
    item_finished = Signal(int, int, int)
    calibration_finished = Signal(dict)
    calibration_failed = Signal(str)

    def __init__(
        self,
        stimulus_viewer: Any,
        final_freqs: Sequence[float],
        user_preferences: UserPreferences,
        voice: Any = None,
        sample_rate: Optional[float] = None,
        harmonics: Optional[int] = None,
        cue_duration_s: float = DEFAULT_CUE_DURATION_S,
        trial_duration_s: float = DEFAULT_TRIAL_DURATION_S,
        discard_s: float = DEFAULT_DISCARD_S,
        min_items: int = DEFAULT_MIN_ITEMS,
        t_values: Iterable[float] = DEFAULT_T_VALUES,
        max_unresolved_fraction: float = DEFAULT_MAX_UNRESOLVED_FRACTION,
        ready_timeout_s: float = DEFAULT_READY_TIMEOUT_S,
        seed: Optional[int] = None,
        parent=None,
    ) -> None:
        """
        Args:
            stimulus_viewer: `StimulusViewer` donde parpadean los estímulos activos.
            final_freqs: Frecuencias finales (resultado de la Calibración),
                una por estímulo y en su mismo orden de índice.
            user_preferences: Preferencias reales del usuario (se usan sus
                canales, ventana de tiempo, la forma de cada estímulo y
                cuáles están activos).
            voice: Objeto con `announce(item_index)` (ej. `VoiceFeedback`)
                para anunciar el ítem a mirar; None para no anunciar.
        """
        super().__init__(parent)

        if len(final_freqs) != len(user_preferences.stimulus):
            raise ValueError(
                f"Se esperaban {len(user_preferences.stimulus)} frecuencias finales "
                f"(una por estímulo), llegaron {len(final_freqs)}."
            )

        self._stimulus_viewer = stimulus_viewer
        self._voice = voice
        self._sample_rate = sample_rate if sample_rate is not None else builtins.SAMPLE_RATE
        self._harmonics = harmonics if harmonics is not None else builtins.SETTINGS.f_bands

        # Config de la corrida: los estímulos reales del usuario con sus
        # frecuencias finales, los mismos activos que en su método de
        # entrada y umbral en 0.0.
        stimuli = [replace(stim, freq=float(freq)) for stim, freq in zip(user_preferences.stimulus, final_freqs)]
        stimulus_on = [bool(on) for on in user_preferences.stimulus_on]
        if len(stimulus_on) != len(stimuli):
            stimulus_on = [True] * len(stimuli)
        if sum(stimulus_on) < 2:
            # Con un solo estímulo el margen da 0/0 (ver frequency_calibrator.py).
            raise ValueError("La Validación necesita al menos 2 estímulos activos.")
        self._prefs = UserPreferences(
            classification_method="CCA",
            time_window=user_preferences.time_window,
            channels=dict(user_preferences.channels),
            stimulus=stimuli,
            stimulus_on=stimulus_on,
            threshold=0.0,
        )

        self._cue_duration_s = cue_duration_s
        self._trial_duration_s = trial_duration_s
        self._discard_s = discard_s
        self._t_values = tuple(t_values)
        self._max_unresolved_fraction = max_unresolved_fraction
        self._seed = seed if seed is not None else random.SystemRandom().randrange(2**31)

        # El orden se arma acá (no en start()) para que la UI pueda mostrar
        # la secuencia completa antes de arrancar.
        active_indices = [index for index, on in enumerate(stimulus_on) if on]
        self._n_classes = len(active_indices)
        self._item_order = build_item_sequence(active_indices, min_items, random.Random(self._seed))

        # Clasificador propio, aislado del que usa la sesión en producción.
        self.classifier = EEGSignalCCAClassifier()

        self._item_position = 0
        self._current_item: Optional[int] = None
        self._current_records: List[Tuple[float, bool]] = []
        self._records_by_item: RecordsByItem = {}
        self._last_decision_count = 0
        self._cue_elapsed = 0
        self._trial_elapsed = 0
        self._cueing = False
        self._in_discard = True
        self._running = False
        self._waiting_ready = False

        self._cue_timer = QTimer(self)
        self._cue_timer.setInterval(1000)
        self._cue_timer.timeout.connect(self._on_cue_tick)

        self._trial_timer = QTimer(self)
        self._trial_timer.setInterval(1000)
        self._trial_timer.timeout.connect(self._on_trial_tick)

        # Alineación de las ventanas con el tramo analizado, ver
        # DEFAULT_WINDOW_ALIGN_MARGIN_S en frequency_calibrator.py.
        self._align_timer = QTimer(self)
        self._align_timer.setSingleShot(True)
        self._align_timer.setInterval(int(max(0.0, discard_s - DEFAULT_WINDOW_ALIGN_MARGIN_S) * 1000))
        self._align_timer.timeout.connect(self.classifier.clear_buffer)

        # StimulusViewer no avisa si el proceso de la ventana crashea antes
        # de abrir: sin este tope la corrida quedaría colgada para siempre
        # en "esperando la ventana".
        self._ready_timer = QTimer(self)
        self._ready_timer.setSingleShot(True)
        self._ready_timer.setInterval(int(ready_timeout_s * 1000))
        self._ready_timer.timeout.connect(self._on_ready_timeout)

        self._stimulus_viewer.stimuli_ready.connect(self._on_stimuli_ready)
        stimulus_failed = getattr(self._stimulus_viewer, "stimulus_failed", None)
        if stimulus_failed is not None:
            stimulus_failed.connect(self._on_stimulus_failed)

    # ------------------------------------------------------------------
    @property
    def item_order(self) -> List[int]:
        """Índice de estímulo de cada ítem, en el orden en que se van a pedir
        (un mismo estímulo puede repetirse)."""
        return list(self._item_order)

    def start(self) -> None:
        """Arranca la corrida completa (termina con `calibration_finished` o
        `calibration_failed`, ambas asíncronas vía señales Qt)."""
        if self._running:
            return
        self._running = True
        self._item_position = 0
        self._records_by_item = {}

        self.classifier.load_data(self._sample_rate, self._prefs, self._harmonics)
        self.classifier.load_threshold(0.0)  # decisión cruda por ventana (ver docstring de módulo)
        self.classifier.clear_buffer()

        if self._stimulus_viewer.is_running():
            self._stimulus_viewer.stop_stim()
        self._stimulus_viewer.load_stimulus_use(self._prefs.stimulus, self._prefs.stimulus_on)
        self._waiting_ready = True
        self._ready_timer.start()
        self._stimulus_viewer.start_stim()

    def cancel(self) -> None:
        """Corta la corrida en curso (si hay una) sin emitir `calibration_finished`."""
        if not self._running:
            return
        self._stop_run()

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    def receive_classification(self, result: int) -> None:
        """Conectar a la señal de clasificación del pipeline en uso mientras
        `is_running()` sea True (ver docstring de la clase)."""
        if not self._running or self._waiting_ready or self._cueing or self._in_discard:
            return
        if result < 0:
            return
        # El margen no viaja en la señal: se lee del clasificador, junto con
        # el estímulo de esa misma ventana (misma lectura bajo lock). El
        # contador evita registrar dos veces una misma ventana.
        count, _rho, margin, predicted = self.classifier.last_raw_decision()
        if count == self._last_decision_count or margin is None:
            return
        self._last_decision_count = count

        was_correct = predicted == self._current_item
        self._current_records.append((margin, was_correct))
        self.window_classified.emit(self._current_item, predicted, margin, was_correct)

    # ------------------------------------------------------------------
    def _stop_run(self) -> None:
        self._running = False
        self._waiting_ready = False
        self._cueing = False
        self._ready_timer.stop()
        self._cue_timer.stop()
        self._trial_timer.stop()
        self._align_timer.stop()
        if self._stimulus_viewer.is_running():
            self._stimulus_viewer.stop_stim()

    def _fail(self, reason: str) -> None:
        if not self._running:
            return
        self._stop_run()
        self.calibration_failed.emit(reason)

    def _on_stimulus_failed(self, reason: str) -> None:
        self._fail(reason)

    def _on_ready_timeout(self) -> None:
        self._fail("La ventana de estímulos no terminó de abrirse.")

    def _on_stimuli_ready(self, _hwnd: int) -> None:
        if not self._running or not self._waiting_ready:
            return
        self._waiting_ready = False
        self._ready_timer.stop()
        # Parpadean desde acá hasta el final de la corrida.
        self._stimulus_viewer.start_flicker()
        self._advance_item()

    def _advance_item(self) -> None:
        if self._item_position >= len(self._item_order):
            self._finish()
            return

        self._current_item = self._item_order[self._item_position]
        self._current_records = []
        self._in_discard = True

        self.item_started.emit(self._current_item, self._item_position + 1, len(self._item_order))
        if self._voice is not None:
            self._voice.announce(self._current_item)

        if self._cue_duration_s <= 0:
            self._begin_trial()
            return
        self._cueing = True
        self._cue_elapsed = 0
        self.cueing.emit(int(self._cue_duration_s))
        self._cue_timer.start()

    def _on_cue_tick(self) -> None:
        self._cue_elapsed += 1
        self.cueing.emit(max(0, int(self._cue_duration_s) - self._cue_elapsed))
        if self._cue_elapsed >= self._cue_duration_s:
            self._cue_timer.stop()
            self._begin_trial()

    def _begin_trial(self) -> None:
        self._cueing = False
        self._trial_elapsed = 0
        self._in_discard = True
        self._last_decision_count = self.classifier.last_raw_decision()[0]
        self._trial_timer.start()
        self._align_timer.start()

    def _on_trial_tick(self) -> None:
        self._trial_elapsed += 1
        self.time_elapsed.emit(self._trial_elapsed)
        if self._in_discard and self._trial_elapsed >= self._discard_s:
            self._in_discard = False
        if self._trial_elapsed >= self._trial_duration_s:
            self._trial_timer.stop()
            self._end_item()

    def _end_item(self) -> None:
        self._in_discard = True
        self._records_by_item[self._item_position] = list(self._current_records)
        hits = sum(1 for _, was_correct in self._current_records if was_correct)
        self.item_finished.emit(self._current_item, hits, len(self._current_records))

        self._item_position += 1
        self._advance_item()

    def _finish(self) -> None:
        self._stop_run()
        try:
            threshold = sweep_thresholds(self._records_by_item, self._t_values, self._max_unresolved_fraction)
        except ValueError as error:
            self.calibration_failed.emit(str(error))
            return
        swept_threshold = threshold
        threshold = replace_null_threshold(threshold)

        summary = summarize_threshold(
            self._records_by_item, threshold, self._prefs.time_window, n_classes=self._n_classes
        )
        result = {
            "date": datetime.now().isoformat(timespec="seconds"),
            "seed": self._seed,
            "frequencies": [stim.freq for stim in self._prefs.stimulus],
            "item_order": list(self._item_order),
            "n_classes": self._n_classes,
            "time_window": self._prefs.time_window,
            "cue_duration_s": self._cue_duration_s,
            "trial_duration_s": self._trial_duration_s,
            "discard_s": self._discard_s,
            "max_unresolved_fraction": self._max_unresolved_fraction,
            "records_by_item": {position: list(records) for position, records in self._records_by_item.items()},
            "threshold": threshold,
            "swept_threshold": swept_threshold,  # el del barrido, antes de reemplazar un 0 por el por defecto
            "accuracy": summary["accuracy"],
            "unresolved_fraction": summary["unresolved_fraction"],
            "mean_decision_time_s": summary["mean_decision_time_s"],
            "itr": summary["itr"],
        }
        self.calibration_finished.emit(result)
