# ─────────────────────────────────────────────────────────────────
# reporting/report_generator.py  —  Generador central de informes
#
# Descripción:
#   Escucha eventos del sistema durante toda la sesión y acumula
#   los datos para generar un informe estructurado al finalizar.
#
#   El informe recoge:
#     - Redes Wi-Fi detectadas (SSID, BSSID, canal, RSSI, cifrado)
#     - Handshakes WPA/WPA2 capturados
#     - Anomalías RF detectadas
#     - Congestión de canales observada
#     - Estadísticas resumen de la sesión
#
#   Formatos de exportación soportados: JSON, CSV, HTML
# ─────────────────────────────────────────────────────────────────

# json: para exportación en formato JSON
import json

# csv: para exportación en formato CSV (tablas)
import csv

# os: para crear directorios y rutas de ficheros
import os

# datetime: para timestamps en los informes
from datetime import datetime

# Importamos los exportadores especializados
from reporting.json_exporter import export_to_json
from reporting.html_exporter import export_to_html

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class ReportGenerator:
    """
    Generador central de informes de sesión.

    Se suscribe a todos los eventos relevantes del sistema y
    va acumulando los datos durante la sesión. Al finalizar,
    genera los informes en los formatos configurados.
    """

    def __init__(self, event_bus):
        """
        Constructor del generador de informes.

        Parámetros:
            event_bus (EventBus): bus de eventos del sistema.
        """
        # Referencia al bus de eventos
        self.event_bus = event_bus

        # ── Acumuladores de datos de la sesión ────────────────────

        # Lista de todas las redes detectadas durante la sesión
        self.networks = []

        # Lista de handshakes capturados
        self.handshakes = []

        # Lista de anomalías RF detectadas
        self.rf_anomalies = []

        # Lista de eventos de congestión de canal
        self.channel_congestions = []

        # Timestamp de inicio de sesión
        self.session_start = datetime.now().isoformat()

        # ── Suscripciones a eventos ───────────────────────────────
        # Nos suscribimos a todos los eventos que queremos registrar
        event_bus.subscribe('network_detected',   self._on_network)
        event_bus.subscribe('handshake_detected', self._on_handshake)
        event_bus.subscribe('rf_anomaly',         self._on_anomaly)
        event_bus.subscribe('channel_congestion', self._on_congestion)

        log.info("ReportGenerator inicializado y suscrito a eventos.")

    def _on_network(self, data):
        """Callback: registra una nueva red detectada."""
        # Añadimos un timestamp al dato para el informe
        record = dict(data)   # Copia del diccionario original
        record['timestamp'] = datetime.now().isoformat()

        self.networks.append(record)
        log.debug(f"Reporter: red registrada → {data.get('ssid', '?')}")

    def _on_handshake(self, data):
        """Callback: registra un handshake capturado."""
        record = dict(data)
        record['timestamp'] = datetime.now().isoformat()

        self.handshakes.append(record)
        log.info(f"Reporter: handshake registrado → {data.get('ssid', '?')}")

    def _on_anomaly(self, data):
        """Callback: registra una anomalía RF."""
        record = dict(data)
        record['timestamp'] = datetime.now().isoformat()

        self.rf_anomalies.append(record)

    def _on_congestion(self, data):
        """Callback: registra un evento de congestión de canal."""
        record = dict(data)
        record['timestamp'] = datetime.now().isoformat()

        self.channel_congestions.append(record)

    def get_summary(self):
        """
        Genera un diccionario resumen con las estadísticas de la sesión.

        Retorna:
            dict: resumen con contadores y métricas principales.
        """
        return {
            'session_start':        self.session_start,
            'session_end':          datetime.now().isoformat(),
            'total_networks':       len(self.networks),
            'total_handshakes':     len(self.handshakes),
            'total_rf_anomalies':   len(self.rf_anomalies),
            'total_congestions':    len(self.channel_congestions),
            'networks':             self.networks,
            'handshakes':           self.handshakes,
            'rf_anomalies':         self.rf_anomalies,
            'channel_congestions':  self.channel_congestions,
        }

    def export_all(self, output_dir='.'):
        """
        Exporta el informe completo en todos los formatos configurados.

        Parámetros:
            output_dir (str): directorio donde guardar los ficheros.
        """
        # Creamos el directorio si no existe
        os.makedirs(output_dir, exist_ok=True)

        # Obtenemos el resumen completo de la sesión
        summary = self.get_summary()

        # Exportamos en cada formato soportado
        self._export_json(summary, output_dir)
        self._export_csv(output_dir)
        self._export_html(summary, output_dir)

        log.info(f"Informes generados en: {output_dir}")

    def _export_json(self, summary, output_dir):
        """Exporta el informe completo en formato JSON."""
        try:
            filepath = os.path.join(output_dir, 'report.json')
            export_to_json(summary, filepath)
            log.info(f"Informe JSON generado: {filepath}")
        except Exception as e:
            log.error(f"Error generando JSON: {e}")

    def _export_csv(self, output_dir):
        """Exporta la lista de redes detectadas en formato CSV."""
        try:
            filepath = os.path.join(output_dir, 'networks.csv')

            # Definimos las columnas del CSV
            fieldnames = ['timestamp', 'ssid', 'bssid', 'channel',
                          'power', 'encryption', 'cipher']

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                # DictWriter escribe diccionarios como filas de CSV
                writer = csv.DictWriter(f, fieldnames=fieldnames,
                                        extrasaction='ignore')
                writer.writeheader()             # Escribe la fila de cabecera
                writer.writerows(self.networks)  # Escribe una fila por red

            log.info(f"Informe CSV generado: {filepath}")

        except Exception as e:
            log.error(f"Error generando CSV: {e}")

    def _export_html(self, summary, output_dir):
        """Exporta el informe en formato HTML navegable."""
        try:
            filepath = os.path.join(output_dir, 'report.html')
            export_to_html(summary, filepath)
            log.info(f"Informe HTML generado: {filepath}")
        except Exception as e:
            log.error(f"Error generando HTML: {e}")
