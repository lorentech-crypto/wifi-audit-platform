// ─────────────────────────────────────────────────────────────────
// esp32_firmware/main.cpp  —  Firmware del nodo ESP32
//
// Descripción:
//   Interfaz ligera de monitorización que recibe eventos JSON
//   desde la Raspberry Pi por el puerto serie (UART) y los
//   muestra por consola. Validado en el simulador Wokwi.
//
// Hardware objetivo:
//   - Placa: ESP32-DevKit-V1
//   - Conexión: UART/USB al puerto /dev/ttyUSB0 de la Raspberry Pi
//   - Velocidad: 115200 baudios
//
// Protocolo de mensajes:
//   Cada mensaje es una línea JSON terminada en '\n':
//   {"event":"network_detected","data":{"ssid":"LAB","rssi":"-42"}}
//
// Compilación:
//   Plataforma: Arduino Framework para ESP32
//   IDE: Arduino IDE 2.x o PlatformIO
//   Board: "ESP32 Dev Module"
//
// Nota:
//   Este firmware fue validado en Wokwi (https://wokwi.com) 
// ─────────────────────────────────────────────────────────────────

// Arduino.h: framework base para ESP32 con Arduino
#include <Arduino.h>

// Definimos la velocidad del puerto serie en baudios.
// Debe coincidir EXACTAMENTE con ESP32_BAUD_RATE en config/config.py
#define BAUD_RATE 115200

// Tamaño máximo de un mensaje JSON que puede recibirse.
// Los mensajes del sistema no superan los 512 bytes.
#define MAX_MSG_SIZE 512

// Buffer acumulador de caracteres entrantes.
// Se va llenando con cada carácter recibido hasta encontrar '\n'.
String inputBuffer = "";

// Contador de mensajes recibidos (para estadísticas en consola)
int messageCount = 0;


// ─────────────────────────────────────────────────────────────────
// setup()  —  Inicialización del ESP32 (se ejecuta una sola vez)
// ─────────────────────────────────────────────────────────────────
void setup() {

  // Inicializamos el puerto serie a la velocidad configurada.
  // Serial.begin() configura el hardware UART del ESP32.
  Serial.begin(BAUD_RATE);

  // Esperamos a que el puerto serie esté listo.
  // Es necesario en algunos ESP32 con USB-CDC virtual.
  while (!Serial) {
    delay(10);   // Pausa de 10ms entre comprobaciones
  }

  // Enviamos el mensaje de confirmación de arranque.
  // La Raspberry Pi puede verificar que el ESP32 está listo
  // buscando "ESP32 READY" en su puerto serie.
  Serial.println("ESP32 READY");
  Serial.println("WiFi Audit Platform - Nodo embebido v1.0");
  Serial.println("Esperando eventos de la Raspberry Pi...");
}


// ─────────────────────────────────────────────────────────────────
// loop()  —  Bucle principal (se ejecuta continuamente)
// ─────────────────────────────────────────────────────────────────
void loop() {

  // Comprobamos si hay datos disponibles en el buffer del puerto serie.
  // Serial.available() retorna el número de bytes pendientes de leer.
  while (Serial.available() > 0) {

    // Leemos un carácter del buffer del puerto serie.
    // Serial.read() retorna -1 si no hay datos (aunque ya comprobamos arriba).
    char c = (char)Serial.read();

    // Añadimos el carácter al buffer de mensaje acumulado.
    inputBuffer += c;

    // Comprobamos si el buffer ha crecido demasiado (protección anti-desbordamiento).
    // Si supera el tamaño máximo, probablemente está corrupto: lo reiniciamos.
    if (inputBuffer.length() > MAX_MSG_SIZE) {
      Serial.println("[WARN] Buffer desbordado. Reiniciando.");
      inputBuffer = "";   // Vaciamos el buffer
    }

    // Los mensajes JSON del protocolo terminan con '\n'.
    // Cuando lo encontramos, tenemos un mensaje completo listo para procesar.
    if (c == '\n') {

      // Limpiamos posibles espacios y retornos de carro al final
      inputBuffer.trim();

      // Solo procesamos si el mensaje no está vacío
      if (inputBuffer.length() > 0) {
        processMessage(inputBuffer);   // Procesamos el mensaje
      }

      // Reiniciamos el buffer para el siguiente mensaje
      inputBuffer = "";
    }
  }

  // Pequeña pausa para no saturar el procesador del ESP32.
  // 10ms es suficiente para procesar la velocidad de 115200 baudios.
  delay(10);
}


// ─────────────────────────────────────────────────────────────────
// processMessage()  —  Procesa un mensaje JSON recibido completo
// ─────────────────────────────────────────────────────────────────
void processMessage(String msg) {
  /*
   * Procesa un mensaje JSON completo recibido de la Raspberry Pi.
   *
   * En esta versión simplificada, analizamos el campo "event" del JSON
   * de forma manual (sin librería ArduinoJson) buscando subcadenas.
   * Una versión futura debería usar ArduinoJson para mayor robustez.
   *
   * Parámetros:
   *   msg (String): mensaje JSON completo, p.ej.:
   *   {"event":"network_detected","data":{"ssid":"LAB-WPA2","rssi":"-42"}}
   */

  // Incrementamos el contador de mensajes para estadísticas
  messageCount++;

  // Mostramos el mensaje completo con su número de secuencia
  Serial.print("[MSG #");
  Serial.print(messageCount);
  Serial.print("] ");
  Serial.println(msg);

  // ── Identificación del tipo de evento ────────────────────────
  // Buscamos el campo "event" en el JSON de forma simple.
  // msg.indexOf() retorna la posición de la subcadena, o -1 si no existe.

  if (msg.indexOf("network_detected") >= 0) {
    // Nueva red Wi-Fi detectada por el Scanner
    Serial.println("  → [RED DETECTADA]");
    // TODO: extraer SSID y RSSI con ArduinoJson y mostrar en pantalla LCD

  } else if (msg.indexOf("handshake_detected") >= 0) {
    // Handshake WPA/WPA2 capturado correctamente
    Serial.println("  → *** HANDSHAKE CAPTURADO ***");
    // TODO: activar LED de alerta o sonido

  } else if (msg.indexOf("rf_anomaly") >= 0) {
    // Anomalía estadística en el espectro RF
    Serial.println("  → [!] ANOMALÍA RF DETECTADA");
    // TODO: mostrar alerta en pantalla

  } else if (msg.indexOf("channel_congestion") >= 0) {
    // Canal Wi-Fi con alta ocupación detectado
    Serial.println("  → [!] CANAL CONGESTIONADO");

  } else if (msg.indexOf("system_status") >= 0) {
    // Actualización de estadísticas del sistema
    Serial.println("  → [ESTADO] Actualización de estadísticas");

  } else {
    // Tipo de evento desconocido o no implementado
    Serial.println("  → [?] Evento no reconocido");
  }
}
