# ─────────────────────────────────────────────────────────────────
# rf/channel_monitor.py  —  Monitorización de ocupación de canales Wi-Fi
#
# Descripción:
#   Mantiene un mapa actualizado de la ocupación de los canales Wi-Fi
#   y proporciona métricas para identificar los canales más saturados.
#
#   Canales Wi-Fi de referencia:
#     Banda 2.4 GHz: canales 1-14 (en Europa: 1-13)
#     No solapados (recomendados): 1, 6, 11
#     Banda 5 GHz: canales 36, 40, 44, 48, 52, 56, 60, 64...
# ─────────────────────────────────────────────────────────────────

# defaultdict: diccionario que crea automáticamente valores por defecto
from collections import defaultdict

# Importamos funciones estadísticas del módulo de estadística
from rf.statistics import calculate_mean_rssi, calculate_std_dev

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


class ChannelMonitor:
    """
    Monitoriza la ocupación de los canales Wi-Fi detectados.

    Mantiene un registro de cuántas redes hay en cada canal y
    sus valores RSSI, permitiendo identificar canales saturados
    y proporcionar recomendaciones de canal.
    """

    def __init__(self):
        """
        Constructor del monitor de canales.
        """
        # Diccionario de canales: {canal: {'count': N, 'rssi_list': [...]}}
        # defaultdict crea automáticamente la estructura al acceder a un canal nuevo
        self.channels = defaultdict(lambda: {'count': 0, 'rssi_list': []})

        # Umbral de ocupación para considerar un canal como saturado
        # (porcentaje del total de redes)
        self.saturation_threshold = 0.35   # 35%

    def register_network(self, channel, rssi):
        """
        Registra una red detectada en su canal correspondiente.

        Parámetros:
            channel (str|int): número del canal Wi-Fi.
            rssi    (int): potencia de señal de la red en dBm.
        """
        # Normalizamos el canal a cadena de texto para consistencia
        channel_key = str(channel).strip()

        # Solo procesamos canales válidos (no vacíos ni con caracteres extraños)
        if not channel_key or not channel_key.isdigit():
            return

        # Incrementamos el contador de redes en este canal
        self.channels[channel_key]['count'] += 1

        # Añadimos el RSSI a la lista del canal para estadísticas
        try:
            self.channels[channel_key]['rssi_list'].append(int(rssi))
        except (ValueError, TypeError):
            pass   # Ignoramos RSSI no numérico

    def get_channel_stats(self, channel):
        """
        Retorna las estadísticas de un canal concreto.

        Parámetros:
            channel (str|int): número de canal a consultar.

        Retorna:
            dict: estadísticas con claves 'count', 'mean_rssi',
                  'std_dev', 'occupancy'. None si el canal no existe.
        """
        channel_key = str(channel).strip()

        if channel_key not in self.channels:
            return None

        data        = self.channels[channel_key]
        rssi_list   = data['rssi_list']
        total_nets  = sum(ch['count'] for ch in self.channels.values())

        # Calculamos la ocupación relativa de este canal
        occupancy = data['count'] / max(total_nets, 1)

        return {
            'channel':    channel_key,
            'count':      data['count'],
            'mean_rssi':  calculate_mean_rssi(rssi_list) if rssi_list else 0,
            'std_dev':    calculate_std_dev(rssi_list)   if rssi_list else 0,
            'occupancy':  occupancy,
            'saturated':  occupancy > self.saturation_threshold
        }

    def get_all_channels(self):
        """
        Retorna las estadísticas de todos los canales detectados.

        Retorna:
            list[dict]: lista de estadísticas por canal, ordenada
                        por ocupación descendente (más saturado primero).
        """
        total_nets = sum(ch['count'] for ch in self.channels.values())

        stats = []
        for ch_key, data in self.channels.items():
            rssi_list = data['rssi_list']
            occupancy = data['count'] / max(total_nets, 1)

            stats.append({
                'channel':   ch_key,
                'count':     data['count'],
                'mean_rssi': calculate_mean_rssi(rssi_list) if rssi_list else 0,
                'std_dev':   calculate_std_dev(rssi_list)   if rssi_list else 0,
                'occupancy': occupancy,
                'saturated': occupancy > self.saturation_threshold
            })

        # Ordenamos por ocupación descendente (canal más ocupado primero)
        stats.sort(key=lambda x: x['occupancy'], reverse=True)

        return stats

    def get_least_congested_channel(self, band='2.4'):
        """
        Sugiere el canal menos congestionado para una banda dada.

        Parámetros:
            band (str): '2.4' para la banda de 2.4 GHz, '5' para 5 GHz.

        Retorna:
            str: número del canal recomendado, o 'N/A' si no hay datos.
        """
        # Canales no solapados recomendados para 2.4 GHz
        preferred_24 = ['1', '6', '11']

        # Canales UNII-1 para 5 GHz
        preferred_5  = ['36', '40', '44', '48']

        # Seleccionamos los canales preferidos según la banda
        preferred = preferred_24 if band == '2.4' else preferred_5

        # Entre los canales preferidos, buscamos el menos ocupado
        least_congested = None
        min_occupancy   = float('inf')

        total_nets = sum(ch['count'] for ch in self.channels.values())

        for ch in preferred:
            if ch in self.channels:
                occ = self.channels[ch]['count'] / max(total_nets, 1)
            else:
                # Canal no detectado → está completamente libre
                occ = 0.0

            if occ < min_occupancy:
                min_occupancy   = occ
                least_congested = ch

        return least_congested or 'N/A'
