"""
Script encargado de abrir AsTeRICS ACC (aplicación web) desde la interfaz, usando el
navegador predeterminado del equipo.

Dos modos de apertura:
  * Si el navegador predeterminado es Chromium (Chrome, Edge, Brave, Vivaldi)
    se abre en "modo aplicación" (`--app=URL`): una ventana propia, sin
    pestañas ni barra de direcciones, que se puede ubicar y cerrar sin tocar
    nada más del navegador.
  * Con cualquier otro navegador se abre como pestaña
    (`webbrowser.open`). Su ventana solo se puede ubicar en Firefox (única
    detección soportada) y nunca se cierra: al terminar solo se la devuelve
    a su posición original.

Windows no devuelve la ventana que crea el navegador, así que se la busca por
sondeo (QTimer, sin bloquear la interfaz): en modo aplicación, una ventana
Chromium NUEVA (que no existía antes de lanzar) con "asterics" en el título;
en Firefox, una ventana cuyo título contenga "asterics". No se busca por
título en cualquier ventana: un editor con un archivo "asterics_*.py" abierto
(VS Code también es Chromium) se confundiría con la aplicación.

Se recomienda para el uso de esta aplicación tener como predeterminado un navegador Chromium, para una mejor experiencia.

Autora: Irina Lauritto

"""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import webbrowser
import winreg
from ctypes import wintypes
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer

# Dirección de AsTeRICS Grid. Es una constante a propósito: si cambia el
# sitio, se corrige solo acá.
ASTERICS_URL = "https://grid.asterics.eu"

_CHROMIUM_EXES = {"chrome.exe", "msedge.exe", "brave.exe", "vivaldi.exe"}
_CHROMIUM_CLASS = "Chrome_WidgetWin_1"
_FIREFOX_CLASS = "MozillaWindowClass"

_POLL_INTERVAL_MS = 400
_POLL_MAX_ATTEMPTS = 40  # ~16 s para que el navegador cree la ventana
_REPLACE_DELAY_MS = 1500  # algunos navegadores reaplican su posición guardada al terminar de abrir

_SW_MAXIMIZE = 3
_SW_RESTORE = 9
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_HWND_TOPMOST = -1
_HWND_NOTOPMOST = -2
_WM_CLOSE = 0x0010

# user32 propio (WinDLL nuevo): ctypes.windll.user32 es un objeto compartido y
# otros módulos (game_manager.py) le fijan sus propios prototipos.
_user32 = ctypes.WinDLL("user32")
_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

_user32.EnumWindows.argtypes = [_EnumWindowsProc, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
for _name in ("IsWindowVisible", "IsWindow", "IsZoomed", "SetForegroundWindow"):
    getattr(_user32, _name).argtypes = [wintypes.HWND]
    getattr(_user32, _name).restype = wintypes.BOOL
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
_user32.SetWindowPos.restype = wintypes.BOOL
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL


def _list_windows() -> list[tuple[int, str, str]]:
    """Ventanas visibles con título de otros procesos: (hwnd, título, clase)."""
    found: list[tuple[int, str, str]] = []
    own_pid = os.getpid()

    def callback(hwnd, _lparam):
        if _user32.IsWindowVisible(hwnd):
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                title = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, title, length + 1)
                class_name = ctypes.create_unicode_buffer(256)
                _user32.GetClassNameW(hwnd, class_name, 256)
                pid = wintypes.DWORD()
                _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != own_pid:
                    found.append((int(hwnd), title.value, class_name.value))
        return True

    callback_ref = _EnumWindowsProc(callback)  # referencia viva mientras dura EnumWindows
    _user32.EnumWindows(callback_ref, 0)
    return found


def _window_exists(hwnd: int) -> bool:
    return bool(_user32.IsWindow(hwnd))


def _get_rect(hwnd: int) -> Optional[tuple[int, int, int, int]]:
    rect = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def _default_browser_exe() -> Optional[str]:
    """Ejecutable del navegador predeterminado para enlaces https, leído del
    registro (ProgId elegido por el usuario -> su comando de apertura)."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
        ) as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
            command = winreg.QueryValueEx(key, "")[0]
    except OSError:
        return None
    match = re.match(r'\s*"([^"]+)"', command) or re.match(r"\s*(\S+)", command)
    return match.group(1) if match else None


def set_topmost(hwnd: int, on: bool = True) -> None:
    """Mantiene una ventana por encima de las demás (en particular de la del
    estimulador, que ocupa todo el monitor y, al recibir un clic, quedaría
    delante y la taparía) o la devuelve al orden normal."""
    _user32.SetWindowPos(
        hwnd, _HWND_TOPMOST if on else _HWND_NOTOPMOST, 0, 0, 0, 0,
        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE,
    )


def _is_chromium(exe: Optional[str]) -> bool:
    return bool(exe) and os.path.basename(exe).lower() in _CHROMIUM_EXES and os.path.isfile(exe)


class AstericsLauncher(QObject):
    """Abre AsTeRICS y, opcionalmente, ubica su ventana (ver docstring del
    módulo). Todo corre en el hilo de Qt."""

    def __init__(self, url: str = ASTERICS_URL, parent=None):
        super().__init__(parent)
        self._url = url
        self._hwnd: Optional[int] = None
        self._owned = False  # True: ventana propia (modo aplicación), se puede cerrar
        self._original: Optional[tuple[tuple[int, int, int, int], bool]] = None  # (rect, maximizada)
        self._place: Optional[Callable[[int], None]] = None
        self._before: set[int] = set()
        self._app_mode = False
        self._attempts = 0
        self._close_when_found = False

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._replace_timer = QTimer(self)
        self._replace_timer.setSingleShot(True)
        self._replace_timer.timeout.connect(self._replace)

    # ------------------------------------------------------------------
    def is_open(self) -> bool:
        return self._hwnd is not None and _window_exists(self._hwnd)

    def open(self, place: Optional[Callable[[int], None]] = None) -> bool:
        """Abre AsTeRICS. `place(hwnd)`, si se pasa, se llama cuando se
        detecta la ventana, para ubicarla. Devuelve False si no se pudo
        lanzar el navegador. Si ya está abierta por este objeto, solo la trae
        al frente (y la vuelve a ubicar)."""
        self._close_when_found = False
        if self.is_open():
            _user32.ShowWindow(self._hwnd, _SW_RESTORE)
            _user32.SetForegroundWindow(self._hwnd)
            if place is not None:
                self._place = place
                self._apply_place(self._hwnd)
            return True

        self._place = place
        self._hwnd = None
        self._before = {hwnd for hwnd, _title, _cls in _list_windows()}
        if not self._launch():
            return False
        self._attempts = 0
        self._poll_timer.start(_POLL_INTERVAL_MS)
        return True

    def close(self) -> None:
        """Cierra la ventana propia; si era una pestaña, solo devuelve su
        ventana a la posición que tenía. No hace nada si no hay nada abierto."""
        self._poll_timer.stop()
        self._replace_timer.stop()
        hwnd, owned, original = self._hwnd, self._owned, self._original
        pending_app = self._app_mode and hwnd is None and self._attempts > 0
        self._hwnd, self._owned, self._original, self._place = None, False, None, None

        if hwnd is None:
            if pending_app:
                # El navegador todavía no había creado la ventana: se la
                # sigue esperando solo para cerrarla apenas aparezca.
                self._close_when_found = True
                self._poll_timer.start(_POLL_INTERVAL_MS)
            return
        if not _window_exists(hwnd):
            return
        if owned:
            _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
        elif original is not None:
            set_topmost(hwnd, False)
            self._restore(hwnd, *original)

    # ------------------------------------------------------------------
    def _launch(self) -> bool:
        exe = _default_browser_exe()
        self._app_mode = _is_chromium(exe)
        try:
            if self._app_mode:
                subprocess.Popen([exe, f"--app={self._url}"])
                return True
            return bool(webbrowser.open(self._url))
        except OSError:
            return False

    def _find_window(self) -> Optional[int]:
        for hwnd, title, class_name in _list_windows():
            if "asterics" not in title.lower():
                continue
            if self._app_mode and class_name == _CHROMIUM_CLASS and hwnd not in self._before:
                return hwnd
            if not self._app_mode and class_name == _FIREFOX_CLASS:
                return hwnd
        return None

    def _poll(self) -> None:
        self._attempts += 1
        hwnd = self._find_window()
        if hwnd is None:
            if self._attempts >= _POLL_MAX_ATTEMPTS:
                self._poll_timer.stop()
                self._close_when_found = False
            return
        self._poll_timer.stop()
        if self._close_when_found:
            self._close_when_found = False
            _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            return
        self._adopt(hwnd)

    def _adopt(self, hwnd: int) -> None:
        self._hwnd = hwnd
        self._owned = self._app_mode
        if not self._owned:
            rect = _get_rect(hwnd)
            if rect is not None:
                self._original = (rect, bool(_user32.IsZoomed(hwnd)))
        if self._place is not None:
            self._apply_place(hwnd)
            self._replace_timer.start(_REPLACE_DELAY_MS)

    def _apply_place(self, hwnd: int) -> None:
        """Ubica la ventana y la deja siempre visible (por encima del estimulador)."""
        self._place(hwnd)
        set_topmost(hwnd, True)

    def _replace(self) -> None:
        if self._place is not None and self._hwnd is not None and _window_exists(self._hwnd):
            self._apply_place(self._hwnd)

    @staticmethod
    def _restore(hwnd: int, rect: tuple[int, int, int, int], was_maximized: bool) -> None:
        if was_maximized:
            _user32.ShowWindow(hwnd, _SW_MAXIMIZE)
            return
        x, y, w, h = rect
        _user32.SetWindowPos(hwnd, None, x, y, w, h, _SWP_NOZORDER | _SWP_NOACTIVATE)
