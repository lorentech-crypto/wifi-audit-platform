#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# scripts/install.sh  —  Instalación de todas las dependencias
#
# Descripción:
#   Instala automáticamente todas las dependencias necesarias para
#   ejecutar la plataforma de auditoría Wi-Fi:
#     1. Dependencias del sistema (apt): aircrack-ng, tshark, iw
#     2. Dependencias Python (pip): requirements.txt
#
# Uso:
#   chmod +x scripts/install.sh
#   sudo ./scripts/install.sh
# ─────────────────────────────────────────────────────────────────

# ── Colores para mensajes ─────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[-]${NC} $1"; exit 1; }

# ── Verificar permisos de root ────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Este script necesita permisos de root: sudo ./scripts/install.sh"
fi

info "Instalando dependencias de la plataforma de auditoría Wi-Fi..."
echo "──────────────────────────────────────────────────────────"

# ── Paso 1: actualizar repositorios ──────────────────────────────
info "Actualizando repositorios apt..."
apt-get update -qq || warning "No se pudo actualizar apt. Continuando..."

# ── Paso 2: instalar dependencias del sistema ─────────────────────
info "Instalando herramientas del sistema..."

# Lista de paquetes necesarios con su descripción
PACKAGES=(
    "aircrack-ng"     # Suite de auditoría Wi-Fi (airmon-ng, airodump-ng...)
    "tshark"          # Analizador de paquetes (necesario para pyshark)
    "iw"              # Herramienta de configuración de interfaces inalámbricas
    "wireless-tools"  # Contiene iwconfig para verificar modo monitor
    "python3-pip"     # Gestor de paquetes Python
    "python3-dev"     # Cabeceras Python necesarias para algunos módulos
)

for pkg in "${PACKAGES[@]}"; do
    # Comprobamos si el paquete ya está instalado
    if dpkg -s "$pkg" &>/dev/null; then
        info "  ✓ $pkg ya instalado"
    else
        info "  Instalando $pkg..."
        apt-get install -y -qq "$pkg" || warning "  No se pudo instalar $pkg"
    fi
done

# ── Paso 3: instalar dependencias Python ──────────────────────────
info "Instalando dependencias Python desde requirements.txt..."

# Nos aseguramos de estar en el directorio raíz del proyecto
SCRIPT_DIR="$(dirname "$0")"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Verificamos que requirements.txt existe
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    error "requirements.txt no encontrado en $PROJECT_DIR"
fi

# Instalamos con pip3
pip3 install -r "$PROJECT_DIR/requirements.txt" --quiet

if [ $? -eq 0 ]; then
    info "Dependencias Python instaladas correctamente."
else
    error "Error instalando dependencias Python. Revisa requirements.txt"
fi

# ── Paso 4: verificar instalación ─────────────────────────────────
echo ""
info "Verificando instalación..."

# Comprobamos cada herramienta de aircrack-ng
for tool in airmon-ng airodump-ng aireplay-ng aircrack-ng; do
    if command -v "$tool" &>/dev/null; then
        info "  ✓ $tool"
    else
        warning "  ✗ $tool no encontrado"
    fi
done

# Comprobamos Python y sus módulos principales
python3 -c "import scapy; import serial; print('  ✓ Python modules OK')" 2>/dev/null \
    || warning "  Algunos módulos Python pueden no estar disponibles"

echo ""
echo "──────────────────────────────────────────────────────────"
info "Instalación completada. Ejecuta la plataforma con:"
echo "    sudo ./scripts/start.sh"
