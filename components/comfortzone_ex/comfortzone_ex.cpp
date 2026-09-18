#include "comfortzone_ex.h"

#include <cmath>
#include <cstring>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome {
namespace comfortzone_ex {

static const char *const TAG = "comfortzone_ex";
static constexpr const char *const PROTOCOL_COVERAGE = "9 of 22 read registers decoded";

void ComfortzoneExComponent::setup() {
  this->receiver_enable_pin_->setup();
  this->receiver_enable_pin_->digital_write(false);
  this->bus_online_binary_sensor_->publish_state(false);
  this->protocol_coverage_text_sensor_->publish_state(PROTOCOL_COVERAGE);
  ESP_LOGI(TAG, "RS485 receiver enabled; transmitter remains disabled");
  ESP_LOGI(TAG, "Raw frame logging: %s", this->raw_frame_logging_ ? "enabled" : "disabled");
}

void ComfortzoneExComponent::loop() {
  uint8_t value;
  while (this->available() && this->read_byte(&value)) {
    this->rs485_bytes_++;
    this->consume_byte_(value);
  }

  const uint32_t now = millis();
  const bool online = this->last_decoded_frame_ms_ != 0 &&
                      now - this->last_decoded_frame_ms_ <= BUS_STALE_MS;
  if (online != this->bus_online_state_) {
    this->bus_online_state_ = online;
    this->bus_online_binary_sensor_->publish_state(online);
  }

  if (now - this->last_diagnostic_ms_ >= DIAGNOSTIC_INTERVAL_MS) {
    this->last_diagnostic_ms_ = now;
    this->publish_diagnostics_();
  }
}

void ComfortzoneExComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Comfortzone EX receive-only monitor:");
  LOG_PIN("  Receiver enable pin: ", this->receiver_enable_pin_);
  ESP_LOGCONFIG(TAG, "  Protocol family: EX 0B10");
  ESP_LOGCONFIG(TAG, "  Implemented read registers: 9 of 22 observed");
  ESP_LOGCONFIG(TAG, "  Raw frame logging: %s", this->raw_frame_logging_ ? "enabled" : "disabled");
}

void ComfortzoneExComponent::consume_byte_(uint8_t value) {
  if (this->frame_size_ >= BUFFER_SIZE) {
    this->frame_size_ = 0;
    this->expected_frame_size_ = 0;
  }
  this->frame_[this->frame_size_++] = value;

  if (this->frame_size_ < HEADER_SIZE)
    return;

  if (this->frame_size_ == HEADER_SIZE) {
    if (!this->header_valid_()) {
      std::memmove(this->frame_, this->frame_ + 1, HEADER_SIZE - 1);
      this->frame_size_--;
      return;
    }
    this->expected_frame_size_ = this->frame_[10];
    if (this->expected_frame_size_ < HEADER_SIZE + 1 ||
        this->expected_frame_size_ > BUFFER_SIZE) {
      this->frame_size_ = 0;
      this->expected_frame_size_ = 0;
      return;
    }
  }

  if (this->expected_frame_size_ != 0 && this->frame_size_ == this->expected_frame_size_) {
    this->process_frame_();
    this->frame_size_ = 0;
    this->expected_frame_size_ = 0;
  }
}

bool ComfortzoneExComponent::header_valid_() const {
  uint8_t complement[4];
  for (size_t i = 0; i < 4; i++)
    complement[i] = this->frame_[i] ^ 0xFF;

  const uint8_t command = this->frame_[11];
  return this->frame_[4] == crc8_maxim_(this->frame_, 4) &&
         this->frame_[5] == crc8_maxim_(complement, 4) &&
         (command == 'R' || command == 'W' || command == 'r' || command == 'w');
}

void ComfortzoneExComponent::process_frame_() {
  if (crc8_maxim_(this->frame_, this->frame_size_ - 1) !=
      this->frame_[this->frame_size_ - 1]) {
    this->crc_errors_++;
    return;
  }

  this->valid_frames_++;
  if (this->raw_frame_logging_)
    this->log_raw_frame_();

  if (this->decode_frame_()) {
    this->decoded_frames_++;
    this->last_decoded_frame_ms_ = millis();
  } else {
    this->unsupported_frames_++;
  }
}

void ComfortzoneExComponent::log_raw_frame_() const {
  static constexpr char HEX[] = "0123456789ABCDEF";
  char encoded[BUFFER_SIZE * 2 + 1];
  for (size_t i = 0; i < this->frame_size_; i++) {
    encoded[i * 2] = HEX[this->frame_[i] >> 4];
    encoded[i * 2 + 1] = HEX[this->frame_[i] & 0x0F];
  }
  encoded[this->frame_size_ * 2] = '\0';

  ESP_LOGI(TAG, "CZRAW uptime_ms=%lu frame=%s",
           static_cast<unsigned long>(millis()), encoded);
}

bool ComfortzoneExComponent::decode_frame_() {
  if (this->frame_size_ < 23 || this->frame_[11] != 'r' ||
      this->frame_[16] != 0x0B || this->frame_[17] != 0x10) {
    return false;
  }

  const uint8_t *payload = this->frame_ + HEADER_SIZE;
  const size_t payload_size = this->frame_size_ - HEADER_SIZE - 1;

  if (this->register_is_(0x01, 0x04, 0x00) && payload_size >= 114) {
    constexpr size_t SENSOR_OFFSET = 52;
    constexpr uint8_t SENSOR_INDICES[] = {0, 1, 2, 3, 4, 5, 6, 7, 24};
    sensor::Sensor *const entities[] = {
        this->outdoor_temperature_sensor_,     this->flow_temperature_sensor_,
        this->return_temperature_sensor_,      this->indoor_temperature_sensor_,
        this->hot_gas_temperature_sensor_,     this->exchanger_out_temperature_sensor_,
        this->evaporator_in_temperature_sensor_, this->exhaust_air_temperature_sensor_,
        this->hot_water_temperature_sensor_,
    };
    if (this->should_publish_(PUBLISH_TEMPERATURES)) {
      for (size_t i = 0; i < 9; i++) {
        const int16_t raw = static_cast<int16_t>(
            read_u16_le_(payload + SENSOR_OFFSET + SENSOR_INDICES[i] * 2));
        entities[i]->publish_state(raw / 10.0f);
      }
    }
    return true;
  }

  if (this->register_is_(0x00, 0x89, 0x02) && payload_size >= 11) {
    if (this->should_publish_(PUBLISH_ROOM_SETPOINT)) {
      const int16_t raw = static_cast<int16_t>(read_u16_le_(payload + 9));
      this->room_setpoint_sensor_->publish_state(raw / 10.0f);
    }
    return true;
  }

  if (this->register_is_(0x00, 0x45, 0x03) && payload_size >= 2) {
    if (this->should_publish_(PUBLISH_HOT_WATER_TARGET)) {
      const int16_t raw = static_cast<int16_t>(read_u16_le_(payload));
      this->hot_water_target_sensor_->publish_state(raw / 10.0f);
    }
    return true;
  }

  if (this->register_is_(0x00, 0x28, 0x04) && payload_size >= 72) {
    if (this->should_publish_(PUBLISH_CALCULATED_FLOW)) {
      const int16_t raw = static_cast<int16_t>(read_u16_le_(payload + 70));
      this->calculated_flow_temperature_sensor_->publish_state(raw / 10.0f);
    }
    return true;
  }

  if (this->register_is_(0x00, 0xF7, 0x03) && payload_size >= 8) {
    if (this->should_publish_(PUBLISH_FILTER)) {
      this->filter_change_time_sensor_->publish_state(read_u16_le_(payload + 6));
    }
    return true;
  }

  if (this->register_is_(0x01, 0xD1, 0x02) && payload_size >= 35) {
    this->compressor_frequency_x10_ = read_u16_le_(payload + 33);
    this->current_flow_x10_ = read_u16_le_(payload + 10);
    if (this->should_publish_(PUBLISH_FAN_AND_COMPRESSOR)) {
      this->fan_speed_text_sensor_->publish_state(fan_speed_name_(payload[3]));
      this->fan_power_sensor_->publish_state(read_u16_le_(payload + 2) / 10.0f);
      if (this->heating_flow_known_) {
        this->hot_water_flow_sensor_->publish_state(
            this->heating_flow_x10_ == 0 ? this->current_flow_x10_ / 10.0f : 0.0f);
      }
      this->compressor_frequency_sensor_->publish_state(
          this->compressor_frequency_x10_ / 10.0f);
      this->update_compressor_state_();
    }
    return true;
  }

  if (this->register_is_(0x01, 0xF9, 0x01) && payload_size >= 20) {
    // Provisional mapping: confirm against a display photo while space heating is active.
    this->heating_flow_x10_ = read_u16_le_(payload + 18);
    this->heating_flow_known_ = true;
    if (this->should_publish_(PUBLISH_FLOW_RATES)) {
      this->heating_flow_sensor_->publish_state(this->heating_flow_x10_ / 10.0f);
      this->hot_water_flow_sensor_->publish_state(
          this->heating_flow_x10_ == 0 ? this->current_flow_x10_ / 10.0f : 0.0f);
    }
    return true;
  }

  if (this->register_is_(0x01, 0x40, 0x03) && payload_size >= 16) {
    const uint16_t compressor_output = read_u16_le_(payload);
    const uint32_t additional_heater = read_u32_le_(payload + 2);
    const uint32_t total_output = read_u32_le_(payload + 6);
    this->compressor_input_power_w_ = read_u16_le_(payload + 14);

    if (this->should_publish_(PUBLISH_POWER)) {
      this->compressor_output_power_sensor_->publish_state(compressor_output);
      this->additional_heater_power_sensor_->publish_state(additional_heater);
      this->total_output_power_sensor_->publish_state(total_output);
      this->compressor_input_power_sensor_->publish_state(this->compressor_input_power_w_);
      this->additional_heater_active_binary_sensor_->publish_state(additional_heater > 0);
    }
    return true;
  }

  if (this->register_is_(0x05, 0x28, 0x00) && payload_size >= 24) {
    if (this->should_publish_(PUBLISH_COUNTERS)) {
      this->compressor_energy_sensor_->publish_state(read_u32_le_(payload + 4) / 100.0f);
      this->additional_heater_energy_sensor_->publish_state(
          read_u32_le_(payload + 8) / 100.0f);
      this->hot_water_energy_sensor_->publish_state(read_u32_le_(payload + 12) / 100.0f);
      this->compressor_runtime_sensor_->publish_state(read_u32_le_(payload + 16));
      this->total_runtime_sensor_->publish_state(read_u32_le_(payload + 20));
    }
    return true;
  }

  return false;
}

bool ComfortzoneExComponent::register_is_(uint8_t a, uint8_t b, uint8_t c) const {
  return this->frame_[18] == a && this->frame_[19] == b && this->frame_[20] == c;
}

bool ComfortzoneExComponent::should_publish_(PublishGroup group) {
  const uint32_t now = millis();
  const uint32_t last = this->last_publish_ms_[group];
  if (last != 0 && now - last < PUBLISH_INTERVAL_MS)
    return false;
  this->last_publish_ms_[group] = now == 0 ? 1 : now;
  return true;
}

void ComfortzoneExComponent::update_compressor_state_() {
  this->compressor_running_binary_sensor_->publish_state(
      this->compressor_frequency_x10_ > 0 || this->compressor_input_power_w_ > 0);
}

void ComfortzoneExComponent::publish_diagnostics_() {
  this->rs485_bytes_sensor_->publish_state(this->rs485_bytes_);
  this->valid_frames_sensor_->publish_state(this->valid_frames_);
  this->decoded_frames_sensor_->publish_state(this->decoded_frames_);
  this->unsupported_frames_sensor_->publish_state(this->unsupported_frames_);
  this->crc_errors_sensor_->publish_state(this->crc_errors_);

  ESP_LOGI(TAG,
           "RS485 bytes=%lu valid=%lu decoded=%lu unsupported=%lu crc_errors=%lu",
           static_cast<unsigned long>(this->rs485_bytes_),
           static_cast<unsigned long>(this->valid_frames_),
           static_cast<unsigned long>(this->decoded_frames_),
           static_cast<unsigned long>(this->unsupported_frames_),
           static_cast<unsigned long>(this->crc_errors_));

  if (this->last_decoded_frame_ms_ == 0) {
    this->last_decoded_frame_age_sensor_->publish_state(NAN);
  } else {
    this->last_decoded_frame_age_sensor_->publish_state(
        (millis() - this->last_decoded_frame_ms_) / 1000.0f);
  }
}

uint8_t ComfortzoneExComponent::crc8_maxim_(const uint8_t *data, size_t size) {
  uint8_t crc = 0;
  for (size_t i = 0; i < size; i++) {
    crc ^= data[i];
    for (uint8_t bit = 0; bit < 8; bit++)
      crc = (crc >> 1) ^ ((crc & 1) ? 0x8C : 0x00);
  }
  return crc;
}

uint16_t ComfortzoneExComponent::read_u16_le_(const uint8_t *data) {
  return static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
}

uint32_t ComfortzoneExComponent::read_u32_le_(const uint8_t *data) {
  return static_cast<uint32_t>(data[0]) | (static_cast<uint32_t>(data[1]) << 8) |
         (static_cast<uint32_t>(data[2]) << 16) |
         (static_cast<uint32_t>(data[3]) << 24);
}

const char *ComfortzoneExComponent::fan_speed_name_(uint8_t value) {
  switch (value) {
    case 1:
      return "Low";
    case 2:
      return "Normal";
    case 3:
      return "High";
    default:
      return "Unknown";
  }
}

}  // namespace comfortzone_ex
}  // namespace esphome
