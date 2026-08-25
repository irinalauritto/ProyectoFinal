"""
Módulo de evaluación para sistemas BCI (Brain-Computer Interface).

Contiene la lógica para evaluar el rendimiento del clasificador en tiempo real,
calcular métricas (como accuracy y matriz de confusión) y generar reportes en PDF.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import math
from PySide6.QtCore import QElapsedTimer, QObject, Signal

# Códigos especiales que puede devolver el clasificador
NO_ENOUGH_SAMPLES: int = -2   # No hay muestras suficientes para clasificar
NO_THRESHOLD: int = -1        # No superó el umbral -> se asume que no mira ningún estímulo

SPECIAL_LABEL_NAMES: Dict[int, str] = {
    NO_ENOUGH_SAMPLES: "Muestras insuficientes",
    NO_THRESHOLD: "Sin detección (umbral)",
}


class BCIEvaluator(QObject):
    """
    Evalúa el rendimiento de un clasificador BCI en tiempo real.

    Gestiona la secuencia de estímulos, registra aciertos y fallos, 
    calcula métricas de rendimiento y genera reportes en PDF.

    Signals:
        index_hit (Signal[int]): Se emite cuando el clasificador acierta el estímulo actual.
        index_miss (Signal[int]): Se emite cuando el clasificador falla o devuelve un código especial.
        index_sequence (Signal[int]): Se emite para indicar el índice actual esperado en la secuencia.
        send_time (Signal[int]): Se emite cada segundo con el tiempo transcurrido en segundos.
        finished (Signal): Se emite cuando la evaluación se detiene (manualmente o al completar la secuencia).
    """

    index_hit = Signal(int)
    index_miss = Signal(int)
    index_sequence = Signal(int)
    send_time = Signal(int)
    finished = Signal()

    def __init__(
        self,
        base_dir,
        sequence: Optional[List[int]] = None,
        user_preferences: Optional[Any] = None,
        report_path: Optional[str] = None,
        auto_generate_report: bool = False
        ):
        """
        Inicializa el evaluador BCI.

        Todos los parámetros son opcionales para permitir la instanciación temprana 
        (por ejemplo, para conectar señales antes de tener los datos). 
        Deben establecerse mediante los setters antes de llamar a `start()`.

        Args:
            base_dir: Carpeta base de la aplicación donde se guardan los datos generados (reportes, etc.). 
            sequence: Secuencia de índices de estímulo que el usuario debe intentar seleccionar.
            user_preferences: Objeto con preferencias del usuario (método de clasificación, 
                              ventana de tiempo, canales, estímulos activos).
            report_path: Ruta del archivo PDF a generar.
            auto_generate_report: Si es True, genera el reporte automáticamente al emitir la señal `finished`.
        """
        super().__init__()
        
        self.__sequence = sequence
        self.__user_preferences = user_preferences
        self.__report_path = report_path
        self.__reports_dir = os.path.join(base_dir, "reportes")
        os.makedirs(self.__reports_dir, exist_ok=True)
        self.__auto_generate_report = auto_generate_report

        # Estado de la evaluación
        self.__hits: List[int] = []
        self.__misses: List[int] = []
        self.__is_running = False
        self.__sequence_index = 0
        
        # Control de tiempo
        self.__evaluation_time = QElapsedTimer()
        self.__prev_time = -1
        self.__duration_ms = 0

        # Datos para matriz de confusión
        self.__true_labels: List[int] = []
        self.__predicted_labels: List[int] = []
        self.__timestamps_ms: List[int] = []

        # Conexión automática para generación de reportes
        self.finished.connect(self.__on_finished_generate_report)
    
    def __resolve_path(self, filepath: str) -> str:
        """
        Resuelve una ruta de archivo combinándola con el directorio base si es relativa.

        Si la ruta proporcionada ya es absoluta, la devuelve intacta. De lo
        contrario, la une al directorio base configurado en la instancia.

        Args:
            filepath (str): La ruta del archivo a resolver (puede ser absoluta o relativa).

        Returns:
            str: La ruta absoluta resultante.
        """
        if os.path.isabs(filepath):
            return filepath
        return os.path.join(self.__reports_dir, filepath)
    
    def set_report_path(self, report_path: str) -> None:
        """
        Establece y valida la ruta de salida definitiva para el reporte PDF.

        Toma la ruta proporcionada, la procesa a través del método interno de 
        resolución de rutas para asegurar que sea absoluta y la asigna al 
        atributo privado del reporte.

        Args:
            report_path (str): Ruta de salida deseada (relativa a base_dir o absoluta).

        Returns:
            None
        """
        self.__report_path = self.__resolve_path(report_path)

    # ------------------------------------------------------------------
    # SETTERS
    # ------------------------------------------------------------------

    def set_sequence(self, sequence: List[int]) -> None:
        """Establece la secuencia de estímulos a evaluar."""
        self.__sequence = sequence

    def set_user_preferences(self, user_preferences: Any) -> None:
        """Establece las preferencias del usuario (configuración del sistema)."""
        self.__user_preferences = user_preferences

    def set_report_path(self, report_path: str) -> None:
        """Establece la ruta de salida para el reporte PDF."""
        self.__report_path = report_path

    def set_auto_generate_report(self, auto_generate_report: bool) -> None:
        """Establece si el reporte debe generarse automáticamente al finalizar."""
        self.__auto_generate_report = auto_generate_report

    # ------------------------------------------------------------------
    # CICLO DE VIDA DE LA EVALUACIÓN
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Inicia el proceso de evaluación.

        Raises:
            ValueError: Si no se ha establecido una secuencia mediante `set_sequence`.
        """
        if not self.__sequence:
            raise ValueError("Falta setear sequence antes de llamar a start() (usá set_sequence)")

        self.__sequence_index = 0
        self.__hits.clear()
        self.__misses.clear()
        self.__true_labels.clear()
        self.__predicted_labels.clear()
        self.__timestamps_ms.clear()
        
        self.__is_running = True
        self.__prev_time = -1
        self.__evaluation_time.start()

        # Enviamos primer índice que el BCI debe intentar adivinar
        self.index_sequence.emit(self.__sequence_index)

    def stop(self) -> None:
        """Detiene el proceso de evaluación, registra la duración y emite la señal `finished`."""
        self.__duration_ms = self.__evaluation_time.elapsed()
        self.__is_running = False
        self.finished.emit()

    def add_classification(self, classification: int) -> None:
        """
        Procesa una nueva clasificación del modelo.

        Args:
            classification: Índice de la clase predicha por el clasificador (puede ser un código especial).
        """
        if not self.__is_running:
            return

        actual_time = self.__evaluation_time.elapsed() // 1000

        # Emitir tiempo transcurrido cada segundo
        if (actual_time - self.__prev_time) >= 1:
            self.__prev_time = actual_time
            self.send_time.emit(int(actual_time))

        # Si ya completamos la secuencia, detenemos el proceso
        if self.__sequence_index >= len(self.__sequence):
            self.stop()
            return

        # Sin clasificación válida (no superó el umbral o no hay muestras
        # suficientes): no es un intento resuelto, se sigue esperando en la
        # misma posición sin avanzar ni registrar acierto/fallo.
        if classification < 0:
            return

        target = self.__sequence[self.__sequence_index]

        # Guardamos el intento completo para la matriz de confusión
        self.__true_labels.append(target)
        self.__predicted_labels.append(classification)
        self.__timestamps_ms.append(self.__evaluation_time.elapsed())

        if classification == target:
            print(f"ACIERTO: {classification} == {target}")
            self.__hits.append(self.__sequence_index)
            self.index_hit.emit(classification)
        else:
            # classification es una clase incorrecta (pero válida)
            self.__misses.append(self.__sequence_index)
            self.index_miss.emit(classification)

        # Cada posición de la secuencia se resuelve con un único intento
        # (acierte o falle) y siempre avanza a la siguiente.
        self.__sequence_index += 1

        if self.__sequence_index < len(self.__sequence):
            self.index_sequence.emit(self.__sequence_index)
        else:
            self.stop()

    # ------------------------------------------------------------------
    # PROPIEDADES (GETTERS)
    # ------------------------------------------------------------------

    @property
    def hits(self) -> List[int]:
        """Lista de índices de la secuencia donde se registró un acierto."""
        return self.__hits

    @property
    def misses(self) -> List[int]:
        """Lista de índices de la secuencia donde se registró un fallo."""
        return self.__misses

    @property
    def true_labels(self) -> List[int]:
        """Lista de etiquetas reales (target) de cada intento."""
        return self.__true_labels

    @property
    def predicted_labels(self) -> List[int]:
        """Lista de etiquetas predichas por el clasificador en cada intento."""
        return self.__predicted_labels

    @property
    def duration_ms(self) -> int:
        """Duración total de la evaluación en milisegundos."""
        return self.__duration_ms

    # ------------------------------------------------------------------
    # MÉTRICAS
    # ------------------------------------------------------------------

    def accuracy(self) -> float:
        """
        Calcula el porcentaje de intentos correctos sobre el total de clasificaciones.

        Returns:
            float: Porcentaje de precisión (0.0 a 100.0).
        """
        if not self.__true_labels:
            return 0.0
        
        correct = sum(t == p for t, p in zip(self.__true_labels, self.__predicted_labels))
        return (correct / len(self.__true_labels)) * 100.0

    def __active_stimulus_indices(self) -> Optional[List[int]]:
        """
        Obtiene los índices de los estímulos que estaban encendidos.

        Returns:
            Lista de índices o None si no hay preferencias de usuario configuradas.
        """
        if self.__user_preferences is None:
            return None
        return [i for i, on in enumerate(self.__user_preferences.stimulus_on) if on]

    def __default_class_labels(self) -> List[int]:
        """
        Determina el orden de las clases a mostrar en la matriz de confusión.
        Incluye todos los estímulos encendidos + los códigos especiales (-1, -2).

        Returns:
            Lista ordenada de etiquetas de clase.
        """
        active = self.__active_stimulus_indices()
        if active is not None:
            return sorted(active) + [NO_THRESHOLD, NO_ENOUGH_SAMPLES]
        
        # Fallback: inferir solo de los datos registrados si no hay preferencias
        return sorted(set(self.__true_labels) | set(self.__predicted_labels))

    def __class_display_name(self, label: int) -> str:
        """
        Obtiene el nombre legible para una etiqueta de clase.

        Args:
            label: Etiqueta numérica de la clase.

        Returns:
            Nombre descriptivo de la clase.
        """
        if label in SPECIAL_LABEL_NAMES:
            return SPECIAL_LABEL_NAMES[label]
        
        if self.__user_preferences is not None and 0 <= label < len(self.__user_preferences.stimulus):
            stim = self.__user_preferences.stimulus[label]
            return f"{stim.stim_type} {stim.freq}Hz"
        
        return str(label)

    def get_confusion_matrix(self, class_labels: Optional[List[int]] = None) -> Tuple[np.ndarray, List[int]]:
        """
        Genera la matriz de confusión basada en los intentos registrados.

        Args:
            class_labels: Orden específico de clases. Si es None, usa las clases por defecto.

        Returns:
            Tupla con la matriz de confusión (NxN) y la lista de etiquetas correspondiente.
        """
        if class_labels is None:
            class_labels = self.__default_class_labels()

        label_to_idx = {label: i for i, label in enumerate(class_labels)}
        n = len(class_labels)
        cm = np.zeros((n, n), dtype=int)

        for t, p in zip(self.__true_labels, self.__predicted_labels):
            if t in label_to_idx and p in label_to_idx:
                cm[label_to_idx[t]][label_to_idx[p]] += 1

        return cm, class_labels

    def calculate_itr(self) -> float:
        """
        Calcula la Tasa de Transferencia de Información (ITR) en bits por minuto.

        Utiliza la fórmula de Wolpaw et al.:
            bits_por_trial = log2(N) + P*log2(P) + (1-P)*log2((1-P)/(N-1))
            ITR = bits_por_trial * (60 / T)

        Donde:
            N: cantidad de clases posibles (estímulos activos).
            P: accuracy como probabilidad (0.0 a 1.0).
            T: tiempo promedio por selección, en segundos.

        Returns:
            float: ITR en bits por minuto. Devuelve 0.0 si no hay datos suficientes.

        Raises:
            ValueError: Si no hay al menos 2 clases activas (N < 2), ya que el ITR
                        no está definido para un único estímulo.
        """
        if not self.__true_labels or self.__duration_ms <= 0:
            return 0.0

        n = self.__number_of_classes()
        if n < 2:
            raise ValueError("El ITR requiere al menos 2 clases activas (N >= 2)")

        p = self.accuracy() / 100.0
        n_trials = len(self.__true_labels)
        t_seconds = (self.__duration_ms / 1000.0) / n_trials

        if t_seconds <= 0:
            return 0.0

        bits_per_trial = self.__bits_per_trial(p, n)
        itr = bits_per_trial * (60.0 / t_seconds)
        return itr

    def __number_of_classes(self) -> int:
        """
        Determina N: la cantidad de clases seleccionables (estímulos activos).

        Usa user_preferences si está disponible; si no, infiere del máximo de
        etiquetas verdaderas registradas.

        Returns:
            int: Cantidad de clases N.
        """
        active = self.__active_stimulus_indices()
        if active is not None:
            return len(active)
        return len(set(self.__true_labels))

    def __bits_per_trial(self, p: float, n: int) -> float:
        """
        Calcula los bits de información por trial según Wolpaw et al.

        Maneja los casos límite donde P=0 o P=1, que de otro modo producirían
        log(0) (indefinido).

        Args:
            p: Accuracy como probabilidad (0.0 a 1.0).
            n: Cantidad de clases N.

        Returns:
            float: Bits por trial.
        """
        if p <= 0:
            # Peor caso: rendimiento al azar o peor -> se considera 0 bits útiles
            return 0.0
        if p >= 1:
            # Mejor caso: certeza total
            return math.log2(n)

        return (
            math.log2(n)
            + p * math.log2(p)
            + (1 - p) * math.log2((1 - p) / (n - 1))
        )
    # ------------------------------------------------------------------
    # REPORTE PDF
    # ------------------------------------------------------------------

    def __on_finished_generate_report(self) -> None:
        """Callback interno que dispara la generación del reporte si está habilitado."""
        if self.__auto_generate_report and self.__report_path:
            self.generate_report(self.__report_path)

    def __format_duration(self, ms: int) -> str:
        """Formatea milisegundos a un string legible MM:SS."""
        total_seconds = ms // 1000
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def generate_report(self, filepath: str, extra_session_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Genera un documento PDF con el resumen de la sesión y la matriz de confusión.

        Args:
            filepath: Ruta de salida del archivo PDF (ej: "reporte_sesion1.pdf").
            extra_session_info: Diccionario con metadata adicional para la portada (ej: {"Usuario": "Lautaro"}).
        """
        class_labels = self.__default_class_labels()
        cm, labels = self.get_confusion_matrix(class_labels)
        display_labels = [self.__class_display_name(l) for l in labels]
        acc = self.accuracy()

        session_lines = [
            "Reporte de evaluación BCI",
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Duración: {self.__format_duration(self.__duration_ms)}",
            "",
            f"Total de intentos: {len(self.__true_labels)}",
            f"Selecciones completadas (aciertos): {len(self.__hits)}",
            f"Fallos: {len(self.__misses)}",
            f"Accuracy: {acc:.2f}%",
        ]

        try:
            itr = self.calculate_itr()
            session_lines.append(f"ITR: {itr:.2f} bits/min")
        except ValueError:
            pass
        if self.__user_preferences is not None:
            up = self.__user_preferences
            session_lines += [
                "",
                f"Método de clasificación: {up.classification_method}",
                f"Ventana de tiempo: {up.time_window}s",
                "Canales utilizados: " + ", ".join(
                    f"{idx}:{name}" for idx, name in up.channels.items()
                ),
            ]

        if extra_session_info:
            session_lines.append("")
            for k, v in extra_session_info.items():
                session_lines.append(f"{k}: {v}")
        filepath = self.__resolve_path(filepath)
        with PdfPages(filepath) as pdf:
            # --- Página 1: Resumen de la sesión ---
            fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4
            ax.axis('off')
            ax.text(0.05, 0.95, "\n".join(session_lines), va='top', ha='left',
                    fontsize=12, transform=ax.transAxes)
            pdf.savefig(fig)
            plt.close(fig)

            # --- Página 2: Matriz de confusión ---
            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(cm, cmap='Blues')
            
            ax.set_xticks(range(len(display_labels)))
            ax.set_yticks(range(len(display_labels)))
            ax.set_xticklabels(display_labels, rotation=45, ha='right')
            ax.set_yticklabels(display_labels)
            
            ax.set_xlabel("Predicho")
            ax.set_ylabel("Real")
            ax.set_title("Matriz de confusión")

            thresh = cm.max() / 2.0 if cm.max() > 0 else 0
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(j, i, str(cm[i, j]), ha='center', va='center',
                            color='white' if cm[i, j] > thresh else 'black')

            fig.colorbar(im, ax=ax)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

