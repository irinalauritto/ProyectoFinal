"""Tests de "Guardar señales" y del reporte de la sesión (interfaz/eeg).

Corren sin hardware. Se puede correr con:

    python -m unittest discover -s tests -v

desde `interfaz_ssvep/`.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import numpy as np
from scipy.io import loadmat

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_THIS_DIR = Path(__file__).resolve().parent
for _path in (_THIS_DIR.parent, _THIS_DIR.parent.parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from interfaz.eeg.session_report import SessionLog, build_html, calibration_rows, write_pdf  # noqa: E402
from interfaz.eeg.signal_recorder import SignalRecorder  # noqa: E402
from ssvep.app.dataclasses import Stimulus, UserPreferences  # noqa: E402
from ssvep.app.eeg_signal_classifier import EEGSignalCCAClassifier  # noqa: E402
from ssvep.app.frequency_calibrator import FrequencyCalibrator  # noqa: E402

CALIBRATION = {
    "candidate_freqs": [8.0, 12.0, 16.0],
    "trials": [
        {"freq": 8.0, "repeticion": 1, "aciertos": 9, "ventanas": 10},
        {"freq": 8.0, "repeticion": 2, "aciertos": 9, "ventanas": 10},
        {"freq": 12.0, "repeticion": 2, "aciertos": 8, "ventanas": 10},
        {"freq": 12.0, "repeticion": 1, "aciertos": 9, "ventanas": 10},
        {"freq": 16.0, "repeticion": 1, "aciertos": 7, "ventanas": 10},
        {"freq": 16.0, "repeticion": 2, "aciertos": 6, "ventanas": 10},
    ],
    "accuracies": {8.0: 90.0, 12.0: 85.0, 16.0: 65.0},
    "selected": [8.0, 12.0],
    "anchor_freq": 17.0,
    "refresh_rate": 60,
}


class SignalRecorderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "senales" / "calibracion_1.mat"
        self.recorder = SignalRecorder()

    def tearDown(self):
        self._tmp.cleanup()

    def _load(self):
        return loadmat(str(self.path), simplify_cells=True)

    def test_saves_raw_signal_windows_events_and_result(self):
        self.recorder.begin("validacion", {"canales": ["O1", "Oz"], "umbral": None}, self.path)
        self.recorder.add_samples([[1, 2, 3], [10, 20, 30]])
        self.recorder.add_event("item", estimulo=2, numero=1)
        self.recorder.add_window(np.array([0.5, 0.2]), 0.6, 0, 0, True)
        self.recorder.add_samples([[4], [40]])
        saved = self.recorder.finish("completa", {"umbral_final": 0.3, "orden": [1, 2]})

        self.assertEqual(saved, self.path)
        data = self._load()
        np.testing.assert_array_equal(data["eeg"], [[0, 1, 10], [1, 2, 20], [2, 3, 30], [3, 4, 40]])
        self.assertEqual(data["estado"], "completa")
        self.assertEqual(data["etapa"], "validacion")
        self.assertEqual(data["ventanas"][0], 3)  # una sola fila: muestra al registrarla
        self.assertEqual(data["ventanas"][3], 0)
        np.testing.assert_array_equal(data["ventanas_rho"], [0.5, 0.2])
        self.assertEqual(data["eventos"]["tipo"], "item")
        self.assertEqual(data["eventos"]["estimulo"], 2)
        self.assertEqual(list(data["info"]["canales"]), ["O1", "Oz"])
        self.assertEqual(data["resultado"]["umbral_final"], 0.3)

    def test_nothing_is_saved_without_an_open_stage(self):
        self.recorder.add_samples([[1], [2]])
        self.recorder.add_event("item")
        self.assertIsNone(self.recorder.finish("completa"))
        self.assertFalse(self.path.exists())

    def test_stop_capture_keeps_stage_open_but_ignores_new_data(self):
        self.recorder.begin("validacion", {}, self.path)
        self.recorder.add_samples([[1], [2]])
        self.recorder.stop_capture()
        self.recorder.add_samples([[3], [4]])
        self.assertEqual(self.recorder.stage, "validacion")
        self.recorder.finish("completa")
        self.assertEqual(self._load()["eeg"].tolist(), [0, 1, 2])

    def test_stage_without_samples_can_be_saved(self):
        self.recorder.begin("online", {"canales": ["O1"]}, self.path)
        self.recorder.finish("cancelada")
        self.assertEqual(self._load()["estado"], "cancelada")


    def test_emg_signal_and_calculations(self):
        self.recorder.begin(
            "online", {"canales": ["EMG"]}, self.path, signal_name="emg", calculation_format="envolvente, activacion"
        )
        self.recorder.add_samples([[100, 200]])
        self.recorder.add_calculations([[1.5, 0.0], [2.5, 1.0]])
        self.recorder.finish("completa")
        data = self._load()
        np.testing.assert_array_equal(data["emg"], [[0, 100], [1, 200]])
        np.testing.assert_array_equal(data["calculos"], [[1.5, 0.0], [2.5, 1.0]])
        self.assertEqual(data["formato_calculos"], "envolvente, activacion")
        self.assertNotIn("eeg", data)
        self.assertNotIn("ventanas", data)


class ClassifierObserverTests(unittest.TestCase):
    def test_observer_gets_each_window_with_its_vote(self):
        clf = EEGSignalCCAClassifier()
        clf.load_threshold(0.3)
        seen = []
        clf.set_window_observer(lambda *args: seen.append(args))
        rho = np.array([0.9, 0.1, 0.1])
        results = [clf._validate_threshold(rho) for _ in range(3)]
        self.assertEqual(results, [-1, -1, 0])
        self.assertEqual([window[3] for window in seen], results)
        self.assertEqual(seen[0][2], 0)

        clf.set_window_observer(None)
        clf._validate_threshold(rho)
        self.assertEqual(len(seen), 3)


class CalibrationTableTests(unittest.TestCase):
    def test_rows_follow_accuracy_and_selection(self):
        rows = calibration_rows(CALIBRATION, {8.0: "Espacio", 12.0: "Derecha"})
        by_freq = {row["freq"]: row for row in rows}

        self.assertEqual(by_freq[12.0]["repeticiones"], [(9, 10), (8, 10)])
        self.assertEqual((by_freq[12.0]["aciertos"], by_freq[12.0]["ventanas"]), (17, 20))
        self.assertEqual(by_freq[12.0]["estimulo"], "Derecha")
        self.assertTrue(by_freq[8.0]["seleccionada"])
        self.assertEqual(by_freq[8.0]["colision"], [])
        self.assertFalse(by_freq[16.0]["seleccionada"])
        self.assertEqual(by_freq[16.0]["colision"], [8.0])  # 16 es el doble de 8
        self.assertIsNone(by_freq[16.0]["estimulo"])

    def test_calibrator_keeps_each_trial(self):
        viewer = mock.MagicMock()
        viewer.is_running.return_value = True
        calibrator = FrequencyCalibrator(
            viewer, {0: "O1", 1: "Oz", 2: "O2"}, 1, sample_rate=250.0, harmonics=2,
            candidate_freqs=(8.0,), n_repeats=1,
        )
        finished = []
        calibrator.calibration_finished.connect(finished.append)
        calibrator.start()
        calibrator._resting = False
        calibrator._in_discard = False
        for prediction in (0, 0, 1):
            calibrator.receive_classification(prediction)
        calibrator._end_trial()

        result = finished[0]
        self.assertEqual(result["trials"], [{"freq": 8.0, "repeticion": 1, "aciertos": 2, "ventanas": 3}])
        self.assertEqual(result["decisions"], [(8.0, 0, 0), (8.0, 0, 0), (8.0, 0, 1)])
        self.assertAlmostEqual(result["accuracies"][8.0], 200 / 3)


class ReportTests(unittest.TestCase):
    def _log(self):
        log = SessionLog(paciente="Ana <prueba>", inicio=datetime(2026, 11, 3, 10, 0), fin=datetime(2026, 11, 3, 11, 0))
        log.parametros = {
            "metodo": "Direccional",
            "umbral": 0.25,
            "canales": ["O1", "Oz", "O2"],
            "ventana_s": 1,
            "refractario_s": 5.0,
            "estimulos": [{"nombre": "Espacio", "freq": 12.0, "activo": True}],
        }
        log.calibraciones.append(
            {
                "hora": datetime(2026, 11, 3, 10, 5),
                "metodo": "Direccional",
                "ancla": 17.0,
                "refresco": 60,
                "filas": calibration_rows(CALIBRATION, {8.0: "Espacio", 12.0: "Derecha"}),
            }
        )
        log.validaciones.append(
            {
                "hora": datetime(2026, 11, 3, 10, 15),
                "metodo": "Direccional",
                "descartada": False,
                "umbral_barrido": 0.0,
                "umbral_calculado": 0.1,
                "umbral_final": 0.25,
                "exactitud": 83.3,
                "sin_resolver": 1 / 6,
                "itr": 12.5,
                "items": [[1, "Espacio", "acierto"], [2, "Derecha", "sin resolver"]],
            }
        )
        log.add_change("Umbral", "0.10", "0.25")
        log.estimulaciones_s.append(125.0)
        return log

    def test_html_has_every_section(self):
        html = build_html(self._log())
        for text in (
            "Ana &lt;prueba&gt;", "Rep. 2", "17/20", "85 %", "Con 8 Hz", "Umbral final", "0.25 (ajuste manual)",
            "reemplazado", "sin resolver", "Cambios manuales", "02:05",
        ):
            self.assertIn(text, html)

    def test_sections_say_when_there_was_nothing(self):
        html = build_html(SessionLog(paciente="Ana"))
        self.assertIn("No se realizó calibración", html)
        self.assertIn("No se realizó validación", html)
        self.assertIn("No hubo cambios manuales", html)

    def test_emg_report_has_its_own_sections(self):
        log = SessionLog(paciente="Ana", modalidad="EMG")
        log.parametros = {"filas": [["Tecla", "Enter"]]}
        log.calibraciones.append(
            {
                "hora": datetime(2026, 11, 3, 10, 5), "duracion_s": 30, "muestras": 15000, "media": 1.2, "sd": 0.3,
                "k": 5.0, "sensibilidad": 6.0, "umbral": 2.7, "reactivacion": 1.95,
            }
        )
        log.validaciones.append(
            {
                "hora": datetime(2026, 11, 3, 10, 7), "omitida": False, "intentos": [1, 2, 1], "correcta": False,
                "sensibilidad": 6.0, "refractario_ms": 300,
            }
        )
        log.validaciones.append({"hora": datetime(2026, 11, 3, 10, 9), "omitida": True})
        log.estimulaciones_s.append(65.0)
        html = build_html(log)
        for text in ("Sesión EMG", "Tecla", "1.20 mV", "15000", "2.70 mV", "Validación 2", "omitida", "Uso online", "01:05"):
            self.assertIn(text, html)

    def test_burst_on_same_parameter_is_one_change(self):
        log = SessionLog(paciente="Ana")
        log.add_change("Sensibilidad", "5.0", "5.1")
        log.add_change("Sensibilidad", "5.1", "5.2")
        self.assertEqual(len(log.cambios), 1)
        self.assertEqual((log.cambios[0]["anterior"], log.cambios[0]["nuevo"]), ("5.0", "5.2"))
        log.add_change("Sensibilidad", "5.2", "5.0")  # volvió al valor original
        self.assertEqual(log.cambios, [])

    def test_activity_detection(self):
        log = SessionLog(paciente="Ana")
        self.assertFalse(log.has_activity())
        log.add_change("Umbral", "0.10", "0.20")
        self.assertTrue(log.has_activity())

    def test_pdf_is_written(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        self.assertIsNotNone(app)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sesion.pdf"
            write_pdf(self._log(), path)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
