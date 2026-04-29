# ─────────────────────────────────────────────────────────────────
# scanner/monitor.py  —  Gestión del modo monitor de la interfaz Wi-Fi
#
# Descripción:
#   Encapsula todas las operaciones relacionadas con el modo monitor:
#   activación, desactivación y verificación del estado.
#
#   El modo monitor (también llamado RFMON) permite a una tarjeta Wi-Fi
#   capturar TODOS los paquetes del espectro inalámbrico, sin importar
#   a quién estén dirigidos. Es imprescindible para auditorías Wi-Fi.
#
#   En modo normal ('managed'), una tarjeta solo recibe los paquetes
#   dirigidos a su propia dirección MAC.
# ─────────────────────────────────────────────────────────────────

# subprocess: para ejecutar airmon-ng y verificar el estado con iwconfig
import subprocess

# re: expresiones regulares para analizar la salida de iwconfig
import re

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class MonitorModeManager:
    """
    Gestiona el modo monitor de la interfaz Wi-Fi externa.

    Proporciona métodos para activar, desactivar y verificar
    el modo monitor, abstrayendo los comandos de bajo nivel
    de airmon-ng e iwconfig.
    """

    def __init__(self, interface='wlan1'):
        """
        Constructor del gestor de modo monitor.

        Parámetros:
            interface (str): nombre de la interfaz Wi-Fi física.
                             Por defecto 'wlan1' (la externa en RPi).
                             La interfaz integrada suele ser 'wlan0'.
        """
        # Nombre de la interfaz física (antes del modo monitor)
        self.interface = interface

        # Nombre de la interfaz en modo monitor.
        # airmon-ng añade el sufijo 'mon' por defecto.
        self.monitor_interface = interface + 'mon'

        # Flag que indica si el modo monitor está activo
        self.is_active = False

    def enable(self):
        """
        Activa el modo monitor en la interfaz Wi-Fi configurada.

        Ejecuta: airmon-ng start <interfaz>

        Retorna:
            bool: True si se activó correctamente, False si hubo error.
        """
        log.info(f"Activando modo monitor en '{self.interface}'...")

        try:
            # Primero, matamos procesos que puedan interferir con el modo monitor.
            # NetworkManager, wpa_supplicant y dhclient pueden causar conflictos.
            # airmon-ng check kill los detecta y cierra automáticamente.
            log.debug("Comprobando procesos que pueden interferir...")
            subprocess.run(
                ["airmon-ng", "check", "kill"],
                capture_output=True,
                text=True
            )
            # No usamos check=True aquí porque 'airmon-ng check kill'
            # puede retornar código != 0 si no hay procesos que matar,
            # lo cual no es un error real.

            # Activamos el modo monitor con airmon-ng
            result = subprocess.run(
                ["airmon-ng", "start", self.interface],
                capture_output=True,    # Capturamos stdout y stderr
                text=True,              # Decodificamos como texto UTF-8
                check=True              # Error si código de retorno != 0
            )

            log.debug(f"Salida de airmon-ng start:\n{result.stdout}")

            # Verificamos que la interfaz en modo monitor existe
            if self._verify_monitor_mode():
                self.is_active = True
                log.info(f"Modo monitor activo: '{self.monitor_interface}'")
                return True
            else:
                log.error("La interfaz en modo monitor no aparece en el sistema.")
                return False

        except subprocess.CalledProcessError as e:
            # airmon-ng devolvió error (sin permisos, interfaz inexistente...)
            log.error(f"airmon-ng falló: {e.stderr}")
            return False

        except FileNotFoundError:
            # airmon-ng no está instalado en el sistema
            log.error("airmon-ng no encontrado. Instala: sudo apt install aircrack-ng")
            return False

    def disable(self):
        """
        Desactiva el modo monitor y restaura el modo managed.

        Ejecuta: airmon-ng stop <interfaz_monitor>

        Retorna:
            bool: True si se desactivó correctamente.
        """
        log.info(f"Desactivando modo monitor en '{self.monitor_interface}'...")

        try:
            subprocess.run(
                ["airmon-ng", "stop", self.monitor_interface],
                capture_output=True,
                text=True,
                check=True
            )

            self.is_active = False
            log.info(f"Modo monitor desactivado. Interfaz '{self.interface}' restaurada.")
            return True

        except subprocess.CalledProcessError as e:
            log.error(f"Error al desactivar modo monitor: {e.stderr}")
            return False

    def _verify_monitor_mode(self):
        """
        Verifica que la interfaz en modo monitor existe en el sistema.

        Usa 'iwconfig' para listar las interfaces y busca el nombre
        de la interfaz monitor esperada.

        Retorna:
            bool: True si la interfaz monitor existe y está en modo monitor.
        """
        try:
            # iwconfig lista todas las interfaces inalámbricas y su modo
            result = subprocess.run(
                ["iwconfig"],
                capture_output=True,
                text=True
            )

            # Buscamos el nombre de la interfaz monitor en la salida
            if self.monitor_interface in result.stdout:
                # También verificamos que aparece 'Mode:Monitor'
                if 'Mode:Monitor' in result.stdout:
                    return True

            return False

        except FileNotFoundError:
            # iwconfig no disponible: asumimos que el modo monitor está activo
            log.warning("iwconfig no disponible. Asumiendo modo monitor activo.")
            return True

    def get_monitor_interface(self):
        """
        Retorna el nombre de la interfaz en modo monitor.

        Retorna:
            str: nombre de la interfaz (p.ej. 'wlan1mon').
        """
        return self.monitor_interface
