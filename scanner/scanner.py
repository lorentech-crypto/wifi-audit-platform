# ─────────────────────────────────────────────────────────────────
# scanner/scanner.py  —  Módulo de escaneo y catalogación de redes Wi-Fi
#
# Descripción:
#   Este módulo es el motor de descubrimiento de redes del sistema.
#   Utiliza airodump-ng como backend de captura y procesa su salida
#   CSV en tiempo real para extraer información de cada red detectada.
#
#   Flujo de funcionamiento:
#     1. Activa el modo monitor en la interfaz Wi-Fi externa (wlan1)
#     2. Lanza airodump-ng en segundo plano
#     3. Lee el CSV generado cada N segundos
#     4. Por cada red nueva o actualizada, emite el evento 'network_detected'
#
#   Información extraída por red:
#     - BSSID (dirección MAC del punto de acceso)
#     - SSID  (nombre de la red)
#     - Canal Wi-Fi
#     - Potencia de señal (RSSI en dBm)
#     - Tipo de cifrado (OPN, WEP, WPA, WPA2, WPA3)
#     - Número aproximado de clientes conectados
# ─────────────────────────────────────────────────────────────────

# subprocess: permite lanzar procesos externos (airmon-ng, airodump-ng)
# desde Python y controlar su ejecución
import subprocess

# csv: módulo estándar para leer ficheros CSV (salida de airodump-ng)
import csv

# time: para las pausas entre ciclos de lectura del CSV
import time

# os: para comprobar si el fichero CSV existe antes de intentar leerlo
import os

# threading: para ejecutar el bucle de escaneo en un hilo separado,
# sin bloquear el hilo principal del sistema
import threading

# Importamos el logger del sistema para mensajes estructurados
from utils.logger import get_logger

# Logger específico para el módulo Scanner
log = get_logger(__name__)


class WiFiScanner:
    """
    Módulo de descubrimiento y catalogación de redes inalámbricas.

    Orquesta la activación del modo monitor y el escaneo continuo
    mediante airodump-ng. Emite eventos 'network_detected' a través
    del EventBus para cada red descubierta.
    """

    def __init__(self, event_bus):
        """
        Constructor del scanner.

        Parámetros:
            event_bus (EventBus): bus de eventos compartido del sistema.
                                  Se usa para emitir 'network_detected'.
        """
        # Guardamos la referencia al bus de eventos para poder emitir
        self.event_bus = event_bus

        # Nombre de la interfaz Wi-Fi en modo monitor.
        # airmon-ng convierte 'wlan1' en 'wlan1mon' al activar el modo monitor.
        self.interface = 'wlan1mon'

        # Interfaz física antes de activar el modo monitor
        self.physical_interface = 'wlan1'

        # Prefijo de los ficheros de salida de airodump-ng.
        # airodump-ng añade automáticamente el sufijo '-01.csv', '-01.cap', etc.
        self.output_prefix = 'sessions/scan'

        # Intervalo en segundos entre lecturas del fichero CSV
        # Un valor de 5 s es un buen equilibrio entre reactividad y carga
        self.scan_interval = 5

        # Diccionario para llevar registro de redes ya vistas.
        # Clave: BSSID, Valor: datos completos de la red.
        # Evita emitir el mismo evento repetidamente para la misma red.
        self.known_networks = {}

        # Flag para controlar el bucle de escaneo (permite pararlo limpiamente)
        self.running = False

        log.info("WiFiScanner inicializado.")

    def start(self):
        """
        Activa el modo monitor y lanza el escaneo en un hilo separado.

        Separamos el escaneo en un hilo (Thread) para que no bloquee
        el hilo principal del sistema mientras lee el CSV.
        """
        # Paso 1: activar el modo monitor en la interfaz Wi-Fi externa
        self.enable_monitor_mode()

        # Activamos el flag de control del bucle
        self.running = True

        # Paso 2: crear y arrancar un hilo demonio para el bucle de escaneo.
        # daemon=True: el hilo se cierra automáticamente cuando el proceso
        # principal termina, sin necesitar ser detenido explícitamente.
        scan_thread = threading.Thread(
            target=self._scan_loop,   # Función que ejecuta el hilo
            daemon=True,              # Hilo demonio: muere con el proceso
            name='ScannerThread'      # Nombre para identificarlo en logs
        )

        # Arrancamos el hilo: a partir de aquí, _scan_loop() corre en paralelo
        scan_thread.start()
        log.info("Hilo de escaneo iniciado.")

    def enable_monitor_mode(self):
        """
        Activa el modo monitor en la interfaz Wi-Fi externa.

        El modo monitor permite a la tarjeta capturar todos los paquetes
        del espectro inalámbrico, independientemente de su destinatario.
        Sin este modo, una tarjeta Wi-Fi solo recibe los paquetes
        dirigidos explícitamente a ella.

        Utiliza 'airmon-ng' de la suite Aircrack-ng.
        """
        log.info(f"Activando modo monitor en {self.physical_interface}...")

        try:
            # subprocess.run ejecuta el comando y ESPERA a que termine
            # antes de continuar. Esto es correcto aquí porque necesitamos
            # que el modo monitor esté activo antes de lanzar airodump-ng.
            #
            # ["airmon-ng", "start", "wlan1"] equivale a ejecutar en terminal:
            #   $ airmon-ng start wlan1
            #
            # check=True: si airmon-ng devuelve código de error != 0,
            # Python lanza una excepción CalledProcessError automáticamente
            resultado = subprocess.run(
                ["airmon-ng", "start", self.physical_interface],
                capture_output=True,   # Captura stdout y stderr
                text=True,             # Decodifica la salida como texto
                check=True             # Lanza excepción si hay error
            )

            log.info(f"Modo monitor activado: {self.interface}")
            log.debug(f"Salida de airmon-ng:\n{resultado.stdout}")

        except subprocess.CalledProcessError as e:
            # airmon-ng falló (p.ej. interfaz no encontrada, sin permisos)
            log.error(f"Error al activar modo monitor: {e}")
            log.error("Verifica que wlan1 existe y tienes permisos de root.")
            raise  # Relanzamos la excepción para que main.py la gestione

        except FileNotFoundError:
            # airmon-ng no está instalado en el sistema
            log.error("airmon-ng no encontrado. Instala aircrack-ng primero.")
            raise

    def _scan_loop(self):
        """
        Bucle principal de escaneo (se ejecuta en un hilo separado).

        Lanza airodump-ng y lee periódicamente su fichero CSV de salida.
        Se ejecuta indefinidamente hasta que self.running sea False.
        """
        # Construimos el comando de airodump-ng para escaneo global:
        #
        # airodump-ng: herramienta de captura de tráfico de Aircrack-ng
        # -w sessions/scan: prefijo de los ficheros de salida
        # --output-format csv: genera solo CSV (sin PCAP para el escaneo global)
        # wlan1mon: interfaz en modo monitor
        #
        # airodump-ng sin filtros de canal o BSSID realiza un "channel hopping":
        # salta entre canales capturando redes de todos ellos.
        command = [
            "airodump-ng",
            "-w", self.output_prefix,         # Prefijo de salida
            "--output-format", "csv",          # Solo formato CSV
            "--write-interval", "1",           # Actualiza el CSV cada 1 segundo
            self.interface                     # Interfaz en modo monitor
        ]

        log.info("Lanzando airodump-ng en modo global...")
        log.debug(f"Comando: {' '.join(command)}")

        # subprocess.Popen lanza el proceso en SEGUNDO PLANO.
        # A diferencia de subprocess.run, Popen no espera a que termine.
        # El proceso airodump-ng corre de forma independiente mientras
        # nuestro hilo continúa leyendo el CSV periódicamente.
        self.airodump_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,   # Ignoramos la salida estándar
            stderr=subprocess.DEVNULL    # Ignoramos los mensajes de error
        )

        # Fichero CSV generado por airodump-ng.
        # airodump-ng añade el sufijo '-01.csv' automáticamente.
        csv_file = self.output_prefix + "-01.csv"

        log.info(f"Esperando datos de escaneo en: {csv_file}")

        # Bucle de lectura periódica: corre mientras self.running sea True
        while self.running:

            # Solo intentamos leer si el fichero ya existe en disco.
            # airodump-ng puede tardar unos segundos en crearlo.
            if os.path.exists(csv_file):
                # Llamamos al parser para extraer las redes del CSV
                self._parse_csv(csv_file)
            else:
                log.debug(f"Esperando a que se cree {csv_file}...")

            # Esperamos el intervalo configurado antes del próximo ciclo.
            # Durante estos 5 segundos, el hilo cede el procesador.
            time.sleep(self.scan_interval)

        # Si salimos del bucle, detenemos airodump-ng
        self._stop_airodump()

    def _parse_csv(self, csv_file):
        """
        Lee el CSV de airodump-ng y extrae los datos de cada red.

        El CSV de airodump-ng tiene un formato específico con dos
        secciones separadas por una línea en blanco:
          1. Puntos de acceso (AP): una fila por red con 15+ columnas
          2. Clientes asociados: una fila por cliente

        Solo procesamos la primera sección (APs).

        Parámetros:
            csv_file (str): ruta al fichero CSV a procesar.
        """
        try:
            # Abrimos el CSV con manejo de errores de codificación.
            # airodump-ng puede generar caracteres no UTF-8 en algunos SSIDs.
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:

                # csv.reader parsea automáticamente las comas y las comillas
                reader = csv.reader(f)

                # Procesamos fila a fila
                for row in reader:

                    # ── Filtro 1: filas con suficientes columnas ────
                    # Las filas de AP tienen al menos 15 columnas.
                    # Las filas de cabecera, vacías o de cliente son más cortas.
                    if len(row) < 15:
                        continue

                    # ── Filtro 2: validar que es un BSSID (MAC) ─────
                    # La columna 0 contiene la MAC del AP (p.ej. AA:BB:CC:DD:EE:FF)
                    # Si no contiene ':', no es un BSSID válido.
                    bssid = row[0].strip()
                    if ':' not in bssid:
                        continue

                    # ── Extraer campos del CSV ──────────────────────
                    # La estructura del CSV de airodump-ng es:
                    # Col 0:  BSSID
                    # Col 1:  First time seen
                    # Col 2:  Last time seen
                    # Col 3:  Channel
                    # Col 4:  Speed
                    # Col 5:  Privacy (tipo de cifrado)
                    # Col 6:  Cipher
                    # Col 7:  Authentication
                    # Col 8:  Power (RSSI en dBm)
                    # Col 9:  # beacons
                    # Col 10: # IV
                    # Col 11: LAN IP
                    # Col 12: ID-length
                    # Col 13: ESSID (SSID)
                    # Col 14: Key

                    # Construimos el diccionario de datos de la red
                    network = {
                        'bssid':      bssid,
                        'channel':    row[3].strip(),    # Canal Wi-Fi
                        'power':      row[8].strip(),    # RSSI en dBm (negativo)
                        'encryption': row[5].strip(),    # WPA2, WPA, WEP, OPN...
                        'cipher':     row[6].strip(),    # CCMP, TKIP, WEP...
                        'ssid':       row[13].strip(),   # Nombre de la red
                        'beacons':    row[9].strip(),    # Número de beacons
                    }

                    # ── Emitir evento solo si la red es nueva ───────
                    # Comparamos con el diccionario de redes conocidas
                    if bssid not in self.known_networks:
                        # Primera vez que vemos esta red: la registramos
                        self.known_networks[bssid] = network

                        # Emitimos el evento 'network_detected' con los datos.
                        # Todos los módulos suscritos (RFAnalyzer, Reporter,
                        # ESP32Bridge) reaccionarán automáticamente.
                        self.event_bus.emit('network_detected', network)

                        log.info(
                            f"Red detectada: SSID='{network['ssid']}' "
                            f"BSSID={bssid} "
                            f"CH={network['channel']} "
                            f"RSSI={network['power']} dBm "
                            f"ENC={network['encryption']}"
                        )

                    else:
                        # Red ya conocida: actualizamos solo el RSSI
                        # (puede variar entre ciclos de escaneo)
                        self.known_networks[bssid]['power'] = network['power']

        except PermissionError:
            # El fichero está siendo escrito por airodump-ng al mismo tiempo
            # Es normal y temporal: simplemente esperamos al siguiente ciclo
            log.debug(f"CSV bloqueado por airodump-ng, reintentando en {self.scan_interval}s")

        except Exception as e:
            # Cualquier otro error: lo registramos pero no interrumpimos
            log.error(f"Error parseando CSV: {e}")

    def _stop_airodump(self):
        """Detiene el proceso de airodump-ng de forma limpia."""
        if hasattr(self, 'airodump_process') and self.airodump_process:
            self.airodump_process.terminate()   # Enviamos SIGTERM
            log.info("airodump-ng detenido.")

    def stop(self):
        """Detiene el escaneo. Llamar al cerrar la sesión."""
        self.running = False
        self._stop_airodump()
        log.info("Scanner detenido.")

    def get_network_count(self):
        """
        Retorna el número de redes únicas detectadas en esta sesión.

        Retorna:
            int: número de BSSIDs únicos detectados.
        """
        return len(self.known_networks)

    def get_networks(self):
        """
        Retorna una copia de todas las redes detectadas.

        Retorna:
            dict: copia del diccionario {bssid: datos_red}.
        """
        # Retornamos una copia para evitar modificaciones externas
        return dict(self.known_networks)
