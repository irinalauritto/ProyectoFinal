"""Ventana de estímulos para la Calibración de frecuencias SSVEP.

Variante de `stimulus_viewer.py` con lo que necesita específicamente la
calibración y que esa pantalla no ofrece: posiciones explícitas (los dos
estímulos centrados verticalmente y bien separados, no el reparto
automático en zigzag) y un mensaje de texto + resaltado en rojo durante un
breve descanso antes de cada trial ("Debe mirar el estímulo remarcado").

Archivo nuevo: `stimulus_viewer.py` NO se modifica. Se reusan tal cual sus
piezas de bajo nivel (detección de monitor/DPI, creación de estímulos y de
parpadeo, creación de ventana, detección de refresco) en vez de
duplicarlas -- ver los imports de abajo. `StimulusViewer.__monitor_scales`
y `__work_area` son "privados" solo por convención (name mangling de
Python, no impide el acceso); se llaman explícitamente por su nombre
mangled en `__get_stimulus_regions` para no copiar esa lógica de ctypes.
"""

from __future__ import annotations

import multiprocessing as mp
from multiprocessing import Process, Queue
from multiprocessing.synchronize import Event
import time
from typing import Optional, Tuple

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QWidget
from psychopy import visual

from ssvep.app.dataclasses import Stimulus, StimulusConfig
from ssvep.app.stimulus_viewer import (
    StimulusViewer,
    _StimuliGenerator,
    _StimulusFlicker,
    _create_window,
    _get_refresh_rate,
    _hex_to_psychopy_rgb,
)

REST_MESSAGE = "Debe mirar el estímulo remarcado"
# Mismo rojo que ya usa STIMULUS_COLOR_HEX[3] en stimulus_viewer.py, para
# que el resaltado se sienta consistente con el resto de la app aunque sea
# un mecanismo de dibujo distinto (ver charla previa: esto NO es el mismo
# sistema de recuadros de color por estímulo).
HIGHLIGHT_COLOR_HEX = "#E53935"


class StimulusViewerCalibration(QWidget):
    """Ventana de 2 estímulos (candidata + ancla) para un trial de calibración.

    Uso (mismo patrón que `StimulusViewer`):
        viewer = StimulusViewerCalibration()
        viewer.stimuli_ready.connect(...)
        viewer.load_stimulus_use(candidata, ancla)
        viewer.start_stim()                 # abre la ventana; empieza en descanso
        # al recibir stimuli_ready:
        ...                                  # mostrar el descanso unos segundos
        viewer.start_flicker()              # arranca el parpadeo del trial
        ...
        viewer.start_rest()                 # (opcional) volver a descanso sin cerrar
        viewer.stop_stim()                  # cierra la ventana al terminar el trial

    Señales:
        stimuli_ready(hwnd): la ventana terminó de abrirse.
        flicker_started(timestamp): arrancó el parpadeo (una vez por start_flicker).
        stimulus_failed(motivo): el proceso de la ventana terminó (crasheó)
            antes de llegar a abrir -- sin esto, un fallo del proceso hijo
            (ej. error de PsychoPy/OpenGL al crear la ventana) queda mudo:
            `ready_event` nunca se activa y el que esté esperando
            `stimuli_ready` se queda colgado para siempre sin ningún aviso.
    """

    stimuli_ready = Signal(int)
    flicker_started = Signal(float)
    stimulus_failed = Signal(str)

    def __init__(self, size: int = 217, separation_fraction: float = 0.5, parent=None) -> None:
        """
        Args:
            size: Tamaño base de cada estímulo en píxeles (mismo default
                que `StimulusViewer`).
            separation_fraction: Separación horizontal entre los centros de
                los dos estímulos, como fracción del ancho de pantalla
                (0.5 = cada uno a un cuarto de pantalla del centro, un 50%
                del ancho total entre ambos).
        """
        super().__init__(parent)
        self.__stimulus_size = size
        # Valor original, sin escalar por DPI -- __get_stimulus_regions()
        # parte siempre de este valor (mismo bug/fix que StimulusViewer: sin
        # esto, si start_stim() se llamara mas de una vez sobre la misma
        # instancia, el tamaño se seguiria achicando en cada apertura).
        self.__base_stimulus_size = size
        self.__separation_fraction = separation_fraction

        self.__screen_width: Optional[int] = None
        self.__screen_height: Optional[int] = None
        self.__monitor_index: Optional[int] = None
        self.__monitor_scale: Optional[float] = None

        self.__candidate: Optional[Stimulus] = None
        self.__anchor: Optional[Stimulus] = None
        self.__refresh_rate_override: Optional[int] = None

        self.__process: Optional[Process] = None
        self.__hwnd_queue: Optional[Queue] = None
        self.__stop_event: Optional[Event] = None
        self.__ready_event: Optional[Event] = None
        self.__start_flicker_event: Optional[Event] = None
        self.__rest_event: Optional[Event] = None
        self.__timestamp_queue: Optional[Queue] = None
        self.__stim_update_queue: Optional[Queue] = None

        self.__stimulus_viewer_active = False
        self.__ready_emitted = False

        self.__timer_time_stamp = QTimer(self)
        self.__timer_time_stamp.timeout.connect(self.__process_timestamps)
        self.__timer_ready = QTimer(self)
        self.__timer_ready.timeout.connect(self.__check_ready_events)

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------
    def load_stimulus_use(self, candidate: Stimulus, anchor: Stimulus) -> None:
        """Candidata (la que hay que mirar) y ancla (referencia fija),
        para el próximo `start_stim()`."""
        self.__candidate = candidate
        self.__anchor = anchor

    def update_stimulus_use(self, candidate: Stimulus, anchor: Stimulus) -> None:
        """Cambia la candidata/ancla de la ventana YA ABIERTA (`is_running()`
        True), sin cerrarla ni volver a crear el proceso -- antes cada trial
        cerraba y reabría la ventana entera (`stop_stim()` + `start_stim()`),
        lo que se veía como que la ventana "parpadeaba" (se cerraba) entre
        estímulo y estímulo. Si la ventana no está abierta, es equivalente a
        `load_stimulus_use` (para el primer trial)."""
        self.__candidate = candidate
        self.__anchor = anchor
        if self.__stim_update_queue is not None:
            self.__stim_update_queue.put((candidate, anchor))

    def set_refresh_rate(self, refresh_rate: Optional[int]) -> None:
        """Evita que el proceso de renderizado tenga que medir el refresco
        con PsychoPy (`Window.getActualFrameRate()`, que muestra "Attempting
        to measure frame rate of screen, please wait ..." mientras hace
        flips repetidos y puede demorar mucho o no converger nunca según el
        monitor/driver -- ver FrequencyCalibrator, que ya detecta el
        refresco por su cuenta vía GDI antes de arrancar el barrido).
        Pasar `None` para volver a medirlo con PsychoPy como antes."""
        self.__refresh_rate_override = refresh_rate

    def start_stim(self) -> None:
        """Abre la ventana. Arranca en descanso (candidata resaltada, sin
        parpadear) -- llamar `start_flicker()` para empezar el trial."""
        if self.__candidate is None or self.__anchor is None:
            raise ValueError("Llamar load_stimulus_use(candidata, ancla) antes de start_stim().")

        self.__ready_emitted = False
        self.__timestamp_queue = mp.Queue()
        self.__stop_event = mp.Event()
        self.__ready_event = mp.Event()
        self.__hwnd_queue = mp.Queue()
        self.__start_flicker_event = mp.Event()
        self.__rest_event = mp.Event()
        self.__rest_event.set()
        self.__stim_update_queue = mp.Queue()

        self.__get_stimulus_regions()
        config = StimulusConfig(
            screen_width=self.__screen_width or 0,
            screen_height=self.__screen_height or 0,
            stimulus_data={0: self.__candidate, 1: self.__anchor},
            stimulus_positions=self.__centered_positions(),
            stimulus_size=self.__stimulus_size,
            height_margin=0,
            width_margin=0,
            monitor_index=self.__monitor_index or 0,
        )

        self.__process = mp.Process(
            target=_calibration_stimulus_process,
            args=(
                config,
                self.__stop_event,
                self.__ready_event,
                self.__hwnd_queue,
                self.__start_flicker_event,
                self.__rest_event,
                self.__timestamp_queue,
                self.__refresh_rate_override,
                self.__stim_update_queue,
            ),
            daemon=True,
        )
        self.__stimulus_viewer_active = True
        self.__process.start()
        self.__timer_time_stamp.start(20)
        self.__timer_ready.start(100)

    def stop_stim(self) -> None:
        """Cierra la ventana y libera los recursos del proceso."""
        self.__timer_time_stamp.stop()
        self.__timer_ready.stop()

        if self.__stop_event is not None:
            self.__stop_event.set()

        if self.__process is not None and self.__process.is_alive():
            self.__process.join(timeout=3)
            if self.__process.is_alive():
                self.__process.terminate()
                self.__process.join(timeout=1)

        self.__process = None
        self.__stop_event = None
        self.__ready_event = None
        self.__start_flicker_event = None
        self.__rest_event = None
        self.__timestamp_queue = None
        self.__stim_update_queue = None
        self.__stimulus_viewer_active = False

    def is_running(self) -> bool:
        return self.__stimulus_viewer_active

    def start_rest(self) -> None:
        """Pausa el parpadeo (si estaba corriendo) y muestra el mensaje +
        resaltado en rojo sobre la candidata."""
        if self.__start_flicker_event is not None:
            self.__start_flicker_event.clear()
        if self.__rest_event is not None:
            self.__rest_event.set()

    def start_flicker(self) -> None:
        """Termina el descanso (oculta mensaje/resaltado) y arranca el
        parpadeo de ambos estímulos."""
        if self.__rest_event is not None:
            self.__rest_event.clear()
        if self.__start_flicker_event is not None:
            self.__start_flicker_event.set()

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------
    def __centered_positions(self) -> list[Tuple[int, int]]:
        """Candidata a la izquierda, ancla a la derecha, ambas sobre la
        línea vertical central, separadas `separation_fraction` del ancho
        de pantalla entre sí (ver docstring del constructor)."""
        width = self.__screen_width or 0
        offset = int(width * self.__separation_fraction / 2)
        return [(-offset, 0), (offset, 0)]

    def __get_stimulus_regions(self) -> None:
        # Reusa tal cual la deteccion de monitor/DPI de StimulusViewer (no
        # se duplica esa logica de ctypes -- ver docstring de modulo).
        monitor_scales = StimulusViewer._StimulusViewer__monitor_scales()
        self.__monitor_index, self.__monitor_scale = monitor_scales[-1]
        self.__screen_width, self.__screen_height = StimulusViewer._StimulusViewer__work_area(self.__monitor_index)

        self.__stimulus_size = self.__base_stimulus_size
        if self.__monitor_scale and self.__monitor_scale > 1:
            self.__stimulus_size = int(self.__stimulus_size / self.__monitor_scale)
            self.__screen_width = int(self.__screen_width / self.__monitor_scale)
            self.__screen_height = int(self.__screen_height / self.__monitor_scale)

    def __check_ready_events(self) -> None:
        if self.__ready_event and self.__ready_event.is_set() and not self.__ready_emitted:
            self.__ready_emitted = True
            self.__timer_ready.stop()
            hwnd_val = 0
            if self.__hwnd_queue and not self.__hwnd_queue.empty():
                hwnd_val = self.__hwnd_queue.get_nowait()
            self.stimuli_ready.emit(hwnd_val)
            return

        # El proceso terminó (crasheó) antes de llegar a `ready_event.set()`
        # -- sin este chequeo, un fallo al crear la ventana (ej. error de
        # PsychoPy/OpenGL) deja a quien esté esperando `stimuli_ready`
        # colgado para siempre, sin ningún aviso ni traceback visible (un
        # `daemon=True` de multiprocessing no propaga la excepción al padre).
        if self.__process is not None and not self.__process.is_alive() and not self.__ready_emitted:
            exitcode = self.__process.exitcode
            self.__timer_ready.stop()
            self.__timer_time_stamp.stop()
            self.__process = None
            self.__stim_update_queue = None
            self.__stimulus_viewer_active = False
            self.stimulus_failed.emit(
                f"El proceso de la ventana de estímulos terminó antes de abrir "
                f"(código de salida {exitcode}). Revisá la consola para ver el error."
            )

    def __process_timestamps(self) -> None:
        if not self.__timestamp_queue:
            return
        while not self.__timestamp_queue.empty():
            timestamp = self.__timestamp_queue.get_nowait()
            self.flicker_started.emit(timestamp)


# =============================================================================
# Proceso en segundo plano (multiprocessing) -- análogo a `_stimulus_process`
# de stimulus_viewer.py, pero con el mensaje/resaltado de descanso.
# =============================================================================

def _calibration_stimulus_process(
    config: StimulusConfig,
    stop_event: Event,
    ready_event: Event,
    hwnd_queue: Queue,
    start_flicker_event: Event,
    rest_event: Event,
    timestamp_queue: Queue,
    refresh_rate_override: Optional[int] = None,
    stim_update_queue: Optional[Queue] = None,
) -> None:
    """Función objetivo del proceso de renderizado (2 estímulos + descanso)."""
    win = _create_window(config)
    hwnd = win.winHandle._hwnd
    hwnd_queue.put(hwnd)
    win.setMouseVisible(True)

    pos_candidate = config.stimulus_positions[0]
    pos_anchor = config.stimulus_positions[1]

    # Si ya se conoce el refresco (ver set_refresh_rate/FrequencyCalibrator),
    # se evita _get_refresh_rate(win): mide con flips repetidos de PsychoPy y
    # puede tardar mucho o no converger según el monitor/driver (pantalla de
    # "Attempting to measure frame rate..." que se queda pegada).
    refresh_rate = refresh_rate_override if refresh_rate_override else _get_refresh_rate(win)

    def _build_flickers(candidate_info, anchor_info):
        cand_stim, cand_inv = _StimuliGenerator.create_stimuli(
            win, config.stimulus_size, pos_candidate,
            candidate_info.stim_type, candidate_info.shape_type, candidate_info.direction,
        )
        anchor_stim, anchor_inv = _StimuliGenerator.create_stimuli(
            win, config.stimulus_size, pos_anchor,
            anchor_info.stim_type, anchor_info.shape_type, anchor_info.direction,
        )
        cand_flicker = _StimulusFlicker(cand_stim, cand_inv, candidate_info.freq, win, candidate_info.theta, refresh_rate)
        anchor_flicker = _StimulusFlicker(anchor_stim, anchor_inv, anchor_info.freq, win, anchor_info.theta, refresh_rate)
        # Autocheque de que la frecuencia realmente representada coincide con
        # la nominal dado el refresco detectado (ver
        # _StimulusFlicker.__mean_history en stimulus_viewer.py) -- acá se
        # activa directo (misma instancia, mismo proceso) en vez de a traves
        # de un Event como hace StimulusViewer, porque este proceso ya es
        # propio. Imprime por consola cada ~60 parpadeos; es la verificación
        # visual/de consola que puede hacer el operador sobre el monitor
        # real, no hay forma de leer el resultado booleano desde este
        # proceso hacia el principal.
        cand_flicker.set_stim_check(True)
        anchor_flicker.set_stim_check(True)
        return cand_flicker, anchor_flicker

    cand_flicker, anchor_flicker = _build_flickers(config.stimulus_data[0], config.stimulus_data[1])

    highlight_rect = visual.Rect(
        win=win,
        width=config.stimulus_size + 24,
        height=config.stimulus_size + 24,
        pos=pos_candidate,
        lineColor=_hex_to_psychopy_rgb(HIGHLIGHT_COLOR_HEX),
        lineWidth=5,
        fillColor=None,
    )
    # TextBox2 (no TextStim): TextStim renderiza el texto via
    # pyglet.text.Label, que en Windows pasa por el rasterizador GDI+ de
    # pyglet (pyglet/font/win32.py) -- con ciertas combinaciones de texto
    # (acentos, ancho) ese camino tira `ctypes.ArgumentError: argument 5:
    # TypeError: expected LP_c_ubyte instance instead of c_byte_Array_...`
    # dentro de GdipCreateBitmapFromScan0 y crashea el proceso entero antes
    # de llegar a abrir la ventana (confirmado con traceback real). TextBox2
    # usa el rasterizador de fuentes propio de PsychoPy (FreeType), no pasa
    # por ese camino de pyglet -- por eso se usa acá en vez de TextStim.
    message = visual.TextBox2(
        win=win,
        text=REST_MESSAGE,
        pos=(0, -(config.stimulus_size / 2 + 60)),
        letterHeight=32,
        color=(1, 1, 1),
        alignment='center',
        anchor='center',
        size=(config.screen_width * 0.8, None),
    )

    cand_flicker.static_draw()
    anchor_flicker.static_draw()
    win.flip()
    ready_event.set()

    time_stamp_pending = True
    while not stop_event.is_set():
        win.winHandle.dispatch_events()

        # Cambio de candidata sin cerrar la ventana (ver
        # StimulusViewerCalibration.update_stimulus_use): FrequencyCalibrator
        # ya puso al visor en descanso (rest_event) antes de mandar esto, asi
        # que reconstruir los flickers acá no se nota como un salto brusco.
        if stim_update_queue is not None and not stim_update_queue.empty():
            new_candidate_info, new_anchor_info = stim_update_queue.get_nowait()
            cand_flicker, anchor_flicker = _build_flickers(new_candidate_info, new_anchor_info)
            time_stamp_pending = True

        if start_flicker_event.is_set():
            cand_flicker.draw()
            anchor_flicker.draw()
            if time_stamp_pending:
                timestamp_queue.put(time.perf_counter())
                time_stamp_pending = False
        else:
            time_stamp_pending = True
            cand_flicker.static_draw()
            anchor_flicker.static_draw()
            if rest_event.is_set():
                highlight_rect.draw()
                message.draw()

        win.flip()

    win.close()
