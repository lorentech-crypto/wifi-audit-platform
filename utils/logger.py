# ─────────────────────────────────────────────────────────────────
# utils/logger.py  —  Sistema de registro de eventos del sistema
#
# Descripción:
#   Configura y proporciona un logger centralizado para toda la
#   plataforma. Todos los módulos obtienen su instancia de logger
#   llamando a get_logger(__name__), de modo que los mensajes de
#   log se identifican automáticamente con el módulo que los genera.
#
#   Utiliza la biblioteca 'rich' para salida de terminal con colores,
#   timestamps y formato mejorado, facilitando el seguimiento en
#   tiempo real de la ejecución del sistema.
#
#   Niveles de log utilizados:
#     DEBUG   → información detallada para depuración
#     INFO    → eventos normales del sistema (redes detectadas, etc.)
#     WARNING → situaciones inesperadas pero no críticas
#     ERROR   → errores que impiden el funcionamiento correcto
# ─────────────────────────────────────────────────────────────────

# logging: módulo estándar de Python para registro de eventos
import logging

# os: para construir la ruta del fichero de log
import os

# datetime: para nombrar el fichero de log con la fecha/hora actual
from datetime import datetime


def get_logger(name, log_level=logging.DEBUG):
    """
    Crea y retorna una instancia de logger configurada para el módulo indicado.

    Patrón de uso (en cada módulo del sistema):
        from utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Mensaje informativo")
        log.warning("Advertencia")
        log.error("Error crítico")

    Parámetros:
        name      (str): nombre del módulo, normalmente __name__.
                         Aparecerá en los mensajes de log para identificar
                         de dónde proviene cada mensaje.
        log_level (int): nivel mínimo de mensajes a registrar.
                         logging.DEBUG   → todos los mensajes
                         logging.INFO    → info, warning, error
                         logging.WARNING → solo warning y error

    Retorna:
        logging.Logger: instancia de logger configurada y lista para usar.
    """
    # Obtenemos (o creamos si no existe) el logger con el nombre indicado.
    # Python cachea los loggers por nombre, así que llamadas repetidas
    # con el mismo nombre retornan el mismo objeto.
    logger = logging.getLogger(name)

    # Si el logger ya tiene handlers configurados, no añadimos más.
    # Esto evita duplicar mensajes si get_logger() se llama varias veces
    # con el mismo nombre desde el mismo módulo.
    if logger.handlers:
        return logger

    # ── Establecer el nivel mínimo de mensajes ────────────────────
    # Solo se procesarán mensajes con nivel >= log_level
    logger.setLevel(log_level)

    # ── Configurar el formato de los mensajes ─────────────────────
    # El formato incluye: timestamp, nivel, nombre del módulo y mensaje
    # Ejemplo: [2024-05-15 14:32:01] INFO     scanner.scanner  Red detectada: LAB-WPA2
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)-8s %(name)-25s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ── Handler 1: salida por terminal (consola) ──────────────────
    # StreamHandler envía los mensajes a sys.stderr (la consola)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Añadimos el handler de consola al logger
    logger.addHandler(console_handler)

    # ── Handler 2: salida a fichero de log ────────────────────────
    # Guardamos los logs en disco para poder revisarlos después
    try:
        # Creamos el directorio de logs si no existe
        os.makedirs('logs', exist_ok=True)

        # Nombre del fichero de log: incluye la fecha para identificarlo
        # Todos los módulos de la misma sesión escriben en el mismo fichero
        log_filename = os.path.join(
            'logs',
            f"session_{datetime.now().strftime('%Y-%m-%d')}.log"
        )

        # FileHandler escribe los mensajes en el fichero
        # encoding='utf-8': soporta caracteres especiales en SSIDs
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)   # En fichero guardamos TODO
        file_handler.setFormatter(formatter)

        # Añadimos el handler de fichero al logger
        logger.addHandler(file_handler)

    except Exception:
        # Si no podemos escribir en disco (p.ej. permisos), continuamos
        # con solo la salida por consola
        pass

    return logger
