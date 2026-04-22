# ─────────────────────────────────────────────────────────────────
# utils/helpers.py  —  Funciones auxiliares de uso general
#
# Descripción:
#   Colección de funciones de utilidad usadas por varios módulos.
#   Evita la duplicación de código para operaciones comunes como
#   validación de MACs, formateo de valores RSSI, etc.
# ─────────────────────────────────────────────────────────────────

# re: expresiones regulares para validación de formato MAC
import re

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)

# Expresión regular para validar una dirección MAC en formato estándar
# Acepta: AA:BB:CC:DD:EE:FF y AA-BB-CC-DD-EE-FF
_MAC_REGEX = re.compile(
    r'^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$'
)


def is_valid_mac(mac):
    """
    Valida si una cadena es una dirección MAC bien formada.

    Parámetros:
        mac (str): cadena a validar. Ejemplo: 'AA:BB:CC:DD:EE:FF'

    Retorna:
        bool: True si es una MAC válida, False en caso contrario.

    Ejemplos:
        is_valid_mac('AA:BB:CC:DD:EE:FF')  → True
        is_valid_mac('AA:BB:CC')            → False
        is_valid_mac('no es mac')           → False
    """
    if not mac or not isinstance(mac, str):
        return False   # None o no es cadena

    # Usamos la expresión regular precompilada para mayor eficiencia
    return bool(_MAC_REGEX.match(mac.strip()))


def sanitize_ssid(ssid):
    """
    Limpia un SSID para usarlo de forma segura en nombres de fichero.

    Elimina o reemplaza caracteres que no son válidos en nombres de
    fichero del sistema de archivos (/, \, :, *, etc.).

    Parámetros:
        ssid (str): nombre de red original.

    Retorna:
        str: SSID limpio, apto para usar en nombres de fichero.
             Retorna 'unknown_ssid' si el resultado está vacío.

    Ejemplo:
        sanitize_ssid('Mi Red/Casa:2024')  → 'Mi_Red_Casa_2024'
    """
    if not ssid:
        return 'unknown_ssid'

    # Caracteres no permitidos en nombres de fichero en Linux/Windows
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']

    # Reemplazamos cada carácter inválido por un guión bajo
    result = ssid
    for char in invalid_chars:
        result = result.replace(char, '_')

    # Eliminamos espacios al inicio y al final
    result = result.strip()

    # Si el resultado está vacío tras la limpieza, usamos nombre genérico
    return result if result else 'unknown_ssid'


def rssi_to_quality(rssi):
    """
    Convierte un valor RSSI (dBm) a un porcentaje de calidad de señal.

    La escala estándar mapea el rango [-100, -30] dBm al rango [0, 100]%.

    Parámetros:
        rssi (int|float|str): potencia de señal en dBm.

    Retorna:
        int: calidad entre 0% (sin señal) y 100% (señal excelente).
             Retorna 0 si el valor no es válido.

    Referencia de calidad:
        >  -30 dBm : 100% — señal excelente (a centímetros del AP)
        -50 dBm    :  80% — señal muy buena
        -60 dBm    :  60% — señal buena
        -70 dBm    :  40% — señal aceptable
        -80 dBm    :  20% — señal débil
        < -90 dBm  :   0% — sin conexión práctica
    """
    try:
        rssi_val = int(rssi)
    except (ValueError, TypeError):
        return 0   # Valor no numérico: retornamos 0%

    # Limitamos el rango a [-100, -30] dBm
    # max/min aseguran que no salgamos del rango válido
    rssi_clamped = max(-100, min(-30, rssi_val))

    # Interpolación lineal: mapeamos [-100, -30] → [0, 100]
    # Fórmula: quality = (rssi - min) / (max - min) * 100
    quality = int((rssi_clamped + 100) / 70 * 100)

    return quality


def format_duration(seconds):
    """
    Formatea una duración en segundos a una cadena legible.

    Parámetros:
        seconds (int|float): duración en segundos.

    Retorna:
        str: duración formateada. Ejemplos: '45s', '3m 20s', '1h 5m 10s'
    """
    seconds = int(seconds)

    # Calculamos horas, minutos y segundos restantes
    hours   = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs    = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def mac_to_filename(mac):
    """
    Convierte una dirección MAC en un nombre de fichero válido.

    Elimina los separadores ':' o '-' de la MAC.

    Parámetros:
        mac (str): dirección MAC. Ejemplo: 'AA:BB:CC:DD:EE:FF'

    Retorna:
        str: MAC sin separadores. Ejemplo: 'AABBCCDDEEFF'
    """
    return mac.replace(':', '').replace('-', '').upper()
