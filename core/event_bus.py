# ─────────────────────────────────────────────────────────────────
# core/event_bus.py  —  Bus de eventos interno (patrón publish/subscribe)
#
# Descripción:
#   Implementa el mecanismo de comunicación desacoplada entre todos
#   los módulos del sistema. Ningún módulo necesita conocer a los
#   demás: solo publica o escucha eventos a través de este bus.
#
#   Patrón de diseño: Observer / Publish-Subscribe
#
# Eventos principales del sistema:
#   'network_detected'    → nueva red Wi-Fi detectada por el Scanner
#   'handshake_detected'  → handshake WPA/WPA2 capturado correctamente
#   'rf_anomaly'          → anomalía estadística en el espectro RF
#   'channel_congestion'  → canal Wi-Fi con alta ocupación detectado
#   'capture_started'     → inicio de captura focalizada sobre un AP
#   'capture_finished'    → captura finalizada y fichero PCAP guardado
#   'system_alert'        → alerta genérica del sistema
# ─────────────────────────────────────────────────────────────────

# threading: necesario para proteger el diccionario de listeners
# ante accesos concurrentes desde múltiples hilos
import threading

# Importamos el logger del sistema para registrar eventos relevantes
from utils.logger import get_logger

# Logger específico para este módulo
log = get_logger(__name__)


class EventBus:
    """
    Bus de eventos central del sistema.

    Permite que los módulos se comuniquen sin conocerse directamente.
    Un módulo publica un evento → el bus lo distribuye a todos
    los módulos que se hayan suscrito a ese tipo de evento.

    Ejemplo de uso:
        # En el módulo A (emisor):
        event_bus.emit('network_detected', {'ssid': 'LAB', 'rssi': -42})

        # En el módulo B (receptor):
        event_bus.subscribe('network_detected', self.on_network_found)

        def on_network_found(self, data):
            print(f"Red encontrada: {data['ssid']}")
    """

    def __init__(self):
        """
        Inicializa el bus de eventos con un diccionario vacío de listeners.

        El diccionario tiene la estructura:
            {
                'nombre_evento': [callback1, callback2, ...],
                'otro_evento':   [callback3]
            }
        """
        # Diccionario principal: clave = tipo de evento, valor = lista de callbacks
        # Cada vez que se emita un evento, se llamará a todos sus callbacks
        self.listeners = {}

        # Lock de threading para evitar condiciones de carrera (race conditions)
        # cuando múltiples hilos suscriben o emiten eventos simultáneamente
        self._lock = threading.Lock()

        log.debug("EventBus inicializado correctamente.")

    def subscribe(self, event_type, callback):
        """
        Suscribe una función (callback) a un tipo de evento concreto.

        Cuando se emita ese evento, la función será llamada automáticamente
        con los datos del evento como argumento.

        Parámetros:
            event_type (str): nombre del evento al que suscribirse.
                              Por convención, usamos snake_case:
                              'network_detected', 'rf_anomaly', etc.
            callback (callable): función o método a ejecutar cuando
                                 se emita el evento. Debe aceptar un
                                 parámetro: los datos del evento.

        Ejemplo:
            event_bus.subscribe('network_detected', self.process_network)
        """
        # Usamos el lock para que la suscripción sea thread-safe
        with self._lock:

            # Si es la primera suscripción a este tipo de evento,
            # creamos la lista vacía para ese tipo
            if event_type not in self.listeners:
                self.listeners[event_type] = []
                log.debug(f"Nuevo tipo de evento registrado: '{event_type}'")

            # Añadimos el callback a la lista de listeners de este evento
            self.listeners[event_type].append(callback)

            log.debug(
                f"Callback suscrito a '{event_type}': "
                f"{callback.__qualname__}"
            )

    def emit(self, event_type, data=None):
        """
        Emite un evento: notifica a todos los callbacks suscritos.

        Llama a cada callback registrado para este tipo de evento,
        pasándole los datos asociados como argumento.

        Parámetros:
            event_type (str): nombre del evento a emitir.
            data (any): datos asociados al evento. Puede ser un
                        diccionario, una cadena, un número, etc.
                        Por convención usamos diccionarios Python.

        Ejemplo:
            event_bus.emit('network_detected', {
                'ssid': 'LAB-WPA2',
                'bssid': 'AA:BB:CC:DD:EE:FF',
                'channel': '6',
                'power': '-42',
                'encryption': 'WPA2'
            })
        """
        # Obtenemos la lista de listeners de forma thread-safe
        # Usamos .get() para evitar KeyError si no hay listeners
        with self._lock:
            # Hacemos una copia de la lista para evitar modificaciones
            # durante la iteración (si alguien suscribe en el callback)
            callbacks = list(self.listeners.get(event_type, []))

        # Si no hay nadie suscrito a este evento, simplemente ignoramos
        if not callbacks:
            return

        log.debug(f"Emitiendo evento '{event_type}' a {len(callbacks)} listener(s)")

        # Llamamos a cada callback suscrito con los datos del evento
        for callback in callbacks:
            try:
                # Ejecutamos el callback con los datos del evento
                callback(data)

            except Exception as e:
                # Si un callback falla, registramos el error pero
                # continuamos con el resto de callbacks. Así, un
                # fallo en un módulo no interrumpe a los demás.
                log.error(
                    f"Error en callback '{callback.__qualname__}' "
                    f"para evento '{event_type}': {e}"
                )

    def get_event_types(self):
        """
        Retorna la lista de tipos de eventos registrados.

        Útil para depuración: permite ver qué eventos están activos.

        Retorna:
            list[str]: lista de nombres de eventos con listeners.
        """
        with self._lock:
            # Retornamos las claves del diccionario (nombres de eventos)
            return list(self.listeners.keys())

    def get_listener_count(self, event_type):
        """
        Retorna el número de listeners suscritos a un evento concreto.

        Parámetros:
            event_type (str): nombre del evento a consultar.

        Retorna:
            int: número de callbacks suscritos (0 si no existe el evento).
        """
        with self._lock:
            return len(self.listeners.get(event_type, []))
