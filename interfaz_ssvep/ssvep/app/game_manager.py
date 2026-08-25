
from pathlib import Path
import ctypes
from ctypes import wintypes
import os
import time
from PySide6.QtCore import QObject, QTimer
# ==============================================================================
# 1. DEFINICIÓN DE PROTOTIPOS Y FIRMAS DE LA API DE WINDOWS (Nivel de módulo)
# ==============================================================================

# Firmas de los Callbacks
EnumWindowsProc_t = ctypes.WINFUNCTYPE(
    wintypes.BOOL, 
    wintypes.HWND, 
    wintypes.LPARAM
)

MonitorEnumProc_t = ctypes.WINFUNCTYPE(
    wintypes.BOOL, 
    wintypes.HMONITOR, 
    wintypes.HDC, 
    ctypes.POINTER(wintypes.RECT), 
    wintypes.LPARAM
)

# Declaración explícita de tipos de las APIs de User32

user32 = ctypes.windll.user32

user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL



user32.EnumWindows.argtypes = [EnumWindowsProc_t, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

# Usamos c_void_p para el callback de monitores para evitar el conflicto estricto de ctypes
user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, wintypes.LPRECT, ctypes.c_void_p, wintypes.LPARAM]
user32.EnumDisplayMonitors.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL


# ==============================================================================
# 2. CLASE GAMEMANAGER
# ==============================================================================

class GameManager(QObject):
    CSIDL_DESKTOPDIRECTORY = 0x10
    SW_SHOWNORMAL = 1
    SWP_NOZORDER = 0x0004
    
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    WM_CLOSE = 0x0010
    
    def __init__(self, folder_name: str = "MiCarpeta"):
        super().__init__()
        self.__game_hwnd = None
        self.__stim_hwnd = None
        self.__game_was_minimized = False
        self.desktop = self._get_desktop()
        self.folder = self.desktop / folder_name
        self.folder.mkdir(exist_ok=True)
        self.__screen_info = None

        self.__timer = QTimer(self)
        self.__timer.timeout.connect(self.__update_windows)

    def _get_desktop(self) -> Path:
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(
            None, self.CSIDL_DESKTOPDIRECTORY, None, 0, buf
        )
        return Path(buf.value)

    def list_games(self) -> list[str]:
        """Devuelve los nombres de ejecutables/accesos directos de la carpeta."""
        extensions = (".exe", ".lnk", ".bat")
        return [
            f.stem for f in self.folder.iterdir()
            if f.is_file() and f.suffix.lower() in extensions
        ]

    def load_screen_info(self, info: dict):
        self.__screen_info = info
    def load_hwnd_viewer(self, hwnd: int):
        self.__stim_hwnd = hwnd
        self.__timer.start(500) 
    def _find_file(self, name: str) -> Path | None:
        name = name.lower()
        for f in self.folder.iterdir():
            if f.is_file() and f.stem.lower() == name:
                return f
        return None

    def close_game(self):
        self.__timer.stop()
        if self.__game_hwnd is not None:
            user32.PostMessageW(
                self.__game_hwnd,
                self.WM_CLOSE,
                0,
                0
            )

        self.__game_hwnd = None
    # ---------- Detección de ventana nueva ----------

    @staticmethod
    def _get_open_windows() -> set[int]:
        windows = set()

        def callback(hwnd, lparam):
            if (user32.IsWindowVisible(hwnd)
                    and user32.GetWindowTextLengthW(hwnd) > 0):
                windows.add(hwnd)
            return True

        # Almacenamos la referencia del callback en una variable para que no la barra el Garbage Collector
        callback_inst = EnumWindowsProc_t(callback)
        user32.EnumWindows(callback_inst, 0)
        return windows

    def _wait_new_window(self, before: set[int], timeout: float = 8.0,
                         poll: float = 0.2) -> int | None:
        """Espera a que aparezca una ventana nueva."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(poll)
            new = self._get_open_windows() - before
            if new:
                return next(iter(new))
        return None

    # ---------- Posicionamiento en el espacio libre del monitor ----------

    @staticmethod
    def _get_monitor_rect(monitor_index: int) -> wintypes.RECT | None:
        monitors: list[wintypes.RECT] = []

        def callback(hmonitor, hdc, lprc, lparam):
            r = lprc.contents
            monitors.append(wintypes.RECT(r.left, r.top, r.right, r.bottom))
            return True

        # Protegemos la instancia del callback y la casteamos a void_p para el EnumDisplayMonitors robusto
        callback_inst = MonitorEnumProc_t(callback)
        user32.EnumDisplayMonitors(None, None, ctypes.cast(callback_inst, ctypes.c_void_p), 0)

        if 0 <= monitor_index < len(monitors):
            return monitors[monitor_index]
        return None
    def _position_window(self, hwnd: int):
        """Reposiciona y redimensiona la ventana para ocupar el espacio libre."""
        if self.__screen_info is None:
            print("No se cargó screen_info (load_screen_info). No se puede posicionar.")
            return

        info = self.__screen_info

        monitor_index = info["monitor_index"]
        scale = info["monitor_scale"]
        rect = self._get_monitor_rect(monitor_index)
        if rect is None:
            print(f"No se encontró el monitor con índice {monitor_index}")
            return

        
        screen_heigt = info["height"]
        screen_width = info["width"]
        screen_heigt = int(screen_heigt * scale)
        screen_width = int(screen_width * scale)
        height_margin, width_margin = info["margins"]
        height_margin = int(height_margin * scale)
        width_margin = int(width_margin * scale)
        x = rect.left + width_margin
        y = rect.top + 5
        width = screen_width - width_margin -10
        height = screen_heigt - height_margin -5

        user32.ShowWindow(hwnd, self.SW_SHOWNORMAL)
        user32.SetWindowPos(
            hwnd, None, x, y, width, height, self.SWP_NOZORDER
        )


    # ---------- Apertura del juego ----------

    def open_game(self, name: str) -> bool:
        """Abre el juego y lo reposiciona."""
        file = self._find_file(name)
        if file is None:
            print(f"No se encontró '{name}' en {self.folder}")
            return False

        before = self._get_open_windows()

        try:
            os.startfile(file)
        except OSError as e:
            print(f"Error al abrir '{name}': {e}")
            return False

        hwnd = self._wait_new_window(before)
        if hwnd is None:
            print(f"No se detectó ninguna ventana nueva para '{name}' (timeout)")
            return True

        self._position_window(hwnd)
        self.__game_hwnd = hwnd

        return True
    def place_window(self, hwnd: int):
        """
        Ubica una ventana ya existente (identificada por su hwnd) en el
        espacio libre del monitor, sin pasar por open_game/_wait_new_window.
        Util cuando el hwnd se obtuvo por otra via (ej. una app que ya
        estaba abierta, o un hwnd provisto externamente).
        """
        self._position_window(hwnd)
        self.__game_hwnd = hwnd
    #--------------- control de ventanas ---------------
    def __update_windows(self):
        if self.__game_hwnd is None or self.__stim_hwnd is None:
            return

        minimized = bool(user32.IsIconic(self.__game_hwnd))

        if (
            self.__game_was_minimized
            and not minimized
            and user32.GetForegroundWindow() == self.__game_hwnd
        ):
            user32.SetWindowPos(
                self.__stim_hwnd,
                self.__game_hwnd,
                0, 0, 0, 0,
                self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE
            )

        self.__game_was_minimized = minimized



