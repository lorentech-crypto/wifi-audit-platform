# ─────────────────────────────────────────────────────────────────
# esp32/protocol.py  —  Definición del protocolo de mensajes JSON
#
# Descripción:
#   Define la estructura y los tipos de mensajes del protocolo de
#   comunicación entre la Raspberry Pi y el ESP32.
#
#   Todos los mensajes siguen el mismo esquema JSON:
#     {
#       "event": "<tipo_de_evento>",
#       "data":  { ... campos específicos del evento ... }
#     }
#
#   El firmware ESP32 (esp32_firmware/main.cpp) interpreta este
#   protocolo para actualizar su interfaz de usuario.
# ─────────────────────────────────────────────────────────────────

# ── Tipos de eventos definidos en el protocolo ────────────────────
# Usamos constantes de cadena para evitar errores tipográficos
# y facilitar el mantenimiento si cambian los nombres

EVENT_NETWORK_DETECTED   = 'network_detected'
EVENT_HANDSHAKE_DETECTED = 'handshake_detected'
EVENT_RF_ANOMALY         = 'rf_anomaly'
EVENT_CHANNEL_CONGESTION = 'channel_congestion'
EVENT_CAPTURE_STARTED    = 'capture_started'
EVENT_CAPTURE_FINISHED   = 'capture_finished'
EVENT_SYSTEM_ALERT       = 'system_alert'
EVENT_SYSTEM_STATUS      = 'system_status'


def build_network_message(ssid, bssid, channel, rssi, encryption):
    """
    Construye el mensaje JSON para una red detectada.

    Parámetros:
        ssid       (str): nombre de la red Wi-Fi.
        bssid      (str): dirección MAC del punto de acceso.
        channel    (str): canal Wi-Fi.
        rssi       (str|int): potencia de señal en dBm.
        encryption (str): tipo de cifrado (WPA2, WPA3, etc.).

    Retorna:
        dict: mensaje listo para serializar y enviar.
    """
    return {
        'event': EVENT_NETWORK_DETECTED,
        'data':  {
            'ssid':       str(ssid),
            'bssid':      str(bssid),
            'channel':    str(channel),
            'rssi':       str(rssi),
            'encryption': str(encryption)
        }
    }


def build_handshake_message(ssid, bssid, pcap_file):
    """
    Construye el mensaje JSON para notificar un handshake capturado.

    Parámetros:
        ssid      (str): nombre de la red.
        bssid     (str): MAC del AP.
        pcap_file (str): ruta al fichero PCAP con el handshake.

    Retorna:
        dict: mensaje listo para serializar y enviar.
    """
    return {
        'event': EVENT_HANDSHAKE_DETECTED,
        'data':  {
            'ssid':  str(ssid),
            'bssid': str(bssid),
            'pcap':  str(pcap_file)
        }
    }


def build_anomaly_message(channel, rssi, mean, std_dev):
    """
    Construye el mensaje JSON para una anomalía RF detectada.

    Parámetros:
        channel (str): canal donde se detectó la anomalía.
        rssi    (float): valor RSSI anómalo.
        mean    (float): RSSI medio del historial.
        std_dev (float): desviación estándar del historial.

    Retorna:
        dict: mensaje listo para serializar y enviar.
    """
    return {
        'event': EVENT_RF_ANOMALY,
        'data':  {
            'channel': str(channel),
            'rssi':    round(float(rssi), 1),
            'mean':    round(float(mean), 1),
            'std_dev': round(float(std_dev), 1)
        }
    }


def build_status_message(networks_count, handshakes_count, anomalies_count):
    """
    Construye el mensaje JSON de estado general del sistema.

    Se envía periódicamente para que el ESP32 actualice su pantalla
    de resumen con las estadísticas de la sesión en curso.

    Parámetros:
        networks_count   (int): redes detectadas en la sesión.
        handshakes_count (int): handshakes capturados.
        anomalies_count  (int): anomalías RF detectadas.

    Retorna:
        dict: mensaje listo para serializar y enviar.
    """
    return {
        'event': EVENT_SYSTEM_STATUS,
        'data':  {
            'networks':   networks_count,
            'handshakes': handshakes_count,
            'anomalies':  anomalies_count
        }
    }
