# ─────────────────────────────────────────────────────────────────
# core/orchestrator.py  —  Coordinador central del sistema
#
# Descripción:
#   El Orquestador actúa como director de la plataforma: conoce
#   todos los módulos, coordina su inicialización y proporciona
#   una API de alto nivel para controlar la auditoría.
#
#   Mientras main.py es el punto de entrada (arranque del proceso),
#   el Orquestador es el cerebro que conecta todos los módulos
#   y decide qué hacer con los eventos que llegan del EventBus.
#
#   Responsabilidades:
#     - Verificar prerrequisitos del sistema (root, aircrack-ng)
#     - Inicializar todos los módulos en el orden correcto
#     - Gestionar el ciclo de vida de la sesión de auditoría
#     - Ofrecer métodos de control de alto nivel (start_capture, etc.)
# ─────────────────────────────────────────────────────────────────

# Importamos todos los módulos del sistema
from core.event_bus     import EventBus
from core.session_manager import SessionManager
from scanner.scanner    import WiFiScanner
from capture.handshake_capture import HandshakeCapture
from rf.rf_analyzer     import RFAnalyzer
from esp32.serial_bridge import ESP32Bridge
from reporting.report_generator import ReportGenerator
from config.config      import Config
from utils.logger       import get_logger
from utils.network_utils import is_root, check_aircrack_suite

# Logger para este módulo
log = get_logger(__name__)


class Orchestrator:
    """
    Coordinador central de la plataforma de auditoría Wi-Fi.

    Gestiona el ciclo de vida completo de una sesión de auditoría:
    desde la verificación de prerrequisitos hasta la generación
    del informe final al cerrar la sesión.
    """

    def __init__(self):
        """
        Constructor del orquestador.
        Verifica prerrequisitos y crea el bus de eventos.
        Los módulos se inicializan en setup().
        """
        # Verificamos que el sistema cumple los requisitos mínimos
        self._check_prerequisites()

        # Creamos el bus de eventos central. Es el primero en crearse
        # porque todos los módulos lo necesitan en su constructor.
        self.event_bus = EventBus()

        # Gestor de sesiones: crea el directorio de trabajo con timestamp
        self.session = SessionManager(Config.SESSIONS_DIR)

        # Referencias a los módulos (se inicializan en setup())
        self.scanner  = None
        self.capture  = None
        self.rf       = None
        self.esp32    = None
        self.reporter = None

        # Flag de estado del sistema
        self.running = False

        log.info("Orquestador creado. Llama a setup() para inicializar módulos.")

    def _check_prerequisites(self):
        """
        Verifica que el entorno cumple los requisitos para ejecutar la plataforma.

        Comprueba:
          1. Permisos de root (necesario para el modo monitor)
          2. Disponibilidad de las herramientas de Aircrack-ng
        """
        # ── Verificación 1: permisos de root ─────────────────────
        if not is_root():
            log.error("La plataforma requiere permisos de root.")
            log.error("Ejecuta con: sudo python3 main.py")
            raise PermissionError("Se requieren privilegios de root.")

        log.info("✓ Ejecutando como root.")

        # ── Verificación 2: suite Aircrack-ng ────────────────────
        tools = check_aircrack_suite()
        missing = [t for t, available in tools.items() if not available]

        if missing:
            log.error(f"Herramientas no encontradas: {', '.join(missing)}")
            log.error("Instala con: sudo apt install aircrack-ng")
            raise EnvironmentError(f"Faltan herramientas: {missing}")

        log.info("✓ Suite Aircrack-ng disponible.")

    def setup(self):
        """
        Inicializa todos los módulos del sistema.

        Orden de inicialización (importante):
          1. EventBus (ya creado en __init__)
          2. Módulos que solo escuchan: RFAnalyzer, Reporter, ESP32Bridge
          3. Módulos de captura: HandshakeCapture
          4. Módulo de escaneo: WiFiScanner (el último, porque emite eventos)
        """
        log.info("Inicializando módulos del sistema...")

        # ── RF Analyzer: se suscribe a 'network_detected' ────────
        # Se inicializa antes del scanner porque necesita estar
        # suscrito antes de que empiecen a llegar eventos
        self.rf = RFAnalyzer(
            self.event_bus,
            analysis_interval=Config.RF_ANALYSIS_INTERVAL
        )
        log.info("✓ RF Analyzer inicializado.")

        # ── Reporter: se suscribe a múltiples eventos ────────────
        self.reporter = ReportGenerator(self.event_bus)
        log.info("✓ Reporter inicializado.")

        # ── ESP32 Bridge: conexión serie (opcional) ───────────────
        self.esp32 = ESP32Bridge(
            self.event_bus,
            port=Config.ESP32_SERIAL_PORT,
            baud=Config.ESP32_BAUD_RATE
        )
        log.info("✓ ESP32 Bridge inicializado.")

        # ── Handshake Capture: listo para recibir órdenes ─────────
        self.capture = HandshakeCapture(self.event_bus)
        log.info("✓ HandshakeCapture inicializado.")

        # ── Scanner: el último en inicializarse ───────────────────
        # Al llamar a start() comenzará a emitir eventos que los
        # módulos anteriores ya están listos para procesar
        self.scanner = WiFiScanner(self.event_bus)
        log.info("✓ Scanner inicializado.")

        log.info("Todos los módulos listos.")
        return self

    def start(self):
        """
        Arranca la sesión de auditoría: activa el modo monitor y el escaneo.
        """
        if not self.scanner:
            raise RuntimeError("Llama a setup() antes de start().")

        log.info(f"Iniciando sesión: {self.session.get_session_name()}")
        self.running = True

        # Arrancamos el escáner: activa modo monitor + lanza airodump-ng
        self.scanner.start()
        log.info("Sesión de auditoría en curso.")

    def start_capture(self, bssid, channel, ssid='unknown'):
        """
        Inicia una captura focalizada sobre un AP concreto.

        Parámetros:
            bssid   (str): MAC del punto de acceso objetivo.
            channel (int|str): canal Wi-Fi del AP.
            ssid    (str): nombre de la red (para nombrar ficheros).
        """
        if not self.capture:
            log.error("El módulo de captura no está inicializado.")
            return

        self.capture.capture(bssid, channel, ssid)

    def stop(self):
        """
        Detiene la sesión de auditoría y genera el informe final.
        """
        log.info("Deteniendo sesión de auditoría...")
        self.running = False

        # Detenemos todas las capturas activas
        if self.capture:
            self.capture.stop_all()

        # Detenemos el escáner
        if self.scanner:
            self.scanner.stop()

        # Generamos el informe final de la sesión
        if self.reporter:
            self.reporter.export_all(self.session.get_session_path())

        # Cerramos la conexión serie con el ESP32
        if self.esp32:
            self.esp32.close()

        log.info("Sesión finalizada.")
