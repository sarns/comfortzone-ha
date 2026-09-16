#include <Arduino.h>

// Waveshare ESP32-S3-RS485-CAN pinout.
constexpr int RS485_TX_PIN = 17;
constexpr int RS485_RX_PIN = 18;
constexpr int RS485_ENABLE_PIN = 21;

// Comfortzone's controller bus uses 19200 baud, 8 data bits, no parity, 1 stop bit.
constexpr uint32_t RS485_BAUD = 19200;
constexpr bool RS485_RX_INVERTED = true;

uint32_t byte_count = 0;
uint32_t last_byte_ms = 0;
uint32_t last_status_ms = 0;
volatile uint32_t edge_count = 0;

void ARDUINO_ISR_ATTR on_rs485_edge() {
  edge_count++;
}

void setup() {
  // LOW keeps the RS485 transmitter disabled and the receiver enabled.
  pinMode(RS485_ENABLE_PIN, OUTPUT);
  digitalWrite(RS485_ENABLE_PIN, LOW);

  Serial.begin(115200);
  Serial1.begin(RS485_BAUD, SERIAL_8N1, RS485_RX_PIN, RS485_TX_PIN,
                RS485_RX_INVERTED);
  attachInterrupt(digitalPinToInterrupt(RS485_RX_PIN), on_rs485_edge, CHANGE);

  delay(500);
  Serial.println();
  Serial.println("Comfortzone RS485 receive-only sniffer");
  Serial.printf("RX=GPIO%d%s, TX=GPIO%d, EN=GPIO%d (LOW), %lu 8N1\n",
                RS485_RX_PIN, RS485_RX_INVERTED ? " (inverted)" : "",
                RS485_TX_PIN, RS485_ENABLE_PIN, RS485_BAUD);
}

void loop() {
  while (Serial1.available() > 0) {
    const uint8_t value = Serial1.read();
    const uint32_t now = millis();

    if (byte_count == 0 || now - last_byte_ms > 20) {
      Serial.printf("\n[%10lu ms] ", now);
    }

    Serial.printf("%02X ", value);
    byte_count++;
    last_byte_ms = now;
  }

  const uint32_t now = millis();
  if (now - last_status_ms >= 5000) {
    noInterrupts();
    const uint32_t edges = edge_count;
    interrupts();
    Serial.printf(
        "\n[%10lu ms] status: %lu RS485 bytes, %lu RX signal edges\n", now,
        byte_count, edges);
    last_status_ms = now;
  }

  delay(1);
}
