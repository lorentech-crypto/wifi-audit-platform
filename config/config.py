# ─────────────────────────────────────────────────────────────────
# config/config.py  —  Parámetros globales configurables del sistema
#
# Descripción:
#   Centraliza toda la configuración de la plataforma en un único
#   fichero. Modificar aquí los valores afecta al comportamiento
#   global sin tener que tocar el código de cada módulo.
#
#   Uso en otros módulos:
#     from config.config import Config
#     interfaz = Config.MONITOR_INTERFACE
# ─────────────────────────────────────────────────────────────────


class Config:
    """
    Clase de configuración global del sistema.

    Todos los atributos son variables de clase (no de instancia),
    lo que significa que se accede a ellos directamente sobre la clase:
        Config.MONITOR_INTERFACE   ← correcto
        Config().MONITOR_INTERFACE ← innecesario (también funciona)
    """

    # ── Interfaces de red ────────────────────────────────────────

    # Interfaz Wi-Fi física externa (adaptador Alfa AWUS036ACH)
    # La interna de la RPi (wlan0) se reserva para gestión/SSH
    PHYSICAL_INTERFACE = 'wlan1'

    # Nombre de la interfaz tras activar el modo monitor con airmon-ng
    # airmon-ng añade el sufijo 'mon' por convención
    MONITOR_INTERFACE = 'wlan1mon'

    # ── Puerto serie para comunicación con ESP32 ─────────────────

    # Puerto USB-UART donde está conectado el ESP32 en Linux
    # Si hay varios dispositivos USB-UART, puede ser ttyUSB1, ttyUSB2...
    ESP32_SERIAL_PORT = '/dev/ttyUSB0'

    # Velocidad de comunicación serie en baudios
    # Debe coincidir EXACTAMENTE con la del firmware del ESP32
    ESP32_BAUD_RATE = 115200

    # ── Directorios del sistema ──────────────────────────────────

    # Directorio base para almacenar las capturas de cada sesión
    SESSIONS_DIR = 'sessions'

    # Directorio para los ficheros de log del sistema
    LOGS_DIR = 'logs'

    # ── Parámetros del módulo Scanner ────────────────────────────

    # Segundos entre ciclos de lectura del CSV de airodump-ng
    # Valor más bajo → mayor reactividad pero más carga de CPU
    SCAN_INTERVAL = 5

    # ── Parámetros del módulo RF Analyzer ───────────────────────

    # Segundos entre análisis estadísticos periódicos del espectro
    RF_ANALYSIS_INTERVAL = 10

    # Porcentaje de ocupación de canal a partir del cual se considera saturado
    # 0.30 significa: si más del 30% de las redes están en un canal → saturado
    CHANNEL_SATURATION_THRESHOLD = 0.30

    # ── Parámetros del detector de anomalías ────────────────────

    # Factor k del criterio de detección: |RSSI - μ| > k * σ
    # k=2.0 → detecta outliers a más de 2 desviaciones estándar (~95% CI)
    # k=3.0 → más conservador, menos falsos positivos (~99.7% CI)
    ANOMALY_THRESHOLD_K = 2.0

    # Número mínimo de muestras antes de activar la detección de anomalías
    ANOMALY_MIN_SAMPLES = 10

    # Tamaño de la ventana deslizante de muestras históricas
    ANOMALY_WINDOW_SIZE = 100

    # ── Parámetros del módulo Capture ───────────────────────────

    # Tiempo máximo en segundos esperando un handshake antes de rendirse
    HANDSHAKE_TIMEOUT = 120

    # Intervalo en segundos entre verificaciones del PCAP en busca de handshake
    HANDSHAKE_CHECK_INTERVAL = 3

    # ── Parámetros de desautenticación ──────────────────────────

    # Número de tramas de desautenticación a enviar por ráfaga
    # 5 suele ser suficiente; valores muy altos causan cortes prolongados
    DEAUTH_COUNT = 5

    # ── Parámetros del Reporter ──────────────────────────────────

    # Formatos de exportación del informe final de sesión
    # Valores disponibles: 'json', 'csv', 'html'
    REPORT_FORMATS = ['json', 'html']
