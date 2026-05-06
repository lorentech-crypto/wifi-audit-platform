# ─────────────────────────────────────────────────────────────────
# rf/anomaly_detector.py  —  Detector estadístico de anomalías RF
#
# Descripción:
#   Identifica valores RSSI estadísticamente anómalos usando el
#   criterio de desviación estándar:  |RSSI_i - μ| > k * σ
#
#   El detector aprende el comportamiento "normal" del entorno
#   acumulando muestras históricas. Una vez que tiene suficientes
#   muestras (min_samples), compara cada nueva lectura con el
#   comportamiento esperado y señala las desviaciones significativas.
#
#   Limitación importante:
#   Este detector NO puede identificar con certeza ataques de jamming
#   deliberado. Solo detecta patrones estadísticos anómalos que
#   PUEDEN indicar interferencias, saturación o jamming. Para una
#   detección precisa se necesitaría hardware SDR especializado.
# ─────────────────────────────────────────────────────────────────

# statistics: módulo estándar de Python para cálculos estadísticos
# Usamos statistics.mean y statistics.stdev para mayor robustez
import statistics

# collections.deque: lista circular de tamaño fijo.
# Más eficiente que una lista normal para acumular muestras históricas
# porque elimina automáticamente las muestras más antiguas.
from collections import deque  # ventana deslizante O(1) para append/pop

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class AnomalyDetector:
    """
    Detector de anomalías espectrales basado en estadística descriptiva.

    Mantiene una ventana deslizante de muestras RSSI históricas y
    detecta valores que se alejan significativamente del comportamiento
    estadístico del entorno analizado.
    """

    def __init__(self, threshold_k=2.0, min_samples=10, window_size=100):
        """
        Constructor del detector de anomalías.

        Parámetros:
            threshold_k  (float): factor k del criterio de detección.
                                  |RSSI - μ| > k * σ
                                  k=2.0 → ~95% de valores normales dentro
                                  k=3.0 → ~99.7% (más conservador)
            min_samples  (int):   mínimo de muestras antes de detectar.
                                  Con menos muestras, la estadística no es
                                  representativa del entorno.
            window_size  (int):   tamaño máximo de la ventana histórica.
                                  Las muestras más antiguas se descartan.
                                  Un tamaño de 100 cubre ~8 minutos con
                                  muestras cada 5 segundos.
        """
        # Factor multiplicador para el umbral de detección
        self.threshold_k = threshold_k

        # Número mínimo de muestras antes de activar la detección
        self.min_samples = min_samples

        # Ventana deslizante de muestras RSSI.
        # deque con maxlen descarta automáticamente los elementos más viejos
        # cuando la cola está llena, como una ventana deslizante.
        self.window = deque(maxlen=window_size)

        # Contador total de muestras procesadas (no solo las en ventana)
        self.total_processed = 0

        # Contador de anomalías detectadas en la sesión
        self.anomaly_count = 0

        log.debug(
            f"AnomalyDetector creado: k={threshold_k}, "
            f"min_samples={min_samples}, window={window_size}"
        )

    def process(self, rssi):
        """
        Procesa una nueva muestra RSSI y determina si es anómala.

        Actualiza la ventana histórica y aplica el criterio estadístico
        para determinar si la muestra es un outlier significativo.

        Parámetros:
            rssi (int|float): valor RSSI en dBm de la muestra actual.
                              Típicamente un valor negativo (-30 a -100 dBm).

        Retorna:
            bool: True si la muestra es potencialmente anómala,
                  False si está dentro del comportamiento normal.
        """
        # Añadimos la nueva muestra a la ventana histórica.
        # Si la ventana está llena, deque elimina automáticamente
        # la muestra más antigua (sliding window).
        self.window.append(rssi)

        # Incrementamos el contador total de muestras procesadas
        self.total_processed += 1

        # ── Verificación de suficiencia estadística ───────────────
        # Con menos de min_samples, la media y desviación estándar
        # no son representativas del entorno: esperamos más datos.
        if len(self.window) < self.min_samples:
            log.debug(
                f"Acumulando muestras: {len(self.window)}/{self.min_samples}"
            )
            return False   # Aún no podemos detectar anomalías con fiabilidad

        # ── Cálculo de estadísticas del historial ─────────────────

        # Convertimos la deque a lista para los cálculos del módulo statistics
        sample_list = list(self.window)

        # Media aritmética de todas las muestras en la ventana
        mean = statistics.mean(sample_list)

        # Desviación estándar MUESTRAL (statistics.stdev divide por n-1)
        # Usamos la muestral porque nuestra ventana es una muestra
        # del comportamiento real del entorno (no toda la población)
        std_dev = statistics.stdev(sample_list)

        # ── Aplicación del criterio de anomalía ───────────────────
        #
        # Un valor es anómalo si su distancia a la media es mayor que
        # k veces la desviación estándar:
        #
        #   |rssi - μ| > k * σ
        #
        # Ejemplo con k=2.0:
        #   Si μ = -45 dBm y σ = 5 dBm → umbral = 10 dBm
        #   Un valor de -80 dBm: |(-80) - (-45)| = 35 > 10 → ANÓMALO
        #   Un valor de -48 dBm: |(-48) - (-45)| = 3 < 10  → normal

        # Calculamos cuánto se aleja esta muestra de la media
        deviation = abs(rssi - mean)

        # Calculamos el umbral dinámico (se adapta al entorno)
        # Protegemos contra std_dev=0 (todas las muestras idénticas)
        if std_dev == 0:
            return False   # Sin variación, cualquier valor es "normal"

        threshold = self.threshold_k * std_dev

        # Evaluamos si la muestra supera el umbral de anomalía
        is_anomalous = deviation > threshold

        if is_anomalous:
            # Incrementamos el contador de anomalías detectadas
            self.anomaly_count += 1

            log.warning(
                f"Anomalía detectada #{self.anomaly_count}: "
                f"RSSI={rssi:.0f} dBm | "
                f"μ={mean:.1f} | σ={std_dev:.1f} | "
                f"desv={deviation:.1f} > umbral={threshold:.1f}"
            )

        return is_anomalous

    def get_stats(self):
        """
        Retorna las estadísticas actuales del detector.

        Útil para el módulo Reporter al generar el informe de sesión.

        Retorna:
            dict: estadísticas con claves 'samples', 'mean', 'std_dev',
                  'threshold', 'anomaly_count'.
        """
        # Si no tenemos suficientes muestras, retornamos valores vacíos
        if len(self.window) < self.min_samples:
            return {
                'samples':      len(self.window),
                'mean':         None,
                'std_dev':      None,
                'threshold':    None,
                'anomaly_count': self.anomaly_count
            }

        sample_list = list(self.window)
        mean    = statistics.mean(sample_list)
        std_dev = statistics.stdev(sample_list) if len(sample_list) > 1 else 0

        return {
            'samples':       len(self.window),
            'mean':          round(mean, 2),
            'std_dev':       round(std_dev, 2),
            'threshold':     round(self.threshold_k * std_dev, 2),
            'anomaly_count': self.anomaly_count
        }

    def reset(self):
        """Reinicia el detector: borra el historial y los contadores."""
        self.window.clear()
        self.total_processed = 0
        self.anomaly_count   = 0
        log.info("AnomalyDetector reiniciado.")

# ─────────────────────────────────────────────────────────────────
# Resultados experimentales (añadido tras pruebas en laboratorio)
# Entorno: Kali Linux 2024.1 / Raspberry Pi 4 / Alfa AWUS036ACH
# Red de prueba: LAB-WPA2 (canal 6, RSSI medio -42 dBm)
# Varianza típica observada: 8-12 dBm²
# Con k=2.0: umbral = 2 * sqrt(10) ≈ 6.3 dBm
# ─────────────────────────────────────────────────────────────────
