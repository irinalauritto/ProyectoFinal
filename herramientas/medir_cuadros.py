"""
Mide si el estimulador SSVEP pierde cuadros, sin paciente ni EEG.

Usa el estimulador real de la app (StimulusViewer y su bucle de dibujo, en su
propio proceso), la misma AsTeRICS con barrido y el mismo grabador. Solo envuelve
`win.flip()` para anotar el instante de cada cuadro. Compara, en rondas:

  * solo: únicamente el estimulador.
  * asterics: estimulador + AsTeRICS con barrido.
  * grabacion: estimulador + AsTeRICS con barrido + grabación.

Antes corre un control positivo: pierde cuadros a propósito y verifica que el
detector los encuentre. Si falla, las demás mediciones no valen.

Limitaciones (qué NO mide):
  * Ve cuándo el programa entrega cada cuadro, no cuándo aparece en el monitor:
    un cuadro descartado después por Windows o por el monitor no se detecta. Para
    eso está la filmación.
  * No corre adquisición, clasificador ni voz: no reproduce toda la carga de una
    sesión real.
  * Vale para esta PC, estos estímulos y la duración medida.

Uso (desde la raíz del repositorio, sin tocar la PC durante la prueba). Tarda unos
10 minutos; alcanza para comparar configuraciones, no para descartar pérdidas raras
(para eso, subir --segundos):
    interfaz/.venv/Scripts/python.exe herramientas/medir_cuadros.py

Resultados: senales/medicion_cuadros/<fecha>/ (resumen.txt, resumen.csv, tiempos
de cada condición y los videos). La pantalla parpadea durante toda la prueba.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for _p in (REPO, REPO / "interfaz_ssvep", REPO / "interfaz_emg"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np

import ssvep.app  # noqa: F401  carga SETTINGS en builtins, como la app
from ssvep.app import stimulus_viewer as sv

ENV_SALIDA = "MEDIR_CUADROS_SALIDA"
ENV_INYECTAR = "MEDIR_CUADROS_INYECTAR_CADA_S"

UMBRAL_PERDIDO = 1.5  # intervalo mayor a esto x período = cuadro perdido
DESCARTE_INICIAL_S = 2.0  # lo primero tras arrancar no es representativo
PERFIL = "medicion_cuadros"  # perfil propio: no toca los de los pacientes
DURACION_CONTROL_S = 30
INYECTAR_CADA_S = 3.0
PRUEBA_ASTERICS_TIMEOUT_S = 180


# ---------------------------------------------------------------------------
# Proceso del estimulador (mismo recorrido que sv._stimulus_process)
# ---------------------------------------------------------------------------

def _proceso_medido(
    config, stop_event, ready_event, hwnd_queue, check_on, check_off,
    timestamp_queue, selected_index, start_flicker_event,
) -> None:
    salida = Path(os.environ[ENV_SALIDA])
    inyectar_cada = float(os.environ.get(ENV_INYECTAR) or 0)

    refresco_usado = {}
    original_get_refresh = sv._get_refresh_rate

    def get_refresh(win):
        valor = original_get_refresh(win)
        refresco_usado["hz"] = valor
        return valor

    sv._get_refresh_rate = get_refresh

    win = sv._create_window(config)
    hwnd_queue.put(win.winHandle._hwnd)
    win.setMouseVisible(True)
    flickers = sv._create_flickers(win, config)
    frames = sv._create_stimulus_frames(win, config)
    sv._draw_static_stimuli(flickers, frames, win)
    ready_event.set()

    tiempos: list[float] = []
    inyectados: list[float] = []
    proxima = [None]
    flip_original = win.flip
    periodo = 1 / (refresco_usado.get("hz") or 60)

    def flip(*args, **kwargs):
        midiendo = start_flicker_event.is_set()
        if midiendo and inyectar_cada:
            ahora = time.perf_counter()
            if proxima[0] is None:
                proxima[0] = ahora + DESCARTE_INICIAL_S + inyectar_cada
            elif ahora >= proxima[0]:
                time.sleep(2.5 * periodo)  # hace perder cuadros a propósito
                inyectados.append(time.perf_counter())
                proxima[0] = ahora + inyectar_cada
        resultado = flip_original(*args, **kwargs)
        if midiendo:
            tiempos.append(time.perf_counter())
        return resultado

    win.flip = flip
    sv._main_render_loop(
        win, flickers, frames, stop_event, check_on, check_off,
        start_flicker_event, selected_index, config, timestamp_queue,
    )
    np.save(salida.with_suffix(".npy"), np.array(tiempos))
    salida.with_suffix(".json").write_text(
        json.dumps({"refresco_usado": refresco_usado.get("hz"), "inyectados": inyectados}),
        encoding="utf-8",
    )
    win.close()


# ---------------------------------------------------------------------------
# Análisis
# ---------------------------------------------------------------------------

def analizar(tiempos: np.ndarray, inyectados=()) -> dict:
    """Cuenta cuadros perdidos a partir de los instantes de cada cuadro."""
    tiempos = tiempos[tiempos >= tiempos[0] + DESCARTE_INICIAL_S]
    dt = np.diff(tiempos)
    mediana = float(np.median(dt))
    largos = dt[dt > UMBRAL_PERDIDO * mediana]
    perdidos = int(np.round(largos / mediana).sum() - largos.size)
    duracion = float(tiempos[-1] - tiempos[0])
    # Una pérdida provocada aparece en el intervalo que contiene ese instante.
    indices = np.searchsorted(tiempos, inyectados)
    detectados = sum(1 for i in indices if 0 < i < tiempos.size and dt[i - 1] > UMBRAL_PERDIDO * mediana)
    return {
        "cuadros": int(dt.size),
        "duracion_s": duracion,
        "periodo_ms": mediana * 1000,
        "hz_medidos": (dt.size + perdidos) / duracion,
        "inyectados": len(inyectados),
        "detectados": detectados,
        "eventos": int(largos.size),
        "perdidos": perdidos,
        "max_ms": float(dt.max() * 1000),
        "p99_9_ms": float(np.percentile(dt, 99.9) * 1000),
        "rapidos": int((dt < 0.5 * mediana).sum()),
    }


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------

class Prueba:
    def __init__(self, carpeta: Path, segundos: int):
        from PySide6.QtWidgets import QApplication, QWidget

        from interfaz.shell import asterics_config as cfg
        from interfaz.shell.asterics_launcher import (
            AstericsLauncher, monitor_work_areas, patient_monitor_index,
            patient_monitor_is_secondary, place_in_rect,
        )
        from interfaz.shell.screen_recorder import ScreenRecorder

        self.app = QApplication.instance() or QApplication([])
        self.carpeta = carpeta
        self.segundos = segundos
        self._areas = monitor_work_areas
        self._place_in_rect = place_in_rect
        self._cfg = cfg
        self.padre = QWidget()

        # El mismo StimulusViewer que usa la sesión, con los estímulos de Barrido.
        sv._stimulus_process = _proceso_medido
        self.estimulos = list(sv.builtins.SETTINGS.default_user_preferences.stimulus)
        self.activos = [True, True, False, False, False, False]
        self.viewer = sv.StimulusViewer(
            monitor_index=patient_monitor_index, cover_taskbar=patient_monitor_is_secondary
        )
        self.viewer.load_stimulus_use(self.estimulos, self.activos)
        self._listo = False
        self.viewer.stimuli_ready.connect(lambda _h: setattr(self, "_listo", True))

        cfg.set_active_profile(PERFIL)
        self.asterics = AstericsLauncher(parent=self.padre)
        self._configurado = None
        self.asterics.configured.connect(lambda ok, msg: setattr(self, "_configurado", (ok, msg)))
        self._ajustes = cfg.AstericsInputSettings(mode="barrido", scan_time_ms=1000, key_hold_ms=250)
        self.grabador = ScreenRecorder()
        self._fallo_grabacion = None
        self.grabador.failed.connect(lambda m: setattr(self, "_fallo_grabacion", m))

    def esperar(self, segundos: float, hasta=None) -> bool:
        fin = time.time() + segundos
        while time.time() < fin:
            self.app.processEvents()
            if hasta is not None and hasta():
                return True
            time.sleep(0.02)
        return hasta is None

    def _ubicar(self, hwnd: int) -> None:
        """Misma ubicación que EegMainPage._ubicar_en_espacio_libre (Barrido)."""
        info = self.viewer.get_screen_info()
        left, top, right, bottom = self._areas()[info["monitor_index"]]
        escala = info.get("monitor_scale") or 1
        lado = round(info["margins"][0] * (escala if escala > 1 else 1))
        hueco = max(24, round(lado * 0.15))
        self._place_in_rect(hwnd, left + lado + hueco, top + 6, right - 6, bottom - 6)

    def abrir_asterics(self) -> None:
        self._configurado = None
        if not self.asterics.open(place=self._ubicar, settings=self._ajustes):
            raise RuntimeError("No se pudo abrir AsTeRICS (¿navegador Chromium predeterminado?).")
        if not self.esperar(PRUEBA_ASTERICS_TIMEOUT_S, lambda: self._configurado is not None):
            raise RuntimeError("AsTeRICS no terminó de configurarse a tiempo.")
        if not self._configurado[0]:
            print("  aviso de AsTeRICS:", self._configurado[1], flush=True)
        self.esperar(5)

    def cerrar_asterics(self) -> None:
        self.asterics.close()
        self.esperar(5)

    def medir(self, nombre: str, condicion: str, ronda: int, segundos: int, inyectar: float = 0) -> dict:
        salida = self.carpeta / nombre
        os.environ[ENV_SALIDA] = str(salida)
        os.environ[ENV_INYECTAR] = str(inyectar) if inyectar else ""
        self._listo = False
        self.viewer.start_stim()
        if not self.esperar(60, lambda: self._listo):
            self.viewer.stop_stim()
            raise RuntimeError("El estimulador no llegó a abrirse.")

        video = None
        if condicion in ("asterics", "grabacion") and not self.asterics.is_open():
            self.abrir_asterics()
        if condicion == "grabacion":
            video = salida.with_suffix(".mp4")
            self._fallo_grabacion = None
            error = self.grabador.start(video, self.asterics.debug_port())
            if error:
                self.viewer.stop_stim()
                raise RuntimeError(f"No arrancó la grabación: {error}")

        print(f"  {nombre}: midiendo {segundos} s...", flush=True)
        self.viewer.start_flicker()
        self.esperar(segundos + DESCARTE_INICIAL_S)
        asterics_ok = self.asterics.is_open() if condicion != "solo" else True
        self.viewer.stop_stim()

        valida, motivo = asterics_ok, "" if asterics_ok else "AsTeRICS se cerró durante la medición"
        tam_video = 0.0
        if video is not None:
            guardado = self.grabador.stop()
            tam_video = video.stat().st_size / 2**20 if video.exists() else 0.0
            if guardado is None or self._fallo_grabacion:
                valida, motivo = False, f"la grabación falló: {self._fallo_grabacion or 'video vacío'}"

        tiempos = np.load(salida.with_suffix(".npy"))
        extra = json.loads(salida.with_suffix(".json").read_text(encoding="utf-8"))
        if tiempos.size < 100:
            raise RuntimeError(f"{nombre}: casi no hay cuadros registrados.")
        fila = {
            "medicion": nombre, "condicion": condicion, "ronda": ronda,
            **analizar(tiempos, extra["inyectados"]), "refresco_usado": extra["refresco_usado"],
            "video_mb": round(tam_video, 2), "valida": valida, "motivo": motivo,
        }
        print(
            f"    cuadros {fila['cuadros']} | perdidos {fila['perdidos']} | "
            f"máximo {fila['max_ms']:.1f} ms" + ("" if valida else f" | NO VÁLIDA: {motivo}"),
            flush=True,
        )
        return fila

    def cerrar(self) -> None:
        self.viewer.stop_stim()
        self.grabador.stop()
        self.asterics.close()
        self.esperar(3)


def informe(filas: list[dict], control: dict, ok_control: bool, segundos, rondas) -> str:
    lineas = [f"Medición de cuadros, {datetime.now():%Y-%m-%d %H:%M}", f"{rondas} rondas de {segundos} s por condición", ""]
    lineas.append(
        f"Control positivo: provocadas {control['inyectados']}, detectadas {control['detectados']} -> "
        + ("OK, el detector funciona" if ok_control else "FALLÓ: NO USAR ESTAS MEDICIONES")
    )
    lineas.append("")
    lineas.append(f"{'medición':<16}{'cuadros':>9}{'perdidos':>10}{'eventos':>9}{'máx ms':>9}{'p99.9 ms':>10}{'rápidos':>9}  válida")
    for f in filas:
        lineas.append(
            f"{f['medicion']:<16}{f['cuadros']:>9}{f['perdidos']:>10}{f['eventos']:>9}"
            f"{f['max_ms']:>9.1f}{f['p99_9_ms']:>10.1f}{f['rapidos']:>9}  {'sí' if f['valida'] else 'NO: ' + f['motivo']}"
        )
    lineas.append("")
    lineas.append("Por condición (solo mediciones válidas):")
    for cond in ("solo", "asterics", "grabacion"):
        grupo = [f for f in filas if f["condicion"] == cond and f["valida"]]
        if not grupo:
            lineas.append(f"  {cond}: sin mediciones válidas")
            continue
        n, perdidos = sum(f["cuadros"] for f in grupo), sum(f["perdidos"] for f in grupo)
        minutos = sum(f["duracion_s"] for f in grupo) / 60
        por_ronda = ", ".join(str(f["perdidos"]) for f in grupo)
        total = n + perdidos
        texto = f"  {cond}: {perdidos} perdidos de {total} ({100 * perdidos / total:.2f} %) en {minutos:.1f} min; por ronda: {por_ronda}"
        if perdidos == 0:
            # Regla del 3: cota al 95 %, suponiendo pérdidas independientes.
            texto += f". Cota al 95 %: menos de {3 / minutos:.2f} por minuto"
        lineas.append(texto)
    lineas.append("")

    hz = float(np.median([f["hz_medidos"] for f in filas]))
    usados = sorted({round(f["refresco_usado"], 3) for f in filas if f.get("refresco_usado")})
    lineas.append(f"Refresco: medido {hz:.3f} Hz | usado para el parpadeo: {usados} Hz")
    if any(abs(hz - u) / u > 0.01 for u in usados):
        lineas.append("  AVISO: difieren más de 1 %. Revisar el refresco del monitor.")
    lineas += [
        "",
        "Cómo leerlo: el resultado vale para esta PC, estos estímulos y este tiempo. No ve lo que",
        "Windows o el monitor descarten después de entregado el cuadro (eso lo cubre la filmación).",
        "Muchos 'rápidos' indican que los cuadros se encolan o que no se espera el refresco: en ese",
        "caso los perdidos pueden estar subestimados.",
    ]
    return "\n".join(lineas) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Mide cuadros perdidos del estimulador SSVEP.")
    parser.add_argument("--rondas", type=int, default=3)
    parser.add_argument("--segundos", type=int, default=45, help="duración de cada condición")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    carpeta = REPO / "senales" / "medicion_cuadros" / f"{datetime.now():%Y%m%d_%H%M%S}"
    carpeta.mkdir(parents=True)
    print("Resultados en", carpeta, flush=True)
    print("No uses la PC durante la prueba. La pantalla va a parpadear.", flush=True)

    prueba = Prueba(carpeta, args.segundos)
    filas: list[dict] = []
    try:
        print("Control positivo:", flush=True)
        control = prueba.medir("control", "solo", 0, DURACION_CONTROL_S, inyectar=INYECTAR_CADA_S)
        ok_control = control["inyectados"] > 0 and control["detectados"] == control["inyectados"]
        if not ok_control:
            print("  EL CONTROL POSITIVO FALLÓ: el detector no es confiable.", flush=True)

        for ronda in range(1, args.rondas + 1):
            print(f"Ronda {ronda}/{args.rondas}:", flush=True)
            filas.append(prueba.medir(f"solo_{ronda}", "solo", ronda, args.segundos))
            # Se alterna el orden: si la PC cambia con el tiempo, no se confunde con el efecto.
            orden = ("asterics", "grabacion") if ronda % 2 else ("grabacion", "asterics")
            for condicion in orden:
                filas.append(prueba.medir(f"{condicion}_{ronda}", condicion, ronda, args.segundos))
            prueba.cerrar_asterics()
    finally:
        prueba.cerrar()

    texto = informe(
        filas, control, ok_control, args.segundos, args.rondas
    )
    (carpeta / "resumen.txt").write_text(texto, encoding="utf-8")
    with open(carpeta / "resumen.csv", "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(control.keys()))
        escritor.writeheader()
        escritor.writerows([control, *filas])
    print("\n" + texto, flush=True)
    return 0 if ok_control else 1


if __name__ == "__main__":
    sys.exit(main())
