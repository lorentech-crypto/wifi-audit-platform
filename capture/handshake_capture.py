# ─────────────────────────────────────────────────────────────────
# capture/handshake_capture.py  —  Captura de tráfico y detección de handshakes
#
# Descripción:
#   Este módulo gestiona la captura focalizada de tráfico inalámbrico
#   sobre un punto de acceso concreto (BSSID) y detecta automáticamente
#   la presencia de handshakes WPA/WPA2 en el tráfico capturado.
#
#   ¿Qué es un handshake WPA/WPA2?
#   Es el intercambio de 4 mensajes (EAPOL) que ocurre cuando un cliente
#   se autentica en un punto de acceso WPA/WPA2. Capturarlo permite
#   realizar análisis de la robustez de la contraseña de la red
#   (mediante ataques de diccionario en entornos autorizados).
#
#   Flujo de trabajo:
#     1. Se recibe un BSSID y canal objetivo
#     2. Se lanza airodump-ng focalizado en ese AP
#     3. Se monitoriza el fichero PCAP en busca de tramas EAPOL
#     4. Al detectar un handshake completo, se emite 'handshake_detected'
#
#   ⚠️  AVISO LEGAL: usar EXCLUSIVAMENTE sobre redes propias o con
#       autorización expresa por escrito del administrador de la red.
# ─────────────────────────────────────────────────────────────────

# subprocess: para lanzar airodump-ng focalizado
import subprocess

# os: para gestión de ficheros PCAP y verificar existencia
import os

# threading: para ejecutar la monitorización del handshake en paralelo
import threading

# time: para pausas en el bucle de monitorización
import time

# Importamos el parser de paquetes para analizar el PCAP
from capture.packet_parser import detect_handshake_in_pcap

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class HandshakeCapture:
    """
    Módulo de captura de tráfico inalámbrico y detección de handshakes WPA/WPA2.

    Gestiona capturas focalizadas sobre BSSIDs concretos y notifica
    al sistema cuando se detecta un handshake válido.
    """

    def __init__(self, event_bus):
        """
        Constructor del módulo de captura.

        Parámetros:
            event_bus (EventBus): bus de eventos del sistema.
        """
        # Referencia al bus de eventos para emitir notificaciones
        self.event_bus = event_bus

        # Nombre de la interfaz Wi-Fi en modo monitor
        self.interface = 'wlan1mon'

        # Diccionario de capturas activas: {bssid: proceso_airodump}
        # Permite gestionar múltiples capturas simultáneas
        self.active_captures = {}

        # Directorio base donde se guardan los ficheros de captura
        self.capture_dir = 'sessions'

        log.info("HandshakeCapture inicializado.")

    def capture(self, bssid, channel, ssid='unknown'):
        """
        Lanza una captura focalizada sobre un punto de acceso concreto.

        Fija airodump-ng en el canal del AP objetivo para capturar
        solo el tráfico de ese AP y sus clientes asociados.

        Parámetros:
            bssid   (str): dirección MAC del punto de acceso objetivo.
                           Formato: 'AA:BB:CC:DD:EE:FF'
            channel (int|str): canal Wi-Fi del AP (p.ej. 6 o '6').
            ssid    (str): nombre de la red (solo para nombrar ficheros).

        Retorna:
            str: ruta del prefijo de ficheros de captura generados.
        """
        # Comprobamos si ya hay una captura activa para este BSSID
        # (bug detectado en pruebas: sin esta guarda se lanzaban procesos duplicados)
        if bssid in self.active_captures:
            log.warning(f"Ya hay una captura activa para {bssid}. Ignorando.")
            return None

        # Construimos el nombre del fichero de salida basado en el BSSID.
        # Eliminamos los ':' de la MAC para que sea un nombre válido.
        safe_bssid = bssid.replace(':', '')
        output_name = os.path.join(self.capture_dir, f"cap_{safe_bssid}")

        log.info(f"Iniciando captura sobre {ssid} ({bssid}) en canal {channel}")

        # ── Construir el comando de airodump-ng focalizado ────────
        #
        # Diferencia con el escaneo global:
        #   - '-c CANAL': fijamos el canal (no hace hopping)
        #   - '--bssid MAC': filtramos solo paquetes del AP objetivo
        # Esto maximiza la captura de tramas relevantes.
        command = [
            "airodump-ng",
            "-c", str(channel),       # Canal del AP: fija la captura aquí
            "--bssid", bssid,         # Filtra solo paquetes de este AP
            "-w", output_name,        # Prefijo de los ficheros de salida
            "--output-format", "pcap,csv",  # Genera PCAP (para análisis) y CSV
            self.interface            # Interfaz en modo monitor
        ]

        # Lanzamos airodump-ng en segundo plano (Popen no espera)
        proceso = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,   # Suprimimos la salida en terminal
            stderr=subprocess.DEVNULL    # Suprimimos los mensajes de error
        )

        # Registramos el proceso en el diccionario de capturas activas
        self.active_captures[bssid] = proceso

        # Notificamos al sistema que ha comenzado una nueva captura
        self.event_bus.emit('capture_started', {
            'bssid':   bssid,
            'ssid':    ssid,
            'channel': str(channel),
            'output':  output_name
        })

        # Lanzamos un hilo que monitoriza el PCAP en busca de handshakes
        # daemon=True: se cierra automáticamente con el proceso principal
        monitor_thread = threading.Thread(
            target=self._monitor_handshake,
            args=(bssid, ssid, output_name + '-01.cap'),
            daemon=True,
            name=f'HandshakeMonitor-{safe_bssid}'
        )
        monitor_thread.start()

        log.debug(f"Hilo de monitorización de handshake arrancado para {bssid}")
        return output_name

    def _monitor_handshake(self, bssid, ssid, pcap_file, interval=3, max_wait=120):
        """
        Monitoriza un fichero PCAP en busca de un handshake WPA/WPA2.

        Se ejecuta en un hilo separado. Analiza el PCAP cada 'interval'
        segundos durante un máximo de 'max_wait' segundos.

        Parámetros:
            bssid     (str): MAC del AP que estamos capturando.
            ssid      (str): nombre de la red.
            pcap_file (str): ruta al fichero PCAP generado por airodump-ng.
            interval  (int): segundos entre análisis del PCAP.
            max_wait  (int): tiempo máximo de espera antes de rendirse.
        """
        elapsed = 0   # Tiempo transcurrido desde el inicio

        log.debug(f"Monitorizando handshake en {pcap_file}")

        while elapsed < max_wait:

            # Esperamos el intervalo antes de analizar
            time.sleep(interval)
            elapsed += interval

            # Verificamos que el fichero PCAP ya existe en disco
            if not os.path.exists(pcap_file):
                log.debug(f"PCAP aún no creado, esperando... ({elapsed}s)")
                continue

            # Analizamos el PCAP en busca de tramas EAPOL (handshake)
            # detect_handshake_in_pcap() retorna True si hay handshake completo
            if detect_handshake_in_pcap(pcap_file, bssid):

                log.info(f"✓ Handshake WPA/WPA2 detectado para {ssid} ({bssid})")

                # Emitimos el evento 'handshake_detected' con los datos.
                # El Reporter lo guardará y el ESP32Bridge lo enviará al nodo.
                self.event_bus.emit('handshake_detected', {
                    'bssid':    bssid,
                    'ssid':     ssid,
                    'pcap':     pcap_file,
                    'elapsed':  elapsed
                })

                # Dejamos de monitorizar: ya tenemos el handshake
                break
        else:
            # El bucle terminó sin break: no detectamos handshake en max_wait
            log.warning(
                f"No se detectó handshake para {bssid} "
                f"en {max_wait}s. Puede ser necesario un ataque de deauth."
            )

    def stop_capture(self, bssid):
        """
        Detiene la captura activa sobre un BSSID concreto.

        Parámetros:
            bssid (str): MAC del AP cuya captura se quiere detener.
        """
        if bssid not in self.active_captures:
            log.warning(f"No hay captura activa para {bssid}")
            return

        # Enviamos SIGTERM al proceso airodump-ng para cerrarlo limpiamente
        self.active_captures[bssid].terminate()

        # Eliminamos la referencia del diccionario
        del self.active_captures[bssid]

        log.info(f"Captura detenida para {bssid}")

        # Notificamos al sistema que la captura ha finalizado
        self.event_bus.emit('capture_finished', {'bssid': bssid})

    def stop_all(self):
        """Detiene todas las capturas activas. Llamar al cerrar la sesión."""
        # Iteramos sobre una copia de las claves para poder modificar el dict
        for bssid in list(self.active_captures.keys()):
            self.stop_capture(bssid)

        log.info("Todas las capturas detenidas.")
