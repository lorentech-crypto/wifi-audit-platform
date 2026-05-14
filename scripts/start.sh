#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# scripts/start.sh  —  Script de arranque de la plataforma
#
# Descripción:
#   Automatiza el proceso de arranque completo:
#     1. Verifica que se ejecuta como root
#     2. Activa el modo monitor en la interfaz Wi-Fi externa
#     3. Lanza la plataforma Python
#
# Uso:
#   chmod +x scripts/start.sh
#   sudo ./scripts/start.sh
# ─────────────────────────────────────────────────────────────────

# ── Colores para mensajes en terminal ────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'   # Sin color (reset)

# Función auxiliar para imprimir mensajes con color
info()    { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[-]${NC} $1"; exit 1; }

# ── Verificación 1: permisos de root ─────────────────────────────
# $EUID es el UID efectivo del usuario que ejecuta el script.
# 0 = root. Si no es root, detenemos la ejecución con error.
if [ "$EUID" -ne 0 ]; then
    error "Este script debe ejecutarse como root: sudo ./scripts/start.sh"
fi

info "Plataforma de Auditoría Wi-Fi v1.0"
info "SOLO USO ÉTICO Y AUTORIZADO"
echo "──────────────────────────────────────"

# ── Verificación 2: herramientas de Aircrack-ng ───────────────────
info "Verificando suite Aircrack-ng..."
for tool in airmon-ng airodump-ng aireplay-ng aircrack-ng; do
    if ! command -v "$tool" &>/dev/null; then
        error "$tool no encontrado. Instala: sudo apt install aircrack-ng"
    fi
    info "  ✓ $tool disponible"
done

# ── Verificación 3: interfaz Wi-Fi externa ────────────────────────
IFACE="wlan1"
info "Verificando interfaz $IFACE..."
if ! iw dev | grep -q "Interface $IFACE"; then
    warning "Interfaz $IFACE no detectada."
    warning "Verifica que el adaptador Alfa AWUS036ACH está conectado."
    warning "Interfaces disponibles:"
    iw dev | grep "Interface" | awk '{print "  " $2}'
fi

# ── Activar modo monitor ──────────────────────────────────────────
info "Matando procesos que pueden interferir..."
# airmon-ng check kill detiene NetworkManager, wpa_supplicant, dhclient
airmon-ng check kill > /dev/null 2>&1

info "Activando modo monitor en $IFACE..."
airmon-ng start "$IFACE" > /dev/null 2>&1

# Verificamos que la interfaz en modo monitor existe
if iw dev | grep -q "wlan1mon"; then
    info "Modo monitor activo: wlan1mon"
else
    warning "No se pudo verificar el modo monitor. Continuando..."
fi

echo "──────────────────────────────────────"

# ── Lanzar la plataforma Python ───────────────────────────────────
info "Lanzando la plataforma..."
echo ""

# Nos aseguramos de estar en el directorio raíz del proyecto
# dirname "$0" da la ruta del script; navegamos un nivel arriba
cd "$(dirname "$0")/.." || error "No se pudo acceder al directorio del proyecto"

# Lanzamos Python con sudo para mantener los permisos necesarios
# El flag -u desactiva el buffer de stdout/stderr para logs en tiempo real
python3 -u main.py
