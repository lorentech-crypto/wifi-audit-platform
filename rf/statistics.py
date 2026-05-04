# ─────────────────────────────────────────────────────────────────
# rf/statistics.py  —  Funciones matemáticas para el análisis RF
#
# Descripción:
#   Implementa las fórmulas estadísticas utilizadas por el RFAnalyzer
#   y el AnomalyDetector para caracterizar el estado del espectro.
#
#   Todas las funciones operan sobre listas de valores RSSI (dBm).
#   El RSSI (Received Signal Strength Indicator) es la potencia de
#   la señal recibida, expresada en dBm (decibelios sobre miliwatio).
#   Valores típicos: -30 dBm (señal excelente) a -90 dBm (muy débil).
# ─────────────────────────────────────────────────────────────────

# math: para la raíz cuadrada en el cálculo de desviación estándar
import math


def calculate_mean_rssi(values):
    """
    Calcula la potencia media de señal (RSSI medio) de un conjunto de muestras.

    Fórmula:
        RSSI_avg = (1/n) * Σ RSSI_i
        donde n = número de muestras

    Una media más cercana a 0 indica señal más fuerte.
    Una media muy negativa (p.ej. -80 dBm) indica señal débil o distante.

    Parámetros:
        values (list[int|float]): lista de valores RSSI en dBm.
                                  Los valores deben ser negativos típicamente.

    Retorna:
        float: RSSI medio en dBm. Retorna 0.0 si la lista está vacía.

    Ejemplo:
        calculate_mean_rssi([-42, -45, -40, -48])
        → -43.75
    """
    # Protección contra lista vacía: división por cero
    if not values:
        return 0.0

    # Calculamos la suma de todos los valores RSSI
    total = sum(values)

    # Dividimos entre el número de muestras para obtener la media aritmética
    mean = total / len(values)

    return mean


def calculate_variance(values):
    """
    Calcula la varianza de los valores RSSI respecto a su media.

    La varianza mide la dispersión de las muestras:
    - Varianza baja (< 10): señal estable, pocas fluctuaciones
    - Varianza alta (> 50): señal inestable, posible interferencia

    Fórmula (varianza poblacional):
        σ² = (1/n) * Σ (x_i - μ)²
        donde μ = media y x_i = cada muestra individual

    Nota: usamos la varianza POBLACIONAL (dividimos por n) porque
    estamos analizando TODAS las muestras capturadas (no una muestra
    representativa de una población mayor).

    Parámetros:
        values (list[int|float]): lista de valores RSSI en dBm.

    Retorna:
        float: varianza en dBm². Retorna 0.0 si hay menos de 2 muestras.

    Ejemplo:
        calculate_variance([-42, -45, -40, -48])
        → 8.1875  (dispersión moderada, señal razonablemente estable)
    """
    # Necesitamos al menos 2 muestras para que la varianza sea significativa.
    # Con una sola muestra, la varianza siempre sería 0 (nada que comparar).
    if len(values) < 2:
        return 0.0

    # Paso 1: calculamos la media de las muestras
    mean = calculate_mean_rssi(values)

    # Paso 2: calculamos la diferencia al cuadrado de cada muestra respecto a la media.
    # Usamos list comprehension para mayor claridad:
    # Para cada valor x_i, calculamos (x_i - μ)²
    squared_diffs = [(x - mean) ** 2 for x in values]

    # Paso 3: calculamos la media de los cuadrados de las diferencias
    # Esto es exactamente la definición de varianza poblacional
    variance = sum(squared_diffs) / len(values)

    return variance


def calculate_std_dev(values):
    """
    Calcula la desviación estándar de los valores RSSI.

    La desviación estándar σ es la raíz cuadrada de la varianza.
    Tiene la ventaja de estar en las mismas unidades que los datos (dBm),
    lo que facilita la interpretación:
    - σ < 3 dBm: señal muy estable
    - σ 3-10 dBm: fluctuaciones normales
    - σ > 10 dBm: inestabilidad significativa, posible interferencia

    Fórmula: σ = √σ² = √[ (1/n) * Σ (x_i - μ)² ]

    Parámetros:
        values (list[int|float]): lista de valores RSSI en dBm.

    Retorna:
        float: desviación estándar en dBm. Retorna 0.0 con < 2 muestras.

    Ejemplo:
        calculate_std_dev([-42, -45, -40, -48])
        → 2.86  (desviación estándar de ~3 dBm, señal bastante estable)
    """
    # Calculamos la varianza usando nuestra función anterior
    variance = calculate_variance(values)

    # La desviación estándar es la raíz cuadrada de la varianza.
    # math.sqrt() calcula la raíz cuadrada de un número flotante.
    return math.sqrt(variance)


def calculate_channel_occupancy(channel_networks, total_networks):
    """
    Calcula la ocupación relativa de un canal Wi-Fi.

    Mide qué fracción del total de redes detectadas está en un canal concreto.
    Un canal con muchas redes está más congestionado y tiene más interferencias.

    Fórmula:
        Occupancy = N_channel / N_total

    Parámetros:
        channel_networks (int): número de redes en el canal a analizar.
        total_networks   (int): número total de redes detectadas.

    Retorna:
        float: ocupación entre 0.0 (canal vacío) y 1.0 (todo en ese canal).
               Retorna 0.0 si total_networks es 0.

    Ejemplo:
        calculate_channel_occupancy(8, 20)
        → 0.4  (el 40% de las redes están en este canal → alta ocupación)
    """
    # Protección contra división por cero si no hay redes detectadas
    if total_networks == 0:
        return 0.0

    # Calculamos la fracción de redes en este canal
    occupancy = channel_networks / total_networks

    return occupancy


def is_anomaly(rssi, mean, std_dev, k=2.0):
    """
    Determina si un valor RSSI es estadísticamente anómalo.

    Aplica el criterio de detección de outliers basado en desviaciones
    estándar respecto a la media:

        |RSSI_i - μ| > k * σ

    Si la distancia de la muestra a la media supera k desviaciones
    estándar, la muestra se considera anómala (outlier estadístico).

    Parámetros:
        rssi    (float): valor RSSI de la muestra a evaluar (en dBm).
        mean    (float): RSSI medio del historial.
        std_dev (float): desviación estándar del historial.
        k       (float): factor multiplicador del umbral.
                         k=2 → ~95% de valores normales dentro del umbral
                         k=3 → ~99.7% (más conservador, menos falsos positivos)

    Retorna:
        bool: True si el valor es anómalo, False si es normal.

    Ejemplo:
        is_anomaly(-80, -45, 5.0, k=2)
        → True  (|-80 - (-45)| = 35 > 2*5 = 10 → anómalo)
    """
    # Si la desviación estándar es 0 (todas las muestras iguales),
    # no hay forma de detectar anomalías por definición
    if std_dev == 0:
        return False

    # Calculamos la desviación absoluta de la muestra respecto a la media
    deviation = abs(rssi - mean)

    # Calculamos el umbral dinámico: k multiplicado por la desviación estándar
    threshold = k * std_dev

    # La muestra es anómala si su desviación supera el umbral
    return deviation > threshold
