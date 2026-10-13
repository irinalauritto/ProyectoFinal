"""Configura AsTeRICS Grid desde la interfaz: método de entrada, tiempo de
barrido y duración mínima de la pulsación.

AsTeRICS no ofrece una API para esto, pero guarda su configuración en una base
local del navegador (PouchDB sobre IndexedDB). Con un perfil de navegador
PROPIO de la aplicación (carpeta `profile_dir()`), abierto con el puerto de
depuración de Chromium, se la puede leer y escribir:

  1. Se espera a que AsTeRICS cargue.
  2. Primera vez (perfil nuevo): se crea el usuario "sin registro" y se carga
     el tablero "ARASAAC Comunicador Global Grid Core". Después, el profesional puede
     modificar todo a mano: el perfil conserva sus cambios.
  3. Se escribe el bloque `inputConfig` del documento "MetaData" y se recarga
     la página para que AsTeRICS lo tome.

Los selectores de la primera apertura no dependen del idioma de AsTeRICS
(primer `button.big-button` y botón principal de la tarjeta del tablero).

Nada de lo que esté fuera de `inputConfig` se modifica. Si AsTeRICS cambia su
formato interno, `configure()` devuelve `(False, motivo)` y el llamador debe
avisar y seguir abriendo AsTeRICS sin configurar.
"""

from __future__ import annotations

import itertools
import json
import os
import socket
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

ASTERICS_ORIGIN = "https://grid.asterics.eu"
# Tablero que se carga la primera vez, en orden de preferencia. Se busca por
# palabras del título (sin distinguir mayúsculas), porque el título se traduce
# según el idioma de AsTeRICS ("ARASAAC Comunicador Global Grid Core" en español).
DEFAULT_BOARD_KEYWORDS = (
    ("arasaac", "grid core"),       # Comunicador Global ARASAAC (el que se quiere)
    ("asterics grid default",),     # respaldo: el tablero básico de AsTeRICS
)
DEFAULT_BOARD_NAME = "ARASAAC Comunicador Global Grid Core"

MODES = ("barrido", "secuencial", "direccional")

# La pulsación mínima que exige AsTeRICS es esta fracción de la duración de la
# tecla que envía la interfaz: así la pulsación real siempre la supera.
HOLD_RATIO = 0.6
MIN_HOLD_MS = 50

DEFAULT_SCAN_TIME_S = 1.5


@dataclass(frozen=True)
class AstericsInputSettings:
    """Lo que la interfaz le pide a AsTeRICS."""

    mode: str = "barrido"            # "barrido" | "secuencial" | "direccional"
    scan_time_ms: int = int(DEFAULT_SCAN_TIME_S * 1000)  # solo barrido
    key_hold_ms: int = 250           # duración de la tecla que manda la interfaz

    @property
    def hold_ms(self) -> int:
        """`holdDuration` de AsTeRICS: siempre menor que la pulsación real."""
        return max(MIN_HOLD_MS, round(self.key_hold_ms * HOLD_RATIO))


def profile_dir() -> Path:
    """Carpeta del perfil propio de AsTeRICS (fuera del repositorio)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "ComandoAAC" / "asterics_profile"


_LOG_MAX_BYTES = 100_000


def _log(message: str) -> None:
    """Registro de diagnóstico (`asterics_config.log`, junto al perfil). Nunca
    debe romper la configuración: cualquier error de escritura se ignora."""
    try:
        path = profile_dir().parent / "asterics_config.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > _LOG_MAX_BYTES:
            path.write_text("", encoding="utf-8")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except Exception:
        pass


def free_port() -> int:
    """Un puerto local libre para el control remoto del navegador."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ----------------------------------------------------------------------
# Una sola instancia de Chrome por perfil
# ----------------------------------------------------------------------
# Chrome no abre dos procesos para el mismo perfil: si ya hay uno (o se está
# cerrando), un segundo lanzamiento se le ENTREGA y su puerto de depuración
# nuevo se ignora. Por eso hay que reutilizar el puerto de la instancia viva
# y, si se está cerrando, esperar a que termine antes de lanzar otra.

def _port_file() -> Path:
    return profile_dir().parent / "asterics_debug_port.txt"


def _port_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.7):
            return True
    except Exception:
        return False


def reusable_port() -> Optional[int]:
    """Puerto de control de una instancia de Chrome ya abierta con nuestro
    perfil, o None si no hay ninguna que responda."""
    try:
        port = int(_port_file().read_text().strip())
    except Exception:
        return None
    return port if _port_alive(port) else None


def remember_port(port: int) -> None:
    try:
        _port_file().parent.mkdir(parents=True, exist_ok=True)
        _port_file().write_text(str(port))
    except Exception:
        pass


def profile_processes() -> list:
    """Procesos de navegador que están usando nuestro perfil."""
    try:
        import psutil
    except ImportError:
        return []
    needle = str(profile_dir()).lower()
    found = []
    for proc in psutil.process_iter(["cmdline"]):
        try:
            if any(needle in str(arg).lower() for arg in (proc.info["cmdline"] or [])):
                found.append(proc)
        except Exception:
            continue
    return found


def wait_profile_free(timeout: float = 6.0) -> bool:
    """Espera a que termine una instancia que se está cerrando. Devuelve
    True si el perfil quedó libre."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not profile_processes():
            return True
        time.sleep(0.2)
    return not profile_processes()


def profile_has_window() -> bool:
    """True si alguna instancia del perfil tiene una ventana visible (una
    instancia sin ventanas se está cerrando o es un proceso en segundo plano)."""
    pids = {p.pid for p in profile_processes()}
    if not pids:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32")
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            found.append(hwnd)
        return True

    keep = callback_type(callback)  # referencia viva durante EnumWindows
    user32.EnumWindows(keep, 0)
    return bool(found)


def choose_debug_port() -> tuple[int, bool]:
    """Puerto a usar en este lanzamiento: `(puerto, instancia_existente)`.

    Un segundo lanzamiento con el mismo perfil se entrega a la instancia viva.
    Pero si esa instancia ya no tiene ventanas, probablemente se está cerrando
    (acaba de cerrarse AsTeRICS): entregarle una ventana nueva la haría
    desaparecer junto con ella, sin configurar. Hay que esperar a que termine."""
    port = reusable_port()
    if port is not None:
        if profile_has_window():
            _log(f"se reutiliza la instancia abierta (puerto {port})")
            return port, True
        if wait_profile_free(timeout=4.0):
            _log("la instancia anterior terminó de cerrarse; se lanza una nueva")
        elif reusable_port() == port:
            _log(f"instancia en segundo plano, se reutiliza (puerto {port})")
            return port, True
    elif not wait_profile_free():
        _log("el perfil sigue en uso por un proceso que no responde; se lanza igual")
    port = free_port()
    remember_port(port)
    return port, False


# ----------------------------------------------------------------------
# Parte pura: qué se escribe en `inputConfig` (testeable sin navegador)
# ----------------------------------------------------------------------
def apply_to_input_config(input_config: dict, settings: AstericsInputSettings) -> bool:
    """Modifica `input_config` en el lugar según `settings`. Devuelve True si
    algún valor cambió. Solo toca los interruptores de modo y, en barrido, el
    barrido automático, su tiempo y la pulsación mínima de "SELECT"."""
    if settings.mode not in MODES:
        raise ValueError(f"Método de entrada desconocido: {settings.mode!r}")
    changed = False

    def put(key: str, value) -> None:
        nonlocal changed
        if input_config.get(key) != value:
            input_config[key] = value
            changed = True

    # Un solo método activo a la vez (los campos *Enabled pueden no existir
    # todavía en el documento: se escriben siempre de forma explícita).
    put("scanEnabled", settings.mode == "barrido")
    put("seqEnabled", settings.mode == "secuencial")
    put("dirEnabled", settings.mode == "direccional")

    if settings.mode == "barrido":
        put("scanAuto", True)
        put("scanTimeoutMs", int(settings.scan_time_ms))
        for event in input_config.get("scanInputs", []):
            if event.get("label") == "SELECT":
                if event.get("holdDuration") != settings.hold_ms:
                    event["holdDuration"] = settings.hold_ms
                    changed = True
    elif settings.mode == "secuencial":
        # Se avanza con las flechas que manda la interfaz, no por tiempo.
        put("seqAuto", False)
    return changed


# ----------------------------------------------------------------------
# Conexión con el navegador (protocolo de depuración de Chromium)
# ----------------------------------------------------------------------
class AstericsConfigError(Exception):
    """No se pudo configurar AsTeRICS (el mensaje se muestra al profesional)."""


class _Page:
    """Cliente mínimo del protocolo de depuración, sobre una pestaña/ventana."""

    def __init__(self, ws_url: str):
        from websockets.sync.client import connect  # import perezoso

        self._ws = connect(ws_url, max_size=None, open_timeout=10)
        self._ids = itertools.count(1)

    def call(self, method: str, **params):
        msg_id = next(self._ids)
        self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self._ws.recv(timeout=30))
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise AstericsConfigError(f"Error del navegador: {msg['error']}")
                return msg["result"]

    def eval(self, expression: str, attempts: int = 4):
        """Evalúa JavaScript en la página. Mientras la página navega o se
        recarga, el navegador responde con errores pasajeros (contexto
        destruido, objeto aún no definido): se reintenta unas veces antes de
        darse por vencido."""
        last = ""
        for _ in range(attempts):
            try:
                result = self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
            except AstericsConfigError as exc:
                last = str(exc)
            else:
                if "exceptionDetails" not in result:
                    return result["result"].get("value")
                detail = result["exceptionDetails"]
                last = str(detail.get("exception", {}).get("description") or detail.get("text") or "")[:200]
            time.sleep(0.5)
        _log(f"evaluación fallida: {last}")
        raise AstericsConfigError("Error al ejecutar código en la página de AsTeRICS.")

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


_JS_STATE = (
    "JSON.stringify({hash: location.hash, ready: document.readyState === 'complete',"
    " pouch: typeof PouchDB !== 'undefined', user: localStorage.getItem('LAST_ACTIVEUSER_KEY')})"
)
_JS_CLICK_WELCOME = (
    "(() => { const b = document.querySelector('button.big-button'); if (!b) return false; b.click(); return true; })()"
)
_JS_USE_DEFAULT_BOARD = (
    "(() => {"
    f" const wanted = {json.dumps([list(keys) for keys in DEFAULT_BOARD_KEYWORDS])};"
    " const titles = [...document.querySelectorAll('strong')];"
    " for (const keys of wanted) {"
    "   const s = titles.find(e => { const t = (e.innerText || '').toLowerCase(); return keys.every(k => t.includes(k)); });"
    "   if (!s) continue;"
    "   let c = s; for (let i = 0; i < 8 && c && c.tagName !== 'LI'; i++) c = c.parentElement;"
    "   const b = c && c.querySelector('button.btn-primary');"
    "   if (b) { b.click(); return true; }"
    " }"
    " return false; })()"
)


def _js_read_meta(db_name: str) -> str:
    return (
        "(async () => { const db = new PouchDB(" + json.dumps(db_name) + ");"
        " const a = await db.allDocs({include_docs: true});"
        " const grids = a.rows.filter(r => r.doc.modelName === 'GridData').length;"
        " const m = a.rows.map(r => r.doc).find(d => d.modelName === 'MetaData');"
        " return JSON.stringify({grids: grids, meta: m || null}); })()"
    )


def _js_put(db_name: str, doc: dict) -> str:
    return (
        "(async () => { const db = new PouchDB(" + json.dumps(db_name) + ");"
        " try { await db.put(JSON.parse(" + json.dumps(json.dumps(doc)) + ")); return 'ok'; }"
        " catch (e) { return e && e.status === 409 ? 'conflict' : 'error: ' + (e && e.message); } })()"
    )


def _wait_until(
    predicate: Callable[[], bool],
    deadline: float,
    what: str,
    interval: float = 0.4,
    cancelled: Optional[Callable[[], bool]] = None,
) -> None:
    while time.monotonic() < deadline:
        if cancelled is not None and cancelled():
            raise AstericsConfigError("Configuración cancelada (se cerró AsTeRICS).")
        try:
            if predicate():
                return
        except AstericsConfigError:
            raise
        except Exception:
            pass
        time.sleep(interval)
    raise AstericsConfigError(f"AsTeRICS no respondió a tiempo ({what}).")


def _find_page_ws(port: int, deadline: float, cancelled: Optional[Callable[[], bool]] = None) -> str:
    found: list[str] = []

    def probe() -> bool:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as resp:
            for target in json.load(resp):
                if target.get("type") == "page" and str(target.get("url", "")).startswith(ASTERICS_ORIGIN):
                    found.append(target["webSocketDebuggerUrl"])
                    return True
        return False

    _wait_until(probe, deadline, "conexión con el navegador", cancelled=cancelled)
    return found[0]


def configure(
    port: int,
    settings: AstericsInputSettings,
    timeout: float = 90.0,
    cancelled: Optional[Callable[[], bool]] = None,
) -> tuple[bool, str]:
    """Deja AsTeRICS (ya lanzado con el puerto de depuración `port` y el perfil
    propio) configurado según `settings`. Bloqueante: llamar desde un hilo.
    Devuelve `(ok, mensaje)`."""
    deadline = time.monotonic() + timeout
    page: Optional[_Page] = None
    _log(f"configurar: puerto {port}, {settings}")
    try:
        def wait(predicate: Callable[[], bool], what: str) -> None:
            _wait_until(predicate, deadline, what, cancelled=cancelled)

        page = _Page(_find_page_ws(port, deadline, cancelled))

        def state() -> dict:
            return json.loads(page.eval(_JS_STATE))

        wait(lambda: state()["ready"] and state()["pouch"], "carga de la página")

        # AsTeRICS decide su pantalla inicial (#welcome, #grid/..., #grids) al
        # terminar de cargar: hasta entonces el hash viene vacío y no se puede
        # concluir nada (antes se lo tomaba por "primera vez" y fallaba si el
        # perfil ya tenía usuario).
        wait(lambda: state()["hash"] not in ("", "#"), "pantalla inicial")
        _log(f"pantalla inicial: {state()['hash']}")

        # Primera vez en este perfil: pantalla de bienvenida -> usuario sin registro.
        if state()["hash"].startswith("#welcome"):
            wait(lambda: bool(page.eval(_JS_CLICK_WELCOME)), "botón de inicio sin registro")
            wait(lambda: state()["hash"].startswith("#grid"), "creación del usuario")
            _log("usuario sin registro creado")

        user = state().get("user") or "default-user"
        _log(f"usuario: {user} | pantalla: {state()['hash']}")

        def read_meta() -> dict:
            return json.loads(page.eval(_js_read_meta(user)))

        # Perfil sin tableros: cargar el tablero por defecto de AsTeRICS.
        if read_meta()["grids"] == 0:
            if state()["hash"].startswith("#grids") and not page.eval(_JS_USE_DEFAULT_BOARD):
                raise AstericsConfigError(
                    f"No se encontró el tablero «{DEFAULT_BOARD_NAME}» (ni el básico de AsTeRICS) para cargar."
                )
            # El tablero de ARASAAC es grande: AsTeRICS lo importa por partes y
            # recién al terminar entra a él (`#grid/<id>`). Recargar antes
            # dejaba la importación a medias (y la página en la lista de
            # tableros). Se espera esa entrada y un breve asentamiento.
            wait(lambda: state()["hash"].startswith("#grid/"), "carga del tablero por defecto")
            wait(lambda: read_meta()["grids"] > 0, "tablero por defecto")
            time.sleep(2.0)
            _log("tablero por defecto cargado")

        wait(lambda: read_meta()["meta"] is not None, "configuración de AsTeRICS")

        # Leer - modificar - escribir, con reintento si AsTeRICS escribió a la vez.
        for _ in range(5):
            meta = read_meta()["meta"]
            try:
                inner = json.loads(meta["encryptedDataBase64"])
                input_config = inner["inputConfig"]
            except (KeyError, TypeError, ValueError):
                raise AstericsConfigError(
                    "AsTeRICS cambió el formato de su configuración; no se pudo ajustar automáticamente."
                )
            if not apply_to_input_config(input_config, settings):
                _log(f"sin cambios: {settings}")
                return True, "AsTeRICS ya tenía la configuración pedida."
            meta["encryptedDataBase64"] = json.dumps(inner)
            outcome = page.eval(_js_put(user, meta))
            if outcome == "ok":
                _log(f"configuración escrita: {settings}")
                page.call("Page.reload")
                wait(lambda: state()["ready"], "recarga de la página")
                return True, "AsTeRICS configurado."
            if outcome != "conflict":
                raise AstericsConfigError(f"No se pudo guardar la configuración ({outcome}).")
        raise AstericsConfigError("No se pudo guardar la configuración (conflictos repetidos).")
    except AstericsConfigError as exc:
        _log(f"FALLO: {exc}")
        return False, str(exc)
    except Exception as exc:  # red local, websockets, etc.
        _log(f"FALLO inesperado: {type(exc).__name__}: {exc}")
        return False, f"No se pudo configurar AsTeRICS: {exc}"
    finally:
        if page is not None:
            page.close()
