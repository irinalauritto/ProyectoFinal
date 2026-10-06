"""Tests de que EEGSignalCCAClassifier solo clasifica los estímulos ACTIVOS
de la última carga (`load_data`).

Antes, `load_data` solo agregaba referencias a `_reference_signals` sin
borrar las de cargas anteriores: al cambiar los estímulos activos sobre la
misma instancia (ej. de Direccional a Barrido) los que quedaban inactivos
seguían siendo candidatos. Corren sin Qt ni hardware:

    python -m unittest discover -s tests -v

desde `interfaz_ssvep/`.
"""

import os
import sys
import unittest

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ssvep.app.dataclasses import Stimulus, UserPreferences  # noqa: E402
from ssvep.app.eeg_signal_classifier import EEGSignalCCAClassifier  # noqa: E402

FS = 250.0
FREQS = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5]  # mismo espaciado que Settings.__stimuli_config
CHANNELS = {0: "O1", 1: "Oz", 2: "O2"}


def _prefs(stimulus_on):
    return UserPreferences(
        classification_method="CCA",
        time_window=1,
        channels=dict(CHANNELS),
        stimulus=[Stimulus(f, 0.0, "flic", "square") for f in FREQS],
        stimulus_on=list(stimulus_on),
    )


def _sinusoid(freq):
    """Ventana de 1s, 3 canales, con una sinusoide pura a `freq`."""
    t = np.arange(int(FS)) / FS
    base = np.sin(2 * np.pi * freq * t)
    rng = np.random.default_rng(0)
    return np.vstack([base + 0.05 * rng.standard_normal(base.size) for _ in CHANNELS])


class ActiveStimuliOnlyTests(unittest.TestCase):
    def setUp(self):
        self.clf = EEGSignalCCAClassifier()
        self.clf.load_threshold(0.0)  # decisión cruda: siempre devuelve el mejor candidato

    def test_all_active_can_return_any_stimulus(self):
        self.clf.load_data(FS, _prefs([True] * 6), 2)
        self.assertEqual(self.clf.classify_signal(_sinusoid(9.5)), 3)

    def test_inactive_stimulus_is_never_returned_after_reload_on_same_instance(self):
        # Mismo orden que en la app: primero todos activos, después un modo
        # con menos estímulos (Barrido: solo 0 y 1) sobre la MISMA instancia.
        self.clf.load_data(FS, _prefs([True] * 6), 2)
        self.clf.load_data(FS, _prefs([True, True, False, False, False, False]), 2)

        self.assertEqual(sorted(self.clf._reference_signals.keys()), [0, 1])
        for freq in FREQS:
            self.assertIn(self.clf.classify_signal(_sinusoid(freq)), (0, 1), f"freq={freq}")

    def test_secuencial_subset_with_non_contiguous_indices(self):
        self.clf.load_data(FS, _prefs([True] * 6), 2)
        self.clf.load_data(FS, _prefs([False, True, True, False, True, False]), 2)

        self.assertEqual(sorted(self.clf._reference_signals.keys()), [1, 2, 4])
        for freq in FREQS:
            self.assertIn(self.clf.classify_signal(_sinusoid(freq)), (1, 2, 4), f"freq={freq}")
        # Una señal justo en la frecuencia de un activo se clasifica como ese activo.
        self.assertEqual(self.clf.classify_signal(_sinusoid(FREQS[2])), 2)

    def test_reloading_with_a_changed_frequency_uses_the_new_one(self):
        prefs = _prefs([True, True, False, False, False, False])
        self.clf.load_data(FS, prefs, 2)
        prefs.stimulus[1].freq = 12.0
        self.clf.load_data(FS, prefs, 2)
        self.assertEqual(self.clf.classify_signal(_sinusoid(12.0)), 1)

    def test_going_back_to_a_larger_set_reactivates_stimuli(self):
        self.clf.load_data(FS, _prefs([True, True, False, False, False, False]), 2)
        self.clf.load_data(FS, _prefs([True] * 6), 2)
        self.assertEqual(sorted(self.clf._reference_signals.keys()), [0, 1, 2, 3, 4, 5])
        self.assertEqual(self.clf.classify_signal(_sinusoid(10.5)), 5)


if __name__ == "__main__":
    unittest.main()
