# ─────────────────────────────────────────────────────────────────
# utils/network_utils.py  —  Utilidades de red
#
# Descripción:
#   Funciones de apoyo relacionadas con redes inalámbricas:
#   detección de interfaces disponibles, verificación de permisos
#   de root y consultas al sistema sobre adaptadores Wi-Fi.
# ─────────────────────────────────────────────────────────────────

# subprocess: para ejecutar comandos del sistema (iw, iwconfig, id)
import subprocess

# os: para verificar permisos de usuario (root)
import os

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def is_root():
    """
    Verifica si el proceso se está ejecutando con privilegios de root.

    La mayoría de operaciones de auditoría Wi-Fi (modo monitor,
    inyección de paquetes) requieren permisos de superusuario.

    Retorna:
        bool: True si se ejecuta como root (UID = 0), False en caso contrario.
    """
    # os.getuid() retorna el User ID del proceso actual.
    # En Linux/Unix, el usuario root siempre tiene UID = 0.
    return os.getuid() == 0


def get_wireless_interfaces():
    """
    Obtiene la lista de interfaces inalámbricas disponibles en el sistema.

    Usa el comando 'iw dev' que lista todos los dispositivos Wi-Fi
    actualmente configurados en el kernel.

    Retorna:
        list[str]: lista de nombres de interfaces (p.ej. ['wlan0', 'wlan1']).
                   Retorna lista vacía si hay error o no hay interfaces.

    Ejemplo de salida de 'iw dev':
        phy#0
            Interface wlan0
                ifindex 3
                type managed
        phy#1
            Interface wlan1
                ifindex 4
                type managed
    """
    interfaces = []

    try:
        # Ejecutamos 'iw dev' para listar interfaces Wi-Fi
        result = subprocess.run(
            ['iw', 'dev'],
            capture_output=True,
            text=True,
            check=False   # No lanzamos excepción si iw no está disponible
        )

        # Parseamos la salida línea a línea buscando "Interface NombreInterfaz"
        for line in result.stdout.split('\n'):
            line = line.strip()   # Eliminamos espacios/tabulaciones iniciales

            # Cada interfaz aparece en una línea que empieza por "Interface"
            if line.startswith('Interface'):
                # El nombre de la interfaz es la segunda "palabra" de la línea
                parts = line.split()
                if len(parts) >= 2:
                    interfaces.append(parts[1])   # Añadimos el nombre

    except FileNotFoundError:
        # 'iw' no está instalado; intentamos con 'iwconfig' como alternativa
        log.debug("'iw' no disponible. Intentando con 'iwconfig'...")
        interfaces = _get_interfaces_iwconfig()

    except Exception as e:
        log.error(f"Error obteniendo interfaces inalámbricas: {e}")

    log.debug(f"Interfaces inalámbricas detectadas: {interfaces}")
    return interfaces


def _get_interfaces_iwconfig():
    """
    Método alternativo para obtener interfaces usando iwconfig.

    Se usa cuando 'iw' no está disponible en el sistema.

    Retorna:
        list[str]: lista de nombres de interfaces Wi-Fi.
    """
    interfaces = []

    try:
        result = subprocess.run(
            ['iwconfig'],
            capture_output=True,
            text=True,
            check=False
        )

        # En iwconfig, cada interfaz aparece al inicio de una línea sin sangría
        for line in result.stdout.split('\n'):
            # Las líneas de interfaz empiezan sin espacios y contienen "IEEE"
            if line and not line.startswith(' ') and 'IEEE' in line:
                # El nombre de la interfaz es la primera palabra
                iface = line.split()[0]
                interfaces.append(iface)

    except Exception:
        pass   # Sin iwconfig tampoco: retornamos lista vacía

    return interfaces


def get_interface_mode(interface):
    """
    Obtiene el modo de operación actual de una interfaz inalámbrica.

    Parámetros:
        interface (str): nombre de la interfaz. Ejemplo: 'wlan1'

    Retorna:
        str: modo de operación ('managed', 'monitor', 'unknown').
             'managed' es el modo normal de conexión a redes.
             'monitor' es el modo necesario para auditorías.
    """
    try:
        # 'iw dev INTERFAZ info' muestra información detallada de la interfaz
        result = subprocess.run(
            ['iw', 'dev', interface, 'info'],
            capture_output=True,
            text=True,
            check=False
        )

        # Buscamos la línea que contiene "type" (modo de operación)
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('type'):
                # "type managed" o "type monitor"
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]   # Retornamos el modo

    except Exception as e:
        log.debug(f"Error obteniendo modo de {interface}: {e}")

    return 'unknown'


def check_aircrack_suite():
    """
    Verifica que los componentes de la suite Aircrack-ng están instalados.

    Retorna:
        dict: {herramienta: bool} indicando si cada herramienta está disponible.

    Ejemplo de retorno:
        {
            'airmon-ng':  True,
            'airodump-ng': True,
            'aireplay-ng': True,
            'aircrack-ng': True
        }
    """
    # Lista de herramientas de Aircrack-ng que necesitamos
    tools = ['airmon-ng', 'airodump-ng', 'aireplay-ng', 'aircrack-ng']

    # Diccionario de resultados
    availability = {}

    for tool in tools:
        try:
            # '--help' o '--version' generalmente retornan código 0 o 1
            # Lo importante es que NO retornen FileNotFoundError
            subprocess.run(
                [tool, '--help'],
                capture_output=True,
                check=False   # No lanzar excepción por código != 0
            )
            # Si llegamos aquí, la herramienta existe
            availability[tool] = True
            log.debug(f"✓ {tool} disponible.")

        except FileNotFoundError:
            # La herramienta no está instalada
            availability[tool] = False
            log.warning(f"✗ {tool} NO encontrado. Instala: sudo apt install aircrack-ng")

    return availability
