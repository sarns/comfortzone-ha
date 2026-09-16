#include <Arduino.h>

#include <comfortzone_heatpump.h>
#include <rs485_interface.h>

// Waveshare ESP32-S3-RS485-CAN board pins.
constexpr int RS485_TX_PIN = 17;
constexpr int RS485_RX_PIN = 18;
constexpr int RS485_ENABLE_PIN = 21;
constexpr uint32_t RS485_BAUD = 19200;
constexpr uint32_t REPORT_INTERVAL_MS = 5000;
constexpr uint32_t WARMUP_MS = 10000;

uint32_t rs485_bytes = 0;

// The Waveshare transceiver presents the Comfortzone signal inverted to the
// ESP32 UART. This interface is deliberately receive-only: DE stays LOW and
// writes are discarded.
class ReadOnlyComfortzoneBus : public RS485Interface {
 public:
  void begin() override {
    pinMode(RS485_ENABLE_PIN, OUTPUT);
    digitalWrite(RS485_ENABLE_PIN, LOW);
    Serial1.begin(RS485_BAUD, SERIAL_8N1, RS485_RX_PIN, RS485_TX_PIN, true);
  }

  int available() override { return Serial1.available(); }
  int read_byte() override {
    const int value = Serial1.read();
    if (value >= 0) {
      rs485_bytes++;
    }
    return value;
  }
  int write_bytes(const void *, int) override { return 0; }
  void flush() override { Serial1.flush(); }

  void enable_receiver_mode() override {
    digitalWrite(RS485_ENABLE_PIN, LOW);
  }

  void enable_sender_mode() override {
    // Remain in receive mode even if a caller accidentally requests TX mode.
    digitalWrite(RS485_ENABLE_PIN, LOW);
  }
};

ReadOnlyComfortzoneBus bus;
comfortzone_heatpump heatpump(&bus);

uint32_t query_frames = 0;
uint32_t reply_frames = 0;
uint32_t corrupted_frames = 0;
uint32_t unknown_frames = 0;
uint32_t ex_decoded_frames = 0;
uint32_t first_valid_frame_ms = 0;
uint32_t last_report_ms = 0;

uint8_t frame_buffer[256];
uint16_t frame_size = 0;

struct ExReadings {
  bool temperatures_valid = false;
  bool settings_valid = false;
  bool fan_valid = false;
  bool power_valid = false;
  bool counters_valid = false;

  uint16_t year = 0;
  uint8_t month = 0;
  uint8_t day = 0;
  uint8_t hour = 0;
  uint8_t minute = 0;
  uint8_t second = 0;
  int16_t temperatures_x10[31] = {};
  int16_t room_setpoint_x10 = 0;
  int16_t hot_water_target_x10 = 0;
  uint8_t fan_speed = 0;
  uint16_t compressor_frequency_x10 = 0;
  uint16_t compressor_output_w = 0;
  uint32_t additional_heater_w = 0;
  uint32_t total_output_w = 0;
  uint16_t compressor_input_w = 0;
  uint32_t compressor_energy_x100 = 0;
  uint32_t additional_heater_energy_x100 = 0;
  uint32_t hot_water_energy_x100 = 0;
  uint32_t compressor_runtime_minutes = 0;
  uint32_t total_runtime_minutes = 0;

  bool complete() const {
    return temperatures_valid && settings_valid && fan_valid && power_valid &&
           counters_valid;
  }
};

ExReadings ex;

uint16_t read_u16_le(const uint8_t *value) {
  return static_cast<uint16_t>(value[0]) |
         (static_cast<uint16_t>(value[1]) << 8);
}

uint32_t read_u32_le(const uint8_t *value) {
  return static_cast<uint32_t>(value[0]) |
         (static_cast<uint32_t>(value[1]) << 8) |
         (static_cast<uint32_t>(value[2]) << 16) |
         (static_cast<uint32_t>(value[3]) << 24);
}

bool register_is(uint8_t a, uint8_t b, uint8_t c) {
  return frame_buffer[18] == a && frame_buffer[19] == b &&
         frame_buffer[20] == c;
}

void decode_ex_frame() {
  if (frame_size < 23 || frame_buffer[11] != 'r' ||
      frame_buffer[16] != 0x0B || frame_buffer[17] != 0x10) {
    return;
  }

  const uint8_t *payload = frame_buffer + 21;
  const size_t payload_size = frame_size - 22;

  if (register_is(0x01, 0x04, 0x00) && payload_size >= 114) {
    ex.hour = payload[0];
    ex.minute = payload[1];
    ex.second = payload[2];
    ex.day = payload[3];
    ex.month = payload[4];
    ex.year = 2000 + payload[5];
    for (size_t i = 0; i < 31; i++) {
      ex.temperatures_x10[i] =
          static_cast<int16_t>(read_u16_le(payload + 52 + i * 2));
    }
    ex.temperatures_valid = true;
  } else if (register_is(0x00, 0x89, 0x02) && payload_size >= 11) {
    // Same leading layout as the public v2.21 xC1 status frame. This EX
    // revision appends two bytes to the frame.
    ex.room_setpoint_x10 = static_cast<int16_t>(read_u16_le(payload + 9));
    ex.settings_valid = ex.hot_water_target_x10 != 0;
  } else if (register_is(0x00, 0x45, 0x03) && payload_size >= 2) {
    // Same leading field as the public v2.21 xC5 hot-water status frame.
    ex.hot_water_target_x10 = static_cast<int16_t>(read_u16_le(payload));
    ex.settings_valid = ex.room_setpoint_x10 != 0;
  } else if (register_is(0x01, 0xD1, 0x02) && payload_size >= 35) {
    // This 0x51-byte EX frame retains the useful offsets from the public
    // x51 layout.
    ex.fan_speed = payload[3];
    ex.compressor_frequency_x10 = read_u16_le(payload + 33);
    ex.fan_valid = true;
  } else if (register_is(0x01, 0x40, 0x03) && payload_size >= 16) {
    // Power fields retain the public v2.21 xB9 leading layout.
    ex.compressor_output_w = read_u16_le(payload);
    ex.additional_heater_w = read_u32_le(payload + 2);
    ex.total_output_w = read_u32_le(payload + 6);
    ex.compressor_input_w = read_u16_le(payload + 14);
    ex.power_valid = true;
  } else if (register_is(0x05, 0x28, 0x00) && payload_size >= 24) {
    // Runtime/energy layout is unchanged from public protocol 1.8/2.21.
    ex.compressor_energy_x100 = read_u32_le(payload + 4);
    ex.additional_heater_energy_x100 = read_u32_le(payload + 8);
    ex.hot_water_energy_x100 = read_u32_le(payload + 12);
    ex.compressor_runtime_minutes = read_u32_le(payload + 16);
    ex.total_runtime_minutes = read_u32_le(payload + 20);
    ex.counters_valid = true;
  } else {
    return;
  }

  ex_decoded_frames++;
}

const char *fan_speed_name(uint8_t value) {
  switch (value) {
    case 1:
      return "low";
    case 2:
      return "normal";
    case 3:
      return "high";
    default:
      return "unknown";
  }
}

void print_readings() {
  Serial.printf(
      "{\"type\":\"comfortzone_readings\",\"uptime_s\":%lu,"
      "\"protocol\":\"EX_0B10\",\"complete\":%s,"
      "\"heatpump_time\":\"%04u-%02u-%02uT%02u:%02u:%02u\","
      "\"temperatures_c\":{\"outdoor_te0\":%.1f,\"flow_te1\":%.1f,"
      "\"return_te2\":%.1f,\"indoor_te3\":%.1f,\"hot_gas_te4\":%.1f,"
      "\"exchanger_out_te5\":%.1f,\"evaporator_in_te6\":%.1f,"
      "\"exhaust_air_te7\":%.1f,\"hot_water_te24\":%.1f},"
      "\"state\":{\"compressor_running\":%s,\"additional_heater\":%s},"
      "\"fan\":{\"speed\":\"%s\",\"speed_code\":%u},"
      "\"setpoints_c\":{\"room\":%.1f,\"hot_water_target\":%.1f},"
      "\"power\":{\"compressor_frequency_hz\":%.1f,\"compressor_output_w\":%d,"
      "\"additional_heater_w\":%lu,\"total_output_w\":%lu,"
      "\"compressor_input_w\":%d},"
      "\"energy_kwh\":{\"compressor\":%.2f,\"additional_heater\":%.2f,"
      "\"hot_water\":%.2f},"
      "\"runtime_minutes\":{\"compressor\":%lu,\"total\":%lu},"
      "\"frames\":{\"query\":%lu,\"reply\":%lu,\"corrupted\":%lu,"
      "\"unknown\":%lu,\"ex_decoded\":%lu}}\n",
      millis() / 1000, ex.complete() ? "true" : "false",
      ex.year, ex.month, ex.day, ex.hour, ex.minute, ex.second,
      ex.temperatures_x10[0] / 10.0, ex.temperatures_x10[1] / 10.0,
      ex.temperatures_x10[2] / 10.0, ex.temperatures_x10[3] / 10.0,
      ex.temperatures_x10[4] / 10.0, ex.temperatures_x10[5] / 10.0,
      ex.temperatures_x10[6] / 10.0, ex.temperatures_x10[7] / 10.0,
      ex.temperatures_x10[24] / 10.0,
      (ex.compressor_frequency_x10 > 0 || ex.compressor_input_w > 0)
          ? "true"
          : "false",
      ex.additional_heater_w > 0 ? "true" : "false",
      fan_speed_name(ex.fan_speed), ex.fan_speed,
      ex.room_setpoint_x10 / 10.0, ex.hot_water_target_x10 / 10.0,
      ex.compressor_frequency_x10 / 10.0, ex.compressor_output_w,
      static_cast<unsigned long>(ex.additional_heater_w),
      static_cast<unsigned long>(ex.total_output_w), ex.compressor_input_w,
      ex.compressor_energy_x100 / 100.0,
      ex.additional_heater_energy_x100 / 100.0,
      ex.hot_water_energy_x100 / 100.0,
      static_cast<unsigned long>(ex.compressor_runtime_minutes),
      static_cast<unsigned long>(ex.total_runtime_minutes), query_frames,
      reply_frames, corrupted_frames, unknown_frames, ex_decoded_frames);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  heatpump.begin();
  heatpump.set_grab_buffer(frame_buffer, sizeof(frame_buffer), &frame_size);
  Serial.printf(
      "Comfortzone receive-only monitor: protocol=%d, RX=GPIO%d inverted, "
      "DE=GPIO%d LOW\n",
      HP_PROTOCOL, RS485_RX_PIN, RS485_ENABLE_PIN);
}

void loop() {
  const comfortzone_heatpump::PROCESSED_FRAME_TYPE result = heatpump.process();
  switch (result) {
    case comfortzone_heatpump::PFT_QUERY:
      query_frames++;
      break;
    case comfortzone_heatpump::PFT_REPLY:
      reply_frames++;
      break;
    case comfortzone_heatpump::PFT_CORRUPTED:
      corrupted_frames++;
      break;
    case comfortzone_heatpump::PFT_UNKNOWN:
      unknown_frames++;
      break;
    default:
      break;
  }

  if (result != comfortzone_heatpump::PFT_NONE && frame_size > 0) {
    decode_ex_frame();
  }

  if (first_valid_frame_ms == 0 && ex_decoded_frames > 0) {
    first_valid_frame_ms = millis();
  }

  const uint32_t now = millis();
  if (now - last_report_ms >= REPORT_INTERVAL_MS) {
    if (first_valid_frame_ms != 0 &&
        now - first_valid_frame_ms >= WARMUP_MS) {
      print_readings();
    } else {
      Serial.printf(
          "{\"type\":\"comfortzone_waiting\",\"uptime_s\":%lu,"
          "\"protocol\":\"%d\",\"rs485_bytes\":%lu,"
          "\"frames\":{\"query\":%lu,\"reply\":%lu,\"corrupted\":%lu,"
          "\"unknown\":%lu}}\n",
          now / 1000, HP_PROTOCOL, rs485_bytes, query_frames, reply_frames,
          corrupted_frames, unknown_frames);
    }
    last_report_ms = now;
  }

  delay(1);
}
