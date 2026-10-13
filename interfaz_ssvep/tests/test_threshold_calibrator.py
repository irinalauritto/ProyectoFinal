"""Tests unitarios de la Validación (cálculo automático del umbral).

Cubren las funciones puras de threshold_calibrator.py (compute_margin,
evaluate_threshold, sweep_thresholds, summarize_threshold), la exposición
del rho/margen crudo en el clasificador y la persistencia del campo
`threshold` a través de repositories.py. Corren sin hardware (la base de
datos es SQLite en memoria). Se puede correr con:

    python -m unittest discover -s tests -v

desde `interfaz_ssvep/`.
"""

import os
import sys
import unittest

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ssvep.app import eeg_signal_classifier  # noqa: E402
from ssvep.app.bci_evaluator import bits_per_trial, calculate_itr  # noqa: E402
from ssvep.app.dataclasses import DEFAULT_THRESHOLD, Stimulus, UserPreferences  # noqa: E402
from ssvep.app.eeg_signal_classifier import EEGSignalCCAClassifier  # noqa: E402
from ssvep.app.managers import PreferencesManager, UserManager  # noqa: E402
from ssvep.app.models import Base  # noqa: E402
from ssvep.app.repositories import PreferencesRepositorySQLAlchemy, UserRepositorySQLAlchemy  # noqa: E402
from ssvep.app.threshold_calibrator import (  # noqa: E402
    build_item_sequence,
    replace_null_threshold,
    compute_margin,
    evaluate_threshold,
    summarize_threshold,
    sweep_thresholds,
)

T_VALUES = [i / 100.0 for i in range(0, 101)]

# Secuencias fabricadas: 6 ítems, ventanas en orden temporal (margen, fue_correcta).
# - Los ítems 0 a 3 aciertan desde la primera ventana, con margen claro.
# - El ítem 4 arranca con una ventana ruidosa INCORRECTA de margen bajo
#   (0.12) y recién después acierta con margen alto.
# - El ítem 5 es débil: acierta, pero nunca pasa de 0.35.
RECORDS = {
    0: [(0.50, True), (0.55, True), (0.60, True)],
    1: [(0.45, True), (0.52, True), (0.48, True)],
    2: [(0.62, True), (0.40, True), (0.58, True)],
    3: [(0.41, True), (0.47, True), (0.66, True)],
    4: [(0.12, False), (0.44, True), (0.51, True)],
    5: [(0.30, True), (0.35, True), (0.28, True)],
}


class ComputeMarginTests(unittest.TestCase):
    def test_is_the_function_factored_out_of_the_classifier(self):
        # No es una reimplementación: es la misma función que usa _validate_threshold.
        self.assertIs(compute_margin, eeg_signal_classifier.compute_margin)

    def test_known_vector(self):
        # (0.6 - 0.1) / (0.6 + 0.2 + 0.1 - 0.1) = 0.5 / 0.8
        self.assertAlmostEqual(compute_margin(np.array([0.6, 0.2, 0.1])), 0.625)

    def test_two_targets_with_null_loser_gives_one(self):
        self.assertAlmostEqual(compute_margin([0.8, 0.0]), 1.0)

    def test_two_targets_general(self):
        # (0.9 - 0.3) / (1.2 - 0.3)
        self.assertAlmostEqual(compute_margin([0.9, 0.3]), 0.6 / 0.9)

    def test_all_equal_gives_zero(self):
        self.assertEqual(compute_margin([0.4, 0.4, 0.4]), 0.0)

    def test_non_positive_denominator_gives_zero(self):
        self.assertEqual(compute_margin([0.7]), 0.0)  # un único objetivo: 0/0
        self.assertEqual(compute_margin([0.0, 0.0, 0.0]), 0.0)

    def test_order_does_not_matter(self):
        self.assertAlmostEqual(compute_margin([0.1, 0.6, 0.2]), compute_margin([0.6, 0.2, 0.1]))

    def test_returns_python_float(self):
        self.assertIsInstance(compute_margin(np.array([0.6, 0.2, 0.1])), float)


class ClassifierRawDecisionTests(unittest.TestCase):
    FS = 250.0
    FREQS = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5]

    def setUp(self):
        self.clf = EEGSignalCCAClassifier()
        prefs = UserPreferences(
            classification_method="CCA",
            time_window=1,
            channels={0: "O1", 1: "Oz", 2: "O2"},
            stimulus=[Stimulus(f, 0.0, "flic", "square") for f in self.FREQS],
            stimulus_on=[True] * 6,
        )
        self.clf.load_data(self.FS, prefs, 2)

    def _sinusoid(self, freq):
        t = np.arange(int(self.FS)) / self.FS
        rng = np.random.default_rng(0)
        base = np.sin(2 * np.pi * freq * t)
        return np.vstack([base + 0.05 * rng.standard_normal(base.size) for _ in range(3)])

    def test_nothing_exposed_before_first_window(self):
        self.assertEqual(self.clf.last_raw_decision(), (0, None, None, None))
        self.assertIsNone(self.clf.last_rho)
        self.assertIsNone(self.clf.last_margin)

    def test_exposes_rho_and_margin_of_last_window(self):
        self.clf.load_threshold(0.0)
        result = self.clf.classify_signal(self._sinusoid(9.5))

        count, rho, margin, stim_id = self.clf.last_raw_decision()
        self.assertEqual(result, 3)  # el valor devuelto no cambia
        self.assertEqual(count, 1)
        self.assertEqual(stim_id, 3)
        self.assertEqual(rho.shape, (6,))
        self.assertEqual(int(np.argmax(rho)), 3)
        self.assertAlmostEqual(margin, compute_margin(rho))
        np.testing.assert_array_equal(self.clf.last_rho, rho)
        self.assertEqual(self.clf.last_margin, margin)

    def test_exposed_even_when_threshold_rejects_the_window(self):
        # Umbral inalcanzable: el clasificador devuelve -1, pero el rho y el
        # margen crudos de esa ventana quedan igual a disposición.
        self.clf.load_threshold(2.0)
        self.assertEqual(self.clf.classify_signal(self._sinusoid(9.5)), -1)
        _count, _rho, margin, stim_id = self.clf.last_raw_decision()
        self.assertEqual(stim_id, 3)
        self.assertGreater(margin, 0.0)

    def test_counter_advances_per_window(self):
        self.clf.classify_signal(self._sinusoid(8.0))
        self.clf.classify_signal(self._sinusoid(10.5))
        count, _rho, _margin, stim_id = self.clf.last_raw_decision()
        self.assertEqual(count, 2)
        self.assertEqual(stim_id, 5)

    def test_active_threshold_still_needs_three_of_four_votes(self):
        # Mismo comportamiento de producción que antes de factorizar el margen.
        self.clf.load_threshold(0.05)
        window = self._sinusoid(9.0)
        results = [self.clf.classify_signal(window) for _ in range(3)]
        self.assertEqual(results, [-1, -1, 2])


class BuildItemSequenceTests(unittest.TestCase):
    MODES = {"barrido": [0, 1], "secuencial": [0, 1, 2, 4], "direccional": [0, 1, 2, 3, 4, 5]}

    def test_every_mode_has_six_items(self):
        import random

        for name, active in self.MODES.items():
            for seed in range(50):
                with self.subTest(mode=name, seed=seed):
                    sequence = build_item_sequence(active, 6, random.Random(seed))
                    self.assertEqual(len(sequence), 6)
                    self.assertEqual(set(sequence), set(active))  # todos los activos, solo activos

    def test_repetitions_are_as_even_as_possible(self):
        import random
        from collections import Counter

        for seed in range(50):
            barrido = Counter(build_item_sequence([0, 1], 6, random.Random(seed)))
            self.assertEqual(sorted(barrido.values()), [3, 3])
            secuencial = Counter(build_item_sequence([0, 1, 2, 4], 6, random.Random(seed)))
            self.assertEqual(sorted(secuencial.values()), [1, 1, 2, 2])
            direccional = Counter(build_item_sequence(list(range(6)), 6, random.Random(seed)))
            self.assertEqual(sorted(direccional.values()), [1] * 6)

    def test_same_stimulus_is_not_asked_twice_in_a_row(self):
        import random

        for active in self.MODES.values():
            for seed in range(50):
                sequence = build_item_sequence(active, 6, random.Random(seed))
                self.assertTrue(all(a != b for a, b in zip(sequence, sequence[1:])), sequence)

    def test_same_seed_gives_same_sequence(self):
        import random

        first = build_item_sequence([0, 1, 2, 4], 6, random.Random(3))
        self.assertEqual(first, build_item_sequence([0, 1, 2, 4], 6, random.Random(3)))

    def test_more_active_stimuli_than_minimum_keeps_them_all(self):
        import random

        self.assertEqual(sorted(build_item_sequence(list(range(8)), 6, random.Random(0))), list(range(8)))


class EvaluateThresholdTests(unittest.TestCase):
    def test_takes_first_window_over_threshold_not_the_average(self):
        # La primera ventana >= T es incorrecta; las siguientes, correctas.
        records = {0: [(0.30, False), (0.80, True), (0.90, True)]}
        self.assertEqual(evaluate_threshold(records, 0.2).accuracy, 0.0)
        # Subiendo T, la primera que lo supera pasa a ser la segunda (correcta).
        outcome = evaluate_threshold(records, 0.5)
        self.assertEqual(outcome.accuracy, 100.0)
        self.assertEqual(outcome.mean_windows_to_decision, 2.0)

    def test_item_without_any_window_over_threshold_is_unresolved(self):
        outcome = evaluate_threshold(RECORDS, 0.40)
        self.assertAlmostEqual(outcome.unresolved_fraction, 1 / 6)  # solo el ítem 5
        self.assertEqual(outcome.accuracy, 100.0)  # entre los 5 resueltos

    def test_accuracy_is_among_resolved_items_only(self):
        records = {0: [(0.9, True)], 1: [(0.9, False)], 2: [(0.1, True)]}
        outcome = evaluate_threshold(records, 0.5)
        self.assertAlmostEqual(outcome.unresolved_fraction, 1 / 3)
        self.assertEqual(outcome.accuracy, 50.0)

    def test_nothing_resolved(self):
        outcome = evaluate_threshold(RECORDS, 0.99)
        self.assertEqual(outcome, (1.0, 0.0, 0.0))

    def test_item_without_windows_counts_as_unresolved(self):
        outcome = evaluate_threshold({0: [(0.5, True)], 1: []}, 0.0)
        self.assertEqual(outcome.unresolved_fraction, 0.5)

    def test_empty_records(self):
        self.assertEqual(evaluate_threshold({}, 0.1).unresolved_fraction, 1.0)


class SweepThresholdsTests(unittest.TestCase):
    def test_very_low_threshold_accepts_a_noisy_wrong_window(self):
        # T = 0.10 resuelve los 6, pero al ítem 4 lo resuelve con su primera
        # ventana (0.12, incorrecta): 5/6.
        outcome = evaluate_threshold(RECORDS, 0.10)
        self.assertEqual(outcome.unresolved_fraction, 0.0)
        self.assertAlmostEqual(outcome.accuracy, 5 / 6 * 100.0)

    def test_reasonable_threshold_resolves_everything_correctly(self):
        outcome = evaluate_threshold(RECORDS, 0.25)
        self.assertEqual(outcome.unresolved_fraction, 0.0)
        self.assertEqual(outcome.accuracy, 100.0)

    def test_very_high_threshold_leaves_several_items_unresolved(self):
        # T = 0.60: solo los ítems 0, 2 y 3 tienen alguna ventana que llegue.
        outcome = evaluate_threshold(RECORDS, 0.60)
        self.assertAlmostEqual(outcome.unresolved_fraction, 3 / 6)
        self.assertEqual(outcome.accuracy, 100.0)

    def test_low_threshold_loses_against_a_better_one(self):
        self.assertAlmostEqual(sweep_thresholds(RECORDS, [0.10, 0.25]), 0.25)

    def test_high_threshold_is_discarded_despite_perfect_accuracy(self):
        # 0.60 tiene 100% entre los resueltos, pero deja 50% sin resolver.
        self.assertAlmostEqual(sweep_thresholds(RECORDS, [0.10, 0.60]), 0.10)

    def test_full_sweep_picks_lowest_threshold_with_best_accuracy(self):
        # 100% recién se alcanza cuando T supera la ventana ruidosa (0.12);
        # de ahí en más hay empate y gana el T más bajo.
        self.assertAlmostEqual(sweep_thresholds(RECORDS, T_VALUES), 0.13)

    def test_tie_goes_to_lowest_threshold_regardless_of_input_order(self):
        self.assertAlmostEqual(sweep_thresholds(RECORDS, [0.35, 0.20, 0.30, 0.25]), 0.20)

    def test_unresolved_fraction_exactly_at_the_limit_is_kept(self):
        # 5 ítems, 1 sin resolver = 20% justo: no supera el máximo.
        records = {i: [(0.9, True)] for i in range(4)}
        records[4] = [(0.1, True)]
        self.assertAlmostEqual(sweep_thresholds(records, [0.5], max_unresolved_fraction=0.2), 0.5)

    def test_max_unresolved_fraction_is_configurable(self):
        self.assertAlmostEqual(sweep_thresholds(RECORDS, [0.10, 0.60], max_unresolved_fraction=0.5), 0.60)

    def test_no_surviving_threshold_raises(self):
        with self.assertRaises(ValueError):
            sweep_thresholds(RECORDS, [0.60, 0.90])

    def test_empty_records_raise(self):
        with self.assertRaises(ValueError):
            sweep_thresholds({}, T_VALUES)


class ReplaceNullThresholdTests(unittest.TestCase):
    def test_zero_becomes_the_default(self):
        self.assertEqual(replace_null_threshold(0.0), DEFAULT_THRESHOLD)
        self.assertEqual(DEFAULT_THRESHOLD, 0.1)

    def test_non_zero_is_kept_even_below_the_default(self):
        self.assertEqual(replace_null_threshold(0.03), 0.03)
        self.assertEqual(replace_null_threshold(0.13), 0.13)

    def test_all_first_windows_correct_ends_at_the_default(self):
        # Caso que motiva la regla: todo acierta de entrada, el barrido da 0.
        records = {i: [(0.5, True), (0.6, True)] for i in range(6)}
        swept = sweep_thresholds(records, T_VALUES)
        self.assertEqual(swept, 0.0)
        self.assertEqual(replace_null_threshold(swept), 0.1)


class SummarizeThresholdTests(unittest.TestCase):
    def test_accuracy_and_itr_at_threshold(self):
        summary = summarize_threshold(RECORDS, 0.25, window_s=2.0)
        # Todos resueltos con la 1ra ventana salvo el ítem 4 (2da): 7/6 ventanas.
        self.assertEqual(summary["accuracy"], 100.0)
        self.assertEqual(summary["unresolved_fraction"], 0.0)
        self.assertAlmostEqual(summary["mean_decision_time_s"], 7 / 6 * 2.0)
        self.assertAlmostEqual(summary["itr"], calculate_itr(1.0, 6, 7 / 6 * 2.0))

    def test_itr_uses_shared_wolpaw_helper(self):
        summary = summarize_threshold(RECORDS, 0.10, window_s=1.0)
        expected = bits_per_trial(5 / 6, 6) * 60.0
        self.assertAlmostEqual(summary["itr"], expected)

    def test_nothing_resolved_gives_zero_itr(self):
        self.assertEqual(summarize_threshold(RECORDS, 0.99, window_s=1.0)["itr"], 0.0)


class ThresholdPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.users = UserManager(UserRepositorySQLAlchemy(self.session))
        self.prefs = PreferencesManager(PreferencesRepositorySQLAlchemy(self.session))
        self.user_id = self.users.register_new_user("Prueba").id

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _prefs(self, **kwargs):
        return UserPreferences(
            classification_method="CCA",
            time_window=2.0,
            channels={0: "O1", 1: "Oz", 2: "O2"},
            stimulus=[Stimulus(8.0 + i, 0.0, "flic", "square") for i in range(6)],
            stimulus_on=[True] * 6,
            **kwargs,
        )

    def test_threshold_is_saved_and_recovered(self):
        self.prefs.save_or_update_preferences(self.user_id, self._prefs(threshold=0.27))
        self.assertAlmostEqual(self.prefs.get_user_preferences(self.user_id).threshold, 0.27)

    def test_threshold_is_updated(self):
        self.prefs.save_or_update_preferences(self.user_id, self._prefs(threshold=0.27))
        self.prefs.save_or_update_preferences(self.user_id, self._prefs(threshold=0.41))
        self.session.expire_all()  # fuerza a releer de la base, no del caché de la sesión
        self.assertAlmostEqual(self.prefs.get_user_preferences(self.user_id).threshold, 0.41)

    def test_default_threshold_when_not_specified(self):
        self.prefs.save_or_update_preferences(self.user_id, self._prefs())
        self.assertAlmostEqual(self.prefs.get_user_preferences(self.user_id).threshold, DEFAULT_THRESHOLD)

    def test_other_fields_are_not_affected(self):
        self.prefs.save_or_update_preferences(self.user_id, self._prefs(threshold=0.33))
        loaded = self.prefs.get_user_preferences(self.user_id)
        self.assertEqual([s.freq for s in loaded.stimulus], [8.0, 9.0, 10.0, 11.0, 12.0, 13.0])
        self.assertEqual(loaded.channels, {0: "O1", 1: "Oz", 2: "O2"})


class ThresholdColumnMigrationTests(unittest.TestCase):
    """Una base creada antes de que existiera el campo no tiene la columna."""

    OLD_SCHEMA = """
        CREATE TABLE preferences (
            user_id INTEGER NOT NULL,
            classification_method VARCHAR(50) NOT NULL,
            time_windows FLOAT NOT NULL,
            stim_frequency VARCHAR(1000) NOT NULL,
            stim_shape VARCHAR(1000) NOT NULL,
            channels VARCHAR(1000) NOT NULL,
            stim_on VARCHAR(1000) NOT NULL,
            stim_theta VARCHAR(1000) NOT NULL,
            stim_type VARCHAR(1000) NOT NULL,
            stim_direction VARCHAR(1000) NOT NULL,
            PRIMARY KEY (user_id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """

    def test_existing_database_gets_the_column_with_the_default(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(255) NOT NULL)"))
            conn.execute(text(self.OLD_SCHEMA))
            conn.execute(text("INSERT INTO users (id, name) VALUES (1, 'Viejo')"))
            conn.execute(text(
                "INSERT INTO preferences VALUES (1, 'CCA', 2.0, '[8.0, 9.0]', '[\"square\", \"circle\"]', "
                "'{\"0\": \"O1\"}', '[true, true]', '[0.0, 0.0]', '[\"flic\", \"flic\"]', '[null, null]')"
            ))
        session = sessionmaker(bind=engine)()
        try:
            prefs = PreferencesManager(PreferencesRepositorySQLAlchemy(session))
            loaded = prefs.get_user_preferences(1)
            self.assertAlmostEqual(loaded.threshold, DEFAULT_THRESHOLD)
            self.assertEqual([s.freq for s in loaded.stimulus], [8.0, 9.0])

            loaded.threshold = 0.22
            prefs.save_or_update_preferences(1, loaded)
            session.expire_all()
            self.assertAlmostEqual(prefs.get_user_preferences(1).threshold, 0.22)

            # Crear de nuevo el repositorio sobre la base ya migrada no falla.
            PreferencesRepositorySQLAlchemy(session)
        finally:
            session.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
