"""
Módulo de interfaces gráficas para el evaluador BCI.

Contiene las clases de widgets para el operador, el usuario y 
la visualización de secuencias de estímulos, utilizando PySide6.
"""

import sys


from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap

from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QLabel, QWidget
from ssvep.ui.bci_evaluator_operator import Ui_BCIEvaluatorOperator
from ssvep.ui.bci_evaluator_user import Ui_BCIEvaluatorUser
from ssvep.ui.sequence_widget import Ui_sequenceWidget



class BCIEvaluatorOperator(QWidget):
    """
    Widget de la interfaz para el operador del sistema BCI.

    Gestiona el control de inicio/parada de la prueba y muestra 
    estadísticas en tiempo real (tiempo, aciertos y fallos).

    Signals:
        start_test_request (Signal): Se emite cuando se solicita iniciar la prueba.
        stop_test_request (Signal): Se emite cuando se solicita detener la prueba o se cierra la ventana.
    """

    start_test_request = Signal()
    stop_test_request = Signal()

    def __init__(self) -> None:
        """Inicializa el widget, carga la interfaz desde el archivo .ui y configura los controles."""
        super().__init__()
        
        self.__ui = Ui_BCIEvaluatorOperator()
        self.__ui.setupUi(self)
        self.setAttribute(Qt.WA_StyledBackground, True)
                

        
        # Variables de control
        self.__hits = 0
        self.__misses = 0
        
        # Conexión de botones
        self.__ui.btn_start.clicked.connect(self.start_test_request.emit)
        self.__ui.btn_start.setEnabled(False)
        self.__ui.btn_stop.clicked.connect(self.stop)
        self.__ui.btn_stop.setEnabled(False)

    def set_time(self, time: int) -> None:
        """
        Actualiza la etiqueta de tiempo en la interfaz.

        Args:
            time (int): Tiempo total en segundos.
        """
        minutes, seconds = divmod(time, 60)
        text = f"Tiempo {minutes:02d}:{seconds:02d}"
        self.__ui.lbl_time.setText(text)
    
    def register_hit(self) -> None:
        """Incrementa el contador de aciertos y actualiza la interfaz."""
        self.__hits += 1
        self.__ui.lbl_hits.setText(f"Aciertos: {self.__hits}")
        
    def register_miss(self) -> None:
        """Incrementa el contador de fallos y actualiza la interfaz."""
        self.__misses += 1
        self.__ui.lbl_miss.setText(f"Errores: {self.__misses}")
        
    def load_sequence_widget(self, widget: QWidget) -> None:
        """
        Incrusta un widget de secuencia en el layout designado.

        Args:
            widget (QWidget): El widget de secuencia a mostrar.
        """
        self.__ui.sequence_layout.setContentsMargins(0, 0, 0, 0)
        self.__ui.sequence_layout.addWidget(widget)
    
    def closeEvent(self, event) -> None:
        """
        Maneja el evento de cierre de la ventana, emitiendo la señal de parada.

        Args:
            event: Evento de cierre de Qt.
        """
        self.stop_test_request.emit()
        event.accept() 
    
    def stop(self) -> None:
        """Reinicia los contadores y cierra la ventana del operador."""
        self.__hits = 0
        self.__misses = 0
        self.close()
    
    def enable_buttons(self) -> None:
        """Habilita los botones de inicio y parada."""
        self.__ui.btn_start.setEnabled(True)
        self.__ui.btn_stop.setEnabled(True)


class BCIEvaluatorUser(QWidget):
    """
    Widget de la interfaz para el usuario del sistema BCI.

    Muestra los estímulos y gestiona su propio ciclo de vida.

    Signals:
        window_closed (Signal): Se emite cuando la ventana del usuario se cierra.
    """

    window_closed = Signal()

    def __init__(self) -> None:
        """Inicializa el widget y carga la interfaz desde el archivo .ui."""
        super().__init__() 
        
        self.__ui = Ui_BCIEvaluatorUser()
        self.__ui.setupUi(self)
        self.setAttribute(Qt.WA_StyledBackground, True)        


    def load_sequence_widget(self, widget: QWidget) -> None:
        """
        Incrusta un widget de secuencia en el layout designado.

        Args:
            widget (QWidget): El widget de secuencia a mostrar.
        """
        self.__ui.sequence_layout.setContentsMargins(0, 0, 0, 0)
        self.__ui.sequence_layout.addWidget(widget)
        
        
    
    def closeEvent(self, event) -> None:
        """
        Maneja el evento de cierre, emitiendo la señal correspondiente.

        Args:
            event: Evento de cierre de Qt.
        """
        self.window_closed.emit()
        event.accept()
        
    def stop(self) -> None:
        """Cierra la ventana de forma controlada."""
        self.close()


class SequenceWidget(QWidget):
    """
    Widget encargado de visualizar la secuencia de estímulos esperados y detectados.

    Organiza las imágenes en una cuadrícula y permite resaltar el estímulo actual,
    así como registrar visualmente aciertos y fallos.
    """

    COLUMNS = 12

    def __init__(self) -> None:
        """Inicializa el widget, carga la UI"""
        super().__init__() 
        
        self.__stimulus_icons_hits = {
            0: ":/images/stims_icons/esc_hit.png",
            1: ":/images/stims_icons/space_hit.png",
            2: ":/images/stims_icons/right_hit.png",
            3: ":/images/stims_icons/up_hit.png",
            4: ":/images/stims_icons/left_hit.png",
            5: ":/images/stims_icons/down_hit.png"
        }
        self.__stimulus_icons_neutral = {
            0: ":/images/stims_icons/esc_neutral.png",
            1: ":/images/stims_icons/space_neutral.png",
            2: ":/images/stims_icons/right_neutral.png",
            3: ":/images/stims_icons/up_neutral.png",
            4: ":/images/stims_icons/left_neutral.png",
            5: ":/images/stims_icons/down_neutral.png"
        }
        self.__stimulus_icons_miss = {
            0: ":/images/stims_icons/esc_miss.png",
            1: ":/images/stims_icons/space_miss.png",
            2: ":/images/stims_icons/right_miss.png",
            3: ":/images/stims_icons/up_miss.png",
            4: ":/images/stims_icons/left_miss.png",
            5: ":/images/stims_icons/down_miss.png"
        }
        
        self.__stimulus_colors = {
            0: "#F2C200",  # Escape / cuadrado -> amarillo
            1: "#1E88E5",  # Espacio / círculo -> azul
            2: "#FB8C00",  # Derecha -> naranja
            3: "#43A047",  # Arriba -> verde
            4: "#8E24AA",  # Izquierda -> violeta
            5: "#E53935",  # Abajo -> rojo
        }

        self.__detected_count = 0
        self.__expected_labels = []
        self.__expected_colors = []
        self.__last_highlighted_index = None

        self.__ui = Ui_sequenceWidget()
        self.__ui.setupUi(self)
        


        # Configurar estiramiento de columnas para distribución uniforme
        for layout_name in ("expectedSequenceLayout", "detectedSequenceLayout"):
            grid = getattr(self.__ui, layout_name)
            for c in range(self.COLUMNS):
                grid.setColumnStretch(c, 1)

    def add_sequence(self, sequence: list[int]) -> None:
        """
        Recibe una lista de índices y genera la cuadrícula de imágenes esperadas.

        Args:
            sequence (list[int]): Lista de índices que representan la secuencia de estímulos.
        """
        self.__clear_layout(self.__ui.expectedSequenceLayout)
        self.__expected_labels.clear()
        self.__expected_colors.clear()
        self.__last_highlighted_index = None

        for i, index in enumerate(sequence):
            resource_path = self.__stimulus_icons_neutral.get(index)

            if resource_path:
                pixmap = QPixmap(resource_path)
                label_img = ScalableLabel(pixmap)
                self.__expected_labels.append(label_img)
                self.__expected_colors.append(self.__stimulus_colors.get(index))

                row = i // self.COLUMNS
                col = i % self.COLUMNS
                self.__ui.expectedSequenceLayout.addWidget(label_img, row, col)
            else:
                print(f"Error: El índice de estímulo {index} no está en el diccionario.")

    def highlight_expected_index(self, index: int) -> None:
        """
        Resalta con su color fijo únicamente el estímulo que hay que mirar
        ahora; el resto queda sin recuadro. Los estímulos anteriores a
        `index` (los que ya tuvieron su turno) quedan atenuados de forma
        permanente para el resto de la prueba.

        Args:
            index (int): Índice de la secuencia a resaltar. Si es -1 o inválido, limpia todos los resaltados.
        """
        for i, label in enumerate(self.__expected_labels):
            color = self.__expected_colors[i] if i == index else None
            label.set_highlight(color)
            label.set_faded(i < index)

    def clear_sequence(self) -> None:
        """Limpia la secuencia esperada, tanto del layout como de las referencias internas."""
        self.__clear_layout(self.__ui.expectedSequenceLayout)
        self.__expected_labels.clear()
        self.__last_highlighted_index = None

    def clear_detected_sequence(self) -> None:
        """Limpia la secuencia de estímulos detectados y reinicia el contador."""
        self.__clear_layout(self.__ui.detectedSequenceLayout)
        self.__detected_count = 0

    def add_hit(self, hit_index: int) -> None:
        """
        Añade visualmente un estímulo acertado a la secuencia detectada.

        Args:
            hit_index (int): Índice del estímulo acertado.
        """
        resource_path = self.__stimulus_icons_hits.get(hit_index)
        if resource_path:
            pixmap = QPixmap(resource_path)
            label_img = ScalableLabel(pixmap)
            self.__add_detected_widget(label_img)
        else:
            print(f"Error: El índice de estímulo {hit_index} no está en el diccionario de hits.")

    def add_miss(self, miss_index: int) -> None:
        """
        Añade visualmente un estímulo fallado a la secuencia detectada.

        Args:
            miss_index (int): Índice del estímulo fallado.
        """
        resource_path = self.__stimulus_icons_miss.get(miss_index)
        if resource_path:
            pixmap = QPixmap(resource_path)
            label_img = ScalableLabel(pixmap)
            self.__add_detected_widget(label_img)
        else:
            print(f"Error: El índice de estímulo {miss_index} no está en el diccionario de misses.")

    def __add_detected_widget(self, label_img: QLabel) -> None:
        """
        Método interno para añadir un widget al layout de detectados y gestionar su posición.

        Args:
            label_img (QLabel): La etiqueta con la imagen a añadir.
        """
        row = self.__detected_count // self.COLUMNS
        col = self.__detected_count % self.COLUMNS

        if col == 0:
            self.__ui.detectedSequenceLayout.setRowStretch(row, 1)

        self.__ui.detectedSequenceLayout.addWidget(label_img, row, col)
        self.__detected_count += 1

    def __clear_layout(self, layout) -> None:
        """
        Método interno para eliminar todos los widgets de un QLayout de forma segura.

        Args:
            layout: Instancia de QLayout a limpiar.
        """
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
    
    def hide_detected_sequence (self, hide):
        self.__ui.lblDetectedSequence.setVisible(hide)
        self.__ui.scrollArea.setVisible(hide)


class ScalableLabel(QLabel):
    """
    Etiqueta personalizada que escala pixmap manteniendo la relación de aspecto.

    Attributes:
        MIN_SIZE (int): Tamaño mínimo en píxeles (ancho y alto).
        PREFERRED_SIZE (int): Tamaño preferido para el cálculo de hints de tamaño.
    """

    MIN_SIZE = 20
    PREFERRED_SIZE = 90
    FADED_OPACITY = 0.3

    def __init__(self, pixmap: QPixmap, parent: QWidget = None) -> None:
        """
        Inicializa la etiqueta con un pixmap.

        Args:
            pixmap (QPixmap): Imagen original a mostrar.
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.__original_pixmap = pixmap
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(self.MIN_SIZE, self.MIN_SIZE)
        self.setFixedSize(self.PREFERRED_SIZE, self.PREFERRED_SIZE)
        self.__opacity_effect = QGraphicsOpacityEffect(self)
        self.__opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.__opacity_effect)
        self._update_pixmap()

    def set_faded(self, faded: bool) -> None:
        """
        Atenúa (o restaura) la opacidad del ícono, para marcar de forma
        permanente los estímulos de la secuencia que ya tuvieron su turno.

        Args:
            faded (bool): True para atenuar, False para opacidad normal.
        """
        self.__opacity_effect.setOpacity(self.FADED_OPACITY if faded else 1.0)

    def set_highlight(self, color: str | None) -> None:
        """
        Marca este ícono como el estímulo que hay que mirar ahora, con un
        borde fino de su color asignado. `color=None` quita el recuadro.

        Args:
            color (str | None): Color CSS del borde (ej. "#F2C200"), o None.
        """
        if color:
            self.setStyleSheet(f"border: 3px solid {color}; border-radius: 6px;")
        else:
            self.setStyleSheet("")

    def resizeEvent(self, event) -> None:
        """
        Sobrescribe el resizeEvent para actualizar la escala del pixmap.

        Args:
            event: QResizeEvent con parametros para redimención.
        """
        self._update_pixmap()
        super().resizeEvent(event)

    def _update_pixmap(self) -> None:
        """Actualiza el pixmap escalado según el tamaño actual del widget."""
        if self.__original_pixmap.isNull() or self.size().width() <= 0:
            return
        
        scaled = self.__original_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)

    def sizeHint(self) -> QSize:
        """Devuelve el tamaño preferido del widget."""
        return QSize(self.PREFERRED_SIZE, self.PREFERRED_SIZE)

    def minimumSizeHint(self) -> QSize:
        """Devuelve el tamaño mínimo permitido para el widget."""
        return QSize(self.MIN_SIZE, self.MIN_SIZE)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    ventana_prueba = SequenceWidget()
    mi_secuencia = [3, 0, 5, 2, 1, 4, 0, 2, 5, 3, 4, 1]
    ventana_prueba.add_sequence(mi_secuencia)

    ventana_prueba.resize(900, 400)
    ventana_prueba.show()
    ventana_prueba.highlight_expected_index(0)

    resultado_simulado = iter([
        ("hit", 3), ("hit", 0), ("miss", 5), ("hit", 2),
        ("miss", 1), ("hit", 4), ("hit", 0), ("miss", 2),
        ("hit", 5), ("hit", 3), ("miss", 4), ("hit", 1)
    ])

    paso_actual = [0] 

    def procesar_siguiente() -> None:
        """Función callback para el QTimer que simula la llegada de resultados."""
        try:
            tipo, index = next(resultado_simulado)
        except StopIteration:
            timer.stop()
            ventana_prueba.highlight_expected_index(-1)
            return

        if tipo == "hit":
            ventana_prueba.add_hit(index)
        else:
            ventana_prueba.add_miss(index)
            
        paso_actual[0] += 1
        ventana_prueba.highlight_expected_index(paso_actual[0])

    timer = QTimer()
    timer.timeout.connect(procesar_siguiente)
    timer.start(1000)

    sys.exit(app.exec())
