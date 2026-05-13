# ─────────────────────────────────────────────────────────────────
# reporting/json_exporter.py  —  Exportación de informes a JSON
#
# Descripción:
#   Serializa el resumen de la sesión a un fichero JSON bien formateado.
#   JSON es el formato principal porque es legible por humanos,
#   fácilmente importable en herramientas externas y compatible
#   con APIs web para futuras integraciones.
# ─────────────────────────────────────────────────────────────────

# json: módulo estándar para serialización JSON
import json

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def export_to_json(data, filepath):
    """
    Guarda el diccionario de datos en un fichero JSON formateado.

    Parámetros:
        data     (dict): datos a serializar. Normalmente el resumen
                         completo de la sesión generado por ReportGenerator.
        filepath (str):  ruta completa del fichero de salida.
                         Ejemplo: 'sessions/2024-05-15_14-30-22/report.json'

    Retorna:
        bool: True si la exportación fue exitosa, False si hubo error.
    """
    try:
        # Abrimos el fichero en modo escritura con codificación UTF-8.
        # UTF-8 es necesario para SSIDs con caracteres no ASCII (acentos, emojis, etc.)
        with open(filepath, 'w', encoding='utf-8') as f:

            # json.dump() serializa el diccionario Python a JSON en el fichero.
            # indent=4: formatea el JSON con 4 espacios de sangría para legibilidad.
            # ensure_ascii=False: permite caracteres UTF-8 en el JSON
            #   (sin esto, los caracteres no-ASCII se escaparían como \uXXXX)
            # sort_keys=True: ordena las claves alfabéticamente para consistencia
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False,
                sort_keys=True
            )

        log.debug(f"JSON exportado correctamente: {filepath}")
        return True

    except PermissionError:
        # No tenemos permisos de escritura en ese directorio
        log.error(f"Sin permisos para escribir en: {filepath}")
        return False

    except TypeError as e:
        # El diccionario contiene un tipo de dato no serializable por JSON
        # (p.ej. objetos Python, bytes, sets...)
        log.error(f"Datos no serializables a JSON: {e}")
        return False

    except Exception as e:
        log.error(f"Error exportando JSON: {e}")
        return False


def load_from_json(filepath):
    """
    Carga un informe JSON previamente guardado.

    Útil para analizar informes de sesiones anteriores o
    para pruebas unitarias del sistema de reporting.

    Parámetros:
        filepath (str): ruta al fichero JSON a cargar.

    Retorna:
        dict: datos del informe, o None si hay error.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # json.load() deserializa el JSON y retorna un diccionario Python
            data = json.load(f)

        log.debug(f"JSON cargado correctamente: {filepath}")
        return data

    except FileNotFoundError:
        log.error(f"Fichero no encontrado: {filepath}")
        return None

    except json.JSONDecodeError as e:
        # El fichero existe pero no es JSON válido (corrupto o incompleto)
        log.error(f"Error parseando JSON en {filepath}: {e}")
        return None

    except Exception as e:
        log.error(f"Error cargando JSON: {e}")
        return None
