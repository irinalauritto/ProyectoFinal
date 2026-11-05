"""Verifica que el parpadeo salga a la frecuencia pedida, con cualquier refresco.

Se ejecuta desde `interfaz_ssvep/`: python -m unittest tests.test_stimulus_flicker
"""

import os
import sys
import unittest

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ssvep.app.stimulus_viewer import _StimulusFlicker  # noqa: E402


class _Fake:
    """Reemplaza a un estímulo de PsychoPy: anota el estado en cada cuadro."""

    def __init__(self, states, value):
        self.states, self.value = states, value

    def draw(self):
        self.states.append(self.value)


def _make_flicker(freq, refresh, theta, states, now):
    return _StimulusFlicker(
        _Fake(states, 1.0), _Fake(states, -1.0), freq, None, theta, refresh, clock=lambda: now[0]
    )


def _main_frequency(freq, refresh, theta=0.0, seconds=60):
    states, now = [], [0.0]
    flicker = _make_flicker(freq, refresh, theta, states, now)
    for _ in range(round(refresh * seconds)):
        flicker.draw()
        now[0] += 1 / refresh
    signal = np.array(states) - np.mean(states)
    power = np.abs(np.fft.rfft(signal)) ** 2
    return np.fft.rfftfreq(signal.size, 1 / refresh)[np.argmax(power)]


class FlickerFrequencyTests(unittest.TestCase):
    def test_all_stimuli_at_common_refresh_rates(self):
        for refresh in (59.94, 60, 119.88, 120, 144):
            for freq in (8, 8.5, 9, 9.5, 10, 10.5):
                with self.subTest(refresh=refresh, freq=freq):
                    self.assertAlmostEqual(_main_frequency(freq, refresh), freq, delta=0.05)

    def test_phase_does_not_change_frequency(self):
        self.assertAlmostEqual(_main_frequency(8.5, 120, theta=1.5), 8.5, delta=0.05)

    def test_lost_frames_do_not_lower_frequency(self):
        """Con 5 % de cuadros perdidos, la frecuencia media se mantiene."""
        refresh, freq, seconds = 120, 8.5, 60
        rng = np.random.default_rng(0)
        states, now = [], [0.0]
        flicker = _make_flicker(freq, refresh, 0.0, states, now)
        for _ in range(refresh * seconds):
            if rng.random() >= 0.05:
                flicker.draw()
            now[0] += 1 / refresh
        changes = np.count_nonzero(np.diff(states))
        self.assertAlmostEqual(changes / 2 / seconds, freq, delta=0.05)


if __name__ == "__main__":
    unittest.main()
