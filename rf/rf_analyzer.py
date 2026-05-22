# ─────────────────────────────────────────────────────────────────
# rf/rf_analyzer.py  —  Analizador estadístico del espectro RF
#
# Descripción:
#   Componente más relevante y diferenciador del proyecto.
#   Calcula periódicamente métricas estadísticas del espectro
#   inalámbrico a partir de los valores RSSI de las redes detectadas:
#
#     - RSSI medio global y por canal
#     - Varianza y desviación estándar del espectro
#     - Ocupación relativa de cada canal Wi-Fi
#     - Estabilidad temporal de las señales
#
#   Se suscribe al evento 'network_detected' del EventBus y procesa
#   cada nueva red automáticamente sin intervención manual.
#
#   Emite eventos propios cuando detecta condiciones anómalas:
#     'channel_congestion' → canal con alta ocupación detectado
#     'rf_anomaly'         → anomalía estadística en el espectro
# ─────────────────────────────────────────────────────────────────

# threading: para ejecutar el análisis periódico en un hilo separado
import threading

# time: para las pausas en el bucle de análisis periódico
import time

# Importamos las funciones matemáticas del módulo de estadística
from rf.statistics import (
    calculate_mean_rssi,
    calculate_variance,
    calculate_std_dev,
    calculate_channel_occupancy,
)

# Importamos el detector de anomalías
from rf.anomaly_detector import AnomalyDetector
from rf.channel_monitor import ChannelMonitor

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class RFAnalyzer:
    """
    Analizador estadístico del espectro de radiofrecuencia Wi-Fi.

    Procesa los datos de redes detectadas para calcular métricas
    de ocupación espectral y detectar condiciones anómalas.

    Importante: este módulo NO usa hardware SDR especializado.
    Trabaja exclusivamente con los valores RSSI reportados por
    el adaptador Wi-Fi convencional. Esto tiene limitaciones:
    no puede identificar el origen físico exacto de interferencias,
    pero sí puede detectar patrones estadísticos anómalos.
    """

    def __init__(self, event_bus, analysis_interval=10):
        """
        Constructor del analizador RF.

        Parámetros:
            event_bus         (EventBus): bus de eventos del sistema.
            analysis_interval (int): segundos entre análisis periódicos.
                                     Por defecto 10 segundos.
        """
        # Referencia al bus de eventos para emitir y suscribirse
        self.event_bus = event_bus

        # Lista acumulativa de todas las redes detectadas en la sesión.
        # Cada elemento es el diccionario de datos de una red.
        self.networks = []

        # Diccionario de datos por canal: {canal: [lista de RSSI]}
        # Permite calcular métricas independientes para cada canal.
        # Los canales Wi-Fi van del 1 al 14 (2.4GHz) y del 36+ (5GHz).
        self.channel_data = {}

        # Monitor de ocupación de canales Wi-Fi
        self.channel_monitor = ChannelMonitor()

        # Instancia del detector de anomalías.
        # Analiza cada nuevo RSSI para detectar desviaciones anómalas.
        self.anomaly_detector = AnomalyDetector(threshold_k=2.0)

        # Intervalo entre análisis periódicos del espectro
        self.analysis_interval = analysis_interval

        # Lock para proteger el acceso concurrente a self.networks
        # y self.channel_data desde múltiples hilos
        self._lock = threading.Lock()

        # Nos suscribimos al evento 'network_detected' del bus.
        # Cada vez que el Scanner detecte una red nueva, se llamará
        # automáticamente a self.process_network()
        event_bus.subscribe('network_detected', self.process_network)

        # Arrancamos el hilo de análisis periódico
        self._start_periodic_analysis()

        log.info("RFAnalyzer inicializado y suscrito a 'network_detected'.")

    def process_network(self, network):
        """
        Procesa una red recién detectada y actualiza las métricas espectrales.

        Este método es el callback del evento 'network_detected'.
        Se llama automáticamente por el EventBus cada vez que el
        módulo Scanner emite dicho evento.

        Parámetros:
            network (dict): datos de la red con claves:
                            'bssid', 'ssid', 'channel', 'power', 'encryption'
        """
        # Intentamos convertir el RSSI a entero para los cálculos.
        # airodump-ng reporta el RSSI como cadena de texto (p.ej. '-42').
        try:
            rssi = int(network.get('power', '0'))
        except (ValueError, TypeError):
            # Si el RSSI no es un número válido, ignoramos esta red
            log.debug(f"RSSI no válido para {network.get('bssid', '?')}: {network.get('power')}")
            return

        # Extraemos el canal (puede ser vacío en algunos APs)
        channel = network.get('channel', '').strip()

        # Registramos la red en el monitor de canales
        self.channel_monitor.register_network(channel, rssi)

        # ── Actualización thread-safe de los datos acumulados ─────
        with self._lock:

            # Añadimos la red a la lista acumulativa de la sesión
            self.networks.append(network)

            # Acumulamos el RSSI en el historial del canal correspondiente
            if channel:
                if channel not in self.channel_data:
                    # Primera red detectada en este canal
                    self.channel_data[channel] = []
                self.channel_data[channel].append(rssi)

        # ── Análisis inmediato de la nueva muestra ────────────────

        # Comprobamos si este valor RSSI es anómalo respecto al historial
        # El detector actualiza su historial internamente con cada llamada
        if self.anomaly_detector.process(rssi):

            log.warning(
                f"¡Anomalía RF detectada! RSSI={rssi} dBm "
                f"en red '{network.get('ssid', '?')}' (canal {channel})"
            )

            # Emitimos el evento de anomalía RF para que otros módulos
            # (Reporter, ESP32Bridge) puedan reaccionar
            self.event_bus.emit('rf_anomaly', {
                'bssid':   network.get('bssid'),
                'ssid':    network.get('ssid'),
                'channel': channel,
                'rssi':    rssi,
                'reason':  'rssi_outlier'
            })

    def _start_periodic_analysis(self):
        """
        Lanza un hilo que ejecuta el análisis periódico del espectro.

        El análisis periódico calcula métricas globales y por canal
        cada 'analysis_interval' segundos, independientemente de si
        hay nuevas redes detectadas.
        """
        # Función que ejecuta el hilo: bucle infinito con pausa
        def analysis_loop():
            while True:
                # Esperamos el intervalo configurado
                time.sleep(self.analysis_interval)

                # Ejecutamos el análisis global del espectro
                self._run_spectral_analysis()

        # Creamos y arrancamos el hilo como demonio
        analysis_thread = threading.Thread(
            target=analysis_loop,
            daemon=True,
            name='RFAnalysisThread'
        )
        analysis_thread.start()
        log.debug(f"Análisis periódico cada {self.analysis_interval}s iniciado.")

    def _run_spectral_analysis(self):
        """
        Ejecuta el análisis estadístico completo del espectro.

        Calcula métricas globales y por canal, y detecta canales
        con alta ocupación (posible congestión).
        """
        # Obtenemos una copia thread-safe de los datos actuales
        with self._lock:
            # Si no tenemos suficientes datos, no analizamos todavía
            if len(self.networks) < 3:
                return

            # Copia de las listas para trabajar fuera del lock
            all_networks   = list(self.networks)
            channel_data   = {ch: list(vals) for ch, vals in self.channel_data.items()}

        # ── Métricas globales ─────────────────────────────────────

        # Extraemos todos los valores RSSI de todas las redes vistas
        all_rssi = []
        for net in all_networks:
            try:
                all_rssi.append(int(net.get('power', '0')))
            except (ValueError, TypeError):
                pass

        if len(all_rssi) < 2:
            return

        # Calculamos las estadísticas globales del espectro
        global_mean    = calculate_mean_rssi(all_rssi)
        global_std_dev = calculate_std_dev(all_rssi)
        global_var     = calculate_variance(all_rssi)

        log.info(
            f"[RF] Redes={len(all_networks)} | "
            f"RSSI medio={global_mean:.1f} dBm | "
            f"σ={global_std_dev:.1f} | "
            f"σ²={global_var:.1f}"
        )

        # ── Análisis por canal ────────────────────────────────────

        total_networks = len(all_networks)

        for channel, rssi_list in channel_data.items():

            if len(rssi_list) < 2:
                continue

            # Métricas de este canal
            ch_mean      = calculate_mean_rssi(rssi_list)
            ch_std       = calculate_std_dev(rssi_list)
            ch_occupancy = calculate_channel_occupancy(len(rssi_list), total_networks)

            log.debug(
                f"  Canal {channel}: redes={len(rssi_list)} | "
                f"RSSI={ch_mean:.1f} dBm | σ={ch_std:.1f} | "
                f"ocupación={ch_occupancy:.1%}"
            )

            # ── Detección de congestión ───────────────────────────
            # Un canal con más del 30% de todas las redes se considera
            # potencialmente congestionado
            CONGESTION_THRESHOLD = 0.30

            if ch_occupancy > CONGESTION_THRESHOLD:
                log.warning(
                    f"Canal {channel} congestionado: "
                    f"{ch_occupancy:.1%} de ocupación"
                )

                # Emitimos el evento de congestión
                self.event_bus.emit('channel_congestion', {
                    'channel':        channel,
                    'occupancy':      ch_occupancy,
                    'network_count':  len(rssi_list),
                    'mean_rssi':      ch_mean,
                    'std_dev':        ch_std
                })

    def get_summary(self):
        """
        Retorna un resumen de las métricas espectrales actuales.

        Retorna:
            dict: resumen con claves 'total_networks', 'global_mean_rssi',
                  'global_std_dev', 'channels' (dict por canal).
        """
        with self._lock:
            all_rssi = []
            for net in self.networks:
                try:
                    all_rssi.append(int(net.get('power', '0')))
                except (ValueError, TypeError):
                    pass

            channel_summary = {}
            for ch, rssi_list in self.channel_data.items():
                if rssi_list:
                    channel_summary[ch] = {
                        'count':     len(rssi_list),
                        'mean_rssi': calculate_mean_rssi(rssi_list),
                        'std_dev':   calculate_std_dev(rssi_list),
                        'occupancy': calculate_channel_occupancy(
                            len(rssi_list), max(len(self.networks), 1)
                        )
                    }

        return {
            'total_networks':  len(self.networks),
            'global_mean_rssi': calculate_mean_rssi(all_rssi) if all_rssi else 0,
            'global_std_dev':   calculate_std_dev(all_rssi) if all_rssi else 0,
            'channels':         channel_summary
        }
