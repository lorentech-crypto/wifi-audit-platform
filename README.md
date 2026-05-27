WiFi Audit Platform

**Plataforma portátil de auditoría automatizada de redes Wi-Fi sobre Raspberry Pi 4**

Trabajo Fin de Bátxelor — Seguridad de Redes Inalámbricas  

Plataforma modular desarrollada en Python que automatiza el flujo de auditoría de seguridad Wi-Fi integrando la suite Aircrack-ng mediante una capa de control personalizada. El sistema incorpora módulos experimentales de análisis estadístico del espectro de radiofrecuencia y detección de anomalías.

**Hardware objetivo:** Raspberry Pi 4 Model B (4 GB RAM)  
**Adaptador Wi-Fi:** Alfa AWUS036ACH (chipset RTL8812AU)  
**Sistema operativo:** Kali Linux 2024.1

## Arquitectura del sistema
´´´
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
´´´
## Módulos principales

| Módulo | Función | Estado |
|---|---|---|
| `core/event_bus.py` | Bus de eventos publish/subscribe 
| `scanner/scanner.py` | Escaneo de redes con airodump-ng
| `capture/handshake_capture.py` | Captura de handshakes WPA/WPA2
| `rf/rf_analyzer.py` | Análisis estadístico del espectro
| `rf/anomaly_detector.py` | Detección de anomalías RF
| `esp32/serial_bridge.py` | Comunicación serial con ESP32
| `reporting/report_generator.py` | Generación de informes

## Resultados obtenidos en laboratorio

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

## Resultados obtenidos en laboratorio

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

## Resultados obtenidos en laboratorio

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
