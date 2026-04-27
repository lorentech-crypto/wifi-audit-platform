# ─────────────────────────────────────────────────────────────────
# core/session_manager.py  —  Gestión del ciclo de vida de sesiones
#
# Descripción:
#   Gestiona la creación y organización de las sesiones de auditoría.
#   Cada vez que se lanza la plataforma, se crea una sesión nueva
#   con su propio directorio de trabajo, nombrado con la fecha y hora.
#   Todos los ficheros generados durante la sesión (capturas PCAP,
#   CSVs, informes) se guardan dentro de ese directorio.
# ─────────────────────────────────────────────────────────────────

# os: para crear directorios y construir rutas de ficheros
import os

# datetime: para generar nombres de sesión basados en fecha y hora
from datetime import datetime

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger específico para este módulo
log = get_logger(__name__)


class SessionManager:
    """
    Gestiona el ciclo de vida de una sesión de auditoría.

    Una sesión es la unidad de trabajo de la plataforma: agrupa
    todos los ficheros generados durante una ejecución concreta.

    Ejemplo de estructura de directorios generada:
        sessions/
        └── 2024-05-15_14-30-22/
            ├── scan-01.csv          ← salida de airodump-ng
            ├── handshake_AABBCC.cap ← captura PCAP
            └── report.json          ← informe de la sesión
    """

    def __init__(self, base_dir='sessions'):
        """
        Constructor del gestor de sesiones.

        Parámetros:
            base_dir (str): directorio base donde se crearán las sesiones.
                            Por defecto es 'sessions/' relativo al CWD.
        """
        # Directorio base donde se almacenarán todas las sesiones
        self.base_dir = base_dir

        # Nombre de la sesión actual, generado a partir de la fecha/hora
        # Formato: YYYY-MM-DD_HH-MM-SS  (compatible con sistemas de ficheros)
        self.session_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # Ruta completa del directorio de la sesión actual
        # Ejemplo: 'sessions/2024-05-15_14-30-22'
        self.session_dir = os.path.join(self.base_dir, self.session_name)

        # Creamos el directorio de la sesión al instanciar el manager
        self._create_session_dir()

    def _create_session_dir(self):
        """
        Crea el directorio de la sesión actual en el sistema de ficheros.

        El flag exist_ok=True evita errores si el directorio ya existe
        (aunque con nombres basados en timestamps esto no debería ocurrir).
        """
        # os.makedirs crea la ruta completa, incluyendo directorios intermedios
        # exist_ok=True: no lanza error si el directorio ya existe
        os.makedirs(self.session_dir, exist_ok=True)

        log.info(f"Sesión iniciada: {self.session_name}")
        log.info(f"Directorio de trabajo: {self.session_dir}")

    def get_session_path(self, filename=''):
        """
        Construye la ruta completa de un fichero dentro de la sesión actual.

        Parámetros:
            filename (str): nombre del fichero (opcional).
                            Si está vacío, retorna el directorio de sesión.

        Retorna:
            str: ruta completa del fichero o directorio.

        Ejemplo:
            manager.get_session_path('scan')
            → 'sessions/2024-05-15_14-30-22/scan'
        """
        # Construimos la ruta uniendo el directorio de sesión con el fichero
        return os.path.join(self.session_dir, filename)

    def get_session_name(self):
        """
        Retorna el nombre identificador de la sesión actual.

        Retorna:
            str: nombre de la sesión (p.ej. '2024-05-15_14-30-22').
        """
        return self.session_name

    def list_sessions(self):
        """
        Lista todas las sesiones de auditoría almacenadas.

        Retorna:
            list[str]: lista de nombres de sesiones ordenada cronológicamente.
        """
        try:
            # Listamos los subdirectorios del directorio base
            # sorted() los ordena alfabéticamente (que es cronológico con el formato de fecha)
            sessions = sorted([
                d for d in os.listdir(self.base_dir)
                if os.path.isdir(os.path.join(self.base_dir, d))
            ])
            return sessions

        except FileNotFoundError:
            # Si el directorio base no existe, retornamos lista vacía
            log.warning(f"Directorio base '{self.base_dir}' no encontrado.")
            return []
