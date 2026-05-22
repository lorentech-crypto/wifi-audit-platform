# ─────────────────────────────────────────────────────────────────
# reporting/csv_exporter.py  —  Exportación de informes a CSV
#
# Descripción:
#   Exporta los datos de la sesión a ficheros CSV separados por tipo.
#   CSV es el formato más compatible con hojas de cálculo y herramientas
#   de análisis externas (Excel, LibreOffice, pandas, etc.).
#
#   Genera tres ficheros independientes:
#     - networks.csv     → redes Wi-Fi detectadas
#     - handshakes.csv   → handshakes WPA/WPA2 capturados
#     - rf_anomalies.csv → anomalías RF detectadas
# ─────────────────────────────────────────────────────────────────

# csv: módulo estándar para escritura de ficheros CSV
import csv

# os: para construir rutas de ficheros
import os

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def export_networks_csv(networks, output_dir):
    """
    Exporta la lista de redes detectadas a un fichero CSV.

    Parámetros:
        networks   (list[dict]): lista de redes detectadas durante la sesión.
        output_dir (str): directorio donde guardar el fichero.

    Retorna:
        bool: True si la exportación fue exitosa, False si hubo error.
    """
    # Ruta completa del fichero de salida
    filepath = os.path.join(output_dir, 'networks.csv')

    # Columnas del CSV: las claves del diccionario de cada red
    # El orden importa: define cómo aparecen las columnas en el fichero
    fieldnames = [
        'timestamp',    # Fecha y hora de detección
        'ssid',         # Nombre de la red
        'bssid',        # Dirección MAC del AP
        'channel',      # Canal Wi-Fi
        'power',        # RSSI en dBm
        'encryption',   # Tipo de cifrado (WPA2, WPA3, WEP, OPN)
        'cipher',       # Algoritmo de cifrado (CCMP, TKIP...)
        'auth',         # Método de autenticación (PSK, MGT...)
        'beacons',      # Número de beacons capturados
    ]

    return _write_csv(networks, filepath, fieldnames)


def export_handshakes_csv(handshakes, output_dir):
    """
    Exporta la lista de handshakes capturados a un fichero CSV.

    Parámetros:
        handshakes (list[dict]): lista de handshakes detectados.
        output_dir (str): directorio donde guardar el fichero.

    Retorna:
        bool: True si la exportación fue exitosa.
    """
    filepath = os.path.join(output_dir, 'handshakes.csv')

    # Columnas específicas para handshakes
    fieldnames = [
        'timestamp',   # Momento de detección del handshake
        'ssid',        # Nombre de la red
        'bssid',       # MAC del punto de acceso
        'pcap',        # Ruta al fichero PCAP con el handshake
        'elapsed',     # Segundos transcurridos hasta la detección
    ]

    return _write_csv(handshakes, filepath, fieldnames)


def export_anomalies_csv(anomalies, output_dir):
    """
    Exporta la lista de anomalías RF a un fichero CSV.

    Parámetros:
        anomalies  (list[dict]): lista de anomalías RF detectadas.
        output_dir (str): directorio donde guardar el fichero.

    Retorna:
        bool: True si la exportación fue exitosa.
    """
    filepath = os.path.join(output_dir, 'rf_anomalies.csv')

    # Columnas específicas para anomalías RF
    fieldnames = [
        'timestamp',   # Momento de detección de la anomalía
        'channel',     # Canal Wi-Fi donde se detectó
        'rssi',        # Valor RSSI anómalo en dBm
        'reason',      # Motivo de la anomalía (rssi_outlier, etc.)
        'bssid',       # BSSID asociado (si lo hay)
        'ssid',        # SSID asociado (si lo hay)
    ]

    return _write_csv(anomalies, filepath, fieldnames)


def _write_csv(data, filepath, fieldnames):
    """
    Función interna: escribe una lista de diccionarios en un fichero CSV.

    Parámetros:
        data       (list[dict]): datos a escribir, uno por fila.
        filepath   (str): ruta completa del fichero CSV de salida.
        fieldnames (list[str]): orden y nombres de las columnas.

    Retorna:
        bool: True si se escribió correctamente, False si hubo error.
    """
    try:
        # Abrimos el fichero en modo escritura.
        # newline='': necesario en Windows para evitar líneas en blanco dobles.
        # encoding='utf-8': permite SSIDs con caracteres especiales.
        with open(filepath, 'w', newline='', encoding='utf-8') as f:

            # DictWriter escribe cada diccionario como una fila del CSV.
            # extrasaction='ignore': ignora claves del dict no presentes
            # en fieldnames, en lugar de lanzar un error.
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                extrasaction='ignore'
            )

            # Escribimos la fila de cabecera con los nombres de columna
            writer.writeheader()

            # Escribimos una fila por cada elemento de la lista
            writer.writerows(data)

        log.debug(f"CSV exportado: {filepath} ({len(data)} filas)")
        return True

    except PermissionError:
        log.error(f"Sin permisos para escribir en: {filepath}")
        return False

    except Exception as e:
        log.error(f"Error exportando CSV {filepath}: {e}")
        return False
