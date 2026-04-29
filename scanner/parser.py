# ─────────────────────────────────────────────────────────────────
# scanner/parser.py  —  Parser de la salida CSV de airodump-ng
#
# Descripción:
#   Convierte el fichero CSV generado por airodump-ng en una lista
#   de diccionarios Python estructurados, uno por cada red detectada.
#
#   El CSV de airodump-ng tiene un formato especial con DOS secciones:
#
#   SECCIÓN 1 — Puntos de acceso (AP):
#     BSSID, First time seen, Last time seen, channel, Speed,
#     Privacy, Cipher, Authentication, Power, # beacons, # IV,
#     LAN IP, ID-length, ESSID, Key
#
#   SECCIÓN 2 — Clientes asociados (separada por línea en blanco):
#     Station MAC, First time seen, Last time seen, Power,
#     # packets, BSSID, Probed ESSIDs
#
#   Este parser extrae SOLO la sección de APs.
# ─────────────────────────────────────────────────────────────────

# csv: módulo estándar para leer ficheros con valores separados por comas
import csv

# os: para verificar que el fichero existe antes de intentar leerlo
import os

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def parse_airodump_csv(filepath):
    """
    Lee un fichero CSV de airodump-ng y retorna la lista de redes.

    Parámetros:
        filepath (str): ruta completa al fichero CSV de airodump-ng.
                        Ejemplo: 'sessions/scan-01.csv'

    Retorna:
        list[dict]: lista de diccionarios, uno por cada red detectada.
                    Retorna lista vacía si hay error o el fichero no existe.

    Estructura de cada diccionario retornado:
        {
            'bssid':      str,   # MAC del AP (AA:BB:CC:DD:EE:FF)
            'ssid':       str,   # Nombre de la red (puede estar vacío)
            'channel':    str,   # Canal Wi-Fi (1-14 para 2.4GHz, 36+ para 5GHz)
            'power':      str,   # RSSI en dBm (valor negativo, p.ej. '-42')
            'encryption': str,   # Tipo de cifrado: OPN, WEP, WPA, WPA2, WPA3
            'cipher':     str,   # Algoritmo: CCMP, TKIP, WEP
            'auth':       str,   # Autenticación: PSK, MGT, OPN
            'beacons':    str,   # Número de beacons capturados
            'clients':    int,   # Número de clientes asociados (de sección 2)
        }
    """
    # Verificamos que el fichero existe antes de abrirlo
    if not os.path.exists(filepath):
        log.debug(f"CSV no encontrado aún: {filepath}")
        return []   # Retornamos lista vacía, no es un error crítico

    # Lista que acumulará los diccionarios de cada red
    networks = []

    try:
        # Abrimos el fichero con manejo de errores de codificación.
        # airodump-ng puede generar caracteres no-UTF8 en SSIDs con
        # caracteres especiales o en ciertos sistemas embebidos.
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:

            # Leemos todas las líneas del fichero de una sola vez
            lines = f.readlines()

        # ── Separar sección de APs de sección de clientes ────────
        # Las dos secciones están separadas por una línea en blanco
        # seguida de una línea de cabecera con "Station MAC"
        ap_lines = []         # Líneas de la sección de APs
        in_clients = False    # Flag: estamos en la sección de clientes

        for line in lines:
            # Detectamos el inicio de la sección de clientes
            if 'Station MAC' in line:
                in_clients = True
                continue

            # Solo acumulamos líneas de la sección de APs
            if not in_clients:
                ap_lines.append(line)

        # ── Parsear la sección de APs ─────────────────────────────
        # Usamos csv.reader sobre las líneas ya filtradas
        reader = csv.reader(ap_lines)

        for row in reader:

            # Saltamos filas con menos de 14 columnas:
            # son cabeceras, líneas en blanco o filas incompletas
            if len(row) < 14:  # airodump-ng CSV tiene mínimo 15 columnas para APs
                continue

            # La columna 0 debe ser un BSSID válido (contiene ':')
            bssid = row[0].strip()
            if ':' not in bssid or len(bssid) < 17:
                continue   # No es una MAC válida, saltamos

            # Construimos el diccionario con todos los campos del AP
            network = {
                'bssid':      bssid,
                'channel':    row[3].strip(),    # Columna 3: canal
                'power':      row[8].strip(),    # Columna 8: RSSI (dBm)
                'encryption': row[5].strip(),    # Columna 5: Privacy (WPA2...)
                'cipher':     row[6].strip(),    # Columna 6: Cipher (CCMP...)
                'auth':       row[7].strip(),    # Columna 7: Auth (PSK, MGT...)
                'beacons':    row[9].strip(),    # Columna 9: nº beacons
                'ssid':       row[13].strip(),   # Columna 13: ESSID (nombre)
                'clients':    0                  # Se completará más abajo
            }

            # Añadimos la red a la lista de resultados
            networks.append(network)

        log.debug(f"CSV parseado: {len(networks)} redes encontradas en {filepath}")
        return networks

    except PermissionError:
        # El fichero está siendo escrito por airodump-ng: es normal
        log.debug("CSV ocupado por airodump-ng, reintentando en el próximo ciclo.")
        return []

    except Exception as e:
        log.error(f"Error inesperado parseando {filepath}: {e}")
        return []


def normalize_encryption(raw):
    """
    Normaliza el tipo de cifrado al formato estándar del sistema.

    airodump-ng puede devolver variantes como 'WPA2 ', 'WPA2 WPA',
    'OPN', 'WEP', 'WPA3 SAE', etc. Esta función las unifica.

    Parámetros:
        raw (str): cadena de cifrado tal como viene del CSV.

    Retorna:
        str: tipo de cifrado normalizado ('WPA2', 'WPA', 'WEP', 'OPN', 'WPA3').
    """
    # Limpiamos espacios y convertimos a mayúsculas para comparación
    cleaned = raw.strip().upper()

    # Comprobamos en orden de más específico a más general
    if 'WPA3' in cleaned or 'SAE' in cleaned:
        return 'WPA3'
    elif 'WPA2' in cleaned:
        return 'WPA2'
    elif 'WPA' in cleaned:
        return 'WPA'
    elif 'WEP' in cleaned:
        return 'WEP'
    elif 'OPN' in cleaned or cleaned == '':
        return 'OPN'
    else:
        # Retornamos el valor tal cual si no reconocemos el formato
        return cleaned
