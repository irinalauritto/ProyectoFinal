"""
Registro de una sesión (EEG o EMG) y su reporte en PDF.

`SessionLog` junta lo que pasó entre que se inicia la sesión y se finaliza:
calibraciones, validaciones, cambios manuales, tiempo de estimulación y parámetros
finales. `write_pdf` lo imprime al finalizar la sesión.

Autora: Irina Lauritto
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Optional

RAFAGA_S = 2.0


@dataclass
class SessionLog:
    paciente: str
    inicio: datetime = field(default_factory=datetime.now)
    fin: Optional[datetime] = None
    calibraciones: list[dict] = field(default_factory=list)
    validaciones: list[dict] = field(default_factory=list)
    cambios: list[dict] = field(default_factory=list)
    estimulaciones_s: list[float] = field(default_factory=list)
    archivos: list[str] = field(default_factory=list)
    parametros: dict = field(default_factory=dict)
    modalidad: str = "EEG"

    def add_change(self, parametro: str, anterior: Any, nuevo: Any) -> None:
        """Registra un cambio. Una ráfaga sobre el mismo parámetro (arrastrar un
        deslizador) queda como un solo cambio."""
        ahora = datetime.now()
        if self.cambios and self.cambios[-1]["parametro"] == parametro:
            ultimo = self.cambios[-1]
            if (ahora - ultimo["hora"]).total_seconds() < RAFAGA_S:
                ultimo["hora"] = ahora
                ultimo["nuevo"] = nuevo
                if ultimo["anterior"] == nuevo:
                    self.cambios.pop()
                return
        self.cambios.append({"hora": ahora, "parametro": parametro, "anterior": anterior, "nuevo": nuevo})

    def has_activity(self) -> bool:
        return bool(self.calibraciones or self.validaciones or self.cambios or self.estimulaciones_s)


def calibration_rows(result: dict, assignment: dict[float, str]) -> list[dict]:
    """Una fila por candidata, con lo necesario para seguir el cálculo de exactitud
    y la selección de frecuencias.

    Args:
        result: Resultado de `FrequencyCalibrator` (`candidate_freqs`, `trials`,
            `accuracies`, `selected`).
        assignment: `{frecuencia: nombre del estímulo}` con la asignación final.
    """
    from ssvep.app.frequency_calibrator import collides

    selected = list(result["selected"])
    rows = []
    for freq in result["candidate_freqs"]:
        trials = sorted((t for t in result["trials"] if t["freq"] == freq), key=lambda t: t["repeticion"])
        chocan = [other for other in selected if other != freq and collides(freq, other)]
        rows.append(
            {
                "freq": freq,
                "repeticiones": [(t["aciertos"], t["ventanas"]) for t in trials],
                "aciertos": sum(t["aciertos"] for t in trials),
                "ventanas": sum(t["ventanas"] for t in trials),
                "exactitud": result["accuracies"].get(freq),
                "colision": chocan if freq not in selected else [],
                "seleccionada": freq in selected,
                "estimulo": assignment.get(freq),
            }
        )
    return rows


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table border="1" cellspacing="0" cellpadding="4" width="100%"><tr>{head}</tr>{body}</table>'


def _calibration_html(entry: dict, number: int) -> str:
    n_repeats = max((len(row["repeticiones"]) for row in entry["filas"]), default=0)
    headers = ["Frec."] + [f"Rep. {i + 1}" for i in range(n_repeats)]
    headers += ["Total", "Exactitud", "Colisión armónica", "Elegida", "Estímulo asignado"]
    rows = []
    for row in entry["filas"]:
        repeticiones = [f"{a}/{v}" for a, v in row["repeticiones"]]
        repeticiones += ["—"] * (n_repeats - len(repeticiones))
        exactitud = "—" if row["exactitud"] is None else f"{row['exactitud']:.0f} %"
        colision = "Con " + ", ".join(f"{f:g} Hz" for f in row["colision"]) if row["colision"] else "No"
        rows.append(
            [f"{row['freq']:g} Hz", *repeticiones, f"{row['aciertos']}/{row['ventanas']}", exactitud, colision,
             "Sí" if row["seleccionada"] else "No", row["estimulo"] or "—"]
        )
    return (
        f"<h3>Calibración {number} ({entry['hora']:%H:%M}, método {escape(entry['metodo'])})</h3>"
        f"<p>Ancla: {entry['ancla']:g} Hz. Refresco del monitor: {entry['refresco']} Hz.</p>"
        + _table(headers, rows)
    )


def _validation_html(entry: dict, number: int) -> str:
    estado = "descartada" if entry["descartada"] else "guardada"
    filas = [
        ["Umbral calculado", f"{entry['umbral_calculado']:.2f}"],
    ]
    if entry["umbral_barrido"] != entry["umbral_calculado"]:
        filas.append(["Resultado del barrido (reemplazado)", f"{entry['umbral_barrido']:.2f}"])
    if entry["umbral_final"] is not None:
        manual = " (ajuste manual)" if entry["umbral_final"] != entry["umbral_calculado"] else ""
        filas.append(["Umbral final", f"{entry['umbral_final']:.2f}{manual}"])
    filas += [
        ["Exactitud", f"{entry['exactitud']:.0f} %"],
        ["Ítems sin resolver", f"{entry['sin_resolver']:.0%}"],
        ["ITR", f"{entry['itr']:.1f} bits/min"],
    ]
    return (
        f"<h3>Validación {number} ({entry['hora']:%H:%M}, método {escape(entry['metodo'])}, {estado})</h3>"
        + _table(["Parámetro", "Valor"], filas)
        + "<p></p>"
        + _table(["Ítem", "Estímulo pedido", "Resultado"], entry["items"])
    )


def _emg_calibration_html(entry: dict, number: int) -> str:
    return f"<h3>Calibración {number} ({entry['hora']:%H:%M})</h3>" + _table(
        ["Parámetro", "Valor"],
        [
            ["Duración en reposo", f"{entry['duracion_s']:g} s"],
            ["Muestras", entry["muestras"]],
            ["Media en reposo", f"{entry['media']:.2f} mV"],
            ["Desvío estándar en reposo", f"{entry['sd']:.2f} mV"],
            ["Sensibilidad", f"{entry['sensibilidad']:.1f}"],
            ["k", f"{entry['k']:.1f}"],
            ["Umbral de disparo (media + k · desvío)", f"{entry['umbral']:.2f} mV"],
            ["Umbral de reactivación", f"{entry['reactivacion']:.2f} mV"],
        ],
    )


def _emg_validation_html(entry: dict, number: int) -> str:
    titulo = f"<h3>Validación {number} ({entry['hora']:%H:%M}"
    if entry["omitida"]:
        return titulo + ", omitida)</h3>"
    resultado = "correcta" if entry["correcta"] else "con intentos que no dieron exactamente 1 evento"
    return (
        titulo + f", {resultado})</h3>"
        f"<p>Sensibilidad: {entry['sensibilidad']:.1f}. Refractario: {entry['refractario_ms']} ms.</p>"
        + _table(["Intento", "Eventos detectados"], [[i, n] for i, n in enumerate(entry["intentos"], start=1)])
    )


def build_html(log: SessionLog) -> str:
    fin = f"{log.fin:%d/%m/%Y %H:%M}" if log.fin else "—"
    parts = [
        f"<h1>Sesión {escape(log.modalidad)}</h1>",
        f"<p><b>Paciente:</b> {escape(log.paciente)}<br>",
        f"<b>Inicio:</b> {log.inicio:%d/%m/%Y %H:%M}<br><b>Fin:</b> {fin}</p>",
        "<h2>Parámetros utilizados</h2>",
    ]
    p = log.parametros
    if "filas" in p:
        parts.append(_table(["Parámetro", "Valor al finalizar"], p["filas"]))
    elif p:
        parts.append(
            _table(
                ["Parámetro", "Valor al finalizar"],
                [
                    ["Método de entrada", p["metodo"]],
                    ["Umbral", f"{p['umbral']:.2f}"],
                    ["Canales", ", ".join(p["canales"])],
                    ["Ventana de clasificación", f"{p['ventana_s']:g} s"],
                    ["Tiempo refractario", f"{p['refractario_s']:g} s"],
                ],
            )
        )
        parts.append("<p></p>")
        parts.append(
            _table(
                ["Estímulo", "Frecuencia", "Activo"],
                [[s["nombre"], f"{s['freq']:g} Hz", "Sí" if s["activo"] else "No"] for s in p["estimulos"]],
            )
        )

    parts.append("<h2>Calibración</h2>")
    if log.calibraciones:
        render = _emg_calibration_html if log.modalidad == "EMG" else _calibration_html
        parts += [render(entry, i) for i, entry in enumerate(log.calibraciones, start=1)]
    else:
        parts.append("<p>No se realizó calibración en esta sesión.</p>")

    parts.append("<h2>Validación</h2>")
    if log.validaciones:
        render = _emg_validation_html if log.modalidad == "EMG" else _validation_html
        parts += [render(entry, i) for i, entry in enumerate(log.validaciones, start=1)]
    else:
        parts.append("<p>No se realizó validación en esta sesión.</p>")

    parts.append("<h2>Cambios manuales</h2>")
    if log.cambios:
        parts.append(
            _table(
                ["Hora", "Parámetro", "Anterior", "Nuevo"],
                [[f"{c['hora']:%H:%M:%S}", c["parametro"], c["anterior"], c["nuevo"]] for c in log.cambios],
            )
        )
    else:
        parts.append("<p>No hubo cambios manuales.</p>")

    total = round(sum(log.estimulaciones_s))
    titulo = "Uso online" if log.modalidad == "EMG" else "Estimulación"
    parts.append(f"<h2>{titulo}</h2><p>Duración total: {total // 60:02d}:{total % 60:02d} (min:s).</p>")

    if log.archivos:
        parts.append("<h2>Señales guardadas</h2><p>" + "<br>".join(escape(a) for a in log.archivos) + "</p>")
    return "".join(parts)


def ask_finish_session(parent: Any, allow_cancel: bool) -> Optional[bool]:
    """Pregunta si imprimir al finalizar. True: imprimir, False: no, None: canceló."""
    from PySide6.QtWidgets import QMessageBox

    box = QMessageBox(parent)
    box.setWindowTitle("Finalizar sesión")
    box.setText("Se va a finalizar la sesión. ¿Querés imprimirla en un PDF?")
    print_button = box.addButton("Imprimir PDF", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Finalizar sin imprimir", QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole) if allow_cancel else None
    # QMessageBox calcula su ancho sin la negrita de la hoja de estilos: fijar
    # el mínimo de cada botón evita que su texto quede cortado.
    for button in box.buttons():
        button.setMinimumWidth(button.sizeHint().width())
    box.exec()
    if cancel_button is not None and box.clickedButton() is cancel_button:
        return None
    return box.clickedButton() is print_button


def print_session(parent: Any, log: SessionLog, folder: Optional[Path]) -> None:
    """Pide dónde guardar el PDF de la sesión y lo genera."""
    from PySide6.QtCore import QStandardPaths
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    name = f"sesion_{log.modalidad}_{log.paciente}_{log.inicio:%Y-%m-%d_%H-%M}.pdf".replace(" ", "_")
    folder = folder or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
    path, _filter = QFileDialog.getSaveFileName(parent, "Imprimir sesión", str(folder / name), "PDF (*.pdf)")
    if not path:
        return
    try:
        write_pdf(log, path)
    except OSError as error:
        QMessageBox.warning(parent, "Imprimir sesión", f"No se pudo guardar el PDF:\n\n{error}")


def write_pdf(log: SessionLog, path: str | Path) -> None:
    """Imprime el reporte de la sesión en `path`. Requiere una QGuiApplication."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument

    writer = QPdfWriter(str(path))
    writer.setTitle(f"Sesión {log.modalidad} - {log.paciente}")
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(15, 15, 15, 15),
            QPageLayout.Unit.Millimeter,
        )
    )
    document = QTextDocument()
    document.setDefaultFont(QFont("Arial", 9))
    document.setDefaultStyleSheet("th { background-color: #e9ecef; } h1, h2, h3 { color: #1f2d3d; }")
    document.setHtml(build_html(log))
    # Con el tamaño de página explícito, print_ no agrega sus márgenes de 2 cm.
    document.setPageSize(QSizeF(writer.pageLayout().paintRectPoints().size()))
    document.print_(writer)
