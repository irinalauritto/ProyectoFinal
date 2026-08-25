       
from typing import Any
from PySide6.QtCore import QObject, Signal, Slot


class EEGSignalProcessor(QObject):
    """Procesador de señales EEG que coordina el filtrado, estimación de PSD y clasificación.

    Esta clase actúa como un orquestador en tiempo real: recibe muestras de señal decodificadas,
    las filtra, opcionalmente calcula la Densidad Espectral de Potencia (PSD) y las envía 
    a un clasificador para obtener resultados de forma continua.
    """
    
    # Señales para comunicar resultados al hilo principal (GUI)
    filteredData = Signal(list)          # Emite la señal filtrada
    psdData = Signal(object, object)     # Emite (frecuencias, potencias)
    classificationResult = Signal(int)   # Emite el ID del estímulo clasificado
    errorOccurred = Signal(str)          # Emite mensajes de error

    def __init__(self, signal_processor: Any, psd_estimator: Any):
        """Inicializa el procesador de señales.

        Args:
            signal_processor: Objeto encargado del filtrado de la señal (debe tener `eeg_stream_filter`).
            psd_estimator: Objeto encargado de estimar la PSD (debe tener `add_sample`, `clear_buffer` y señal `psd_ready`).
        """
        super().__init__()
        
        self._filters = signal_processor
        self._classifier: Any = None
        self._psd = psd_estimator
        
        # Estados de control
        self._psd_enabled = True
        self._is_processing = False
        self._classify_enabled = False
        self._classifier_ready = False
        self._clear_buffer_pending = False

        # Conexión segura de señales
        if self._psd is not None:
            self._psd.psd_ready.connect(self._on_psd_ready)

    @Slot(object)
    def on_data_decoded(self, sample: Any) -> None:
        """Procesa una nueva muestra de señal EEG decodificada.

        Este método se llama típicamente desde un Slot conectado a la llegada de nuevos datos.
        Gestiona el flujo: filtrado -> PSD (opcional) -> clasificación (opcional) -> limpieza.

        Args:
            sample: La muestra de señal entrante (lista o array numpy).
        """
        if not self._is_processing:
            return

        try:
            # 1. Filtrar la muestra entrante
            filtered = self._filters.eeg_stream_filter(sample)
            self.filteredData.emit(filtered)

            # 2. Enviar al estimador de PSD si está habilitado y disponible
            if self._psd is not None and self._psd_enabled:
                self._psd.add_sample(filtered)

            # 3. Clasificación en tiempo real
            if self._classifier is not None and self._classify_enabled and self._classifier_ready:
                result = self._classifier.update_buffer(filtered)
                if result is not None:
                    self.classificationResult.emit(result)
            
            # 4. Limpieza de búferes pendiente (ej. al desactivar clasificación o reiniciar)
            if self._clear_buffer_pending:
                if self._psd is not None:
                    self._psd.clear_buffer()
                if self._classifier is not None:
                    self._classifier.clear_buffer()
                self._clear_buffer_pending = False

        except Exception as e:
            error_msg = f"Error al procesar la señal: {e}"
            print(error_msg)
            self.errorOccurred.emit(error_msg)

    def start(self) -> None:
        """Inicia el procesamiento de la señal entrante."""
        self._is_processing = True

    def stop(self) -> None:
        """Detiene el procesamiento y limpia el búfer del estimador PSD."""
        self._is_processing = False
        if self._psd is not None:
            self._psd.clear_buffer()

    def load_classifier(self, classifier: Any) -> None:
        """Carga y habilita el clasificador de señales.

        Args:
            classifier: Instancia del clasificador (ej. EEGSignalTRCAClassifier).
        """
        self._classifier = classifier
        self._classify_enabled = True

    def set_psd_enabled(self, value: bool) -> None:
        """Habilita o deshabilita el cálculo de la Densidad Espectral de Potencia (PSD).

        Args:
            value: True para habilitar, False para deshabilitar.
        """
        self._psd_enabled = value

    def set_enable_classify(self, value: bool) -> None:
        """Habilita o deshabilita la clasificación.

        Si se deshabilita, se marca una bandera para limpiar los búferes en el siguiente ciclo.
        
        Args:
            value: True para habilitar, False para deshabilitar.
        """
        self._classify_enabled = value
        if not value:
            self._clear_buffer_pending = True

    def set_classifier_ready(self, value: bool) -> None:
        """Indica si el clasificador ha terminado de entrenarse/cargarse y está listo para usar.

        Si se marca como no listo (False), se programa la limpieza de los búferes para evitar 
        clasificaciones con datos residuales o modelos incompletos.
        
        Args:
            value: True si está listo, False si no lo está.
        """
        self._classifier_ready = value
        if not value:
            self._clear_buffer_pending = True

    @Slot(object, object)
    def _on_psd_ready(self, freqs: Any, power: Any) -> None:
        """Slot interno que re-emite los datos de PSD calculados hacia la GUI.

        Args:
            freqs: Array o lista de frecuencias.
            power: Array o lista de valores de potencia.
        """
        self.psdData.emit(freqs, power)
