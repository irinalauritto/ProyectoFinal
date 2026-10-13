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
import threading
import webbrowser
import winreg
from ctypes import wintypes
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

# Dirección de AsTeRICS Grid. Es una constante a propósito: si cambia el
# sitio, se corrige solo acá.
ASTERICS_URL = "https://grid.asterics.eu"

_CHROMIUM_EXES = {"chrome.exe", "msedge.exe", "brave.exe", "vivaldi.exe"}
_CHROMIUM_CLASS = "Chrome_WidgetWin_1"
_FIREFOX_CLASS = "MozillaWindowClass"

_POLL_INTERVAL_MS = 400
_POLL_MAX_ATTEMPTS = 40  # ~16 s para que el navegador cree la ventana
_CLOSE_CHECK_MS = 1500  # cada cuánto se verifica que la ventana se cerró
_CLOSE_MAX_RETRIES = 4
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


def _window_visible(hwnd: int) -> bool:
    """Existe Y está visible. Una ventana de Chrome recién cerrada puede
    seguir existiendo, oculta, mientras el proceso termina: no cuenta."""
    return bool(_user32.IsWindow(hwnd)) and bool(_user32.IsWindowVisible(hwnd))


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

    # (ok, mensaje) al terminar de configurar AsTeRICS (ver asterics_config.py).
    configured = Signal(bool, str)
    _worker_done = Signal(bool, str, int)  # uso interno: (ok, mensaje, generacion)

    def __init__(self, url: str = ASTERICS_URL, parent=None):
        super().__init__(parent)
        self._url = url
        self._debug_port: Optional[int] = None  # puerto de control remoto (perfil propio)
        self._config_busy = False
        self._config_generation = -1  # apertura a la que pertenece la configuracion en curso
        self._pending_settings = None
        self._generation = 0  # invalida resultados de configuraciones de una apertura anterior
        self._worker_done.connect(self._on_worker_done)
        self._hwnd: Optional[int] = None
        self._owned = False  # True: ventana propia (modo aplicación), se puede cerrar
        self._original: Optional[tuple[tuple[int, int, int, int], bool]] = None  # (rect, maximizada)
        self._place: Optional[Callable[[int], None]] = None
        self._before: set[int] = set()
        self._app_mode = False
        self._attempts = 0
        self._close_when_found = False
        self._launching = False  # lanzado, pero su ventana todavia no apareció
        self._closing: Optional[tuple[int, int, Optional[int]]] = None  # (hwnd, intento, puerto)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._replace_timer = QTimer(self)
        self._replace_timer.setSingleShot(True)
        self._replace_timer.timeout.connect(self._replace)

    # ------------------------------------------------------------------
    def is_open(self) -> bool:
        return self._hwnd is not None and _window_visible(self._hwnd)

    def open(self, place: Optional[Callable[[int], None]] = None, settings=None) -> bool:
        """Abre AsTeRICS. `place(hwnd)`, si se pasa, se llama cuando se
        detecta la ventana, para ubicarla. `settings`
        (asterics_config.AstericsInputSettings), si se pasa, configura
        AsTeRICS (método de entrada, tiempo de barrido, pulsación) en un
        hilo aparte y avisa con la señal `configured`; requiere un navegador
        Chromium (se abre con un perfil propio que conserva los cambios del
        profesional). Devuelve False si no se pudo lanzar el navegador. Si ya
        está abierta por este objeto, solo la trae al frente (y la vuelve a
        ubicar y configurar)."""
        reuse_pending = self._close_when_found and self._poll_timer.isActive()
        self._close_when_found = False
        if self._closing is not None:
            closing_hwnd, _attempt, closing_port = self._closing
            self._closing = None
            if _window_visible(closing_hwnd) and self._hwnd is None:
                # El cierre pedido todavía no se concretó: se la reutiliza.
                self._hwnd, self._owned, self._debug_port = closing_hwnd, True, closing_port
        if self.is_open():
            _user32.ShowWindow(self._hwnd, _SW_RESTORE)
            _user32.SetForegroundWindow(self._hwnd)
            if place is not None:
                self._place = place
                self._apply_place(self._hwnd)
            if settings is not None:
                self.apply_settings(settings)
            return True

        if reuse_pending:
            # Se abrió y se cerró antes de que el navegador creara la ventana:
            # esa ventana está por aparecer, se la reutiliza en vez de lanzar
            # otra (quedarían dos).
            self._place = place
            self._generation += 1
            if settings is not None and self._debug_port is not None:
                self._run_config(settings)
            return True

        self._place = place
        self._hwnd = None
        self._before = {hwnd for hwnd, _title, _cls in _list_windows()}
        self._generation += 1
        if not self._launch(settings):
            return False
        self._attempts = 0
        self._launching = self._app_mode
        self._poll_timer.start(_POLL_INTERVAL_MS)
        return True

    def close(self) -> None:
        """Cierra la ventana propia; si era una pestaña, solo devuelve su
        ventana a la posición que tenía. No hace nada si no hay nada abierto."""
        self._poll_timer.stop()
        self._replace_timer.stop()
        self._generation += 1  # descarta una configuracion en curso
        self._pending_settings = None
        hwnd, owned, original = self._hwnd, self._owned, self._original
        pending_app = self._launching and hwnd is None
        closing_port = self._debug_port
        if not pending_app:
            self._debug_port = None  # (si la ventana aun no aparecio se lo conserva por si se reabre)
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
            self._request_close(hwnd, 0, closing_port)
        elif original is not None:
            set_topmost(hwnd, False)
            self._restore(hwnd, *original)

    # ------------------------------------------------------------------
    def _request_close(self, hwnd: int, attempt: int, port: Optional[int]) -> None:
        """Pide cerrar la ventana y verifica: el navegador puede ignorar el
        primer cierre (por ejemplo, mientras recarga la página), así que se
        reintenta unas veces hasta que desaparece."""
        self._closing = (hwnd, attempt, port)
        _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
        QTimer.singleShot(_CLOSE_CHECK_MS, self._verify_closed)

    def _verify_closed(self) -> None:
        if self._closing is None:
            return
        hwnd, attempt, port = self._closing
        if not _window_visible(hwnd):
            self._closing = None
        elif attempt >= _CLOSE_MAX_RETRIES:
            self._closing = None  # no responde: se la deja (el profesional puede cerrarla)
        else:
            self._request_close(hwnd, attempt + 1, port)

    def _launch(self, settings=None) -> bool:
        exe = _default_browser_exe()
        self._app_mode = _is_chromium(exe)
        try:
            if self._app_mode:
                args = [exe]
                if settings is not None:
                    # Perfil propio + puerto de control local: permite
                    # configurar AsTeRICS sin tocar el Chrome habitual.
                    from interfaz.shell import asterics_config as cfg

                    profile = cfg.profile_dir()
                    profile.mkdir(parents=True, exist_ok=True)
                    # Reutiliza la instancia viva del perfil (o espera a que una
                    # que se está cerrando termine): ver asterics_config.py.
                    self._debug_port, _ = cfg.choose_debug_port()
                    args += [
                        f"--user-data-dir={profile}",
                        f"--remote-debugging-port={self._debug_port}",
                        f"--remote-allow-origins=http://127.0.0.1:{self._debug_port}",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ]
                args.append(f"--app={self._url}")
                subprocess.Popen(args)
                if settings is not None:
                    self._run_config(settings)
                return True
            opened = bool(webbrowser.open(self._url))
            if opened and settings is not None:
                self.configured.emit(
                    False,
                    "La configuración automática de AsTeRICS requiere Chrome, Edge, Brave o Vivaldi "
                    "como navegador predeterminado.",
                )
            return opened
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Configuracion de AsTeRICS (en un hilo, para no bloquear la interfaz)
    def apply_settings(self, settings) -> bool:
        """Reaplica la configuración con AsTeRICS ya abierta por este objeto.
        False si no hay una ventana propia con control remoto."""
        if self._debug_port is None:
            return False
        self._run_config(settings)
        return True

    def _run_config(self, settings) -> None:
        if self._config_busy and self._config_generation == self._generation:
            self._pending_settings = settings  # se aplica al terminar la actual (queda la ultima)
            return
        # Un trabajo de una apertura anterior que siga vivo no bloquea a esta:
        # se cancela solo (ver `cancelled`) y su resultado se descarta.
        self._config_busy = True
        self._config_generation = self._generation
        port, generation = self._debug_port, self._generation

        def work() -> None:
            from interfaz.shell import asterics_config as cfg

            ok, message = cfg.configure(port, settings, cancelled=lambda: generation != self._generation)
            self._worker_done.emit(ok, message, generation)

        threading.Thread(target=work, name="asterics-config", daemon=True).start()

    def _on_worker_done(self, ok: bool, message: str, generation: int) -> None:
        if generation != self._generation:
            return  # se cerró (o reabrió) AsTeRICS mientras se configuraba; no es de esta apertura
        self._config_busy = False
        self.configured.emit(ok, message)
        pending, self._pending_settings = self._pending_settings, None
        if pending is not None and self._debug_port is not None:
            self._run_config(pending)

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
                self._launching = False
            return
        self._poll_timer.stop()
        self._launching = False
        if self._close_when_found:
            self._close_when_found = False
            self._request_close(hwnd, 0, self._debug_port)
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
