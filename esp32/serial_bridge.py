# ─────────────────────────────────────────────────────────────────
# esp32/serial_bridge.py  —  Puente serial Raspberry Pi ↔ ESP32
#
# Descripción:
#   Transmite eventos del sistema al nodo ESP32 mediante comunicación
#   serial UART, utilizando mensajes estructurados en formato JSON.
#
#   El ESP32 actúa como terminal ligero de monitorización: recibe
#   los eventos y los representa en su interfaz (consola o pantalla LCD).
#   No realiza operaciones de captura ni análisis intensivo.
#
#   Protocolo de comunicación:
#     - Interfaz física: UART sobre cable USB (Raspberry Pi ↔ ESP32)
#     - Velocidad: 115200 baudios
#     - Formato de mensaje: JSON seguido de salto de línea '\n'
#     - El ESP32 usa el '\n' como delimitador de fin de mensaje
#
#   Nota sobre la validación:
#     Este módulo fue validado en el simulador Wokwi al no disponer
#     del hardware ESP32 físico durante el desarrollo.
#     Ver: esp32_firmware/ para el firmware del nodo.
# ─────────────────────────────────────────────────────────────────

# json: para serializar los eventos Python a cadenas JSON
import json

# threading: para proteger el acceso al puerto serie desde múltiples hilos
import threading

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class ESP32Bridge:
    """
    Puente de comunicación serial entre la Raspberry Pi y el ESP32.

    Escucha eventos del EventBus y los transmite al nodo ESP32
    en formato JSON a través del puerto serie USB.
    """

    def __init__(self, event_bus, port='/dev/ttyUSB0', baud=115200):
        """
        Constructor del puente serial.

        Intenta abrir la conexión serie con el ESP32 al instanciarse.
        Si el ESP32 no está conectado, el sistema continúa funcionando
        sin la componente de visualización embebida.

        Parámetros:
            event_bus (EventBus): bus de eventos del sistema.
            port  (str): puerto serie donde está conectado el ESP32.
                         '/dev/ttyUSB0' es el nombre estándar en Linux
                         para el primer dispositivo USB-UART.
            baud  (int): velocidad de comunicación en baudios.
                         Debe coincidir con la configuración del firmware.
        """
        # Referencia al bus de eventos para suscribirse a eventos
        self.event_bus = event_bus

        # Objeto de conexión serie (None si el ESP32 no está disponible)
        self.serial = None

        # Lock para garantizar que los mensajes se envíen completos
        # sin intercalarse cuando varios hilos llaman a _send() a la vez
        self._lock = threading.Lock()

        # Intentamos abrir la conexión serie con el ESP32
        self._connect(port, baud)

        # Nos suscribimos a los eventos que queremos retransmitir al ESP32
        # Solo transmitimos eventos de alto nivel (no los de depuración)
        event_bus.subscribe('network_detected',   self.send_network)
        event_bus.subscribe('handshake_detected', self.send_handshake)
        event_bus.subscribe('rf_anomaly',         self.send_anomaly)
        event_bus.subscribe('channel_congestion', self.send_congestion)
        event_bus.subscribe('system_alert',       self.send_alert)

        log.info("ESP32Bridge inicializado.")

    def _connect(self, port, baud):
        """
        Intenta establecer la conexión serie con el ESP32.

        Parámetros:
            port (str): puerto serie (p.ej. '/dev/ttyUSB0').
            baud (int): velocidad en baudios.
        """
        try:
            # Importamos pyserial solo aquí para evitar error de importación
            # si el paquete no está instalado pero el ESP32 tampoco se usa
            import serial

            # Abrimos el puerto serie con timeout de 1 segundo.
            # timeout evita que las operaciones de lectura bloqueen indefinidamente
            self.serial = serial.Serial(port, baud, timeout=1)

            log.info(f"ESP32 conectado en {port} a {baud} baudios.")

        except ImportError:
            # pyserial no está instalado en el entorno Python
            log.warning("pyserial no instalado. Sin comunicación ESP32.")
            log.warning("Instala con: pip install pyserial")
            self.serial = None

        except Exception as e:
            # Puerto no disponible: ESP32 no conectado o puerto ocupado
            log.warning(f"ESP32 no disponible en {port}: {e}")
            log.warning("El sistema funcionará sin la interfaz embebida.")
            self.serial = None

    def _send(self, message_dict):
        """
        Serializa un diccionario a JSON y lo envía por el puerto serie.

        Método interno utilizado por todos los métodos send_*().

        El mensaje JSON se termina con '\n' que el firmware ESP32
        usa como delimitador para saber cuándo ha llegado un mensaje completo.

        Parámetros:
            message_dict (dict): datos a enviar.
                                 Estructura: {'event': '...', 'data': {...}}
        """
        # Si el puerto serie no está disponible, no hacemos nada
        if self.serial is None:
            return

        try:
            # Usamos el lock para que solo un hilo envíe a la vez.
            # Sin esto, dos eventos simultáneos podrían intercalar sus bytes
            # y generar JSON corrupto en el receptor.
            with self._lock:

                # Convertimos el diccionario a cadena JSON
                # ensure_ascii=False: permite caracteres UTF-8 (SSIDs con acentos)
                json_str = json.dumps(message_dict, ensure_ascii=False)

                # Añadimos el delimitador de fin de mensaje
                line = json_str + '\n'

                # Codificamos a bytes UTF-8 y enviamos por el puerto serie
                self.serial.write(line.encode('utf-8'))

                log.debug(f"Enviado al ESP32: {json_str[:80]}...")  # Log truncado

        except Exception as e:
            # Error de escritura (cable desconectado, ESP32 reiniciado, etc.)
            log.warning(f"Error enviando al ESP32: {e}")
            # Marcamos el puerto como no disponible para evitar más errores
            self.serial = None

    def send_network(self, network_data):
        """Transmite los datos de una red recién detectada al ESP32."""
        self._send({
            'event': 'network_detected',
            'data':  {
                'ssid':       network_data.get('ssid', ''),
                'bssid':      network_data.get('bssid', ''),
                'channel':    network_data.get('channel', ''),
                'rssi':       network_data.get('power', ''),
                'encryption': network_data.get('encryption', '')
            }
        })

    def send_handshake(self, data):
        """Transmite la notificación de handshake capturado al ESP32."""
        self._send({
            'event': 'handshake_detected',
            'data':  {
                'ssid':  data.get('ssid', ''),
                'bssid': data.get('bssid', ''),
                'pcap':  data.get('pcap', '')
            }
        })

    def send_anomaly(self, data):
        """Transmite una alerta de anomalía RF al ESP32."""
        self._send({'event': 'rf_anomaly', 'data': data})

    def send_congestion(self, data):
        """Transmite una alerta de congestión de canal al ESP32."""
        self._send({'event': 'channel_congestion', 'data': data})

    def send_alert(self, data):
        """Transmite una alerta genérica del sistema al ESP32."""
        self._send({'event': 'system_alert', 'data': data})

    def close(self):
        """Cierra la conexión serie. Llamar al finalizar la sesión."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            log.info("Conexión serie con ESP32 cerrada.")
