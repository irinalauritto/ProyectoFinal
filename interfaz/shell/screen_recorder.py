"""
Graba en video la ventana de AsTeRICS, para evaluar después la factibilidad del uso
del tablero.

Las imágenes las entrega el propio navegador (`Page.startScreencast`), por el mismo
puerto de control con el que se configura AsTeRICS (ver asterics_config.py). Se eligió
esta vía porque:
  * graba solo la página: no incluye los estímulos ni lo que tape a la ventana, y
    no depende de dónde esté ubicada;
  * no muestra nada en la pantalla del paciente: ni ventana, ni ícono, ni aviso de
    "REC". La captura de la pantalla desde el navegador muestra su barra de
    "compartiendo pantalla" y la de Windows (Graphics Capture) un borde amarillo. El
    único indicador de la grabación está en la pantalla del operador;
  * capturar la ventana con ffmpeg (`gdigrab`) da imagen negra con Chrome.
Requiere un navegador Chromium con el perfil propio de la aplicación. No graba la
barra de título de la ventana ni el audio.

El navegador manda una imagen solo cuando algo cambia. Para que el video conserve la
duración real, se le pasa a ffmpeg la última imagen a ritmo fijo (`FPS`). Confirmar
cada imagen recién en ese momento hace que el navegador no genere más de las que se usan.

ffmpeg comprime en un proceso aparte, con prioridad baja para no competir con la
adquisición ni el estimulador. Si la aplicación se cierra de golpe, se cierra su
entrada: ffmpeg termina solo y deja el video legible.

Autora: Irina Lauritto
"""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QWidget

from interfaz.shell import asterics_config as cfg
from interfaz.shell.asterics_launcher import AstericsLauncher

FPS = 15
_JPEG_QUALITY = 80
_CONNECT_TIMEOUT_S = 15
_WINDOW_CHECK_MS = 1000
_STOP_TIMEOUT_S = 5


def build_command(ffmpeg: str, path: Path) -> list[str]:
    """Comando de ffmpeg que convierte en video las imágenes JPEG que recibe por su entrada."""
    return [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "pipe:0",
        # H.264 en yuv420p exige lados pares.
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-g", str(2 * FPS),
        "-movflags", "+frag_keyframe+empty_moov+default_base_moof",
        str(path),
    ]


class ScreenRecorder(QObject):
    """Recibe las imágenes en un hilo y se las pasa a ffmpeg. Avisa con `failed` si
    la grabación se interrumpe sin que se haya pedido."""

    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: Optional[subprocess.Popen] = None
        self._path: Optional[Path] = None
        self._errors = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def is_recording(self) -> bool:
        return self._process is not None

    def start(self, path: Path, port: int) -> Optional[str]:
        """Empieza a grabar. Devuelve None si arrancó, o el motivo por el que no."""
        if self.is_recording():
            return None
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError) as error:
            return f"No se encontró ffmpeg (imageio-ffmpeg): {error}"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._errors = tempfile.TemporaryFile()
            self._process = subprocess.Popen(
                build_command(ffmpeg, path),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=self._errors,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS,
            )
        except OSError as error:
            self._release()
            return str(error)
        self._path = path
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            args=(self._process, self._errors, port, self._stop_event),
            name="grabacion-pantalla",
            daemon=True,
        )
        self._thread.start()
        return None

    def stop(self) -> Optional[Path]:
        """Termina la grabación. Devuelve la ruta del video, o None si no quedó ninguno."""
        process, path = self._process, self._path
        if process is None:
            return None
        self._stop_event.set()
        self._thread.join(timeout=_STOP_TIMEOUT_S)
        try:
            process.stdin.close()  # sin más imágenes, ffmpeg cierra el archivo y termina
            process.wait(timeout=_STOP_TIMEOUT_S)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            process.kill()
            process.wait()
        self._release()
        return path if path.is_file() and path.stat().st_size > 0 else None

    def _release(self) -> None:
        if self._errors is not None:
            self._errors.close()
        self._process, self._path, self._errors, self._thread = None, None, None, None

    def _run(self, process: subprocess.Popen, errors, port: int, stop: threading.Event) -> None:
        try:
            self._stream(process.stdin, port, stop)
        except Exception as exc:  # conexión con el navegador, o ffmpeg que terminó
            if stop.is_set():
                return
            detail = ""
            if process.poll() is not None:
                try:
                    errors.seek(0)
                    detail = errors.read().decode(errors="replace").strip()[-400:]
                except (OSError, ValueError):
                    pass
            self.failed.emit(detail or str(exc) or type(exc).__name__)

    @staticmethod
    def _stream(output, port: int, stop: threading.Event) -> None:
        from websockets.sync.client import connect  # import perezoso

        url = cfg._find_page_ws(port, time.monotonic() + _CONNECT_TIMEOUT_S, stop.is_set)
        with connect(url, max_size=None, open_timeout=_CONNECT_TIMEOUT_S) as ws:
            next_id = 0

            def send(method: str, **params) -> int:
                nonlocal next_id
                next_id += 1
                ws.send(json.dumps({"id": next_id, "method": method, "params": params}))
                return next_id

            def begin() -> int:
                """Pide la transmisión y la imagen actual: una página quieta no
                manda ninguna hasta que algo cambie."""
                send("Page.startScreencast", format="jpeg", quality=_JPEG_QUALITY)
                return send("Page.captureScreenshot", format="jpeg", quality=_JPEG_QUALITY)

            send("Page.enable")
            screenshot_id = begin()
            latest: Optional[bytes] = None
            unconfirmed = None  # imagen pendiente de confirmar al navegador
            next_tick: Optional[float] = None

            while not stop.is_set():
                wait = 0.1 if next_tick is None else max(0.0, next_tick - time.monotonic())
                try:
                    message = json.loads(ws.recv(timeout=wait))
                except TimeoutError:
                    message = {}
                method = message.get("method")
                if method == "Page.screencastFrame":
                    latest = base64.b64decode(message["params"]["data"])
                    unconfirmed = message["params"]["sessionId"]
                elif method == "Page.loadEventFired":
                    screenshot_id = begin()  # la recarga de la página puede cortar la transmisión
                elif message.get("id") == screenshot_id and "result" in message:
                    latest = base64.b64decode(message["result"]["data"])

                if latest is None:
                    continue
                now = time.monotonic()
                if next_tick is None:
                    next_tick = now
                if now < next_tick:
                    continue
                while now >= next_tick:
                    output.write(latest)
                    next_tick += 1 / FPS
                output.flush()
                if unconfirmed is not None:
                    send("Page.screencastFrameAck", sessionId=unconfirmed)
                    unconfirmed = None
            send("Page.stopScreencast")


class ScreenRecordingControl(QObject):
    """Botón "Grabar pantalla", su indicador y la pregunta antes de abrir AsTeRICS.
    Lo comparten las pantallas de EEG y EMG, que lo ubican en su encabezado.

    La grabación sigue a la ventana de AsTeRICS: si se la pide antes de que esté
    abierta, queda pendiente y arranca en ese momento; termina cuando la ventana se
    cierra."""

    def __init__(
        self,
        page: QWidget,
        asterics: AstericsLauncher,
        next_path: Callable[[], Path],
        on_saved: Callable[[Path], None],
    ):
        super().__init__(page)
        self._page = page
        self._asterics = asterics
        self._next_path = next_path
        self._on_saved = on_saved
        self._pending = False
        self._recorder = ScreenRecorder(self)
        self._recorder.failed.connect(self._on_failed)
        asterics.window_placed.connect(self._on_window_placed)
        asterics.window_not_found.connect(self._on_window_not_found)
        self._window_timer = QTimer(self)
        self._window_timer.setInterval(_WINDOW_CHECK_MS)
        self._window_timer.timeout.connect(self._check_window)

        self.label = QLabel("")
        self.label.setObjectName("WarningLabel")
        self.button = QPushButton()
        self.button.setObjectName("SecondaryButton")
        self.button.setToolTip(
            "Graba en video la ventana de AsTeRICS, sin mostrarle ningún aviso al paciente. "
            "Se guarda junto con las señales de la sesión."
        )
        self.button.clicked.connect(self._on_clicked)
        self._refresh()

    def is_recording(self) -> bool:
        return self._recorder.is_recording()

    def ask_before_asterics(self) -> None:
        """Pregunta si se quiere grabar, salvo que ya se haya pedido. El diálogo
        depende de la página, así que aparece en la pantalla del operador."""
        if self.is_recording() or self._pending:
            return
        answer = QMessageBox.question(
            self._page,
            "Grabar pantalla",
            "¿Grabar la ventana de AsTeRICS mientras se usa?\n\n"
            "En la pantalla del paciente no aparece ningún aviso de grabación.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.start()

    def start(self) -> None:
        """Graba ya si AsTeRICS está abierta; si no, cuando lo esté."""
        if self.is_recording():
            return
        if not self._asterics.is_open():
            self._pending = True
            self._refresh()
            return
        self._pending = False
        port = self._asterics.debug_port()
        if port is None:
            error = "Hace falta que AsTeRICS se abra con Chrome, Edge, Brave o Vivaldi."
        else:
            try:
                error = self._recorder.start(self._next_path(), port)
            except OSError as exc:
                error = str(exc)
        if error is None:
            self._window_timer.start()
        else:
            self._warn(error)
        self._refresh()

    def stop(self) -> None:
        """Termina la grabación o cancela la pendiente."""
        self._pending = False
        self._window_timer.stop()
        path = self._recorder.stop()
        if path is not None:
            self._on_saved(path)
        self._refresh()

    def _on_clicked(self) -> None:
        if self.is_recording() or self._pending:
            self.stop()
        else:
            self.start()

    def _on_window_placed(self) -> None:
        if self._pending:
            self.start()

    def _on_window_not_found(self) -> None:
        if self._pending:
            self.stop()
            self._warn("No se detectó la ventana de AsTeRICS.")

    def _check_window(self) -> None:
        if not self._asterics.is_open():
            self.stop()

    def _on_failed(self, motivo: str) -> None:
        window_open = self._asterics.is_open()
        self.stop()  # conserva lo grabado hasta acá
        if window_open:  # si se cerró AsTeRICS, es el final normal de la grabación
            self._warn(motivo)

    def _refresh(self) -> None:
        if self.is_recording():
            self.button.setText("Detener grabación")
            self.label.setText("● Grabando AsTeRICS")
        elif self._pending:
            self.button.setText("Cancelar grabación")
            self.label.setText("Grabará cuando AsTeRICS esté abierta")
        else:
            self.button.setText("Grabar pantalla")
            self.label.setText("")

    def _warn(self, motivo: str) -> None:
        QMessageBox.warning(self._page, "Grabar pantalla", f"No se pudo grabar la pantalla:\n\n{motivo}")
