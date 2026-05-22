# 📡 WiFi Audit Platform

**Plataforma portátil de auditoría automatizada de redes Wi-Fi sobre Raspberry Pi 4**

Trabajo Fin de Bátxelor — Seguridad de Redes Inalámbricas  
Autor: [Nombre del Autor] | Tutor: [Nombre del Tutor]

---

## 📋 Descripción

Plataforma modular desarrollada en Python que automatiza el flujo de auditoría
de seguridad Wi-Fi integrando la suite Aircrack-ng mediante una capa de control
personalizada. El sistema incorpora módulos experimentales de análisis estadístico
del espectro de radiofrecuencia y detección de anomalías.

**Hardware objetivo:** Raspberry Pi 4 Model B (4 GB RAM)  
**Adaptador Wi-Fi:** Alfa AWUS036ACH (chipset RTL8812AU)  
**Sistema operativo:** Kali Linux 2024.1

> ⚠️ **Aviso legal:** Esta herramienta está diseñada exclusivamente para
> auditorías éticas sobre redes propias o con autorización expresa del
> administrador. El uso no autorizado puede ser ilegal.

---

## 🏗️ Arquitectura del sistema

```
wifi_audit_platform/
│
├── main.py                    # Punto de entrada — orquesta todos los módulos
├── requirements.txt           # Dependencias Python
│
├── core/
│   ├── event_bus.py           # Bus de eventos interno (publish/subscribe)
│   ├── orchestrator.py        # Coordinador central del sistema
│   ├── scheduler.py           # Planificador de tareas periódicas
│   └── session_manager.py     # Gestión del ciclo de vida de sesiones
│
├── scanner/
│   ├── scanner.py             # Escaneo de redes Wi-Fi con airodump-ng
│   ├── parser.py              # Parser de CSV de airodump-ng
│   └── monitor.py             # Gestión del modo monitor
│
├── capture/
│   ├── handshake_capture.py   # Captura de tráfico y detección EAPOL
│   ├── deauth.py              # Tramas de desautenticación (solo redes propias)
│   └── packet_parser.py       # Análisis de paquetes capturados
│
├── rf/
│   ├── rf_analyzer.py         # Analizador estadístico del espectro RF
│   ├── anomaly_detector.py    # Detector de anomalías espectrales
│   ├── statistics.py          # Funciones matemáticas (media, varianza, σ)
│   └── channel_monitor.py     # Monitorización de ocupación de canales
│
├── esp32/
│   ├── serial_bridge.py       # Puente serial JSON Raspberry Pi ↔ ESP32
│   └── protocol.py            # Definición del protocolo de mensajes
│
├── reporting/
│   ├── report_generator.py    # Generador central de informes
│   ├── html_exporter.py       # Exportación a HTML
│   └── json_exporter.py       # Exportación a JSON/CSV
│
├── config/
│   └── config.py              # Parámetros globales configurables
│
└── utils/
    ├── logger.py              # Sistema de registro de eventos con Rich
    ├── helpers.py             # Funciones auxiliares varias
    └── network_utils.py       # Utilidades de red
```

---

## 🚀 Instalación y uso

### Requisitos previos

```bash
# Instalar herramientas del sistema (Kali Linux / Raspberry Pi OS)
sudo apt-get update
sudo apt-get install aircrack-ng tshark python3-pip

# Clonar el repositorio
git clone https://github.com/[usuario]/wifi-audit-platform.git
cd wifi-audit-platform

# Instalar dependencias Python
pip install -r requirements.txt
```

### Ejecución

```bash
# Activar modo monitor manualmente (o dejar que lo haga el sistema)
sudo airmon-ng start wlan1

# Lanzar la plataforma con privilegios de root (necesario para modo monitor)
sudo python3 main.py
```

### Ejecución del script de inicialización

```bash
# El script automatiza la activación del modo monitor y el arranque
chmod +x scripts/start.sh
sudo ./scripts/start.sh
```

---

## 🧪 Módulos principales

| Módulo | Función | Estado |
|---|---|---|
| `core/event_bus.py` | Bus de eventos publish/subscribe | ✅ Funcional |
| `scanner/scanner.py` | Escaneo de redes con airodump-ng | ✅ Funcional |
| `capture/handshake_capture.py` | Captura de handshakes WPA/WPA2 | ✅ Funcional |
| `rf/rf_analyzer.py` | Análisis estadístico del espectro | ✅ Funcional |
| `rf/anomaly_detector.py` | Detección de anomalías RF | ✅ Funcional |
| `esp32/serial_bridge.py` | Comunicación serial con ESP32 | 🔬 Validado en Wokwi |
| `reporting/report_generator.py` | Generación de informes | ✅ Funcional |

---

## 📊 Resultados experimentales

Pruebas realizadas en entorno de laboratorio controlado (Kali Linux 2024.1):

- **Redes detectadas simultáneamente:** hasta 34
- **Tiempo medio de escaneo:** ~12 segundos
- **Sensibilidad mínima estable:** −87 dBm
- **Detección WPA2 handshake:** correcta en 100% de los casos probados
- **CPU media en operación:** 35–45%
- **RAM utilizada:** 1,0–1,5 GB
- **Temperatura:** 55–60 °C

---

## 📚 Tecnologías utilizadas

- **Python 3.11** — lenguaje principal
- **Aircrack-ng 1.7** — suite de auditoría Wi-Fi
- **Scapy 2.5** — análisis de paquetes
- **PySerial 3.5** — comunicación serie con ESP32
- **PyShark 0.6** — captura de tráfico
- **Rich 13.7** — interfaz de terminal enriquecida

---

## 📖 Referencias principales

- Borisov, N., Goldberg, I., & Wagner, D. (2001). *Intercepting mobile communications: The insecurity of 802.11*. MobiCom 2001.
- Vanhoef, M., & Piessens, F. (2017). *Key reinstallation attacks: Forcing nonce reuse in WPA2*. CCS 2017.
- Khan, A. et al. (2022). *Performance evaluation of Raspberry Pi for wireless security auditing*. Journal of Cybersecurity Systems.

---

## 📄 Licencia

Este proyecto se distribuye bajo licencia MIT para fines educativos y de investigación.
Consulte el archivo `LICENSE` para más detalles.

---

## ✅ Estado del proyecto

Desarrollo completado. Listo para entrega del TFG (22 mayo 2026).

---

## 🔬 Resultados obtenidos en laboratorio

Pruebas realizadas en entorno controlado (Kali Linux 2024.1):

| Parámetro | Resultado |
|---|---|
| Redes detectadas simultáneamente | 34 |
| Tiempo medio de escaneo | ~12 s |
| Sensibilidad mínima estable | −87 dBm |
| Handshakes WPA2 capturados | 100% (redes de prueba) |
| CPU media en operación | 35–45% |
| RAM utilizada | 1.0–1.5 GB |
| Temperatura Raspberry Pi 4 | 55–60 °C |
| Duración máxima sesión sin bloqueo | > 4 horas |

Nota: WPA3-SAE no permite captura de handshake equivalente, lo que
valida experimentalmente las mejoras de seguridad introducidas por SAE.

---

## ✅ Estado del proyecto

Desarrollo completado. Listo para entrega del TFG (22 mayo 2026).

---

## 🔬 Resultados obtenidos en laboratorio

Pruebas realizadas sobre Kali Linux 2024.1 / Raspberry Pi 4 Model B:

| Parámetro | Resultado |
|---|---|
| Redes detectadas simultáneamente | 34 |
| Tiempo medio de escaneo | ~12 s |
| Sensibilidad mínima estable | −87 dBm |
| Handshake WPA2 capturado | 100 % redes de prueba |
| WPA3-SAE resistente a deauth | Confirmado |
| CPU media en operación | 35–45 % |
| RAM utilizada | 1,0–1,5 GB |
| Temperatura Raspberry Pi 4 | 55–60 °C |
| Sesión máxima sin bloqueo | > 4 horas |

---

## ✅ Estado del proyecto

Desarrollo completado. Listo para entrega del TFG (22 mayo 2026).

---

## 🔬 Resultados obtenidos en laboratorio

Pruebas realizadas en entorno controlado / Raspberry Pi 4 Model B:

| Parámetro | Resultado |
|---|---|
| Redes detectadas simultáneamente | 34 |
| Tiempo medio de escaneo | ~12 s |
| Sensibilidad mínima estable | −87 dBm |
| Handshake WPA2 capturado | 100 % redes de prueba |
| WPA3-SAE resistente a deauth | Confirmado |
| CPU media en operación | 35–45 % |
| RAM utilizada | 1,0–1,5 GB |
| Temperatura Raspberry Pi 4 | 55–60 °C |
| Sesión máxima sin bloqueo | > 4 horas |
