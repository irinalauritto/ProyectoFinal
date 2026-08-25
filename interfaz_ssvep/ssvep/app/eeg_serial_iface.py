import sys
import time
import traceback
from array import array
from os import fstat
from threading import Event, Thread
from timeit import default_timer as timer
import builtins

import serial
from PySide6.QtCore import QObject, QTimerEvent, Signal, Slot
from serial.tools import list_ports

from ssvep.app import mat_recording

AMPLIFIER_GAINS = {1:b'0', 2:b'1', 4:b'2', 6:b'3', 8:b'4', 12:b'5', 24:b'6'}
SAMPLING_RATES  = {250:b'G', 500:b'F', 1000:b'S', 2000:b'A'}

START_STREAMING = b'b'
STOP_STREAMING  = b's'

CHANNEL_OFF = b'1'
CHANNEL_ON  = b'0'

START_BYTE  = 0xA0
STOP_BYTE   = 0xC0

PORT_READ_INTERVAL = .05 # Intervalo de lectura de puerto serie (seg)
PORT_READ_TIMEOUT  = 4.0 # Timeout de recepcion de datos (seg)

class EEGSerialInterface(QObject):
    """
    Conexion serial e interfaz con dispositivo EEG. 
    """
    streamStarted = Signal(bool) # notifica cuando se inicia / termina streaming
    dataDecoded   = Signal(list) # envia nuevas muestras adquiridas (list de arrays)
    portException = Signal(str)  # envia mensaje de error del puerto serie
    portFound     = Signal(str)  # recibe el puerto utilizado por interfaz EEG
    signalDesinc = Signal(str)

    def __init__(self, parent = None, save_stream = False):
        super().__init__(parent)
        # Inicializar atributos
        self.__streaming_thread = None
        self.__streaming = False
        # Flag guardar stream en archivo
        self.__save_stream = save_stream
        # Conectar signal emitida al encontrar puerto auto.
        self.portFound.connect(self.__open)
        self.__setup_serial_port()

    def is_open(self):
        """ Puerto abierto. """
        return self.__serial_port.is_open

    def is_streaming(self):
        """ Puerto transmitiendo. """
        return self.__streaming

    def __setup_serial_port(self):
        """ Inicializa configuracion puerto serie. """
        # Instancia de libreria Serial
        s_port = serial.Serial()
        s_port.timeout = 0 # non-blocking
        s_port.write_timeout = 0 # non-blocking
        self.__serial_port = s_port

    def __start_thread(self):
        """ Inicia timer de transmision. """
        self.__stop_thread()
        self.__streaming_thread = IfaceStreamReader(self.__serial_port, self.__enabled_channels_set, 
            self.dataDecoded.emit, self.portException.emit, self.__save_stream, self.signalDesinc.emit)
        self.__streaming_thread.start()

    def __stop_thread(self):
        """ Finaliza timer de transmision. """
        if self.__streaming_thread:
            self.__streaming_thread.cancel()
            self.__streaming_thread.join(.5)
            self.__streaming_thread = None

    def begin_connection(self, enabled_channels_indexes):
        """ Abrir puerto e iniciar streaming. """
        self.__enabled_channels_set = set(enabled_channels_indexes)
        if builtins.SETTINGS.intf_port_auto:
            IfacePortFinder(builtins.SETTINGS.intf_port_name, builtins.SETTINGS.intf_baudrate, .1, self.portFound.emit).start()
        else:
            self.__open(builtins.SETTINGS.intf_port_name)

    def end_connection(self):
        """ Fnalizar streaming y cerrar puerto. """
        self.__close()

    def __open(self, port_name):
        """ Abre la conexion del puerto serie. """
        # Si port es nulo, no se pudo reconocer o no se configuro
        if not port_name:
            self.portException.emit(self.tr('Puerto serie de amplificador EEG no reconocido.'))
            return
        # Intenta conectar al puerto COM
        self.__serial_port.port = port_name
        self.__serial_port.baudrate = builtins.SETTINGS.intf_baudrate
        try:
            self.__serial_port.open()
            # Setear ultimo puerto conectado
            builtins.SETTINGS.intf_port_name = port_name
        except:
            self.portException.emit(
                self.tr('No se ha podido conectar al Puerto: [{0}].').format(port_name))
        else:
            # Iniciar thread streaming
            self.__start()

    def __close(self):
        """ Cierra la conexion del puerto serie. """
        try:
            if self.__streaming:
                self.__stop()
            self.__serial_port.close()
        except:
            pass

    def __start(self):
        """ Inicia transmision. """
        try:
            self.__force_stop_streaming()
            self.__setup_channels()
            self.__clear_buffers()
            self.__serial_port.write(START_STREAMING)
            self.__streaming = True
            self.__start_thread()
        except:
            pass
        finally:
            self.streamStarted.emit(self.__streaming)

    def __stop(self):
        """ Finaliza streaming. """
        try:
            self.__stop_thread()
            self.__streaming = False
            self.__force_stop_streaming()
            # Da tiempo al dispositivo a procesar el stop antes de cerrar
            # el puerto (si no, __close() lo cierra enseguida y el byte
            # de stop puede perderse sin llegar a transmitirse).
            time.sleep(0.05)
        except:
            pass
        finally:
            self.streamStarted.emit(self.__streaming)

    def __clear_buffers(self, input_b=True, output_b=True):
        """ Limpia los buffer del puerto serie. """
        if input_b:
            self.__serial_port.reset_input_buffer()
        if output_b:
            self.__serial_port.reset_output_buffer()

    def __force_stop_streaming(self):
        """
        Envia byte de stop streaming por si no se finalizo correctamente.
        Como alternativa se podria resetear el disp. y esperar handshake.
        """
        self.__serial_port.write(STOP_STREAMING)
        self.__serial_port.flush()

    def __setup_channels(self):

        """ Configura canales y frecuencia de muestreo por defecto. """
        s_port = self.__serial_port
        for i in range(builtins.CHANNELS_NUMBER):

            ch_enabled = (CHANNEL_ON if i in self.__enabled_channels_set else CHANNEL_OFF)
            s_port.write(b'x') # Begin Channel Setting
            s_port.write(bytes(str(i+1).encode()))
            s_port.write(ch_enabled) # 0 Enabled - 1 Disabled
            s_port.write(AMPLIFIER_GAINS[builtins.PGA_GAIN])
            s_port.write(ch_enabled) # 0 Normal electrode input - 1 Input shorted
            s_port.write(b'1') # bias set
            s_port.write(b'1') # srb2 set
            s_port.write(b'0') # srb1 set
            s_port.write(b'X') # End Channel Setting
            s_port.flush()
            time.sleep(0.05)

        s_port.write(SAMPLING_RATES[builtins.SAMPLE_RATE])

        # Flush no es necesario si write es non-blocking
        s_port.flush()
        # Delay por las dudas se demore en configurar canales
        time.sleep(0.05)
        

class IfaceStreamReader(Thread):
    """
    Lector y decodificador de stream de OpenBCI y BioAmp.
    """
    def __init__(self, serial_port, channels_set, new_data_function, port_exc_function, save_stream, signal_desinc_function):
        Thread.__init__(self, daemon = True)
        self.serial_port  = serial_port
        self.channels_set = channels_set
        self.new_data_function = new_data_function
        self.port_exc_function = port_exc_function
        self.signal_desinc_function = signal_desinc_function
        self.finished = Event()
        # Array que actua como buffer de bytes
        self.input_buffer    = array('B') # unsigned char
        self.last_sample_idx = 0xFF # indice muestra 0 - 255
        # Crear archivo de stream
        if save_stream:
            file_name = time.strftime('stream-%H-%M-%S.bin', time.localtime())
            self.output_file = open(file_name,'wb')
        else:
            self.output_file = None

    def run(self):
        """ Lee y decodifica datos de entrada del puerto serie. """
        # Tiempo de ultima lectura correcta

        self.last_read_time = timer()
        while not self.finished.wait(PORT_READ_INTERVAL):
            try:

                data = self.serial_port.read_all()
                if data:
                    # Actualizar tiempo de ultima lectura
                    self.last_read_time = timer()
                    # Agrega nuevos bytes al buffer y decodifica
                    self.input_buffer.extend(data)
                    self.decode_input_data()
                    # Escribe stream en archivo
                    if self.output_file:
                        self.output_file.write(data)
                else:
                    if timer() - self.last_read_time > PORT_READ_TIMEOUT:
                        raise serial.SerialException('Tiempo de espera agotado al recibir señal.')
            except serial.SerialException as e:
                # Conexion perdida
                traceback.print_exc()
                self.port_exc_function('Comunicación serie detenida.')
                self.cancel()
            except:
                pass
        # Cierra archivo de stream
        if self.output_file:
            self.output_file.close()

    def cancel(self):
        """ Detener lectura de puerto serie. """
        self.finished.set()

    def decode_input_data(self):
        """
        Decodifica informacion en buffer de entrada
        y emite signal 'dataDecoded' con nuevas muestras.
        """
        # Incoming Packet Structure:
        # Start Byte(1)|Sample ID(1)|Channel Data(24)|Aux Data(6)|End Byte(1)
        # 0xA0|0-255|8, 3-byte signed ints|3 2-byte signed ints|0xC0
        new_eeg_samples = [array('i') for _ in self.channels_set] # signed int
        i = 0
        while i <= len(self.input_buffer)-33:
            if self.input_buffer[i] == START_BYTE and self.input_buffer[i+32] == STOP_BYTE: # header y footer
                self.verify_sample_index(self.input_buffer[i+1])
                channel_index = 0
                enabled_channel_index = 0
                for j in range(i+2, i+26, 3):
                    if channel_index not in self.channels_set:
                        # Canal apagado
                        channel_index += 1
                        continue
                    sample = self.get_decoded_sample(self.input_buffer[j:j+3])
                    new_eeg_samples[enabled_channel_index].append(sample)
                    enabled_channel_index += 1
                    channel_index += 1
                i += 33
            else: # header y/o footer no encontrados
                i += 1
        self.input_buffer = self.input_buffer[i:]
        # Enviar Signal con nuevas muestras (si hay)
        if new_eeg_samples and new_eeg_samples[0]:
            self.new_data_function(new_eeg_samples)

    def verify_sample_index(self, new_sample_idx):
        """ Verificar indice de muestra. """
        if (new_sample_idx - self.last_sample_idx != 1) and (self.last_sample_idx - new_sample_idx != 0xFF):
            mes = f'Indice muestras desinc.: {self.last_sample_idx} -> {new_sample_idx}'
            print(mes, file=sys.stderr)
            self.signal_desinc_function(mes)
            
        self.last_sample_idx = new_sample_idx

    def get_decoded_sample(self, bytes_b):
        byte_high = bytes_b[0]
        # A positive full-scale input produces an output code of 7FFFFFh
        # and the negative fullscale input produces an output code of 800000h.
        if byte_high & 0x80 == 0x80:
            byte_high &= 0x7F # negativo
        else:
            byte_high |= 0x80 # positivo
        return (byte_high << 16) | (bytes_b[1] << 8) | bytes_b[2]

class IfacePortFinder(Thread):
    """
    Se conecta a cada puerto serie hasta reconocer dispositivo EEG.
    Al finalizar invoca function con nombre del puerto de interfaz.
    """
    def __init__(self, last_port, port_baudrate, read_interval, result_function):
        Thread.__init__(self, daemon = True)
        self.last_connected_port = last_port
        self.port_baudrate   = port_baudrate
        self.read_interval   = read_interval
        self.result_function = result_function
        self.finished = Event()
        # Tiempo maximo de espera en respuesta
        self.wait_time = 1. # segundos

    def run(self):
        found_port = self.find_port()
        self.result_function(found_port)
        self.cancel()

    def cancel(self):
        """ Finalizar antes que procese todos los puertos. """
        self.finished.set()

    def openbci_id(self, port) -> bool:
        line = ''
        # Wait for device to send data
        wait_time = self.wait_time
        while wait_time > .0 and not self.finished.wait(self.read_interval):
            if port.in_waiting == 0:
                wait_time -= self.read_interval
                continue
            line += port.read().decode('utf-8', errors='replace')
            # Look for end sequence $$$
            if '$$$' in line:
                return True
        return False

    def find_port(self) -> str:
        openbci_port = None
        ports = [port[0] for port in list_ports.comports()]
        ports.reverse()
        # Ubica al principio de la lista el ultimo puerto conectado
        try:
            ports.remove(self.last_connected_port)
            ports.insert(0, self.last_connected_port)
        except:
            pass
        # Busca conectar con disp. EEG en cada puerto disponible
        for port in ports:
            try:
                s = serial.Serial(port, self.port_baudrate, timeout=0, write_timeout=0)
                s.write(b'v')
                openbci_serial = self.openbci_id(s)
                s.close()
                if openbci_serial:
                    openbci_port = port
                    break
            except (OSError, serial.SerialException):
                pass
        return openbci_port

class EEGFileInterface(QObject):
    """
    Simulador de conexion serial con dispositivo EEG. 
    """
    streamStarted = Signal(bool) # notifica cuando se inicia / termina streaming
    dataDecoded   = Signal(list) # envia nuevas muestras adquiridas (list de arrays)
    portException = Signal(str)  # envia mensaje de error del puerto serie

    def __init__(self, parent = None, save_stream = False, arch_n = None):
        super().__init__(parent)
        self.__streaming_thread = None
        self.__streaming = False
        self.__is_open = False
        self.__channels = {}
        self.__default_source = arch_n if arch_n is not None else 'test_signal.bin'
        self.__active_source = self.__default_source

    def is_open(self):
        return self.__is_open

    def is_streaming(self):
        return self.__streaming

    def set_source_file(self, path):
        """
        Cambia el archivo de señal a reproducir en la próxima conexión.

        Args:
            path: Ruta a un archivo (`.bin` crudo o `.mat` grabado). `None`
                o vacío vuelve al archivo por defecto de esta instancia.
        """
        self.__active_source = path if path else self.__default_source

    def __load_signal_source(self) -> bool:
        """ Carga la señal desde `.mat` grabado o `.bin` crudo, según la extensión. """
        if str(self.__active_source).lower().endswith('.mat'):
            return self.__read_mat_file()
        return self.__read_signal_file()

    def __read_signal_file(self) -> bool:
        self.__signal_len = 0
        self.__signal_list = []
        self.__index, self.__before = 0, 0
        try:
            with open(self.__active_source,'rb') as in_file:
                file_byte_size = fstat(in_file.fileno()).st_size
                # Archivo con todos los canales de senal
                channel_bytes = file_byte_size // builtins.CHANNELS_NUMBER
                # Tamano de muestras es 4 bytes
                self.__signal_len = channel_bytes >> 2
                for i in range(builtins.CHANNELS_NUMBER):
                    channel_samples = array('i', in_file.read(channel_bytes))
                    self.__signal_list.append(channel_samples)
        except Exception as e:
            self.portException.emit(str(e))
        finally:
            return bool(self.__signal_list)

    def __read_mat_file(self) -> bool:
        """ Carga una grabación SSVEP (.mat) haciendo coincidir canales por nombre. """
        self.__signal_len = 0
        self.__signal_list = []
        self.__index, self.__before = 0, 0
        try:
            data = mat_recording.load_recording(self.__active_source)
            eeg = data['eeg']
            recorded_channels = [str(name).strip() for name in data['info']['channels']]
            samples = eeg[:, 1:].astype('int32')  # descarta columna de timestamp
            self.__signal_len = samples.shape[0]
            name_to_col = {name: idx for idx, name in enumerate(recorded_channels)}

            for ch_index in range(builtins.CHANNELS_NUMBER):
                ch_name = self.__channels.get(ch_index)
                if ch_name is not None and ch_name in name_to_col:
                    self.__signal_list.append(array('i', samples[:, name_to_col[ch_name]].tolist()))
                else:
                    self.__signal_list.append(array('i', [0] * self.__signal_len))
        except Exception as e:
            self.portException.emit(str(e))
        finally:
            return bool(self.__signal_list)

    @Slot(QTimerEvent)
    def timerEvent(self, _):
        def get_samples_in_range(start = 0, end = 0):
            return [array('i', self.__signal_list[ch][start:end]) for ch in self.__enabled_channels_set]
        
        now = timer()
        samples = int((now - self.__before) * builtins.SAMPLE_RATE)
        self.__before = now
        #
        new_samples = get_samples_in_range(self.__index, self.__index+samples)
        self.__index += samples
        self.dataDecoded.emit(new_samples)
        #
        if self.__index > self.__signal_len:
            self.__index -= self.__signal_len
            new_samples_ = get_samples_in_range(0, self.__index)
            self.dataDecoded.emit(new_samples_)

    def __start_thread(self):
        """ Inicia timer de transmision. """
        self.__stop_thread()
        self.__streaming_thread = self.startTimer(100)

    def __stop_thread(self):
        """ Finaliza timer de transmision. """
        if self.__streaming_thread:
            self.killTimer(self.__streaming_thread)
            self.__streaming_thread = None

    def begin_connection(self, channels):
        """ Abrir puerto e iniciar streaming. """
        self.__channels = dict(channels)
        self.__enabled_channels_set = set(self.__channels)
        if self.__load_signal_source():
            self.__open()

    def end_connection(self):
        """ Fnalizar streaming y cerrar puerto. """
        self.__close()

    def __open(self):
        """ Abre la 'conexion' del puerto serie. """
        try:
            self.__is_open = True
            self.__start()
        except:
            pass

    def __close(self):
        """ Cierra la 'conexion' del puerto serie. """
        try:
            if self.__streaming:
                self.__stop()
            self.__is_open = False
        except:
            pass
        
        
    def __start(self):
    #     """ Inicia transmision. """    
        if not self.is_open():
            return
        try:
            self.__before = timer()
            self.__start_thread()
            self.__streaming = True
        except Exception as e:
            self.portException.emit(f"Error al iniciar: {e}")
        finally:
            self.streamStarted.emit(self.__streaming)


    def __stop(self):
        """ Finaliza streaming. """
        if not self.is_open():
            return
        try:
            self.__stop_thread()
            self.__streaming = False
        except:
            pass
        finally:
            self.streamStarted.emit(self.__streaming)
