# ─────────────────────────────────────────────────────────────────
# main.py  —  Punto de entrada de la plataforma de auditoría Wi-Fi
#
# Autor:      [Nombre del Autor]
# Versión:    1.0.0  — versión de entrega TFG
# Fecha:      2024
# Licencia:   MIT (solo para uso ético y autorizado)
#
# Descripción:
#   Este fichero es el punto de arranque de toda la plataforma.
#   Su única responsabilidad es:
#     1. Crear el bus de eventos central (EventBus)
#     2. Instanciar todos los módulos del sistema
#     3. Arrancar el escaneo Wi-Fi
#     4. Mantener el proceso vivo en un bucle de espera
#
#   Todo el procesamiento real ocurre dentro de los módulos;
#   este fichero solo orquesta el arranque.
#
# Uso:
#   sudo python3 main.py
#   (requiere privilegios de root para el modo monitor)
# ─────────────────────────────────────────────────────────────────

# ── Importaciones de módulos internos del sistema ─────────────────

# WiFiScanner: responsable de descubrir redes usando airodump-ng
from scanner.scanner import WiFiScanner

# RFAnalyzer: calcula estadísticas del espectro a partir del RSSI
from rf.rf_analyzer import RFAnalyzer

# EventBus: permite que los módulos se comuniquen sin acoplarse
from core.event_bus import EventBus

# ESP32Bridge: transmite eventos al nodo ESP32 por puerto serie
from esp32.serial_bridge import ESP32Bridge

# HandshakeCapture: captura tráfico y detecta handshakes WPA/WPA2
from capture.handshake_capture import HandshakeCapture

# ReportGenerator: almacena y exporta los resultados de la sesión
from reporting.report_generator import ReportGenerator

# Logger: sistema de registro enriquecido con timestamps y colores
from utils.logger import get_logger

# ── Importaciones de la biblioteca estándar de Python ─────────────

# time: necesario para la pausa del bucle principal (time.sleep)
import time

# signal: permite capturar Ctrl+C para cerrar el sistema limpiamente
import signal

# sys: para salir del proceso con un código de error si es necesario
import sys


# ── Instancia global del logger para este fichero ────────────────
# Usamos el nombre del módulo (__name__ = '__main__') para identificar
# de qué fichero provienen los mensajes de log
log = get_logger(__name__)


def shutdown_handler(signum, frame):
    """
    Manejador de señal para el cierre limpio del sistema.

    Se ejecuta automáticamente cuando el usuario pulsa Ctrl+C
    (señal SIGINT) o cuando el sistema recibe SIGTERM.

    Parámetros:
        signum (int): número de la señal recibida
        frame: frame de ejecución actual (no se usa aquí)
    """
    # Informamos al usuario de que el cierre ha sido solicitado
    log.info("Señal de cierre recibida. Deteniendo el sistema...")

    # sys.exit(0) lanza una excepción SystemExit que Python gestiona
    # limpiamente, cerrando todos los recursos abiertos
    sys.exit(0)


def main():
    """
    Función principal del sistema.

    Sigue el patrón de arranque en tres fases:
      Fase 1 → Infraestructura: bus de eventos
      Fase 2 → Módulos: instanciar todos los componentes
      Fase 3 → Ejecución: arrancar el escaneo y el bucle de espera
    """

    # ── Registrar el manejador de Ctrl+C ─────────────────────────
    # A partir de este punto, si el usuario pulsa Ctrl+C, se llamará
    # a shutdown_handler en lugar de lanzar un KeyboardInterrupt
    signal.signal(signal.SIGINT,  shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # ── Mensaje de bienvenida ─────────────────────────────────────
    log.info("=" * 60)
    log.info("  Plataforma de Auditoría Wi-Fi v1.0.0")
    log.info("  SOLO PARA USO ÉTICO Y AUTORIZADO")
    log.info("=" * 60)

    # ── FASE 1: crear el bus de eventos central ───────────────────
    #
    # El EventBus es el componente más crítico del sistema.
    # Todos los módulos lo reciben en su constructor para poder:
    #   - emitir eventos cuando detectan algo relevante
    #   - suscribirse a eventos de otros módulos
    #
    # Se crea PRIMERO porque el resto de módulos lo necesitan
    # en el momento de su instanciación.
    log.info("Inicializando bus de eventos...")
    event_bus = EventBus()

    # ── FASE 2: instanciar todos los módulos ──────────────────────
    #
    # El orden de instanciación no es crítico (todos se suscriben
    # al bus de eventos en su __init__), pero lo mantenemos lógico:
    # primero los módulos de adquisición, luego los de análisis,
    # y finalmente los de salida.

    log.info("Inicializando módulo de escaneo Wi-Fi...")
    scanner = WiFiScanner(event_bus)
    # El scanner es el módulo que genera los eventos 'network_detected'
    # que desencadenan toda la cadena de procesamiento

    log.info("Inicializando analizador RF...")
    rf_analyzer = RFAnalyzer(event_bus)
    # El RF Analyzer escucha 'network_detected' y calcula estadísticas
    # de ocupación espectral y varianza de RSSI

    log.info("Inicializando módulo de captura de tráfico...")
    capture = HandshakeCapture(event_bus)
    # El módulo de captura está listo para recibir órdenes de captura
    # cuando el orquestador o el usuario seleccionen un objetivo

    log.info("Inicializando puente serial ESP32...")
    esp32 = ESP32Bridge(event_bus)
    # El puente serial se conecta al ESP32 (si está disponible)
    # y le retransmite los eventos relevantes por JSON/UART

    log.info("Inicializando generador de informes...")
    reporter = ReportGenerator(event_bus)
    # El reporter escucha todos los eventos y va acumulando
    # los datos para generar el informe final de la sesión

    # ── FASE 3: arrancar el escaneo ───────────────────────────────
    #
    # Llamamos a scanner.start() que:
    #   1. Activa el modo monitor en la interfaz Wi-Fi externa
    #   2. Lanza airodump-ng en segundo plano
    #   3. Comienza a leer y parsear los resultados del CSV
    #
    # A partir de este momento, el sistema opera de forma autónoma
    # mediante la cadena de eventos del EventBus.
    log.info("Arrancando escaneo de redes Wi-Fi...")
    scanner.start()

    log.info("Sistema en funcionamiento. Pulse Ctrl+C para detener.")

    # ── Bucle principal de espera ─────────────────────────────────
    #
    # El bucle while True mantiene vivo el proceso principal.
    # Todo el procesamiento real ocurre en los hilos internos
    # de cada módulo; este hilo solo espera.
    #
    # time.sleep(1) cede el control del procesador durante 1 segundo,
    # evitando que el bucle consuma CPU innecesariamente.
    while True:
        time.sleep(1)


# ── Punto de entrada estándar de Python ──────────────────────────
#
# La condición `if __name__ == "__main__"` asegura que main()
# solo se ejecute cuando este fichero se lanza directamente:
#   sudo python3 main.py   →  __name__ == '__main__'  →  ejecuta main()
#
# Si otro módulo importa main.py:
#   from main import algo  →  __name__ == 'main'      →  NO ejecuta main()
#
# Esto evita ejecuciones accidentales al importar el fichero.
if __name__ == "__main__":
    main()
