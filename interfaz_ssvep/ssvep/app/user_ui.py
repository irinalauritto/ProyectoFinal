"""
Módulo de Interfaz de Usuario para la aplicación SSVEP.

Este módulo contiene la clase principal UserUI, que gestiona la ventana,
las señales, la navegación entre páginas y la interacción con el usuario
mediante una interfaz cargada dinámicamente desde un archivo .ui.
"""

import os
import sys

from PySide6.QtCore import Signal

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox


from ssvep.app.dataclasses import ClassificationMethods, StimulusTypes, UserPreferences
from ssvep.ui.ssvep_ui import Ui_SSVEP


class UserUI(QMainWindow):
    """
    Clase principal de la interfaz de usuario para la aplicación SSVEP.

    Gestiona la carga de la interfaz desde un archivo .ui, la conexión de señales
    y ranuras (slots), y la navegación entre las diferentes pantallas de la aplicación
    (inicio, selección de usuario, configuración, selección de juego).

    Attributes:
        new_user_request (Signal): Solicita la creación de un nuevo usuario (str: nombre).
        request_user_preferences (Signal): Solicita las preferencias de un usuario (int: user_id).
        remove_user_request (Signal): Solicita la eliminación de un usuario (int: user_id).
        save_user_preferences_request (Signal): Solicita guardar preferencias (int: user_id, UserPreferences: prefs).
        user_list_request (Signal): Solicita la actualización de la lista de usuarios.
        chk_toggle_space (Signal): Alterna el estado del estímulo de espacio (int: index, bool: state).
        start_training_request (Signal): Solicita iniciar el entrenamiento.
        start_test_request (Signal): Solicita iniciar la prueba.
        stop_game_request (Signal): Solicita detener el juego actual.
        psd_graph_request (Signal): Alterna la visualización del gráfico PSD (bool: state).
        game_list_request (Signal): Solicita la lista de juegos disponibles.
        bandpass_request (Signal): Alterna el filtro bandpass (bool: state).
        notch_request (Signal): Alterna el filtro notch (bool: state).
        average_request (Signal): Alterna el promedio de señales (bool: state).
        eeg_speed_request (Signal): Cambia la velocidad de visualización del EEG (float: speed).
        eeg_scale_request (Signal): Cambia la escala de visualización del EEG (int: scale).
        eeg_amplitude_request (Signal): Cambia la unidad de amplitud del EEG (int: amplitude).
        psd_channel_request (Signal): Cambia el canal para el gráfico PSD (int: channel_index).
        psd_mode_request (Signal): Cambia el modo de visualización del PSD (int: mode_index).
        start_game_request (Signal): Solicita iniciar un juego específico (str: game_name).
        start_streaming_request (Signal): Solicita iniciar el streaming de datos.
        stop_streaming_request (Signal): Solicita detener el streaming de datos.
        close_request (Signal): Solicita el cierre de la aplicación.
        threshold_request (Signal): Actualiza el umbral de clasificación (float: threshold).
        overlap_request (Signal): Actualiza el porcentaje de solapamiento (float: overlap).
        windows_welch_request (Signal): Actualiza el tamaño de la ventana de Welch (float: window_size).
        enable_control_request (Signal): Activa/desactiva el control (bool: state).
        enable_classify_request (Signal): Activa/desactiva la clasificación (bool: state).
    """

    # Señales de gestión de usuarios
    new_user_request = Signal(str)
    request_user_preferences = Signal(int)
    remove_user_request = Signal(int)
    save_user_preferences_request = Signal(int, UserPreferences)
    user_list_request = Signal()
    chk_toggle_space = Signal(int, bool)

    # Señales de control de juego y procesamiento
    start_training_request = Signal()
    start_test_request = Signal()
    stop_game_request = Signal()
    start_game_request = Signal(str)
    game_list_request = Signal()
    start_streaming_request = Signal()
    stop_streaming_request = Signal()
    close_request = Signal()

    # Señales de configuración de señal y visualización
    psd_graph_request = Signal(bool)
    bandpass_request = Signal(bool)
    notch_request = Signal(bool)
    average_request = Signal(bool)
    eeg_speed_request = Signal(float)
    eeg_scale_request = Signal(int)
    eeg_amplitude_request = Signal(int)
    psd_channel_request = Signal(int)
    psd_mode_request = Signal(int)
    threshold_request = Signal(float)
    overlap_request = Signal(float)
    windows_welch_request = Signal(float)
    enable_control_request = Signal(bool)
    enable_classify_request = Signal(bool)
    press_duration_request = Signal(int)
    audio_feedback_request = Signal(bool)

    def __init__(self) -> None:
        """Inicializa la ventana principal, carga la interfaz .ui y conecta las señales."""
        super().__init__()

        # --- Variables de estado ---
        self.__user: int | None = None
        self.__users: dict | None = None
        self.__user_preferences: UserPreferences | None = None
        self.__classification_methods = ClassificationMethods
        self.__stim_type = StimulusTypes
        self.__file_path = "./res/info/info.html"
        
        self.__selected_game: str | None = None
        self.__channels: dict | None = None
        self.__selected_channel: int | None = None
        self.__selected_eeg_speed: int | None = None
        self.__selected_eeg_scale: int | None = None
        self.__selected_eeg_amplitude: int | None = None
        self.__selected_psd_mode: int | None = None
        self.__selected_threshold: float | None = None

        self.__win_val: int = 1
        self.__over_val: int = 50
        self.__start_game: bool = False

        self.__led_list_freqs: list = []
        self.__enable_stimulus: list = []

        # --- Carga de la interfaz gráfica (.ui) ---
        self.__ui = Ui_SSVEP()
        self.__ui.setupUi(self)
        # --- Inicialización de listas de widgets ---
        self._init_widget_lists()

        # --- Conexión de señales y slots ---
        self._connect_signals()

        # Sincroniza el indicador de umbral con el valor real del slider
        # desde el arranque, para que nunca quede con el texto de relleno
        # de Qt Designer ("TextLabel").
        self.__on_threshold_changed()

    def _init_widget_lists(self) -> None:
        """Inicializa las listas de referencia a widgets de la interfaz."""

        self.__led_list_freqs = [
            self.__ui.led_user_cfg_esc,
            self.__ui.led_user_cfg_space,
            self.__ui.led_user_cfg_right,
            self.__ui.led_user_cfg_up,
            self.__ui.led_user_cfg_left,
            self.__ui.led_user_cfg_down,
        ]

        self.__enable_stimulus = [
            self.__ui.chk_cfg_show_esc,
            self.__ui.chk_cfg_show_space,
            self.__ui.chk_cfg_show_right,
            self.__ui.chk_cfg_show_up,
            self.__ui.chk_cfg_show_left,
            self.__ui.chk_cfg_show_down,
        ]

    def _connect_signals(self) -> None:
        """Conecta todos los eventos de la interfaz con sus respectivos métodos."""
        # Navegación principal
        self.__ui.btn_start_main.clicked.connect(self.__on_start_main)
        self.__ui.btn_settings_main.clicked.connect(self.__show_user_selection_page)
        self.__ui.btn_info.clicked.connect(self.__on_info)
        self.__ui.btn_exit_info.clicked.connect(self.__show_initial_page)

        # Gestión de usuarios
        self.__ui.btn_user_exit.clicked.connect(self.__show_initial_page)
        self.__ui.btn_user_continue.clicked.connect(self.__on_btn_user_continue)
        self.__ui.ql_user_list.itemClicked.connect(self.__on_user_selected)
        self.__ui.btn_user_save.clicked.connect(self.__on_btn_user_save)

        # Configuración de usuario
        self.__ui.btn_user_cfg_exit.clicked.connect(self.__show_user_selection_page)
        self.__ui.btn_user_cfg_continue.clicked.connect(self.__show_game_selection_page)
        self.__ui.btn_user_cfg_continue.setEnabled(False)
        self.__ui.btn_user_cfg_remove.clicked.connect(self.__on_btn_user_remove)
        self.__ui.btn_user_cfg_save.clicked.connect(self.__on_btn_user_save_preferences)
        self.__ui.chk_toggle_space.clicked.connect(self.__on_chk_toggle_space_changed)
        self.__ui.hsld_time_window.valueChanged.connect(self.__on_time_window_changed)

        for led in self.__led_list_freqs:
            led.editingFinished.connect(self.on_editing_finished)

        # Configuración de juego y señal
        self.__ui.chk_bandpass.clicked.connect(self.__on_chk_bandpass_changed)
        self.__ui.chk_notch.clicked.connect(self.__on_chk_notch_changed)
        self.__ui.chk_average.clicked.connect(self.__on_chk_average_changed)
        self.__ui.chk_psd.clicked.connect(self.__on_chk_psd)
        
        self.__ui.btn_start_train.clicked.connect(self.start_training_request.emit)
        self.__ui.btn_start_train.setEnabled(False)
        
        self.__ui.btn_start_test.clicked.connect(self.start_test_request.emit)
        self.__ui.btn_start_test.setEnabled(True)
        
        self.__ui.btn_start_game.clicked.connect(self.__on_start_stop_game)
        self.__ui.btn_start_game.setEnabled(False)
        self.__ui.btn_exit_game_setup.clicked.connect(self.__on_exit_game_setup)
        self.__ui.lw_games.itemClicked.connect(self.__on_game_selected)

        # Controles de visualización EEG/PSD
        self.__ui.cb_eeg_speed.currentIndexChanged.connect(self.__on_eeg_speed_changed)
        self.__ui.cb_eeg_scale.currentIndexChanged.connect(self.__on_eeg_scale_changed)
        self.__ui.cb_eeg_amplitude.currentIndexChanged.connect(self.__on_eeg_amplitude_changed)
        self.__ui.cb_psd_mode.currentIndexChanged.connect(self.__on_psd_mode_changed)
        self.__ui.cb_psd_channel.currentIndexChanged.connect(self.__on_psd_channel_changed)

        # Sliders y checkboxes adicionales
        for stim in self.__enable_stimulus:
            stim.clicked.connect(self.__on_enable_stimulus)

        self.__ui.hsld_windows_welch.valueChanged.connect(self.__on_windows_welch_changed)
        self.__ui.hsld_windows_welch.setSingleStep(10)
        
        self.__ui.hsld_overlap.valueChanged.connect(self.__on_overlap_changed)
        self.__ui.hsld_overlap.setSingleStep(5)
        
        self.__ui.hsld_threshold.valueChanged.connect(self.__on_threshold_changed)
        self.__ui.hsld_threshold.setSingleStep(5)
        
        self.__ui.chk_enable_control.clicked.connect(self.__on_enable_control_changed)
        self.__ui.chk_enable_control.setChecked(False)

        self.__ui.chk_enable_audio_feedback.clicked.connect(self.__on_audio_feedback_changed)
        self.__ui.chk_enable_audio_feedback.setChecked(False)

        self.__ui.chk_enable_classify.clicked.connect(self.__on_enable_classify_changed)
        self.__ui.chk_enable_classify.setChecked(False)

        self.__ui.hsld_press_duration.valueChanged.connect(self.__on_press_duration_changed)
        self.__ui.hsld_press_duration_2.valueChanged.connect(self.__on_press_duration_changed)

    # =========================================================================
    # Métodos de Ciclo de Vida y Navegación
    # =========================================================================

    def start_ui(self) -> None:
        """Muestra la ventana maximizada y establece la página inicial."""
        self.showMaximized()
        self.__show_initial_page()

    def closeEvent(self, event) -> None:
        """
        Maneja el evento de cierre de la ventana.

        Args:
            event: Evento de cierre de Qt.
        """
        value = self.confirm_action("¿Estás seguro de que quieres salir?", "Salir", "Cancelar")
        if value:
            self.close_request.emit()
            event.accept()
        else:
            event.ignore()

    def __show_initial_page(self) -> None:
        """Muestra la página del menú principal."""
        self.__ui.stackedWidget.setCurrentWidget(self.__ui.page_main_menu)

    def __show_info_page(self) -> None:
        """Muestra la página de información."""
        self.__ui.stackedWidget.setCurrentWidget(self.__ui.page_info)

    def __show_user_selection_page(self) -> None:
        """Muestra la página de selección de usuario y solicita la lista actualizada."""
        self.__ui.stackedWidget.setCurrentWidget(self.__ui.page_user_selection)
        self.user_list_request.emit()

    def __show_user_config_page(self) -> None:
        """Muestra la página de configuración del usuario seleccionado."""
        self.__ui.stackedWidget.setCurrentWidget(self.__ui.page_user_config)
        self.request_user_preferences.emit(self.__user)

    def __show_game_selection_page(self) -> None:
        """Muestra la página de configuración y selección de juego."""
        self.start_streaming_request.emit()
        self.__ui.stackedWidget.setCurrentWidget(self.__ui.page_game_setup)
        
        # Configuración inicial de filtros
        self.__ui.chk_bandpass.setChecked(True)
        self.__ui.chk_notch.setChecked(True)
        self.__ui.chk_average.setChecked(False)
        self.__on_chk_bandpass_changed()
        self.__on_chk_notch_changed()
        self.__on_chk_average_changed()
        
        self.__ui.chk_psd.setChecked(True)
        self.__ui.pte_messages.clear()
        
        self.game_list_request.emit()
        self.__add_combo_items()
        
        self.__ui.eeg_container.show()
        self.__ui.psd_container.show()
        
        # Configuración inicial de sliders
        self.__ui.hsld_threshold.setMinimum(0)
        self.__ui.hsld_threshold.setMaximum(80)
        self.__on_windows_welch_changed(self.__win_val)
        
        self.__ui.hsld_overlap.blockSignals(True)
        self.__ui.hsld_overlap.setMinimum(0)
        self.__ui.hsld_overlap.setMaximum(90)
        self.__ui.hsld_overlap.setValue(self.__over_val)
        self.__ui.hsld_overlap.blockSignals(False)
        self.__on_overlap_changed(self.__over_val)

        if self.__selected_threshold is None:
            self.__ui.hsld_threshold.setValue(10)
            self.__on_threshold_changed()
            
        self.__on_enable_control_changed()
        self.__on_enable_classify_changed()

    # =========================================================================
    # Métodos de Gestión de Usuarios
    # =========================================================================

    def load_users(self, p_users: dict) -> None:
        """
        Carga y actualiza la lista de usuarios en la interfaz.

        Args:
            p_users: Diccionario con los usuarios {id: nombre}.
        """
        self.__users = p_users
        self.__users_list_update()

    def __users_list_update(self) -> None:
        """Actualiza el widget de lista con los nombres de los usuarios."""
        self.__ui.ql_user_list.clear()
        if self.__users is not None:
            self.__ui.ql_user_list.addItems(list(self.__users.values()))

    def __on_user_selected(self, item) -> None:
        """
        Maneja la selección de un usuario de la lista.

        Args:
            item: Elemento de la lista seleccionado.
        """
        selected_user = item.text()
        for userid, username in self.__users.items():
            if username == selected_user:
                self.__user = userid
                break

    def __on_btn_user_continue(self) -> None:
        """Valida que haya un usuario seleccionado antes de continuar a la configuración."""
        if self.__user is None:
            QMessageBox.critical(self, "Error", "No se ha seleccionado ningún usuario. Por favor, seleccione uno.")
        else:
            self.__show_user_config_page()

    def __on_btn_user_save(self) -> None:
        """Solicita la creación de un nuevo usuario con el nombre ingresado."""
        username = self.__ui.le_input_username.text().strip()
        if not username:
            QMessageBox.critical(self, "Error", "El nombre de usuario no puede estar vacío.")
        else:
            self.new_user_request.emit(username)
            self.__ui.le_input_username.clear()

    def __on_btn_user_remove(self) -> None:
        """Solicita la eliminación del usuario actualmente seleccionado."""
        if self.confirm_action("¿Deseas eliminar el usuario?", "Eliminar", "Cancelar"):
            self.remove_user_request.emit(self.__user)
            self.__show_user_selection_page()
            self.__user = None

    def load_user_preferences(self, p_user_preferences: UserPreferences) -> None:
        """
        Carga las preferencias del usuario en los campos de la interfaz.

        Args:
            p_user_preferences: Objeto con las preferencias del usuario.
        """
        self.__user_preferences = p_user_preferences
        self.__ui.lbl_user_cfg_user_n.setText(str(self.__users[self.__user]))
        self.__ui.chk_toggle_space.setChecked(False)
        self.__on_chk_toggle_space_changed()

        # Cargar frecuencias de estímulos
        stimulus_data = self.__user_preferences.stimulus
        for index, stim in enumerate(stimulus_data):
            if isinstance(stim.freq, float):
                self.__led_list_freqs[index].setText(str(stim.freq))
            else:
                QMessageBox.critical(self, "Error", "La frecuencia del estímulo debe ser un número decimal")
                raise ValueError("stim_freqs deben ser float")

        # Cargar método de clasificación
        method = self.__user_preferences.classification_method
        try:
            self.__ui.qc_cass_method.setCurrentIndex(self.__classification_methods[method].value)
            val = self.__classification_methods[method].value != 0
            self.__ui.btn_start_train.setVisible(val)
        except Exception as e:
            QMessageBox.critical(self, "Error", "El método de clasificación no está implementado, revise los nombres utilizados.")
            raise e

        # Cargar tipo de estímulo
        stim_type = self.__user_preferences.stimulus[0].stim_type
        try:
            self.__ui.qc_estimulus_method.setCurrentIndex(self.__stim_type[stim_type].value)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Revisar los valores de los estímulos:\n\n{e}")
            raise e

        # Cargar estado de estímulos y ventana de tiempo
        for index in range(len(self.__enable_stimulus)):
            self.__enable_stimulus[index].setChecked(self.__user_preferences.stimulus_on[index])
        
        self.__ui.hsld_time_window.setValue(int(self.__user_preferences.time_window * 10))
        self.__ui.lbl_time_response.setText(f'{self.__user_preferences.time_window} s')
        self.__channels = self.__user_preferences.channels
        self.__ui.btn_user_cfg_continue.setEnabled(True)

    def __on_btn_user_save_preferences(self) -> None:
        """Valida y guarda las preferencias modificadas por el usuario."""
        # Validar frecuencias
        for index, led in enumerate(self.__led_list_freqs):
            text = led.text().strip()
            if not text:
                QMessageBox.critical(self, "Error", "No se permite guardar frecuencias vacías.")
                return
            try:
                freq = float(text)
                if freq == 0:
                    QMessageBox.critical(self, "Error", "No se permite guardar frecuencias con valor 0.")
                    return
                self.__user_preferences.stimulus[index].freq = freq
            except ValueError:
                QMessageBox.critical(self, "Error", f"La frecuencia en la posición {index+1} no es un número válido.")
                return

        # Guardar método de clasificación
        method_index = self.__ui.qc_cass_method.currentIndex()
        self.__user_preferences.classification_method = self.__classification_methods(method_index).name
        val = self.__classification_methods(method_index).name != self.__classification_methods(0).name
        self.__ui.btn_start_train.setVisible(val)

        # Guardar tipo de estímulo
        combo_index = self.__ui.qc_estimulus_method.currentIndex()
        try:
            enum_name = self.__stim_type(combo_index).name
            for stim in self.__user_preferences.stimulus:
                stim.stim_type = enum_name
        except ValueError:
            QMessageBox.critical(self, "Error", "El tipo de estímulo seleccionado no es válido.")
            return

        # Guardar estado de estímulos y ventana de tiempo
        for index in range(len(self.__enable_stimulus)):
            self.__user_preferences.stimulus_on[index] = self.__enable_stimulus[index].isChecked()
        
        self.__user_preferences.time_window = self.__ui.hsld_time_window.value() / 10.0

        self.save_user_preferences_request.emit(self.__user, self.__user_preferences)
        
    def __on_time_window_changed (self, value):
        """
        Actualiza el tiempo de respuesta en el Qlabel.
        
        Args:
            Value: Valor entero devuelto por hsld_time_window.
        """
        self.__ui.lbl_time_response.setText(f'{value/10} s')
        

    # =========================================================================
    # Métodos de Configuración de Juego y Señal
    # =========================================================================

    def game_list_update(self, games: list[str] | None = None) -> None:
        """
        Actualiza la lista de juegos disponibles en la interfaz.

        Args:
            games: Lista de nombres de juegos.
        """
        self.__ui.lw_games.clear()
        self.__ui.lw_games.addItem("Estimulador")
        if games is not None:
            self.__ui.lw_games.addItems(games)

    def enabled_button_filters(self, enabled: bool) -> None:
        """
        Habilita o deshabilita los checkboxes de filtros.

        Args:
            enabled: Estado deseado para los botones de filtro.
        """
        self.__ui.chk_bandpass.setEnabled(enabled)
        self.__ui.chk_notch.setEnabled(enabled)
        self.__ui.chk_average.setEnabled(enabled)

    def __on_game_selected(self, item) -> None:
        """
        Maneja la selección de un juego.

        Args:
            item: Elemento de la lista de juegos seleccionado.
        """
        self.__selected_game = item.text()
        self.__ui.btn_start_game.setEnabled(True)

    def __on_start_stop_game(self) -> None:
        """Alterna entre iniciar y detener el juego seleccionado."""
        if not self.__start_game:
            self.__start_game = True
            self.start_game_request.emit(self.__selected_game)
            self.__ui.btn_start_game.setText("Detener\njuego")
            self.__ui.lw_games.setEnabled(False)
        else:
            self.__start_game = False
            self.stop_game_request.emit()
            self.__ui.btn_start_game.setText("Iniciar\njuego")
            self.__ui.lw_games.clearSelection()
            self.__ui.btn_start_game.setEnabled(False)
            self.__ui.lw_games.setEnabled(True)

    def __on_exit_game_setup(self) -> None:
        """Sale de la configuración del juego y detiene el streaming."""
        self.stop_streaming_request.emit()
        self.__ui.eeg_container.hide()
        self.__ui.psd_container.hide()
        self.__show_initial_page()

    def __on_chk_psd(self, state: bool) -> None:
        """
        Muestra u oculta los contenedores de PSD según el estado del checkbox.

        Args:
            state: Estado del checkbox PSD.
        """
        if state:
            self.__ui.psd_container.show()
            self.__ui.welch_settings_widget.show()
        else:
            self.__ui.psd_container.hide()
            self.__ui.welch_settings_widget.hide()
        self.psd_graph_request.emit(state)

    def __on_chk_bandpass_changed(self) -> None:
        """Emite el estado del filtro bandpass."""
        self.bandpass_request.emit(self.__ui.chk_bandpass.isChecked())

    def __on_chk_notch_changed(self) -> None:
        """Emite el estado del filtro notch."""
        self.notch_request.emit(self.__ui.chk_notch.isChecked())

    def __on_chk_average_changed(self) -> None:
        """Emite el estado del promedio de señales."""
        self.average_request.emit(self.__ui.chk_average.isChecked())

    def __on_enable_control_changed(self) -> None:
        """Emite el estado de activación del control y despliega/oculta el submenú de duración de pulsación."""
        checked = self.__ui.chk_enable_control.isChecked()
        self.__ui.press_duration_widget.setVisible(checked)
        self.enable_control_request.emit(checked)

    def __on_audio_feedback_changed(self) -> None:
        """Emite el estado de activación de la retroalimentación auditiva."""
        checked = self.__ui.chk_enable_audio_feedback.isChecked()
        self.audio_feedback_request.emit(checked)

    def __on_press_duration_changed(self, value: int) -> None:
        """
        Sincroniza los dos controles de duración de pulsación (configuración
        de usuario y pantalla de juego) y emite el nuevo valor.

        Args:
            value: Nueva duración en milisegundos, desde cualquiera de los dos sliders.
        """
        for slider in (self.__ui.hsld_press_duration, self.__ui.hsld_press_duration_2):
            if slider.value() != value:
                slider.blockSignals(True)
                slider.setValue(value)
                slider.blockSignals(False)

        text = f"{value} ms"
        self.__ui.lbl_press_duration_value.setText(text)
        self.__ui.lbl_press_duration_value_2.setText(text)

        self.press_duration_request.emit(value)

    def __on_enable_classify_changed(self) -> None:
        """Emite el estado de activación de la clasificación."""
        self.enable_classify_request.emit(self.__ui.chk_enable_classify.isChecked())

    # =========================================================================
    # Métodos de Control de Visualización (Combos y Sliders)
    # =========================================================================

    def __on_eeg_speed_changed(self) -> None:
        """Emite el cambio de velocidad de visualización del EEG."""
        speed = self.__ui.cb_eeg_speed.currentData()
        self.__selected_eeg_speed = self.__ui.cb_eeg_speed.currentIndex()
        self.eeg_speed_request.emit(speed)

    def __on_eeg_scale_changed(self) -> None:
        """Emite el cambio de escala de visualización del EEG."""
        scale = self.__ui.cb_eeg_scale.currentData()
        self.__selected_eeg_scale = self.__ui.cb_eeg_scale.currentIndex()
        self.eeg_scale_request.emit(scale)

    def __on_eeg_amplitude_changed(self) -> None:
        """Emite el cambio de unidad de amplitud del EEG."""
        amp = self.__ui.cb_eeg_amplitude.currentData()
        self.__selected_eeg_amplitude = self.__ui.cb_eeg_amplitude.currentIndex()
        self.eeg_amplitude_request.emit(amp)

    def __on_psd_channel_changed(self) -> None:
        """Emite el cambio de canal para el gráfico PSD."""
        index = self.__ui.cb_psd_channel.currentIndex()
        self.__selected_channel = index
        self.psd_channel_request.emit(index)

    def __on_psd_mode_changed(self) -> None:
        """Emite el cambio de modo de visualización del PSD."""
        self.__selected_psd_mode = self.__ui.cb_psd_mode.currentIndex()
        self.psd_mode_request.emit(self.__selected_psd_mode)

    def __on_threshold_changed(self) -> None:
        """Actualiza la etiqueta y emite el nuevo valor del umbral."""
        threshold = self.__ui.hsld_threshold.value()
        self.__ui.threshold_indicator.setText(str(threshold))
        self.__selected_threshold = threshold
        self.threshold_request.emit(threshold / 100.0)

    def __on_windows_welch_changed(self, value: int) -> None:
        """
        Actualiza la etiqueta y emite el tamaño de la ventana de Welch.

        Args:
            value: Valor del slider de ventana de Welch.
        """
        self.__win_val = value
        self.__ui.lbl_windows_welch.setText(f"Tamaño de ventana: {value} s")
        self.windows_welch_request.emit(float(value))

    def __on_overlap_changed(self, value: int) -> None:
        """
        Actualiza la etiqueta y emite el porcentaje de solapamiento.

        Args:
            value: Valor del slider de solapamiento.
        """
        self.__over_val = value
        self.__ui.lbl_overlap_percentage.setText(f"Porcentaje de sobreposición: {value}%")
        self.overlap_request.emit(value / 100.0)

    def __add_combo_items(self) -> None:
        """Rellena los QComboBox con sus opciones por defecto o guardadas."""
        combos = [
            self.__ui.cb_eeg_speed,
            self.__ui.cb_eeg_scale,
            self.__ui.cb_eeg_amplitude,
            self.__ui.cb_psd_mode,
        ]
        for cb in combos:
            cb.blockSignals(True)

        # EEG Speed
        self.__ui.cb_eeg_speed.clear()
        self.__ui.cb_eeg_speed.addItem("x1.0", 1.0)
        self.__ui.cb_eeg_speed.addItem("x0.5", 0.5)
        self.__ui.cb_eeg_speed.addItem("x2.0", 2.0)
        self.__selected_eeg_speed = self.__selected_eeg_speed or 0
        self.__ui.cb_eeg_speed.setCurrentIndex(self.__selected_eeg_speed)
        self.__on_eeg_speed_changed()

        # EEG Scale
        self.__ui.cb_eeg_scale.clear()
        self.__ui.cb_eeg_scale.addItem("x100", 100)
        self.__ui.cb_eeg_scale.addItem("x1", 1)
        self.__ui.cb_eeg_scale.addItem("x10", 10)
        self.__ui.cb_eeg_scale.addItem("x1000", 1000)
        self.__selected_eeg_scale = self.__selected_eeg_scale or 0
        self.__ui.cb_eeg_scale.setCurrentIndex(self.__selected_eeg_scale)
        self.__on_eeg_scale_changed()

        # EEG Amplitude
        self.__ui.cb_eeg_amplitude.clear()
        self.__ui.cb_eeg_amplitude.addItem("mV", 0)
        self.__ui.cb_eeg_amplitude.addItem("uV", 1)
        self.__ui.cb_eeg_amplitude.addItem("nV", 2)
        self.__selected_eeg_amplitude = 1 if self.__selected_eeg_amplitude is None else self.__selected_eeg_amplitude
        self.__ui.cb_eeg_amplitude.setCurrentIndex(self.__selected_eeg_amplitude)
        self.__on_eeg_amplitude_changed()

        # PSD Mode
        self.__ui.cb_psd_mode.clear()
        self.__ui.cb_psd_mode.addItem("Valor absoluto")
        self.__ui.cb_psd_mode.addItem("Decibeles [dB]")
        self.__ui.cb_psd_mode.addItem("Normalizado")
        self.__selected_psd_mode = 2 if self.__selected_psd_mode is None else self.__selected_psd_mode
        self.__ui.cb_psd_mode.setCurrentIndex(self.__selected_psd_mode)
        self.__on_psd_mode_changed()

        # PSD Channel
        self.__ui.cb_psd_channel.clear()
        if self.__channels is not None:
            for index, channel in self.__channels.items():
                self.__ui.cb_psd_channel.addItem(channel, index)
        self.__selected_channel = self.__selected_channel or 0
        self.__ui.cb_psd_channel.setCurrentIndex(self.__selected_channel)

        for cb in combos:
            cb.blockSignals(False)

    # =========================================================================
    # Métodos de Utilidad y Helpers de UI
    # =========================================================================

    def __on_info(self) -> None:
        """Muestra la página de información y carga su contenido."""
        self.__show_info_page()
        self.__load_info()

    def __load_info(self) -> None:
        """Carga el contenido HTML del archivo de información."""
        if os.path.exists(self.__file_path):
            with open(self.__file_path, "r", encoding="utf-8") as file:
                html_content = file.read()
            self.__ui.html_viewer.setHtml(html_content)
        else:
            QMessageBox.warning(
                self, "Aviso", f"No se encontró el archivo info.html en:\n{self.__file_path}\nSe usará texto por defecto."
            )
            self.__ui.html_viewer.setHtml("<h2>Información del Sistema SSVEP</h2><p>Archivo no encontrado.</p>")

    def __on_start_main(self) -> None:
        """Redirige al juego si hay usuario, o a la selección de usuario si no."""
        if self.__user is not None:
            self.__show_game_selection_page()
        else:
            self.__show_user_selection_page()

    def __on_chk_toggle_space_changed(self) -> None:
        """Emite el cambio de estado del checkbox de espacio."""
        value = self.__ui.chk_toggle_space.isChecked()
        self.chk_toggle_space.emit(1, value)

    def __on_enable_stimulus(self) -> None:
        """Habilita o deshabilita los campos de frecuencia según el estado del estímulo."""
        for index in range(len(self.__enable_stimulus)):
            is_checked = self.__enable_stimulus[index].isChecked()
            self.__led_list_freqs[index].setEnabled(is_checked)
            if not is_checked and index == 1:  # Índice 1 corresponde al espacio
                self.__ui.chk_toggle_space.setEnabled(False)

    def on_editing_finished(self) -> None:
        """Valida y corrige el valor de frecuencia ingresado en los QLineEdit."""
        line = self.sender()
        if not line or not line.text().strip():
            return

        try:
            text = line.text().replace(',', '.')
            value = float(text)

            line.blockSignals(True)
            if value < 6.0:
                QMessageBox.warning(self, "Aviso", "La frecuencia mínima permitida es 6 Hz. Se ajustará automáticamente.")
                line.setText("6.0")
            elif value > 16.0:
                QMessageBox.warning(self, "Aviso", "La frecuencia máxima permitida es 16 Hz. Se ajustará automáticamente.")
                line.setText("16.0")
            line.blockSignals(False)
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor, ingrese un número válido.")
            line.clear()

    def load_head_widget(self, head_w) -> None:
        """
        Inserta el widget de cabeza en el layout correspondiente.

        Args:
            head_w: Widget a insertar.
        """
        self.__ui.head_channels_layout.setContentsMargins(0, 0, 0, 0)
        if self.__ui.head_channels_layout.indexOf(head_w) == -1:
            self.__ui.head_channels_layout.addWidget(head_w)

    def load_eeg_graph(self, eeg_widget) -> None:
        """
        Inserta el widget del gráfico EEG en el layout correspondiente.

        Args:
            eeg_widget: Widget del gráfico EEG.
        """
        self.__ui.eeg_container_layout.setContentsMargins(0, 0, 0, 0)
        self.__ui.eeg_container_layout.addWidget(eeg_widget)

    def load_psd_graph(self, psd_widget) -> None:
        """
        Inserta el widget del gráfico PSD en el layout correspondiente.

        Args:
            psd_widget: Widget del gráfico PSD.
        """
        self.__ui.psd_container_layout.addWidget(psd_widget)

    def write_message(self, message: str) -> None:
        """
        Escribe un mensaje en el área de texto de la consola.

        Args:
            message: Mensaje a mostrar.
        """
        self.__ui.pte_messages.appendPlainText(message)

    def write_box_message(self, message: str) -> None:
        """
        Muestra un mensaje de error en una caja de diálogo.

        Args:
            message: Mensaje de error a mostrar.
        """
        QMessageBox.critical(self, "Error", message)

    def enable_training(self) -> None:
        """Habilita el botón de inicio de entrenamiento."""
        self.__ui.btn_start_train.setEnabled(True)

    # =========================================================================
    # Métodos de Diálogos
    # =========================================================================

    def confirm_action(self, message: str, button_t: str, button_f: str, title: str = "Confirmar") -> bool:
        """
        Muestra un cuadro de diálogo de confirmación personalizado.

        Args:
            message: Texto principal del mensaje.
            button_t: Texto del botón de confirmación.
            button_f: Texto del botón de cancelación.
            title: Título de la ventana del diálogo.

        Returns:
            bool: True si se presionó el botón de confirmación, False en caso contrario.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Question)

        btn_true = msg_box.addButton(button_t, QMessageBox.ButtonRole.AcceptRole)
        btn_false = msg_box.addButton(button_f, QMessageBox.ButtonRole.RejectRole)

        msg_box.setDefaultButton(btn_false)
        msg_box.exec()

        return msg_box.clickedButton() == btn_true
