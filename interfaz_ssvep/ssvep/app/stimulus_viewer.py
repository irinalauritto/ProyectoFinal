import builtins
import ctypes
import multiprocessing as mp
from multiprocessing import Process, Queue
from multiprocessing.synchronize import Event
from multiprocessing.sharedctypes import Synchronized
import time
from collections import deque
from ctypes import wintypes
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from psychopy import visual
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QWidget
from ssvep.app.dataclasses import StimulusConfig
# =========================================================================
# Constantes y Funciones de Utilidad a Nivel de Módulo
# =========================================================================

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

# Color fijo por tipo de estímulo (mismos valores que SequenceWidget en
# bci_evaluator_widgets.py) para el marco permanente en la ventana de
# estímulos. Claves = índice de estímulo (0-5).
STIMULUS_COLOR_HEX: Dict[int, str] = {
    0: "#F2C200",  # Escape / cuadrado -> amarillo
    1: "#1E88E5",  # Espacio / círculo -> azul
    2: "#FB8C00",  # Derecha -> naranja
    3: "#E53935",  # Abajo -> rojo
    5: "#43A047" , # Arriba -> verde
    4: "#8E24AA",  # Izquierda -> violeta
    }


def _hex_to_psychopy_rgb(hex_color: str) -> Tuple[float, float, float]:
    """Convierte un color hexadecimal '#RRGGBB' al rango [-1, 1] que usa PsychoPy."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r * 2 - 1, g * 2 - 1, b * 2 - 1)


def set_always_on_top(hwnd: int) -> None:
    """
    Establece una ventana de Windows como 'siempre visible' (Always on Top).
    
    Args:
        hwnd: Manejador (handle) de la ventana de Windows.
    """
    user32 = ctypes.windll.user32
    user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
    )



# =========================================================================
# Clase Principal: Widget de Visualización
# =========================================================================

class StimulusViewer(QWidget):
    """
    Widget de PySide6 que gestiona la visualización de estímulos visuales 
    mediante un proceso secundario de PsychoPy.
    
    Signals:
        stimuli_ready (int): Se emite cuando la ventana de PsychoPy está lista, 
                             pasando el HWND de la ventana.
        flicker_started (float): Se emite con el timestamp de inicio del parpadeo.
        message_emitted (str): Señal para emitir mensajes de estado o error.
    """
    stimuli_ready = Signal(int)
    flicker_started = Signal(float)
    message_emitted = Signal(str)

    def __init__(
        self, 
        width: Optional[int] = None, 
        height: Optional[int] = None, 
        size: int = 217, 
        time_stamp: bool = True
    ) -> None:
        """
        Inicializa el widget de visualización de estímulos.

        Args:
            width: Ancho de la pantalla objetivo.
            height: Alto de la pantalla objetivo.
            size: Tamaño base del estímulo en píxeles.
            time_stamp: Si se debe habilitar el seguimiento de timestamps.
        """
        super().__init__()

        # --- Configuración de pantalla ---
        self.__screen_width: Optional[int] = width
        self.__screen_height: Optional[int] = height
        self.__monitor_index: Optional[int] = None
        self.__monitor_scale: Optional[float] = None
        self.__margin: Optional[Tuple[int, int]] = None

        # --- Configuración de estímulos ---
        self.__stimulus_size: int = size
        self.__all_stimuli: List[Any] = []
        self.__stimulus_config: Optional[Dict[int, Any]] = None
        self.__stimulus_positions: List[Tuple[int, int]] = []

        # --- Multiprocessing / IPC ---
        self.__process: Optional[Process] = None
        self.__hwnd_queue: Optional[Queue] = None
        self.__stop_event: Optional[Event] = None
        self.__ready_event: Optional[Event] = None
        self.__start_flicker_event: Optional[Event] = None
        self.__check_refresh_on_event: Optional[Event] = None
        self.__check_refresh_off_event: Optional[Event] = None
        self.__timestamp_queue: Optional[Queue] = None
        self.__selected_index: Optional[Synchronized] = None

        # --- Estado runtime ---
        self.__stimulus_viewer_active: bool = False
        self.__ready_emitted: bool = False

        # --- Timers de Qt ---
        self.__timer_time_stamp = QTimer(self)
        self.__timer_time_stamp.timeout.connect(self.__process_timestamps)
        
        self.__timer_ready = QTimer(self)
        self.__timer_ready.timeout.connect(self.__check_ready_events)

    # ---------------------------------------------------------------------
    # Interfaz Pública
    # ---------------------------------------------------------------------

    def load_stimulus_use(self, all_stimuli: List[Any], stimulus_on: List[bool]) -> None:
        """
        Carga la configuración completa de estímulos posibles y cuáles están
        activos actualmente.

        Las posiciones en pantalla se calculan siempre sobre el conjunto
        completo de estímulos posibles (`all_stimuli`), no sobre la cantidad
        de activos. De esa forma cada estímulo tiene un lugar fijo en
        pantalla que no cambia al activar o desactivar otros estímulos.

        Args:
            all_stimuli: Lista completa de estímulos posibles, en su orden
                de índice original (activos e inactivos).
            stimulus_on: Lista de booleanos que indica, por índice, qué
                estímulos de `all_stimuli` están activos actualmente.
        """
        self.__all_stimuli = all_stimuli
        self.__stimulus_config = {
            index: stim for index, stim in enumerate(all_stimuli) if stimulus_on[index]
        }

    def start_stim(self) -> None:
        """Inicia el proceso de renderizado de estímulos en segundo plano."""
        self.__ready_emitted = False
        self.__timestamp_queue = mp.Queue()
        self.__stop_event = mp.Event()
        self.__ready_event = mp.Event()
        self.__hwnd_queue = mp.Queue()
        self.__start_flicker_event = mp.Event()
        self.__check_refresh_on_event = mp.Event()
        self.__check_refresh_off_event = mp.Event()
        self.__selected_index = mp.Value('i', -1)

        self.__get_stimulus_regions()
        self.__calculate_stimulus_positions()

        data = self.__build_config()
        self.__process = mp.Process(
            target=_stimulus_process,
            args=(
                data, self.__stop_event, self.__ready_event, self.__hwnd_queue,
                self.__check_refresh_on_event, self.__check_refresh_off_event,
                self.__timestamp_queue, self.__selected_index, self.__start_flicker_event
            ),
            daemon=True,
        )
        
        self.__stimulus_viewer_active = True
        self.__process.start()
        
        self.__timer_time_stamp.start(20)
        self.__timer_ready.start(100)

    def stop_stim(self) -> None:
        """Detiene de forma segura el proceso de renderizado y limpia los recursos."""
        self.__timer_time_stamp.stop()
        self.__timer_ready.stop()
        
        if self.__stop_event is not None:
            self.__stop_event.set()
        if self.__start_flicker_event is not None:
            self.__start_flicker_event.clear()
            
        if self.__process is not None and self.__process.is_alive():
            self.__process.join(timeout=3)
            if self.__process.is_alive():       
                self.__process.terminate()      
                self.__process.join(timeout=1)
                
        # Limpieza de referencias
        self.__process = None
        self.__stop_event = None
        self.__ready_event = None
        self.__start_flicker_event = None
        self.__check_refresh_on_event = None
        self.__check_refresh_off_event = None
        self.__timestamp_queue = None
        self.__selected_index = None
        self.__stimulus_viewer_active = False

    def is_running(self) -> bool:
        """Indica si el proceso de visualización está activo."""
        return self.__stimulus_viewer_active

    def stimulus_indicate(self, index: int = -1) -> None:
        """
        Resalta un estímulo específico sin iniciar el parpadeo.

        Args:
            index: Índice del estímulo a resaltar (-1 para ninguno).
        """
        if self.__selected_index is not None:
            self.__selected_index.value = index
            self.__start_flicker_event.clear()
        if self.__check_refresh_on_event is not None:
            self.__check_refresh_on_event.set()
    
    def start_flicker(self) -> None:
        """Inicia el parpadeo de los estímulos según la configuración."""
        if self.__selected_index is not None:
            self.__selected_index.value = -1
        if self.__start_flicker_event is not None:
            self.__start_flicker_event.set()

    def get_screen_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre la configuración de la pantalla detectada.

        Returns:
            Diccionario con ancho, alto, índice de monitor, escala y márgenes.
        """
        return {
            'width': self.__screen_width,
            'height': self.__screen_height,
            'monitor_index': self.__monitor_index,
            'monitor_scale': self.__monitor_scale,
            'margins': self.__margin
        }

    # ---------------------------------------------------------------------
    # Lógica Interna: Gestión de Eventos y Timers
    # ---------------------------------------------------------------------

    def __check_ready_events(self) -> None:
        """Verifica si el proceso secundario ha señalado que está listo."""
        if self.__ready_event and self.__ready_event.is_set() and not self.__ready_emitted:
            self.__ready_emitted = True
            self.__timer_ready.stop()

            hwnd_val = 0
            if self.__hwnd_queue and not self.__hwnd_queue.empty():
                hwnd_val = self.__hwnd_queue.get_nowait()

            self.stimuli_ready.emit(hwnd_val)
            
    def __process_timestamps(self) -> None:
        """Procesa y emite los timestamps recibidos del proceso secundario."""
        if not self.__timestamp_queue:
            return

        while not self.__timestamp_queue.empty():
            timestamp = self.__timestamp_queue.get_nowait()
            self.flicker_started.emit(timestamp)

    # ---------------------------------------------------------------------
    # Lógica Interna: Cálculos Geométricos y de Configuración
    # ---------------------------------------------------------------------

    # Orden visual deseado para los estímulos tipo flecha en la fila
    # inferior de la pantalla (de izquierda a derecha).
    __ARROW_DISPLAY_ORDER = {'down': 0, 'left': 1, 'up': 2, 'right': 3}

    @staticmethod
    def __display_order(stimuli_by_index: Dict[int, Any]) -> List[int]:
        """
        Determina en qué orden se le asignan las posiciones geométricas
        recorridas a un conjunto de estímulos.

        Los estímulos no direccionales conservan su orden original (para que
        sigan ocupando primero la columna izquierda). Los estímulos tipo
        flecha se ordenan como abajo, izquierda, arriba, derecha, de forma
        que -al caer en la fila inferior- queden dispuestos de izquierda a
        derecha en ese orden.

        Args:
            stimuli_by_index: Diccionario {índice: estímulo} a ordenar.

        Returns:
            list[int]: Índices de `stimuli_by_index`, en el orden en que
                deben recibir cada posición geométrica recorrida.
        """
        def sort_key(item):
            index, stim = item
            if stim.shape_type == 'arrow' and stim.direction in StimulusViewer.__ARROW_DISPLAY_ORDER:
                return (1, StimulusViewer.__ARROW_DISPLAY_ORDER[stim.direction])
            return (0, index)

        ordered_items = sorted(stimuli_by_index.items(), key=sort_key)
        return [index for index, _ in ordered_items]

    def __calculate_stimulus_positions(self) -> List[Tuple[int, int]]:
        """
        Calcula las posiciones (x, y) de los estímulos activos en pantalla.

        Las posiciones se calculan una única vez sobre el conjunto COMPLETO
        de estímulos posibles (`__all_stimuli`), no sobre la cantidad de
        estímulos activos. Así, cada estímulo tiene siempre el mismo lugar
        fijo en pantalla, sin importar cuáles otros estén activos.
        """
        if not self.__stimulus_config or not self.__all_stimuli:
            return []

        n_total = len(self.__all_stimuli)
        size = self.__stimulus_size
        width = self.__screen_width or 0
        height = self.__screen_height or 0
        h_margin = self.__margin[0] if self.__margin else 0

        total_length = width + height - h_margin - size / 2
        usable_length = total_length - size * n_total
        spacing = int(usable_length / (n_total - 1)) if n_total > 1 else 0

        slots = []
        x_pos = int(-width / 2 + size / 2)
        y_pos = int(height / 2 - size / 2)
        x_init = x_pos
        y_lim = int(-height / 2 + h_margin)
        y_bottom = int(-height / 2 + size / 2)

        slots.append((x_pos, y_pos))
        step = size + spacing

        for i in range(1, n_total):
            if x_pos == x_init:
                y_pos = y_pos - step

            if y_pos < y_bottom:
                if x_pos == x_init:
                    rest = int(y_lim - y_pos)
                    x_pos = x_pos + rest
                    slots.append((x_pos, y_bottom))
                else:
                    x_pos = x_pos + step
                    slots.append((x_pos, y_bottom))
            else:
                slots.append((x_pos, y_pos))

        # Los slots están en orden geométrico de recorrido (columna
        # izquierda, luego fila inferior); se le asigna a cada estímulo del
        # conjunto COMPLETO una posición fija según __display_order.
        all_stimuli_by_index = dict(enumerate(self.__all_stimuli))
        fixed_positions: Dict[int, Tuple[int, int]] = {}
        for slot, stim_index in zip(slots, self.__display_order(all_stimuli_by_index)):
            fixed_positions[stim_index] = slot

        # Solo se devuelven las posiciones (fijas) de los estímulos
        # actualmente activos, en el mismo orden que __stimulus_config.
        positions = [fixed_positions[index] for index in self.__stimulus_config]
        self.__stimulus_positions = positions
        return positions

    def __build_config(self) -> StimulusConfig:
        """Construye el objeto de configuración para el proceso secundario."""
        if self.__margin is None:
            raise ValueError("Margin no calculado. Llama a __get_stimulus_regions primero.")
            
        return StimulusConfig(
            screen_width=self.__screen_width or 0,
            screen_height=self.__screen_height or 0,
            stimulus_data=self.__stimulus_config or {},
            stimulus_positions=self.__stimulus_positions,
            stimulus_size=self.__stimulus_size,
            height_margin=self.__margin[0],
            width_margin=self.__margin[1],
            monitor_index=self.__monitor_index or 0
        )

    def __get_stimulus_regions(self) -> Tuple[int, int]:
        """Obtiene y ajusta las regiones de la pantalla según la escala del monitor."""
        monitors = self.__monitor_scales()
        self.__monitor_index, self.__monitor_scale = monitors[-1]
        
        self.__screen_width, self.__screen_height = self.__work_area(self.__monitor_index)
        
        if self.__monitor_scale and self.__monitor_scale > 1:
            self.__stimulus_size = int(self.__stimulus_size / self.__monitor_scale)
            self.__screen_width = int(self.__screen_width / self.__monitor_scale)
            self.__screen_height = int(self.__screen_height / self.__monitor_scale)
            
        if self.__screen_width is None or self.__screen_height is None:
            raw_w, raw_h = self.__work_area(self.__monitor_index or 0)
            self.__screen_width = int(raw_w / (self.__monitor_scale or 1)) 
            self.__screen_height = int(raw_h / (self.__monitor_scale or 1))
            
        rel_aspect = (self.__screen_width or 1) / (self.__screen_height or 1)
        height_margin = round(self.__stimulus_size)
        width_margin = round(height_margin * rel_aspect)
        self.__margin = (height_margin, width_margin)
        
        return height_margin, width_margin

    # ---------------------------------------------------------------------
    # Lógica Interna: Interacción con Windows API (ctypes)
    # ---------------------------------------------------------------------

    @staticmethod
    def __monitor_scales() -> List[Tuple[int, float]]:
        """
        Enumera los monitores conectados y obtiene su factor de escala DPI.
        """
        shcore = ctypes.windll.shcore
        user32 = ctypes.windll.user32
        monitors = []

        user32.EnumDisplayMonitors.argtypes = [
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            ctypes.c_void_p,
            wintypes.LPARAM
        ]

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
            ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
        )

        def monitor_enum_proc(hMonitor: wintypes.HANDLE, hdcMonitor: wintypes.HDC, 
                              lprcMonitor: Any, dwData: wintypes.LPARAM) -> bool:
            index = len(monitors)
            dpiX = ctypes.c_uint()
            
            shcore.GetDpiForMonitor(hMonitor, 0, ctypes.byref(dpiX), ctypes.byref(ctypes.c_uint()))
            scale = round(dpiX.value / 96.0, 2)
            monitors.append((index, scale))
            return True

        callback_inst = MONITORENUMPROC(monitor_enum_proc)
        user32.EnumDisplayMonitors(None, None, ctypes.cast(callback_inst, ctypes.c_void_p), 0)

        return monitors

    @staticmethod
    def __work_area(index: int) -> Tuple[int, int]:
        """
        Obtiene el área de trabajo (sin barra de tareas) de un monitor específico.
        """
        user32 = ctypes.windll.user32
        monitors = []

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wintypes.DWORD),
            ]

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
            ctypes.POINTER(RECT), wintypes.LPARAM
        )

        def monitor_enum_proc(hMonitor: wintypes.HANDLE, hdcMonitor: wintypes.HDC, 
                              lprcMonitor: Any, dwData: wintypes.LPARAM) -> bool:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)

            if not user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                return False

            work = mi.rcWork
            monitors.append((work.right - work.left, work.bottom - work.top))
            return True

        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), ctypes.c_void_p, wintypes.LPARAM]
        user32.EnumDisplayMonitors.restype = wintypes.BOOL

        callback_inst = MONITORENUMPROC(monitor_enum_proc)
        user32.EnumDisplayMonitors(None, None, ctypes.cast(callback_inst, ctypes.c_void_p), 0)

        # Fallback seguro si el índice está fuera de rango
        return monitors[index] if index < len(monitors) else monitors[-1]


# =========================================================================
# Clases Auxiliares de Renderizado (Privadas)
# =========================================================================

class _StimulusFlicker:
    """
    Gestiona la lógica de parpadeo (flicker) de un estímulo individual 
    sincronizada con la tasa de refresco del monitor.
    """
    def __init__(
        self, 
        stim: Any, 
        stim_inv: Any, 
        stim_freq: float, 
        win: Any, 
        stim_theta: float = 0.0, 
        refresh_rate: int = 60, 
        stim_check: bool = False
    ) -> None:
        self.__win = win
        self.__sequences: Optional[np.ndarray] = None
        self.__idx_sequence = 0
        self.__refresh_rate = refresh_rate
        self.__stim = stim
        self.__stim_inv = stim_inv
        self.__stim_freq = stim_freq
        self.__stim_check = stim_check
        self.__stim_theta = stim_theta
        self.__last_bool: Optional[bool] = None
        self.__mean_report = deque(maxlen=10)
        self.__toggle_times: List[float] = []

    def draw(self) -> None:
        """Dibuja el estado actual del estímulo (parpadeando) y avanza la secuencia."""
        if self.__sequences is None:
            self.__create_sequence()
        
        current_state = bool(self.__sequences[self.__idx_sequence])
        
        if self.__last_bool != current_state:
            self.__toggle_times.append(time.time())
            
        if current_state:
            self.__stim.draw()
        else:
            self.__stim_inv.draw()
            
        self.__last_bool = current_state
        self.__idx_sequence = (self.__idx_sequence + 1) % len(self.__sequences)
        
        if len(self.__toggle_times) > 60:
            self.__mean_history()

    def static_draw(self) -> None:
        """Dibuja el estímulo en estado estático (sin parpadeo)."""
        self.__stim.draw()

    def set_stim_check(self, check: bool) -> None:
        """
        Activa o desactiva la verificación de frecuencia.
        Si se activa, limpia el historial anterior.
        """
        self.__stim_check = check
        if check:
            self.__toggle_times.clear()
            self.__last_bool = None

    def __mean_history(self) -> None:
        """Calcula y registra la media y desviación estándar de los tiempos de conmutación."""
        if self.__stim_check:    
            diff_t = np.diff(np.array(self.__toggle_times))
            diff_t_mean = diff_t.mean()
            diff_t_std = diff_t.std()
            self.__mean_report.append((diff_t_mean, diff_t_std))
            
            measured_freq = (1 / diff_t_mean) / 2
            if abs(measured_freq - self.__stim_freq) >= 1:
                print(f"Frecuencia {self.__stim_freq} no representada correctamente. "
                      f"Frecuencia media medida: {measured_freq:.2f} Hz")
        self.__toggle_times.clear()

    def __create_sequence(self) -> None:
        """Genera la secuencia booleana de parpadeo basada en la frecuencia y fase."""
        frames_per_cycle = self.__refresh_rate / self.__stim_freq
        theta_frames = (self.__stim_theta / (2 * np.pi)) * frames_per_cycle

        self.__sequences = np.array([
            ((k + theta_frames) % frames_per_cycle) < (frames_per_cycle / 2)
            for k in range(self.__refresh_rate)
        ])


class _StimuliGenerator:
    """
    Fábrica estática para generar objetos de estímulos visuales de PsychoPy 
    (tableros de ajedrez o parpadeo sólido) con diferentes máscaras geométricas.
    """
    @staticmethod
    def create_stimuli(
        win: Any, 
        size_stim: int, 
        position: Tuple[int, int], 
        stim_type: str = 'check', 
        shape_type: str = 'square', 
        arrow_dir: Optional[str] = None, 
        grid_size: int = 4
    ) -> Tuple[Any, Any]:
        """
        Crea un par de estímulos (normal e invertido) según la configuración.

        Args:
            win: Ventana de PsychoPy.
            size_stim: Tamaño del estímulo en píxeles.
            position: Tupla (x, y) de la posición.
            stim_type: 'check' (tablero de ajedrez) o 'flic' (parpadeo sólido).
            shape_type: 'square', 'arrow' o 'circle'.
            arrow_dir: Dirección de la flecha ('up', 'down', 'left', 'right').
            grid_size: Número de divisiones en el tablero de ajedrez.

        Returns:
            Tupla con el estímulo normal y su versión invertida.
        """
        if stim_type not in ('check', 'flic'):
            raise ValueError("Invalid stim_type. Use 'check' or 'flic'.")
        if shape_type not in ('square', 'arrow', 'circle'):
            raise ValueError("Invalid shape_type. Use 'square', 'arrow', or 'circle'.")
        if arrow_dir is not None and arrow_dir not in ('up', 'down', 'left', 'right'): 
            raise ValueError("Invalid arrow_dir. Use 'up', 'down', 'left', or 'right'.")
        
        if stim_type == 'check':
            return _StimuliGenerator.__checkboard(win, size_stim, position, shape_type, arrow_dir, grid_size)  
        else:
            return _StimuliGenerator.__flicker(win, size_stim, position, shape_type, arrow_dir, grid_size)
        
    @staticmethod    
    def __checkboard(
        window: Any, size: int, position: Tuple[int, int], 
        shape_type: str, arrow_dir: Optional[str], grid_size: int
    ) -> Tuple[Any, Any]:
        """Genera estímulos tipo tablero de ajedrez (checkerboard)."""
        pattern = np.ones((grid_size, grid_size))
        pattern[::2, ::2] *= -1
        pattern[1::2, 1::2] *= -1
        
        if shape_type == 'square':
            stim = visual.GratingStim(win=window, tex=pattern, pos=position, size=size-1, sf=None, opacity=1, interpolate=False)
            stim_inv = visual.GratingStim(win=window, tex=pattern*-1, pos=position, size=size-1, sf=None, opacity=1, interpolate=False)
        else:
            mask = _StimuliGenerator.__arrow_mask(size, direction=arrow_dir) if shape_type == 'arrow' else _StimuliGenerator.__circle_mask(size)
            stim = visual.ImageStim(win=window, image=pattern, mask=mask, pos=position, size=size-1, opacity=1)
            stim_inv = visual.ImageStim(win=window, image=pattern*-1, mask=mask, pos=position, size=size-1, opacity=1)
            
        return stim, stim_inv
 
    @staticmethod    
    def __flicker(
        window: Any, size: int, position: Tuple[int, int], 
        shape_type: str, arrow_dir: Optional[str], grid_size: int
    ) -> Tuple[Any, Any]:
        """Genera estímulos tipo parpadeo de bloque sólido."""
        pattern = np.ones((grid_size, grid_size))
        
        if shape_type == 'square':
            stim = visual.GratingStim(win=window, tex=pattern, pos=position, size=size, opacity=1, sf=None, interpolate=False)
            stim_inv = visual.GratingStim(win=window, tex=pattern*-1, pos=position, size=size, opacity=1, sf=None, interpolate=False)
        else:
            mask = _StimuliGenerator.__arrow_mask(size, direction=arrow_dir) if shape_type == 'arrow' else _StimuliGenerator.__circle_mask(size)
            stim = visual.ImageStim(win=window, image=pattern, mask=mask, pos=position, size=size, opacity=1)
            stim_inv = visual.ImageStim(win=window, image=pattern*-1, mask=mask, pos=position, size=size, opacity=1)
            
        return stim, stim_inv

    @staticmethod
    def __arrow_mask(size: int, direction: str = 'up') -> np.ndarray:
        """Genera una máscara de matriz para una forma de flecha."""
        img = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(img)
        w, h = size, size

        points = [
            (round(w*0.5), round(h)),
            (round(0), round(h*0.5)),
            (round(w*0.3), round(h*0.5)),
            (round(w*0.3), round(1)),
            (round(w-w*0.3), round(1)),
            (round(w-w*0.3), round(h*0.5)),
            (round(w), round(h*0.5))
        ]
        draw.polygon(points, fill=255)
        # El polígono sin rotar apunta hacia abajo (punta en (w*0.5, h)).
        if direction == 'right':
            img = img.rotate(90)
        elif direction == 'left':
            img = img.rotate(-90)
        elif direction == 'up':
            img = img.rotate(180)
        # 'down': la máscara base ya apunta hacia abajo, sin rotación.

        return (np.array(img).astype(np.float32) / 127.5) - 1.0
    
    @staticmethod
    def __circle_mask(size: int) -> np.ndarray:
        """Genera una máscara de matriz para una forma circular."""
        img = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(img)
        draw.ellipse([(0, 0), (size - 1, size - 1)], fill=255)
        return (np.array(img).astype(np.float32) / 127.5) - 1.0
    
    
    
# =========================================================================
# Lógica de Procesamiento en Segundo Plano (Multiprocessing)
# =========================================================================

def _stimulus_process(
    config: StimulusConfig,
    stop_event: Event,
    ready_event: Event,
    hwnd_queue: Queue,
    check_refresh_on_event: Event,
    check_refresh_off_event: Event,
    timestamp_queue: Queue,
    selected_index: Synchronized,
    start_flicker_event: Event
) -> None:
    """Función objetivo para el proceso de renderizado de PsychoPy."""

    # 1. Inicialización de la ventana
    win = _create_window(config)
    hwnd = win.winHandle._hwnd
    hwnd_queue.put(hwnd)
    win.setMouseVisible(True)

    # 2. Creación de estímulos
    # (Nota: Esta función YA llama a _get_refresh_rate internamente)
    flickers = _create_flickers(win, config)

    # 2b. Marco de color fijo por estímulo (siempre visible)
    stimulus_frames = _create_stimulus_frames(win, config)

    # 3. Detección de refresh rate  <--- ¡ELIMINA ESTA LÍNEA!
    # refresh_rate = _get_refresh_rate(win)

    # 4. Dibujo inicial
    _draw_static_stimuli(flickers, stimulus_frames, win)
    ready_event.set()

    # 5. Bucle principal
    _main_render_loop(
        win, flickers, stimulus_frames, stop_event, check_refresh_on_event,
        check_refresh_off_event, start_flicker_event,
        selected_index, config, timestamp_queue
    )

    win.close()


def _create_window(config: StimulusConfig) -> visual.Window:
    """Crea y configura la ventana de PsychoPy."""
    return visual.Window(
        size=(config.screen_width, config.screen_height),
        screen=config.monitor_index,
        pos=(0, 0),
        fullscr=False,
        color=(-0.9, -0.9, -0.9),
        units='pix',
        allowGUI=False,
        winType='pyglet',
    )


def _create_flickers(win: visual.Window, config: StimulusConfig) -> List[_StimulusFlicker]:
    """Crea todos los objetos de parpadeo para los estímulos."""
    stimulus = []
    for i, stim_info in enumerate(config.stimulus_data.values()):
        pos = config.stimulus_positions[i]
        size = config.stimulus_size
        stim, stim_inv = _StimuliGenerator.create_stimuli(
            win, size, pos,
            stim_info.stim_type,
            stim_info.shape_type,
            stim_info.direction
        )
        stimulus.append((stim, stim_inv, stim_info.freq, stim_info.theta))

    refresh_rate = _get_refresh_rate(win)

    return [
        _StimulusFlicker(stim, stim_inv, freq, win, theta, refresh_rate)
        for stim, stim_inv, freq, theta in stimulus
    ]


def _create_stimulus_frames(win: visual.Window, config: StimulusConfig) -> List[visual.Rect]:
    """Crea el marco de color fijo (uno por estímulo activo) para la ventana de estímulos."""
    frames = []
    for i, stim_index in enumerate(config.stimulus_data.keys()):
        color_hex = STIMULUS_COLOR_HEX.get(stim_index)
        if color_hex is None:
            continue
        frames.append(visual.Rect(
            win=win,
            width=config.stimulus_size,
            height=config.stimulus_size,
            pos=config.stimulus_positions[i],
            lineColor=_hex_to_psychopy_rgb(color_hex),
            lineWidth=3,
            fillColor=None,
        ))
    return frames


def _get_refresh_rate(win: visual.Window) -> int:
    """Detecta la tasa de refresco del monitor."""
    refresh_rate = win.getActualFrameRate()
    refresh_rate = int(refresh_rate) if refresh_rate is not None else 60
    print("refresh_rate detectado:", refresh_rate)
    return refresh_rate


def _draw_static_stimuli(
    flickers: List[_StimulusFlicker], stimulus_frames: List[visual.Rect], win: visual.Window
) -> None:
    """Dibuja todos los estímulos en estado estático, con su marco de color."""
    for f in flickers:
        f.static_draw()
    for frame in stimulus_frames:
        frame.draw()
    win.flip()


def _main_render_loop(
    win: visual.Window,
    flickers: List[_StimulusFlicker],
    stimulus_frames: List[visual.Rect],
    stop_event: Event,
    check_refresh_on_event: Event,
    check_refresh_off_event: Event,
    start_flicker_event: Event,
    selected_index: Synchronized,
    config: StimulusConfig,
    timestamp_queue: mp.Queue
) -> None:
    """Bucle principal de renderizado que maneja la lógica de visualización."""
    start_stimulus = False
    time_stamp_send = False

    # Crear rectángulo de selección
    selection_rect = visual.Rect(
        win=win,
        width=config.stimulus_size,
        height=config.stimulus_size,
        pos=(0, 0),
        fillColor=(1, -1, -1),
        lineColor=(1, -1, -1),
        lineWidth=4,
    )

    while not stop_event.is_set():
        win.winHandle.dispatch_events()

        # Manejar eventos de verificación
        _handle_refresh_check_events(
            flickers, check_refresh_on_event, check_refresh_off_event
        )

        # Lógica de visualización
        if not start_flicker_event.is_set():
            start_stimulus = False
            time_stamp_send = False
            _draw_static_with_selection(flickers, selection_rect, selected_index, config)
        else:
            start_stimulus = True
            for f in flickers:
                f.draw()

        # Marco de color fijo por estímulo, siempre visible
        for frame in stimulus_frames:
            frame.draw()

        win.flip()

        # Enviar timestamp al iniciar parpadeo
        if start_stimulus and not time_stamp_send:
            timestamp_queue.put(time.perf_counter())
            time_stamp_send = True


def _handle_refresh_check_events(
    flickers: List[_StimulusFlicker],
    check_refresh_on_event: Event,
    check_refresh_off_event: Event
) -> None:
    """Maneja los eventos de activación/desactivación de verificación."""
    if check_refresh_on_event.is_set():
        for f in flickers:
            f.set_stim_check(True)
        check_refresh_on_event.clear()
    elif check_refresh_off_event.is_set():
        for f in flickers:
            f.set_stim_check(False)
        check_refresh_off_event.clear()


def _draw_static_with_selection(
    flickers: List[_StimulusFlicker],
    selection_rect: visual.Rect,
    selected_index: Synchronized,
    config: StimulusConfig
) -> None:
    """Dibuja estímulos estáticos con el rectángulo de selección si hay uno seleccionado."""
    for f in flickers:
        f.static_draw()

    if selected_index.value != -1:
        selection_rect.pos = config.stimulus_positions[selected_index.value]
        selection_rect.draw()
