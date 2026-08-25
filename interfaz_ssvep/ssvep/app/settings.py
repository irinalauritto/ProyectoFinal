"""
Módulo de configuración de la aplicación.

Define la configuración fija de la aplicación (hardware, filtros,
visualización, colores). Las preferencias propias de cada usuario
(canales, estímulos, método de clasificación) se gestionan aparte,
en base de datos.
"""

import copy
import builtins
import heapq
import random

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from ssvep.app.dataclasses import Stimulus, UserPreferences


class Settings:
    """
    Configuración de la aplicación.

    Esta clase centraliza los parámetros de la aplicación: ajustes de
    interfaz EEG, visualización, colores y parámetros de estimulación.
    Los valores son fijos en código, no se leen ni se guardan desde
    ningún archivo externo.

    Attributes:
        intf_name (str): Nombre de la interfaz EEG conectada.
        intf_port_name (str): Nombre del puerto serie de la interfaz EEG.
        intf_port_auto (bool): Indica si la búsqueda de puerto es automática.
        out_port_name (str): Nombre del puerto serie de salida del clasificador.
        out_port_baud (int): Baudrate del puerto serie de salida.
        speed_scale (float): Escala de velocidad de graficación en segundos.
        amplitude_scale (int): Escala de amplitud de la señal EEG.
        amplitude_value (int): Valor máximo de amplitud para la graficación.
        px_per_cm (int): Píxeles por centímetro para calibración de monitor.
        signal_color (QColor): Color del trazo de la señal EEG.
        bkgrd_color (QColor): Color de fondo del gráfico EEG.
        grid_color (QColor): Color de la grilla del gráfico EEG.
        zero_line_color (QColor): Color de la línea de punto cero.
        channels_color (QColor): Color de las etiquetas de canales.
        seconds_color (QColor): Color de las etiquetas de segundos.
    """

    # ============================================================
    # Inicialización
    # ============================================================

    def __init__(self):
        """
        Inicializa la instancia de Settings con los valores fijos
        de configuración de la aplicación.
        """
        # Canales y estímulos
        self.__evaluation_total_trials: int = 30
        self.__locked_channels: dict[int, str] = {0: 'O1', 1: 'Oz', 2: 'O2'}
        self.__stimuli_config: dict[int, Stimulus] = {
            0: Stimulus(8, 0, "flic", "square"),
            1: Stimulus(8.5, 0.5, "flic", "circle"),
            2: Stimulus(9, 1.5, "flic", "arrow", "right"),
            3: Stimulus(9.5, 0, "flic", "arrow", "up"),
            4: Stimulus(10, 0.5, "flic", "arrow", "left"),
            5: Stimulus(10.5, 1.5, "flic", "arrow", "down"),
        }

        # Parámetros de entrenamiento
        self.__n_trials: int = 14
        self.__bandas_frec: int = 3
        self.__cue_duration_sec: int = 2  # segundos

        # Límites y restricciones
        self.__max_channels: int = 5

        # Plantilla de preferencias por defecto
        self.__default_prefs_template = UserPreferences(
            classification_method="CCA",
            time_window=1,
            channels=dict(self.locked_channels),
            stimulus=list(self.__stimuli_config.values()),
            stimulus_on=[True] * len(self.__stimuli_config),
        )

        # Interfaz EEG
        self.__interface_name: str = 'BioAmp'
        self.__interface_port_name: str | None = None
        self.__interface_port_auto: bool = True

        # Salida serial del clasificador
        self.__output_port_name: str | None = None
        self.__output_port_baud: int = 115200

        # Envío de teclado (pulso único al detectar un estímulo)
        self.__press_duration_ms: int = 250

        # Graficación EEG
        self.__speed_scale: float = 1.0
        self.__amp_scale: int = 1
        self.__amp_value: int = 100

        # Escala de monitor
        self.__pixels_per_cm: int = 0

        # Colores de graficación EEG
        self.__signal_color: QColor = QColor(0x000000)
        self.__bkgrd_color: QColor = QColor(0xFFFFFF)
        self.__grid_color: QColor = QColor(0xFF0000)
        self.__zero_line_color: QColor = QColor(0xFF8888)
        self.__channel_lbl_color: QColor = QColor(0x0A5E56)
        self.__seconds_lbl_color: QColor = QColor(0x000000)

    # ============================================================
    # Propiedades de interfaz EEG
    # ============================================================

    @property
    def intf_name(self) -> str:
        """
        Obtiene el nombre de la interfaz EEG.

        Returns:
            str: Nombre de la interfaz EEG.
        """
        return self.__interface_name

    @intf_name.setter
    def intf_name(self, value: str) -> None:
        """
        Establece el nombre de la interfaz EEG.

        Args:
            value (str): Nuevo nombre de la interfaz EEG.
        """
        self.__interface_name = value

    @property
    def intf_baudrate(self) -> int:
        """
        Obtiene el baudrate correspondiente a la interfaz EEG actual.

        El baudrate se determina según el tipo de interfaz:
        - Si el nombre contiene 'BCI', usa BCI_SERIAL_BAUDRATE.
        - En caso contrario, usa BA_SERIAL_BAUDRATE.

        Returns:
            int: Baudrate de la interfaz EEG.
        """
        return builtins.BCI_SERIAL_BAUDRATE if 'BCI' in self.intf_name else builtins.BA_SERIAL_BAUDRATE

    @property
    def intf_port_name(self) -> str | None:
        """
        Obtiene el nombre del puerto serie de la interfaz EEG.

        Returns:
            str | None: Nombre del puerto serie, o None si no está configurado.
        """
        return self.__interface_port_name

    @intf_port_name.setter
    def intf_port_name(self, value: str | None) -> None:
        """
        Establece el nombre del puerto serie de la interfaz EEG.

        Args:
            value (str | None): Nombre del puerto serie, o None para búsqueda automática.
        """
        self.__interface_port_name = value

    @property
    def intf_port_auto(self) -> bool:
        """
        Indica si la búsqueda automática del puerto serie está habilitada.

        Returns:
            bool: True si la búsqueda automática está habilitada, False en caso contrario.
        """
        return self.__interface_port_auto

    @intf_port_auto.setter
    def intf_port_auto(self, value: bool) -> None:
        """
        Habilita o deshabilita la búsqueda automática del puerto serie.

        Args:
            value (bool): True para habilitar búsqueda automática, False para deshabilitar.
        """
        self.__interface_port_auto = value

    # ============================================================
    # Propiedades de puerto de salida
    # ============================================================

    @property
    def out_port_name(self) -> str | None:
        """
        Obtiene el nombre del puerto serie de salida del clasificador.

        Returns:
            str | None: Nombre del puerto serie de salida.
        """
        return self.__output_port_name

    @out_port_name.setter
    def out_port_name(self, value: str | None) -> None:
        """
        Establece el nombre del puerto serie de salida del clasificador.

        Args:
            value (str | None): Nombre del puerto serie de salida.
        """
        self.__output_port_name = value

    @property
    def out_port_baud(self) -> int:
        """
        Obtiene el baudrate del puerto serie de salida.

        Returns:
            int: Baudrate del puerto serie de salida.
        """
        return self.__output_port_baud

    @out_port_baud.setter
    def out_port_baud(self, value: int) -> None:
        """
        Establece el baudrate del puerto serie de salida.

        Args:
            value (int): Nuevo baudrate del puerto serie de salida.
        """
        self.__output_port_baud = value

    @property
    def press_duration_ms(self) -> int:
        """
        Obtiene la duración del pulso de tecla enviado al detectar un
        estímulo (carril momentáneo del `KeyboardController`).

        Returns:
            int: Duración en milisegundos.
        """
        return self.__press_duration_ms

    @press_duration_ms.setter
    def press_duration_ms(self, value: int) -> None:
        """
        Establece la duración del pulso de tecla, acotada a [100, 10000] ms.

        Args:
            value (int): Nueva duración en milisegundos.
        """
        self.__press_duration_ms = max(100, min(10000, value))

    # ============================================================
    # Propiedades de graficación EEG
    # ============================================================

    @property
    def speed_scale(self) -> float:
        """
        Obtiene la escala de velocidad de graficación en segundos.

        Returns:
            float: Escala de velocidad actual.
        """
        return self.__speed_scale

    @speed_scale.setter
    def speed_scale(self, value: float) -> None:
        """
        Establece la escala de velocidad de graficación.

        Solo acepta valores válidos: 0.5, 1.0 o 2.0 segundos.

        Args:
            value (float): Nueva escala de velocidad. Debe ser 0.5, 1.0 o 2.0.
        """
        if value in [.5, 1., 2.]:
            self.__speed_scale = value

    @property
    def amplitude_scale(self) -> int:
        """
        Obtiene la escala de amplitud de la señal EEG.

        Returns:
            int: Índice de escala de amplitud (0: mV, 1: uV, 2: nV).
        """
        return self.__amp_scale

    @amplitude_scale.setter
    def amplitude_scale(self, value: int) -> None:
        """
        Establece la escala de amplitud de la señal EEG.

        Solo acepta valores válidos: 0, 1 o 2.

        Args:
            value (int): Índice de escala de amplitud. Debe ser 0, 1 o 2.
        """
        if value in [0, 1, 2]:
            self.__amp_scale = value

    @property
    def amplitude_scale_text(self) -> str:
        """
        Obtiene la escala de amplitud como texto legible.

        Returns:
            str: Texto de la unidad de amplitud ('mV', 'uV', 'nV') o '??' si es inválido.
        """
        elec_units = ['mV', 'uV', 'nV']
        try:
            return elec_units[self.__amp_scale]
        except (IndexError, TypeError):
            return '??'

    @property
    def amplitude_value(self) -> int:
        """
        Obtiene el valor máximo de amplitud para la graficación.

        Returns:
            int: Valor de amplitud actual.
        """
        return self.__amp_value

    @amplitude_value.setter
    def amplitude_value(self, value: int) -> None:
        """
        Establece el valor máximo de amplitud para la graficación.

        Solo acepta valores entre 1 y 1000 inclusive.

        Args:
            value (int): Nuevo valor de amplitud. Debe estar entre 1 y 1000.
        """
        if 1 <= value <= 1000:
            self.__amp_value = value

    # ============================================================
    # Propiedades de monitor
    # ============================================================

    @property
    def px_per_cm(self) -> int:
        """
        Obtiene los píxeles por centímetro del monitor.

        Returns:
            int: Cantidad de píxeles por centímetro.
        """
        return self.__pixels_per_cm

    @px_per_cm.setter
    def px_per_cm(self, value: int) -> None:
        """
        Establece los píxeles por centímetro del monitor.

        Args:
            value (int): Nueva cantidad de píxeles por centímetro.
        """
        self.__pixels_per_cm = value

    # ============================================================
    # Propiedades de colores
    # ============================================================

    @property
    def signal_color(self) -> QColor:
        """
        Obtiene el color del trazo de la señal EEG.

        Returns:
            QColor: Color del trazo de la señal.
        """
        return self.__signal_color

    @signal_color.setter
    def signal_color(self, value: QColor) -> None:
        """
        Establece el color del trazo de la señal EEG.

        Args:
            value (QColor): Nuevo color del trazo de la señal.
        """
        self.__signal_color = value

    @property
    def bkgrd_color(self) -> QColor:
        """
        Obtiene el color de fondo del gráfico EEG.

        Returns:
            QColor: Color de fondo del gráfico.
        """
        return self.__bkgrd_color

    @bkgrd_color.setter
    def bkgrd_color(self, value: QColor) -> None:
        """
        Establece el color de fondo del gráfico EEG.

        Args:
            value (QColor): Nuevo color de fondo.
        """
        self.__bkgrd_color = value

    @property
    def grid_color(self) -> QColor:
        """
        Obtiene el color de la grilla del gráfico EEG.

        Returns:
            QColor: Color de la grilla.
        """
        return self.__grid_color

    @grid_color.setter
    def grid_color(self, value: QColor) -> None:
        """
        Establece el color de la grilla del gráfico EEG.

        Args:
            value (QColor): Nuevo color de la grilla.
        """
        self.__grid_color = value

    @property
    def zero_line_color(self) -> QColor:
        """
        Obtiene el color del indicador de punto cero.

        Returns:
            QColor: Color del indicador de punto cero.
        """
        return self.__zero_line_color

    @zero_line_color.setter
    def zero_line_color(self, value: QColor) -> None:
        """
        Establece el color del indicador de punto cero.

        Args:
            value (QColor): Nuevo color del indicador.
        """
        self.__zero_line_color = value

    @property
    def channels_color(self) -> QColor:
        """
        Obtiene el color de las etiquetas de canales.

        Returns:
            QColor: Color de las etiquetas de canales.
        """
        return self.__channel_lbl_color

    @channels_color.setter
    def channels_color(self, value: QColor) -> None:
        """
        Establece el color de las etiquetas de canales.

        Args:
            value (QColor): Nuevo color de las etiquetas.
        """
        self.__channel_lbl_color = value

    @property
    def seconds_color(self) -> QColor:
        """
        Obtiene el color de las etiquetas de segundos.

        Returns:
            QColor: Color de las etiquetas de segundos.
        """
        return self.__seconds_lbl_color

    @seconds_color.setter
    def seconds_color(self, value: QColor) -> None:
        """
        Establece el color de las etiquetas de segundos.

        Args:
            value (QColor): Nuevo color de las etiquetas.
        """
        self.__seconds_lbl_color = value

    # ============================================================
    # Propiedades de estímulos y entrenamiento
    # ============================================================

    def generate_evaluation_sequence(self, active_indices: list[int]) -> list[int]:
        """
        Genera la secuencia de evaluación de estímulos, usando únicamente los
        índices de estímulos activos (encendidos) para el usuario actual.

        La cantidad total de trials es siempre `evaluation_total_trials`,
        sin importar cuántos estímulos estén activos, para que la prueba de
        desempeño dure lo mismo independientemente de la cantidad de
        estímulos seleccionados. Esos trials se reparten en partes iguales
        (lo más parejo posible) entre los estímulos activos, en un orden
        aleatorio que evita repeticiones consecutivas del mismo estímulo
        (cuando hay más de un estímulo activo).

        Args:
            active_indices: Índices de los estímulos actualmente activos
                (ej: [0, 2, 4] si solo esos estímulos están habilitados).

        Returns:
            list[int]: Lista de índices de estímulo que conforman la secuencia
                de evaluación. Vacía si no hay estímulos activos.
        """
        if not active_indices:
            return []

        n = len(active_indices)
        base, remainder = divmod(self.__evaluation_total_trials, n)

        shuffled_indices = list(active_indices)
        random.shuffle(shuffled_indices)

        counts = {
            index: base + (1 if i < remainder else 0)
            for i, index in enumerate(shuffled_indices)
        }

        if n == 1:
            index = shuffled_indices[0]
            return [index] * counts[index]

        # Algoritmo greedy tipo "reorganize string": en cada paso se elige el
        # estímulo con más repeticiones restantes (con desempate aleatorio),
        # evitando repetir el estímulo del trial anterior. Da una secuencia
        # bien mezclada, sin dos trials consecutivos del mismo estímulo.
        heap = [(-count, random.random(), index) for index, count in counts.items()]
        heapq.heapify(heap)

        pool: list[int] = []
        prev_index = None
        while heap:
            neg_count, _, index = heapq.heappop(heap)

            if index == prev_index:
                # No se puede repetir: se toma el siguiente candidato y se
                # reinserta este para más adelante.
                neg_count2, _, index2 = heapq.heappop(heap)
                pool.append(index2)
                prev_index = index2
                count2 = -neg_count2 - 1
                if count2 > 0:
                    heapq.heappush(heap, (-count2, random.random(), index2))
                heapq.heappush(heap, (neg_count, random.random(), index))
                continue

            pool.append(index)
            prev_index = index
            count = -neg_count - 1
            if count > 0:
                heapq.heappush(heap, (-count, random.random(), index))

        return pool

    @property
    def cue_duration_sec(self) -> int:
        """
        Tiempo que dura la señal que avisa el estímulo que se debe observar

        Returns:
            int: Duración del cue en segundos.
        """
        return self.__cue_duration_sec

    @property
    def trials_use(self) -> int:
        """
        Obtiene el número de ensayos utilizados en el entrenamiento.

        Returns:
            int: Número de ensayos.
        """
        return self.__n_trials

    @property
    def f_bands(self) -> int:
        """
        Obtiene el número de bandas de frecuencia utilizadas.

        Returns:
            int: Número de bandas de frecuencia.
        """
        return self.__bandas_frec

    @property
    def default_user_preferences(self) -> UserPreferences:
        """
        Retorna una copia independiente de la plantilla de preferencias por defecto.

        Utiliza deep copy para garantizar que la copia sea completamente
        independiente de la plantilla original.

        Returns:
            UserPreferences: Copia independiente de las preferencias por defecto.
        """
        return copy.deepcopy(self.__default_prefs_template)

    @property
    def locked_channels(self) -> dict[int, str]:
        """
        Retorna un diccionario con los canales fijos que no se pueden modificar.

        Returns:
            dict[int, str]: Copia del diccionario de canales bloqueados,
                donde la clave es el índice y el valor es el nombre del canal.
        """
        return self.__locked_channels.copy()

    @property
    def max_channels(self) -> int:
        """
        Obtiene el número máximo de canales permitidos.

        Returns:
            int: Número máximo de canales.
        """
        return self.__max_channels


def valid_px_per_cm(value: int, min_val: int = 10, max_val: int = 100) -> int:
    """
    Valida que un valor esté dentro del rango permitido.

    Si el valor está fuera del rango especificado, calcula y retorna los
    píxeles por centímetro físicos del monitor primario. Si no hay monitor
    disponible, retorna un valor por defecto de 40.

    Args:
        value (int): Valor a validar.
        min_val (int): Valor mínimo permitido. Por defecto es 10.
        max_val (int): Valor máximo permitido. Por defecto es 100.

    Returns:
        int: El valor original si está en rango, o los píxeles por cm
            del monitor si está fuera de rango.
    """
    if min_val <= value <= max_val:
        return value

    screen = QApplication.primaryScreen()
    if screen:
        return round(screen.physicalDotsPerInchY() / 2.54)
    return 40