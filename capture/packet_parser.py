# ─────────────────────────────────────────────────────────────────
# capture/packet_parser.py  —  Análisis de paquetes capturados
#
# Descripción:
#   Analiza ficheros PCAP para detectar handshakes WPA/WPA2 completos.
#
#   ¿Qué es un handshake WPA/WPA2?
#   El proceso de autenticación WPA/WPA2 usa un intercambio de 4 mensajes
#   llamado "4-way handshake" (4WH). Los mensajes viajan como tramas EAPOL
#   (Extensible Authentication Protocol over LAN):
#
#     Mensaje 1: AP → Cliente  (ANonce)
#     Mensaje 2: Cliente → AP  (SNonce + MIC)
#     Mensaje 3: AP → Cliente  (GTK cifrado + MIC)
#     Mensaje 4: Cliente → AP  (confirmación)
#
#   Para un ataque de diccionario offline solo se necesitan los mensajes
#   1 y 2 (o 2 y 3), ya que contienen la información necesaria para
#   verificar contraseñas candidatas sin acceder a la red.
# ─────────────────────────────────────────────────────────────────

# os: para verificar existencia del fichero PCAP
import os

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def detect_handshake_in_pcap(pcap_file, bssid=None):
    """
    Detecta si un fichero PCAP contiene un handshake WPA/WPA2 válido.

    Utiliza el ejecutable 'aircrack-ng' en modo verificación para
    analizar el fichero. aircrack-ng puede detectar handshakes
    sin necesidad de proporcionar un diccionario de contraseñas.

    Parámetros:
        pcap_file (str): ruta al fichero PCAP a analizar.
        bssid     (str): MAC del AP para filtrar (opcional).
                         Si es None, analiza todos los handshakes del PCAP.

    Retorna:
        bool: True si se detecta al menos un handshake válido,
              False en caso contrario.
    """
    # Verificamos que el fichero PCAP existe y no está vacío
    if not os.path.exists(pcap_file):
        log.debug(f"PCAP no encontrado: {pcap_file}")
        return False

    # Un PCAP muy pequeño (< 200 bytes) no puede contener un handshake
    if os.path.getsize(pcap_file) < 200:
        log.debug(f"PCAP demasiado pequeño para contener handshake: {pcap_file}")
        return False

    try:
        # Importamos subprocess aquí para no cargarlo si no es necesario
        import subprocess

        # Construimos el comando de verificación de aircrack-ng.
        # aircrack-ng sin diccionario (-w) actúa en modo verificación:
        # solo analiza el PCAP e informa si contiene handshakes válidos.
        command = ["aircrack-ng", pcap_file]

        # Si se especificó un BSSID, filtramos por él
        if bssid:
            command.extend(["-b", bssid])

        # Ejecutamos aircrack-ng y capturamos su salida
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10    # Máximo 10 segundos de análisis
        )

        # aircrack-ng imprime "1 handshake" o "Handshake found" cuando detecta uno
        output = result.stdout + result.stderr

        # Buscamos indicadores de handshake en la salida
        handshake_indicators = [
            'handshake',      # Texto principal de aircrack-ng
            'Handshake',
            'WPA (1 handshake)',
            '1 handshake',
        ]

        for indicator in handshake_indicators:
            if indicator in output:
                log.debug(f"Handshake detectado en {pcap_file}")
                return True

        return False

    except subprocess.TimeoutExpired:
        # El análisis tardó demasiado
        log.debug(f"Timeout analizando {pcap_file}")
        return False

    except FileNotFoundError:
        # aircrack-ng no está instalado
        log.error("aircrack-ng no encontrado para verificación de handshake.")
        return False

    except Exception as e:
        log.error(f"Error analizando PCAP {pcap_file}: {e}")
        return False


def count_eapol_frames(pcap_file):
    """
    Cuenta el número de tramas EAPOL en un fichero PCAP.

    Las tramas EAPOL son los mensajes del 4-way handshake.
    Un handshake completo tiene 4 tramas EAPOL (mensajes 1-4).
    Para un ataque de diccionario offline se necesitan al menos 2.

    Parámetros:
        pcap_file (str): ruta al fichero PCAP.

    Retorna:
        int: número de tramas EAPOL encontradas (0 si hay error).
    """
    try:
        # Usamos pyshark si está disponible (más preciso que aircrack-ng)
        import pyshark

        # Abrimos el fichero PCAP con filtro EAPOL
        cap = pyshark.FileCapture(
            pcap_file,
            display_filter='eapol'   # Solo tramas EAPOL
        )

        # Contamos los paquetes
        count = 0
        for _ in cap:
            count += 1

        cap.close()
        log.debug(f"Tramas EAPOL encontradas en {pcap_file}: {count}")
        return count

    except ImportError:
        # pyshark no está instalado: usamos método alternativo
        log.debug("pyshark no disponible, usando aircrack-ng para verificación.")
        return 2 if detect_handshake_in_pcap(pcap_file) else 0

    except Exception as e:
        log.error(f"Error contando tramas EAPOL: {e}")
        return 0
