from timeit import default_timer as timer
import builtins

from PySide6.QtCore import Qt, QTimerEvent, Signal, Slot
from PySide6.QtGui import (QColor, QFont, QPainter, QPaintEvent, QPen, QPixmap,
                           QResizeEvent)
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from ssvep.app.settings import valid_px_per_cm


X, Y = 0, 1
FRAMES_INTERVAL = 40 #ms = 25 FPS

from ssvep.ui.eeg_widget_ui import Ui_EEGWidget

class EEGWidget(QWidget, Ui_EEGWidget):
    """
    Widget para graficacion de EEG.
    """
    def __init__(self):
        QWidget.__init__(self)
        self.setupUi(self)
        # TODO implementar graficacion de senal guardada
        self.sbEEG.setVisible(False)
        # Timer de graficacion en tiempo real
        self.__streaming_thread = None
        # Pixmaps de grilla y senal de EEG
        self.__grid_pixmap = None
        self.__eeg_pixmap  = None
        # Atributos de graficacion
        self.__old_points   = [(0, 0) for _ in range(builtins.CHANNELS_NUMBER)]
        self.__signal_buffer= [[] for _ in range(builtins.CHANNELS_NUMBER)]
        self.__last_sample  = [0] * builtins.CHANNELS_NUMBER
        self.__graph_seconds = 0
        # Por defecto comienza deshabilitado
        self.setEnabled(False)
        self.__set_channel_labels_outline()
        self.eeg_settings_changed()

    @Slot(bool)
    def setEnabled(self, enabled) -> None:
        # Al deshabilitar oculta labels de canales y graficacion
        super().setEnabled(enabled)       
        if not enabled:
            self.__show_channel_labels(False)
            self.__clear_signal()
        else:
            self.__resize_pixmaps(self.size())

    def eeg_settings_changed(self):
        """ Actualiza GUI al cambiar configuracion de usuario. """
        self.__update_channel_labels_color()
        # Cambia escala de amplitud segun configuracion
        self.__pixels_per_cm = valid_px_per_cm(builtins.SETTINGS.px_per_cm)
        # Implementados: mili, micro y nanovolt
        self.__set_aplitude_unit(builtins.SETTINGS.amplitude_scale)
        # Setea divisor de amplitud
        self.__set_aplitude(builtins.SETTINGS.amplitude_value)
        # Implementados: x0.5, x1.0, x2.0
        self.__set_speed(builtins.SETTINGS.speed_scale)
        # Volver a graficar
        self.__resize_pixmaps(self.size())

    def __set_speed(self, value):
        """ Cambia velocidad de graficacion. """
        self.__speed = value

    def __set_aplitude(self, value):
        """ Cambia escala de amplitud. """
        self.__amplitude = value
        self.__y_scale = self.__pixels_per_cm / self.__amplitude

    def __set_aplitude_unit(self, index):
        """ Cambia unidad de amplitud. """
        if index == 0: # mV - mili
            self.__calibration = builtins.MV_VALUE
        elif index == 1: # uV - micro
            self.__calibration = builtins.MV_VALUE / 1_000
        elif index == 2: # nV - nano
            self.__calibration = builtins.MV_VALUE / 1_000_000

    @Slot(QPaintEvent)
    def paintEvent(self, event):
        """ Grafica pixmaps de grilla y EEG. """
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(event.rect(), self.__grid_pixmap)
        painter.drawPixmap(event.rect(), self.__eeg_pixmap)
        painter.end()

    @Slot(QResizeEvent)
    def resizeEvent(self, event):
        self.__resize_pixmaps(event.size())

    def __reset_old_points(self):
        """ Reiniciar ultimos X e Y de cada canal. """
        for i in range(builtins.CHANNELS_NUMBER):
            self.__old_points[i] = (0, self.__channel_height * ((i << 1) + 1) / 2)

    def __resize_pixmaps(self, size):
        """ Ajusta los pixmaps al nuevo tamano y la cantidad de muestras a graficar. """
        if not self.isEnabled():
            return
        unscaled_seconds = round(size.width() / builtins.SAMPLE_RATE) # tiene que dar al menos 1 seg
        prev_seconds = self.__graph_seconds
        self.__graph_seconds = unscaled_seconds * self.__speed # segundos a graficar
        eeg_size = size
        eeg_size.setWidth(unscaled_seconds * builtins.SAMPLE_RATE) # pixeles a graficar

        # Ajusta altura de canales
        self.__channel_height = eeg_size.height() / self.__enabled_channels
        # Si no cambia la cantidad de segundos o
        # altura de la ventana, no hace falta actualizar.
        if not self.__eeg_pixmap or prev_seconds != self.__graph_seconds or eeg_size != self.__eeg_pixmap.size():
            self.__eeg_pixmap = QPixmap(eeg_size)
            self.__eeg_pixmap.fill(Qt.transparent)
            self.__reset_old_points()
        # La grilla siempre se actualiza
        self.__grid_pixmap = QPixmap(size)
        self.__draw_grid()

    def __start_drawing_timer(self):
        """ Inicia thread de graficacion. """
        self.__stop_drawing_timer()
        # El primer paquete se grafica rapido
        self.__last_draw_time = timer()
        self.__streaming_thread = self.startTimer(FRAMES_INTERVAL)

    def __stop_drawing_timer(self):
        """ Detiene thread de graficacion. """
        if self.__streaming_thread:
            # Como al terminar la graficacion, se termina el estudio,
            # no hace falta graficar lo que queda en buffer.
            self.killTimer(self.__streaming_thread)
            self.__streaming_thread = None

    def stop_drawing(self):
        """ Detiene graficacion de EEG. """
        self.__stop_drawing_timer()

    def add_filtered_signal(self, signal):
        """ Agrega senal ya filtrada al buffer de graficacion. """
        for i, ch in enumerate(signal):
            self.__signal_buffer[i].extend(ch)
        # Si hace falta, inicia timer de graficacion
        if not self.__streaming_thread:
            self.__start_drawing_timer()

    @Slot(QTimerEvent)
    def timerEvent(self, _):
        self.__update_drawn_signal()

    def __update_drawn_signal(self, whole=False):
        """ Calcula la cantidad de muestras a graficar entre timeouts. """
        current_time = timer()
        if not whole: # dibujar en partes
            samples_amount = int((current_time - self.__last_draw_time) * builtins.SAMPLE_RATE) + 1
            if samples_amount > len(self.__signal_buffer[0]):
                samples_amount = len(self.__signal_buffer[0])
        else: # dibujar totalidad
            samples_amount = len(self.__signal_buffer[0])

        if samples_amount > 1:
            samples_amount -= samples_amount % 2 # pasar a numero par
            self.__last_draw_time = current_time
            self.__draw_signal(samples_amount)

    def __get_x_scaled_signal(self, from_idx, to_idx) -> list:
        """ Retorna la senal escalada en X segun velocidad de graficacion. """
        def interpolate_signal(from_idx, to_idx) -> list:
            """ Retorna la senal con sus muestras incrementada en dos. """
            def interpolate(y1, y2) -> float:
                """ Retorna el valor entre y1 e y2. """
                return y1 + ((y2 - y1) / 2)
            
            new_signal = []
            for ch_idx, ch_signal in enumerate(self.__signal_buffer):
                new_ch_signal = [0] * ((to_idx - from_idx) << 1)
                i = 0
                for sample in ch_signal[from_idx:to_idx]:
                    new_ch_signal[i]   = interpolate(self.__last_sample[ch_idx], sample)
                    new_ch_signal[i+1] = sample
                    self.__last_sample[ch_idx] = sample
                    i += 2
                new_signal.append(new_ch_signal)
            return new_signal
        
        if self.__speed == .5:
            # Multiplicar por dos, interpolando
            signal_to_draw = interpolate_signal(from_idx, to_idx)
        elif self.__speed == 1.:
            # Derecho, una muestra por pixel
            signal_to_draw = [ch[from_idx:to_idx] for ch in self.__signal_buffer]
        else:
            # Dividir cada dos muestras
            signal_to_draw = [ch[from_idx:to_idx:2] for ch in self.__signal_buffer]
        return signal_to_draw

    def __draw_signal(self, samples_amount):
        """ Grafica la cantidad de muestras dadas, previamente escala la senal. """
        def clear_out_portion(x_start, x_end):
            """ Borra porcion del pixmap, para luego graficar muestras nuevas. """
            painter.setCompositionMode(QPainter.CompositionMode_Clear) # Limpiar
            painter.eraseRect(x_start, 0, x_end, self.__eeg_pixmap.height())
            painter.setCompositionMode(QPainter.CompositionMode_Source) # Normal

        def draw_samples(ch_idx, samples):
            """ Grafica todas las muestras dadas y actualiza X e Y del canal. """
            old_x, old_y = self.__old_points[ch_idx]
            new_x, new_y = old_x, 0
            for sample in samples:
                # Calcular X e Y
                new_x += 1
                new_y = self.__channel_height / 2 \
                    + round(sample * self.__y_scale / self.__calibration)
                # Limitar altura
                if new_y < 0:
                    new_y = 0
                elif new_y > self.__channel_height:
                    new_y = self.__channel_height
                # Sumar offset del canal
                new_y += self.__channel_height * ch_idx
                # Usar primitivos es mas rapido para graficar
                # Graficar linea entre punto anterior y nuevo 
                painter.drawLine(old_x, old_y, new_x, new_y)
                old_x, old_y = new_x, new_y
            # Checkea fin de pixmap
            if new_x == self.__eeg_pixmap.width():
                new_x = 0
            # Actualizar ultimo X, Y del canal
            self.__old_points[ch_idx] = (new_x, new_y)
        
        # Obtener senal escalada en X
        signal_to_draw = self.__get_x_scaled_signal(0, samples_amount)
        # Reducir buffer con senal
        for i in range(len(self.__signal_buffer)):
            self.__signal_buffer[i] = self.__signal_buffer[i][samples_amount:]
        # Graficar muestras de cada canal en orden
        painter = QPainter()
        painter.begin(self.__eeg_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(builtins.SETTINGS.signal_color)
        #
        signal_length = len(signal_to_draw[0])
        start_idx, end_idx = 0, 0
        # Si no alcanza el pixmap para graficar
        # todas las muestras, grafica en tramos.
        while signal_length >= self.__eeg_pixmap.width() - self.__old_points[0][X]:
            samples_to_draw = self.__eeg_pixmap.width() - self.__old_points[0][X]
            clear_out_portion(self.__old_points[0][X], samples_to_draw)
            end_idx += samples_to_draw
            for ch_index in range(len(signal_to_draw)):
                draw_samples(ch_index, signal_to_draw[ch_index][start_idx:end_idx])
            start_idx = end_idx
            signal_length -= start_idx
        # Grafica las muestras restantes
        if signal_length > 0:
            clear_out_portion(self.__old_points[0][X], signal_length)
            for ch_index in range(len(signal_to_draw)):
                draw_samples(ch_index, signal_to_draw[ch_index][start_idx:])
        #
        painter.end()
        self.update()

    def __draw_grid(self):
        """ Grafica grilla, label de segundos y escala de amplitud. """
        # Inicializa parametros
        
        dx = (self.__grid_pixmap.width() / self.__graph_seconds) / (5 / builtins.SETTINGS.speed_scale) # cada seg separado en 5
        dy = self.__pixels_per_cm / 2
        pen_dash = QPen() # Pen para lineas de puntos
        pen_dash.setColor(builtins.SETTINGS.grid_color)
        pen_dash.setDashPattern([1, dy / 6])
        font_sec = QFont() # Font para label de segundos
        font_sec.setPointSize(12)
        # Pinta grilla del color base
        self.__grid_pixmap.fill(builtins.SETTINGS.bkgrd_color)
        # Comienza a graficar grilla con painter
        painter = QPainter()
        painter.begin(self.__grid_pixmap)
        painter.setFont(font_sec)
        font_metrics = painter.fontMetrics()
        line_count = 0
        pos = .0
        # Grafica lineas verticales y contadores de segundos
        while pos <= self.__grid_pixmap.width():
            # No se grafica el ultimo pixel
            if pos == self.__grid_pixmap.width():
                pos = self.__grid_pixmap.width() - 1
            if line_count % 5 != 0:
                # Linea vertical de puntos
                painter.setPen(pen_dash)
                painter.drawLine(pos, .0, pos, self.__grid_pixmap.height())
            else:
                step = line_count // 5 * builtins.SETTINGS.speed_scale
                # Si 'step' es entero, remueve decimales para el label
                label_text   = str(int(step) if step % 1 == 0 else step)
                label_width  = font_metrics.horizontalAdvance(label_text) / 2
                label_height = font_metrics.height() / 2
                line_height  = self.__grid_pixmap.height()
                # No grafica el label si es el primer o ultimo segundo
                if pos - label_width > 0 and pos + label_width < self.__grid_pixmap.width():
                    painter.setPen(builtins.SETTINGS.seconds_color)
                    painter.drawText(pos - label_width, self.__grid_pixmap.height() - label_height, label_text)
                    line_height -= label_height * 3
                # Linea vertical continua
                painter.setPen(builtins.SETTINGS.grid_color)
                painter.drawLine(pos, .0, pos, line_height)
            pos += dx
            line_count += 1
        # Si alcanza la altura, graficar indicadores
        if self.__channel_height > self.__pixels_per_cm:
            self.__draw_amp_indicator(painter, dx, dy)
            self.__draw_scale_indicator(painter)
        painter.end()

    def __draw_amp_indicator(self, painter, dx, dy):
        """ Grafica en painter indicador del punto cero y de amplitud en cada canal. """
        pen_dash = QPen() # Pen para lineas de puntos
        pen_dash.setColor(builtins.SETTINGS.grid_color)
        pen_dash.setDashPattern([2, dy / 12])
        channel_mid_y = self.__channel_height / 2
        for i in range(self.__enabled_channels):
            # Graficar linea llena del punto cero
            painter.setPen(builtins.SETTINGS.zero_line_color)
            painter.drawLine(0, channel_mid_y, self.__grid_pixmap.width() - 1, channel_mid_y)
            # Calcular top y bottom de amplitud
            top_y = channel_mid_y + (self.__pixels_per_cm / 2)
            bottom_y = top_y - self.__pixels_per_cm
            # Graficar lineas de puntos horizontales
            painter.setPen(pen_dash)
            painter.drawLine(0, top_y, dx, top_y)
            painter.drawLine(0, bottom_y, dx, bottom_y)
            #
            channel_mid_y += self.__channel_height

    def __draw_scale_indicator(self, painter):
        """ Grafica en painter indicador y valor de amplitud y tiempo. """
        # Tamano canvas
        heigth = self.__grid_pixmap.height()
        width  = self.__grid_pixmap.width()
        # Tamano de calipers
        line_heigth = self.__pixels_per_cm
        line_width  = (width / self.__graph_seconds) / (5 / builtins.SETTINGS.speed_scale)
        # Margen inferior y superio
        margin = self.__pixels_per_cm >> 2
        half_margin = margin >> 1
        twice_margin = margin << 1
        painter.setPen(builtins.SETTINGS.grid_color)
        # Graficar L
        painter.drawLine(margin, heigth-margin, margin, heigth-(margin+line_heigth)) # alto
        painter.drawLine(margin, heigth-margin, margin+line_width, heigth-margin) # ancho
        # Graficar Ts
        painter.drawLine(margin-half_margin, heigth-(margin+line_heigth), 
            margin+half_margin, heigth-(margin+line_heigth)) # alto
        painter.drawLine(margin+line_width, heigth-(margin+half_margin), 
            margin+line_width, heigth-(margin-half_margin)) # ancho
        # Fuente para valores de escala
        font_scale = QFont()
        font_scale.setPointSize(11)
        painter.setFont(font_scale)
        # Escribir amplitud y velocidad
        painter.setPen(builtins.SETTINGS.seconds_color)
        painter.drawText(margin+half_margin+2, heigth-(twice_margin + painter.fontMetrics().height()), 
            f"{builtins.SETTINGS.amplitude_value} {builtins.SETTINGS.amplitude_scale_text}") # amplitud
        painter.drawText(margin+half_margin+2, heigth-twice_margin, 
            f"{int(builtins.SETTINGS.speed_scale * 200)} ms") # tiempo

    def __clear_signal(self):
        """ Limpia EEG graficado y buffer de muestras. """
        if not self.__eeg_pixmap:
            return
        self.__eeg_pixmap.fill(Qt.transparent)
        self.__grid_pixmap.fill(Qt.transparent)
        self.update()
        # Limpiar para proxima adq
        self.__signal_buffer = [[] for _ in range(self.__enabled_channels)]
        self.__reset_old_points()

    def __get_channel_labels(self) -> list:
        """ Retorna lista con referencia a labels de canales. """
        result = []
        for i in range(builtins.CHANNELS_NUMBER):
            lbl = getattr(self, f'lblCH{i}', False)
            if lbl: # no deberia ser False
                result.append(lbl)
        return result

    def __set_channel_labels_outline(self):
        """ Agrega un efecto sombreado a los labels de canales. """
        def create_shadow_effect() -> QGraphicsDropShadowEffect:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setColor(QColor(Qt.white))
            shadow.setBlurRadius(4.)
            shadow.setOffset(0.)
            return shadow
        # Crea y asigna una instancia de efecto por cada lbl
        for lbl in self.__get_channel_labels():
            lbl.setGraphicsEffect(create_shadow_effect())

    def __show_channel_labels(self, visible):
        """ Oculta o muestra labels de canales. """
        for label in self.__get_channel_labels():
            label.setVisible(visible)

    def __update_channel_labels_color(self):
        """ Cambia color de fuente de labels de canales. """
        rgb_color = builtins.SETTINGS.channels_color.getRgb()
        style = f'color: rgba{rgb_color};'
        for label in self.__get_channel_labels():
            label.setStyleSheet(style)

    def setup_channel_labels(self, enabled_ch_dict):
        """ Configura labels de canales. """
        self.__enabled_channels = len(enabled_ch_dict)
        self.__signal_buffer = [[] for _ in range(self.__enabled_channels)]
        # Cambiar texto de labels de canales habilitados
        for i, lbl in enumerate(self.__get_channel_labels()):
            ch_name = enabled_ch_dict.get(i)
            if ch_name:
                lbl.setText(ch_name)
                lbl.setVisible(True)
            else:
                lbl.setVisible(False)