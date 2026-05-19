# ─────────────────────────────────────────────────────────────────
# reporting/html_exporter.py  —  Exportación de informes a HTML
#
# Descripción:
#   Genera un informe HTML navegable con los resultados de la sesión.
#   El HTML incluye tablas con las redes detectadas, handshakes
#   capturados y anomalías RF, con estilos CSS básicos.
# ─────────────────────────────────────────────────────────────────

# Importamos el logger del sistema
from utils.logger import get_logger

# Logger para este módulo
log = get_logger(__name__)


def export_to_html(data, filepath):
    """
    Genera un fichero HTML con el informe completo de la sesión.

    Parámetros:
        data     (dict): resumen de la sesión (del ReportGenerator).
        filepath (str):  ruta del fichero HTML de salida.

    Retorna:
        bool: True si la exportación fue exitosa, False si hubo error.
    """
    try:
        # Extraemos los datos principales del resumen
        networks     = data.get('networks', [])
        handshakes   = data.get('handshakes', [])
        anomalies    = data.get('rf_anomalies', [])
        session_start = data.get('session_start', 'N/A')
        session_end   = data.get('session_end',   'N/A')

        # ── Generamos el HTML sección a sección ───────────────────
        html_parts = []

        # Cabecera HTML con estilos CSS básicos
        html_parts.append(_html_header())

        # Sección de resumen general
        html_parts.append(_section_summary(
            len(networks), len(handshakes), len(anomalies),
            session_start, session_end
        ))

        # Tabla de redes detectadas
        html_parts.append(_section_networks(networks))

        # Tabla de handshakes capturados
        html_parts.append(_section_handshakes(handshakes))

        # Tabla de anomalías RF
        html_parts.append(_section_anomalies(anomalies))

        # Pie de página HTML
        html_parts.append(_html_footer())

        # Unimos todas las partes y escribimos el fichero
        html_content = '\n'.join(html_parts)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        log.debug(f"HTML exportado correctamente: {filepath}")
        return True

    except Exception as e:
        log.error(f"Error exportando HTML: {e}")
        return False


def _html_header():
    """Retorna la cabecera HTML con estilos CSS."""
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe de Auditoría Wi-Fi</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; background: #f5f5f5; }
        h1   { color: #1F3864; border-bottom: 3px solid #2E74B5; padding-bottom: 0.3em; }
        h2   { color: #2E74B5; margin-top: 2em; }
        table { border-collapse: collapse; width: 100%; background: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2em; }
        th   { background: #1F3864; color: white; padding: 10px; text-align: left; }
        td   { padding: 8px 10px; border-bottom: 1px solid #ddd; }
        tr:hover td { background: #EBF5FB; }
        .badge-wpa2 { background:#27ae60; color:white; padding:2px 8px;
                      border-radius:10px; font-size:0.85em; }
        .badge-wpa3 { background:#2980b9; color:white; padding:2px 8px;
                      border-radius:10px; font-size:0.85em; }
        .badge-wep  { background:#c0392b; color:white; padding:2px 8px;
                      border-radius:10px; font-size:0.85em; }
        .badge-open { background:#e67e22; color:white; padding:2px 8px;
                      border-radius:10px; font-size:0.85em; }
        .summary-grid { display:grid; grid-template-columns:repeat(4,1fr);
                        gap:1em; margin:1em 0 2em; }
        .summary-card { background:white; padding:1.5em; text-align:center;
                        border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); }
        .summary-card .num { font-size:2.5em; font-weight:bold; color:#1F3864; }
        .summary-card .lbl { color:#666; font-size:0.9em; }
    </style>
</head>
<body>
<h1>📡 Informe de Auditoría Wi-Fi</h1>
<p><em>Generado automáticamente por la plataforma de auditoría Wi-Fi sobre Raspberry Pi 4</em></p>"""


def _section_summary(n_nets, n_hands, n_anom, start, end):
    """Retorna la sección HTML de resumen con tarjetas de estadísticas."""
    return f"""
<h2>Resumen de la Sesión</h2>
<p><strong>Inicio:</strong> {start} &nbsp;|&nbsp; <strong>Fin:</strong> {end}</p>
<div class="summary-grid">
  <div class="summary-card"><div class="num">{n_nets}</div>
    <div class="lbl">Redes detectadas</div></div>
  <div class="summary-card"><div class="num">{n_hands}</div>
    <div class="lbl">Handshakes capturados</div></div>
  <div class="summary-card"><div class="num">{n_anom}</div>
    <div class="lbl">Anomalías RF</div></div>
  <div class="summary-card"><div class="num">{'✓' if n_hands > 0 else '—'}</div>
    <div class="lbl">Estado auditoría</div></div>
</div>"""


def _section_networks(networks):
    """Retorna la tabla HTML de redes detectadas."""
    rows = ''
    for net in networks:
        enc   = net.get('encryption', '')
        badge = f'<span class="badge-{enc.lower()[:4]}">{enc}</span>' \
                if enc else '—'
        rows += f"""<tr>
            <td>{net.get('ssid','—')}</td>
            <td><code>{net.get('bssid','—')}</code></td>
            <td>{net.get('channel','—')}</td>
            <td>{net.get('power','—')} dBm</td>
            <td>{badge}</td>
            <td>{net.get('timestamp','—')}</td>
        </tr>"""

    return f"""
<h2>Redes Detectadas ({len(networks)})</h2>
<table>
  <tr><th>SSID</th><th>BSSID</th><th>Canal</th><th>RSSI</th>
      <th>Cifrado</th><th>Timestamp</th></tr>
  {rows if rows else '<tr><td colspan="6">Sin datos</td></tr>'}
</table>"""


def _section_handshakes(handshakes):
    """Retorna la tabla HTML de handshakes capturados."""
    rows = ''
    for hs in handshakes:
        rows += f"""<tr>
            <td>{hs.get('ssid','—')}</td>
            <td><code>{hs.get('bssid','—')}</code></td>
            <td><code>{hs.get('pcap','—')}</code></td>
            <td>{hs.get('timestamp','—')}</td>
        </tr>"""

    return f"""
<h2>Handshakes WPA/WPA2 Capturados ({len(handshakes)})</h2>
<table>
  <tr><th>SSID</th><th>BSSID</th><th>Fichero PCAP</th><th>Timestamp</th></tr>
  {rows if rows else '<tr><td colspan="4">Ningún handshake capturado</td></tr>'}
</table>"""


def _section_anomalies(anomalies):
    """Retorna la tabla HTML de anomalías RF."""
    rows = ''
    for an in anomalies:
        rows += f"""<tr>
            <td>{an.get('channel','—')}</td>
            <td>{an.get('rssi','—')} dBm</td>
            <td>{an.get('reason','—')}</td>
            <td>{an.get('timestamp','—')}</td>
        </tr>"""

    return f"""
<h2>Anomalías RF Detectadas ({len(anomalies)})</h2>
<table>
  <tr><th>Canal</th><th>RSSI</th><th>Motivo</th><th>Timestamp</th></tr>
  {rows if rows else '<tr><td colspan="4">Sin anomalías detectadas</td></tr>'}
</table>"""


def _html_footer():
    # Mejorado tras revisión del tutor: añadido aviso ético en el pie de página
    """Retorna el pie de página HTML."""
    return """
<hr>
<p style="color:#888; font-size:0.85em;">
  Informe generado por la plataforma de auditoría Wi-Fi.
  ⚠️ Uso exclusivamente ético y autorizado sobre redes propias o con permiso expreso.
</p>
</body>
</html>"""
