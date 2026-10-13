"""
Preparación de AsTeRICS para un paciente, desde la pantalla de Inicio.

El terapeuta abre AsTeRICS (en el perfil propio del paciente), inicia sesión o
usa "sin registrarse", carga el tablero y lo selecciona. Como AsTeRICS ocupa
toda la pantalla, el aviso de "terminé" es un botón flotante que se muestra
DENTRO de su página (ver asterics_config.wait_setup_done); al presionarlo, la
ventana se cierra sola y la interfaz habilita la elección de modalidad.

La ventana se abre maximizada en el monitor del TERAPEUTA: el mismo donde está
esta aplicación (la segunda apertura, durante la sesión, va al monitor del
paciente: ver asterics_launcher.patient_monitor_area).

Solo funciona con un navegador Chromium como predeterminado (Chrome, Edge,
Brave, Vivaldi): hace falta su puerto de control. Con otro navegador `start()`
devuelve False y el llamador decide cómo seguir.

Autora: Irina Lauritto
"""

from __future__ import annotations

import subprocess
import threading
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from interfaz.shell import asterics_config as cfg
from interfaz.shell.asterics_launcher import (
    _CHROMIUM_CLASS,
    _POLL_INTERVAL_MS,
    _POLL_MAX_ATTEMPTS,
    _REPLACE_DELAY_MS,
    ASTERICS_URL,
    _default_browser_exe,
    _is_chromium,
    _list_windows,
    _window_exists,
    monitor_area_of_window,
    place_maximized,
)


def is_supported() -> bool:
    """True si el navegador predeterminado permite la preparación guiada."""
    return _is_chromium(_default_browser_exe())


class AstericsSetup(QObject):
    """Abre AsTeRICS en el perfil activo y avisa cuando el profesional terminó."""

    # (configurada, mensaje) al terminar. Si no se pudo, `mensaje` dice por qué.
    finished = Signal(bool, str)
    _done = Signal(bool, str, int)  # uso interno: (ok, mensaje, generacion)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._generation = 0
        self._done.connect(self._on_done)

        # Ubicación de la ventana: se la busca por sondeo (Windows no devuelve
        # la que crea el navegador) y se la lleva al monitor del terapeuta.
        self._area: Optional[tuple[int, int, int, int]] = None
        self._before: set[int] = set()
        self._attempts = 0
        self._hwnd: Optional[int] = None
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._replace_timer = QTimer(self)
        self._replace_timer.setSingleShot(True)
        self._replace_timer.timeout.connect(self._replace)

    def is_running(self) -> bool:
        return self._running

    def start(self, anchor_hwnd: Optional[int] = None) -> bool:
        """Lanza AsTeRICS con el perfil del paciente activo, maximizada en el
        monitor de la ventana `anchor_hwnd` (la de esta aplicación). False si
        no se pudo (navegador no Chromium o error al lanzarlo). Si ya hay una
        preparación en curso, no hace nada y devuelve True."""
        if self._running:
            return True
        exe = _default_browser_exe()
        if not _is_chromium(exe):
            return False
        profile = cfg.profile_dir()
        self._area = monitor_area_of_window(anchor_hwnd) if anchor_hwnd else None
        self._before = {hwnd for hwnd, _title, _cls in _list_windows()}
        try:
            profile.mkdir(parents=True, exist_ok=True)
            # Reutiliza la instancia viva del perfil (o espera a que una que se
            # está cerrando termine): ver asterics_config.choose_debug_port.
            port, _existing = cfg.choose_debug_port()
            subprocess.Popen([
                exe,
                f"--user-data-dir={profile}",
                f"--remote-debugging-port={port}",
                f"--remote-allow-origins=http://127.0.0.1:{port}",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized",
                f"--app={ASTERICS_URL}",
            ])
        except OSError:
            return False

        self._running = True
        self._generation += 1
        generation = self._generation
        self._attempts = 0
        self._hwnd = None
        self._poll_timer.start(_POLL_INTERVAL_MS)

        def work() -> None:
            ok, message = cfg.wait_setup_done(port, cancelled=lambda: generation != self._generation)
            self._done.emit(ok, message, generation)

        threading.Thread(target=work, name="asterics-setup", daemon=True).start()
        return True

    def cancel(self) -> None:
        """Abandona la espera (no cierra la ventana: eso lo decide el profesional)."""
        self._generation += 1
        self._running = False
        self._stop_timers()

    # ------------------------------------------------------------------
    def _stop_timers(self) -> None:
        self._poll_timer.stop()
        self._replace_timer.stop()

    def _find_window(self) -> Optional[int]:
        for hwnd, title, class_name in _list_windows():
            if "asterics" in title.lower() and class_name == _CHROMIUM_CLASS and hwnd not in self._before:
                return hwnd
        return None

    def _poll(self) -> None:
        self._attempts += 1
        hwnd = self._find_window()
        if hwnd is None:
            if self._attempts >= _POLL_MAX_ATTEMPTS:
                self._poll_timer.stop()
            return
        self._poll_timer.stop()
        self._hwnd = hwnd
        place_maximized(hwnd, self._area)
        # Algunos navegadores reaplican su posición guardada al terminar de abrir.
        self._replace_timer.start(_REPLACE_DELAY_MS)

    def _replace(self) -> None:
        if self._hwnd is not None and _window_exists(self._hwnd):
            place_maximized(self._hwnd, self._area)

    def _on_done(self, ok: bool, message: str, generation: int) -> None:
        if generation != self._generation:
            return  # cancelada o reemplazada
        self._running = False
        self._stop_timers()
        self.finished.emit(ok, message)
