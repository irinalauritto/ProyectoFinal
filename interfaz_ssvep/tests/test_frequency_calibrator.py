"""Tests unitarios de las funciones puras de frequency_calibrator.py.

Corren sin Qt, sin hardware y sin base de datos -- solo importan las
funciones de análisis (collides, compute_candidate_accuracies,
select_final_frequencies). Se puede correr con:

    python -m unittest discover -s tests -v

desde `interfaz_ssvep/` (el bootstrap de sys.path de abajo agrega la raíz
del paquete `ssvep` para que el import funcione sin instalar nada).
"""

import os
import sys
import unittest

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ssvep.app.frequency_calibrator import (  # noqa: E402
    collides,
    compute_candidate_accuracies,
    select_final_frequencies,
)

CANDIDATE_FREQS = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]


class CollidesTests(unittest.TestCase):
    def test_8_and_16_collide(self):
        self.assertTrue(collides(8, 16))

    def test_16_and_8_collide_symmetric(self):
        self.assertTrue(collides(16, 8))

    def test_no_false_positives_among_8_to_16(self):
        for i, f1 in enumerate(CANDIDATE_FREQS):
            for f2 in CANDIDATE_FREQS[i + 1 :]:
                if (f1, f2) == (8.0, 16.0):
                    continue
                with self.subTest(f1=f1, f2=f2):
                    self.assertFalse(collides(f1, f2), f"{f1} y {f2} no deberían colisionar")

    def test_anchor_never_collides_with_candidates(self):
        for f in CANDIDATE_FREQS:
            with self.subTest(f=f):
                self.assertFalse(collides(f, 17.0))

    def test_identical_frequency_collides(self):
        # k=1 siempre coincide consigo misma -- caso degenerado pero correcto.
        self.assertTrue(collides(10.0, 10.0))

    def test_third_harmonic_not_collision_with_default_order(self):
        # 8 * 3 = 24: con n_harmonics=2 (default) no debe contar.
        self.assertFalse(collides(8.0, 24.0))

    def test_third_harmonic_collides_with_higher_order(self):
        self.assertTrue(collides(8.0, 24.0, n_harmonics=3))

    def test_zero_or_negative_never_collides(self):
        self.assertFalse(collides(0.0, 10.0))
        self.assertFalse(collides(-8.0, 16.0))


class ComputeCandidateAccuraciesTests(unittest.TestCase):
    def test_all_hits(self):
        decisions = [(10.0, 0, 0)] * 5
        self.assertEqual(compute_candidate_accuracies(decisions), {10.0: 100.0})

    def test_all_misses(self):
        decisions = [(10.0, 0, 1)] * 5
        self.assertEqual(compute_candidate_accuracies(decisions), {10.0: 0.0})

    def test_mixed_single_candidate(self):
        # 3 aciertos de 4 -> 75%
        decisions = [(10.0, 0, 0), (10.0, 0, 0), (10.0, 0, 0), (10.0, 0, 1)]
        self.assertAlmostEqual(compute_candidate_accuracies(decisions)[10.0], 75.0)

    def test_multiple_candidates_independent(self):
        decisions = [
            (8.0, 0, 0), (8.0, 0, 0),          # 8.0: 2/2 = 100%
            (9.0, 0, 1), (9.0, 0, 0),          # 9.0: 1/2 = 50%
        ]
        result = compute_candidate_accuracies(decisions)
        self.assertAlmostEqual(result[8.0], 100.0)
        self.assertAlmostEqual(result[9.0], 50.0)

    def test_empty_decisions(self):
        self.assertEqual(compute_candidate_accuracies([]), {})

    def test_aggregates_across_repeats(self):
        # Simula 3 repeticiones de la misma candidata con distintos resultados:
        # repeat 1: 2 aciertos, 0 fallos; repeat 2: 1/2; repeat 3: 0/2 -> total 3/6 = 50%
        decisions = (
            [(12.0, 0, 0)] * 2
            + [(12.0, 0, 0), (12.0, 0, 1)]
            + [(12.0, 0, 1)] * 2
        )
        self.assertAlmostEqual(compute_candidate_accuracies(decisions)[12.0], 50.0)


class SelectFinalFrequenciesTests(unittest.TestCase):
    def test_picks_highest_accuracy_first(self):
        accuracies = {8.0: 90.0, 9.0: 95.0, 10.0: 50.0}
        selected = select_final_frequencies(accuracies, n_final=2)
        self.assertEqual(selected, [9.0, 8.0])

    def test_limits_to_n_final(self):
        accuracies = {f: 100.0 - f for f in CANDIDATE_FREQS}  # todas sin colision entre si excepto 8/16
        selected = select_final_frequencies(accuracies, n_final=6)
        self.assertEqual(len(selected), 6)

    def test_8_and_16_never_both_selected(self):
        # 16 con mejor exactitud que 8 -> se descarta 8 (menor exactitud del par).
        accuracies = {8.0: 60.0, 16.0: 90.0, 9.0: 80.0, 10.0: 70.0, 11.0: 65.0, 12.0: 55.0, 13.0: 50.0}
        selected = select_final_frequencies(accuracies, n_final=6)
        self.assertFalse({8.0, 16.0}.issubset(set(selected)))
        self.assertIn(16.0, selected)  # la de mayor exactitud del par colisionante se mantiene

    def test_8_and_16_never_both_selected_reverse_accuracy(self):
        # Mismo test con las exactitudes invertidas: ahora 8 gana el par.
        accuracies = {8.0: 90.0, 16.0: 60.0, 9.0: 80.0, 10.0: 70.0, 11.0: 65.0, 12.0: 55.0, 13.0: 50.0}
        selected = select_final_frequencies(accuracies, n_final=6)
        self.assertFalse({8.0, 16.0}.issubset(set(selected)))
        self.assertIn(8.0, selected)

    def test_full_candidate_set_never_yields_8_and_16_together(self):
        # Barrido completo de 8 a 16, con exactitud aleatoria fija (semilla),
        # nunca deberian quedar 8 Y 16 juntas en el resultado final.
        import random

        rng = random.Random(0)
        for _ in range(50):
            accuracies = {f: rng.uniform(0, 100) for f in CANDIDATE_FREQS}
            selected = select_final_frequencies(accuracies, n_final=6)
            self.assertFalse(
                {8.0, 16.0}.issubset(set(selected)),
                f"8 y 16 no deberian quedar juntas (accuracies={accuracies}, selected={selected})",
            )

    def test_fewer_candidates_than_n_final_returns_all_non_colliding(self):
        accuracies = {8.0: 90.0, 16.0: 80.0}
        selected = select_final_frequencies(accuracies, n_final=6)
        # Solo una de las dos puede quedar (colisionan entre si).
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected, [8.0])

    def test_empty_accuracies_returns_empty(self):
        self.assertEqual(select_final_frequencies({}, n_final=6), [])


if __name__ == "__main__":
    unittest.main()
