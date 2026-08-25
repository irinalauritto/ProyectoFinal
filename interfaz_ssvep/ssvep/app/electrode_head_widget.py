"""
Widget de cabeza con electrodos cicleables (click para activar/desactivar).

Incluye un botón para abrir la misma cabeza en una ventana más grande
(útil para ver mejor la ubicación de los electrodos).
"""

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsPixmapItem,
    QToolButton,
    QDialog,
    QVBoxLayout,
    QLabel,
)
from PySide6.QtGui import QBrush, QPen, QColor, QPixmap, QPainter, QFont, QFontMetrics
 
from PySide6.QtCore import Qt, Signal, QRectF
from res.images import resources_rc


class ElectrodeItem(QGraphicsEllipseItem):
    """Un electrodo individual. Click izquierdo togglea activo/inactivo."""

    def __init__(self, channel_name: str, x: float, y: float, radius: float = 25):
        super().__init__(QRectF(-radius, -radius, radius * 2, radius * 2))
        self.setPos(x, y)
        self.channel_name = channel_name
        self.active = False
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10)
        self._update_style()
        self._locked = False

    def _update_style(self):
        if self.active:
            # Amarillo semitransparente (R=255, G=234, B=0, Alfa=120) 
            # Puedes ajustar el 120 (0 a 255) para más o menos transparencia
            fill_color = QColor(255, 234, 0, 120) 
            border_color = QColor("#f1c40f") # Borde amarillo sólido para definir el click
            border_width = 2
        else:
            # Totalmente transparente cuando está inactivo
            fill_color = QColor(0, 0, 0, 0) 
            border_color = QColor(0, 0, 0, 0)
            border_width = 0

        self.setBrush(QBrush(fill_color))
        self.setPen(QPen(border_color, border_width))

    def toggle(self):
        self.active = not self.active
        self._update_style()

    def mousePressEvent(self, event):
        
        if self._locked:
            event.ignore()
            return
        self.toggle()
        scene = self.scene()
        if isinstance(scene, HeadScene):
            scene.channel_toggled.emit(self.channel_name, self.active)
        super().mousePressEvent(event)
    def set_locked(self, locked):
        self._locked = locked


class HeadScene(QGraphicsScene):
    channel_toggled = Signal(str, bool)


class ElectrodeHeadWidget(QGraphicsView):
    """
    Widget cicleable: cabeza + electrodos posicionados en coordenadas
    normalizadas (0-1) sobre el sistema 10-20 (aprox, simplificado).

    Incluye un botón "⛶" en la esquina superior derecha que abre la misma
    cabeza (misma QGraphicsScene) en una ventana aparte más grande.

    Uso:
        head = ElectrodeHeadWidget()
        head.channel_toggled.connect(mi_slot)
        head.set_active_channels({"Cz", "O1"})   # setea estado inicial
        activos = head.get_active_channels()      # lee estado actual
    """

    channel_toggled = Signal(str, bool)

    # Posiciones normalizadas (0=izquierda/arriba, 1=derecha/abajo) sobre el
    # bounding box de la cabeza. AJUSTAR según tu montaje real de electrodos.

    CHANNEL_POSITIONS = {
        "O1": (0.375, 0.582), #list
        "Oz": (0.50, 0.555), #listo
        "O2": (0.624, 0.583), #listo
        "POz": (0.508, 0.381), #listo
        "PO3": (0.40, 0.491), #listo
        "PO4": (0.608, 0.491), #listo
        "PO7": (0.26, 0.578), #listo
        "PO8": (0.745, 0.585),#listo
    }
    def __init__(self, parent=None, head_size: float = 300):
        super().__init__(parent)
        self._scene = HeadScene(self)
        #self._scene.channel_toggled.connect(self.__on_channel_toggled)
        self._scene.channel_toggled.connect(self.channel_toggled) 
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
            | QPainter.TextAntialiasing
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        #pixmap = QPixmap("../../res/images/electrodes_placement.svg")
        pixmap = QPixmap(":/images/electrodes_placement.svg")

        if pixmap.isNull():
            raise FileNotFoundError("No se pudo cargar la imagen de la cabeza")

        self._head_item = QGraphicsPixmapItem(pixmap)  # sin .scaled()
        self._scene.addItem(self._head_item)
        self._scene.setSceneRect(self._head_item.boundingRect())

        head_w = pixmap.width()
        head_h = pixmap.height()

        self._electrodes = {}
        for name, (nx, ny) in self.CHANNEL_POSITIONS.items():
            item = ElectrodeItem(name, nx * head_w, ny * head_h)
            self._scene.addItem(item)
            self._electrodes[name] = item

        # --- Botón para abrir en ventana grande ---
        self._expand_btn = QToolButton(self)
        self._expand_btn.setText("⛶")
        self._expand_btn.setToolTip("Abrir en ventana grande")
        self._expand_btn.setFixedSize(28, 28)
        self._expand_btn.setStyleSheet(
            "QToolButton { background: rgba(255,255,255,220); "
            "border: 1px solid #888; border-radius: 4px; font-size: 14px; }"
            "QToolButton:hover { background: rgba(255,255,255,255); }"
        )
        self._expand_btn.clicked.connect(self.open_in_window)
        
        self._channels_label = QLabel(self)
        self._channels_label.setAlignment(Qt.AlignLeft)
        self._channels_label.setStyleSheet(
            """
            QLabel {
                color: rgb(15, 15, 15);
                font: 12pt "Cascadia Mono ExtraLight";
                font-weight: bold;
                background-color: rgba(245, 245, 245, 220);
                border: 1px solid rgba(0, 0, 0, 35);
                border-radius: 10px;
                padding: 6px;
            }
            """
        )
        # Ocultar por defecto hasta que se le pasen canales
        self._channels_label.setVisible(False)

        # Referencia al diálogo abierto (evita que el GC lo destruya y evita duplicados)
        self._expanded_dialog = None
        
        self.__locked_channels = set()

    def resizeEvent(self, event):
        super().resizeEvent(event)
 
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._expand_btn.move(self.width() - self._expand_btn.width() - 8, 8)
        self._update_label_position()


        
    def _update_label_position(self):
        """Calcula el ancho dinámico y centra el label arriba."""
        if self._channels_label.isVisible():
            # Le damos un tamaño ajustado a su texto más el padding
            self._channels_label.adjustSize()
            
            # Margen superior de 8px y centrado horizontalmente
            x = 8#(self.width() - self._channels_label.width()) // 2
            y = 8
            self._channels_label.move(x, y)




    def set_channels_display(self, channels_dict: dict) -> None:
        """
        Recibe un diccionario {numero_canal: nombre_canal} 
        y los muestra formateados en el QLabel superior.
        Ejemplo: {1: "O1", 2: "Oz", 3: "O2"} -> "1: O1 | 2: Oz | 3: O2"
        """
        self._channels_label.clear()

        if not channels_dict:
            self._channels_label.setVisible(False)
            return

        # Formateamos los elementos del diccionario combinándolos con un separador visual
        items = [f'Canal {num}: {name}' for num, name in sorted(channels_dict.items())]
        text = "\n".join(items)
        
        self._channels_label.setText(text)
        self._channels_label.setVisible(True)
        
        # Forzar el cálculo de posición tras cambiar el texto
        self._update_label_position()

    def set_active_channels(self, channel_names) -> None:
        """Setea el estado inicial (por ej. al cargar preferencias del usuario)."""
        names = set(channel_names)
        
        for name, item in self._electrodes.items():
            
            item.active = name in names
            item._update_style()
            
    def set_locked_channels(self, locked_channels) -> None:
        """Setea los canales que habilitados permanentemente"""

        self.__locked_channels = set(locked_channels)
        self.set_active_channels(locked_channels)
        
        for name, item in self._electrodes.items():

            item.set_locked(name in locked_channels)
        
    def get_active_channels(self) -> set:
        return {name for name, item in self._electrodes.items() if item.active}
    
    def clear(self) -> None:
        """
        Resetea por completo el widget a su estado inicial:
        Desactiva y desbloquea todos los electrodos del mapa.
        """
        # 1. Vaciar el conjunto interno de canales bloqueados
        self.__locked_channels.clear()
        
        # 2. Resetear el estado de cada electrodo individual
        for item in self._electrodes.values():
            item.active = False
            item.set_locked(False)
            item._update_style()
            


    def open_in_window(self):
        """Abre la MISMA escena en una ventana más grande (no modal).

        Como es la misma instancia de QGraphicsScene, los clics en cualquiera
        de las dos ventanas quedan sincronizados automáticamente: no hay
        estado duplicado que mantener al día a mano.
        """
        if self._expanded_dialog is not None:
            # Ya está abierta: la traemos al frente en vez de abrir otra
            self._expanded_dialog.raise_()
            self._expanded_dialog.activateWindow()
            return

        self._expanded_dialog = _ExpandedHeadDialog(self._scene, parent=self.window())
        self._expanded_dialog.finished.connect(self.__on_expanded_dialog_closed)
        self._expanded_dialog.show()

    def __on_expanded_dialog_closed(self):
        self._expanded_dialog = None


class _ExpandedHeadDialog(QDialog):
    """Ventana secundaria que muestra la MISMA escena que el widget chico."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ubicación de electrodos")
        self.resize(700, 800)
        
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        self._view = QGraphicsView(scene, self)
        self._view.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        layout.addWidget(self._view)

    def showEvent(self, event):
        super().showEvent(event)
        self._view.fitInView(self._view.scene().sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._view.fitInView(self._view.scene().sceneRect(), Qt.KeepAspectRatio)
