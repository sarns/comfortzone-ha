#include "comfortzone_ex.h"

#include <cmath>
#include <cstring>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome {
namespace comfortzone_ex {

static const char *const TAG = "comfortzone_ex";
static constexpr const char *const PROTOCOL_COVERAGE = "8 of 22 read registers decoded";

void ComfortzoneExComponent::setup() {
  this->receiver_enable_pin_->setup();
  this->receiver_enable_pin_->digital_write(false);
  this->bus_online_binary_sensor_->publish_state(false);
  this->protocol_coverage_text_sensor_->publish_state(PROTOCOL_COVERAGE);
  ESP_LOGI(TAG, "RS485 receiver enabled; writes %s", this->allow_write_ ? "allowed" : "disabled");
  ESP_LOGI(TAG, "Raw frame logging: %s", this->raw_frame_logging_ ? "enabled" : "disabled");
}

void ComfortzoneExComponent::loop() {
  uint8_t value;
  while (this->available() && this->read_byte(&value)) {
    this->rs485_bytes_++;
    this->consume_byte_(value);
  }
  this->check_tx_timeouts_();

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
  this->last_loop_end_us_ = micros();
}

void ComfortzoneExComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Comfortzone EX monitor:");
  ESP_LOGCONFIG(TAG, "  Writes: %s", this->allow_write_ ? "allowed" : "disabled");
  LOG_PIN("  Receiver enable pin: ", this->receiver_enable_pin_);
  ESP_LOGCONFIG(TAG, "  Protocol family: EX 0B10");
  ESP_LOGCONFIG(TAG, "  Implemented read registers: 8 of 22 observed");
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
  // Before logging: the send window after a request is short.
  this->handle_tx_on_frame_();
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

void FanSpeedSelect::control(size_t index) { this->parent_->request_fan_speed(index); }

void SetpointNumber::control(float value) { this->parent_->request_setpoint(this->slot_, value); }

void HotWaterSwitch::write_state(bool state) { this->parent_->request_switch(this->slot_, state); }

void ComfortzoneExComponent::request_fan_speed(size_t option_index) {
  if (option_index > 2)
    return;
  // Register 00DC03 = 004503 byte 151; the speeds are 1, 2 and 3.
  const uint8_t value = static_cast<uint8_t>(option_index + 1);
  this->queue_write_(TX_FAN, 0x00, 0xDC, 0x03, &value, 1);
}

void ComfortzoneExComponent::request_setpoint(TxSlot slot, float value) {
  const bool hot_water = slot == TX_HOT_WATER_TARGET;
  const float low = hot_water ? 40.0f : 18.0f;
  const float high = hot_water ? 55.0f : 25.0f;
  if (std::isnan(value) || value < low || value > high) {
    ESP_LOGW(TAG, "CZTX rejected: setpoint %.1f outside %.1f..%.1f", value, low, high);
    return;
  }

  const int16_t raw = static_cast<int16_t>(std::lround(value * 10.0f));
  const uint8_t bytes[] = {static_cast<uint8_t>(raw & 0xFF), static_cast<uint8_t>(raw >> 8)};
  if (hot_water) {
    this->queue_write_(slot, 0x00, 0x45, 0x03, bytes, 2);  // 004503 byte 0
  } else {
    this->queue_write_(slot, 0x00, 0x92, 0x02, bytes, 2);  // 008902 byte 9
  }
}

void ComfortzoneExComponent::request_switch(TxSlot slot, bool on) {
  const bool extra = slot == TX_HOT_WATER_EXTRA;
  const uint32_t now = millis();
  if (on) {
    const int8_t other = extra ? this->published_legionella_ : this->published_hot_water_extra_;
    const uint32_t off_ms = this->switch_off_ms_[slot];
    if (other == 1 || (off_ms != 0 && now - off_ms < SWITCH_ON_LOCKOUT_MS)) {
      ESP_LOGW(TAG, "CZTX rejected: %s", other == 1 ? "other hot water program active" : "switched off too recently");
      this->forget_published_state_(slot);
      return;
    }
  } else {
    this->switch_off_ms_[slot] = now == 0 ? 1 : now;
  }

  // Prefix 0x81 sets bits, 0x41 clears them: main-screen WW Extra 001D bit 0x40, legionella 0017 bit 0x01.
  const uint8_t prefix = on ? 0x81 : 0x41;
  const uint8_t reg = extra ? 0x1D : 0x17;
  const uint8_t set_bits = extra ? 0x40 : 0x01;
  const uint8_t bytes[] = {static_cast<uint8_t>(on ? set_bits : static_cast<uint8_t>(~set_bits)),
                           static_cast<uint8_t>(on ? 0x00 : 0xFF)};
  this->queue_write_(slot, prefix, reg, 0x00, bytes, 2);
}

void ComfortzoneExComponent::queue_write_(TxSlot slot, uint8_t reg0, uint8_t reg1, uint8_t reg2,
                                          const uint8_t *value, size_t size) {
  if (!this->allow_write_) {
    ESP_LOGW(TAG, "CZTX rejected: allow_write is off");
    this->forget_published_state_(slot);
    return;
  }

  // Panel write frame as seen on the bus.
  static constexpr uint8_t HEADER[] = {0x65, 0x6F, 0xDE, 0x02, 0xD3, 0x5E, 0x41, 0x44, 0x44, 0x52,
                                       0x00, 'W',  0x01, 0x02, 0x03, 0x04, 0x0B, 0x10};
  TxRequest &request = this->tx_requests_[slot];
  std::memcpy(request.frame, HEADER, sizeof(HEADER));
  request.frame[18] = reg0;
  request.frame[19] = reg1;
  request.frame[20] = reg2;
  std::memcpy(request.frame + HEADER_SIZE, value, size);
  request.size = static_cast<uint8_t>(HEADER_SIZE + size + 1);
  request.frame[10] = request.size;
  request.frame[request.size - 1] = crc8_maxim_(request.frame, request.size - 1);
  request.attempts = 0;
  request.queued = true;
  const uint32_t now = millis();
  request.queued_ms = now;
  this->high_frequency_.start();
  ESP_LOGI(TAG, "CZTX queued slot %u register %02X%02X%02X", slot, reg0, reg1, reg2);
}

void ComfortzoneExComponent::handle_tx_on_frame_() {
  if (this->tx_awaiting_ack_) {
    if (this->frame_[11] == 'w' && std::memcmp(this->frame_ + 18, this->tx_active_register_, 3) == 0) {
      ESP_LOGI(TAG, "CZTX acknowledged after %lu ms", static_cast<unsigned long>(millis() - this->tx_sent_ms_));
      this->tx_awaiting_ack_ = false;
    }
    return;
  }

  if (this->frame_[11] == 'R' && this->in_tx_window_() && !this->available())
    this->transmit_next_();
}

bool ComfortzoneExComponent::in_tx_window_() const {
  // The heat pump starts these replies at least about 45 ms after the request, which leaves room for
  // a write of 12.5 ms. It answers the write after the reply and the panel's next request.
  return this->register_is_(0x00, 0x45, 0x03) || this->register_is_(0x00, 0x89, 0x02) ||
         this->register_is_(0x00, 0x8D, 0x04) || this->register_is_(0x03, 0xBD, 0x0D) ||
         this->register_is_(0x03, 0x0B, 0x0D) || this->register_is_(0x01, 0x40, 0x03);
}

void ComfortzoneExComponent::transmit_next_() {
  const uint32_t now = millis();
  if (this->tx_sent_ms_ != 0 && now - this->tx_sent_ms_ < TX_MIN_SPACING_MS)
    return;

  // A stalled loop may have seen the request late, and the window could already be over.
  const uint32_t loop_age_us = micros() - this->last_loop_end_us_;
  if (loop_age_us > TX_MAX_LOOP_AGE_US)
    return;

  for (uint8_t slot = 0; slot < TX_SLOT_COUNT; slot++) {
    TxRequest &request = this->tx_requests_[slot];
    if (!request.queued)
      continue;

    request.queued = false;
    request.attempts++;
    this->tx_active_slot_ = static_cast<TxSlot>(slot);
    std::memcpy(this->tx_active_register_, request.frame + 18, 3);
    this->receiver_enable_pin_->digital_write(true);
    this->write_array(request.frame, request.size);
    this->flush();
    this->receiver_enable_pin_->digital_write(false);
    this->tx_sent_ms_ = millis();
    this->tx_awaiting_ack_ = true;
    ESP_LOGI(TAG, "CZTX attempt %u slot %u after R %02X%02X%02X, loop age %lu us, took %lu ms", request.attempts, slot,
             this->frame_[18], this->frame_[19], this->frame_[20], static_cast<unsigned long>(loop_age_us),
             static_cast<unsigned long>(this->tx_sent_ms_ - now));
    return;
  }
}

void ComfortzoneExComponent::check_tx_timeouts_() {
  const uint32_t now = millis();
  if (this->tx_awaiting_ack_ && now - this->tx_sent_ms_ >= TX_ACK_TIMEOUT_MS) {
    this->tx_awaiting_ack_ = false;
    TxRequest &request = this->tx_requests_[this->tx_active_slot_];
    if (!request.queued) {
      if (request.attempts >= TX_MAX_ATTEMPTS) {
        ESP_LOGW(TAG, "CZTX failed: no acknowledge after %u attempts", request.attempts);
        this->forget_published_state_(this->tx_active_slot_);
      } else {
        ESP_LOGW(TAG, "CZTX no acknowledge for attempt %u, retrying", request.attempts);
        request.queued = true;
      }
    }
  }

  bool work_left = this->tx_awaiting_ack_;
  for (uint8_t slot = 0; slot < TX_SLOT_COUNT; slot++) {
    TxRequest &request = this->tx_requests_[slot];
    if (request.queued && now - request.queued_ms >= TX_QUEUE_TIMEOUT_MS) {
      ESP_LOGW(TAG, "CZTX dropped slot %u: no bus window", slot);
      request.queued = false;
      this->forget_published_state_(static_cast<TxSlot>(slot));
    }
    work_left = work_left || request.queued;
  }
  if (!work_left)
    this->high_frequency_.stop();
}

// Makes the next bus reply publish the entity again, so that a failed request does not stay on screen.
void ComfortzoneExComponent::forget_published_state_(TxSlot slot) {
  switch (slot) {
    case TX_FAN:
      this->published_fan_speed_ = 0;
      break;
    case TX_HOT_WATER_TARGET:
      this->published_hot_water_target_ = SETPOINT_UNKNOWN;
      break;
    case TX_ROOM_SETPOINT:
      this->published_room_setpoint_ = SETPOINT_UNKNOWN;
      break;
    case TX_HOT_WATER_EXTRA:
      this->published_hot_water_extra_ = SWITCH_UNKNOWN;
      break;
    case TX_LEGIONELLA:
      this->published_legionella_ = SWITCH_UNKNOWN;
      break;
    default:
      break;
  }
}

void ComfortzoneExComponent::update_write_entities_status_(const uint8_t *payload) {
  // 010400 byte 25 bit 0x40: main-screen WW Extra. Byte 18 bit 0x20 is set for both programs.
  const int8_t extra = (payload[25] & 0x40) != 0 ? 1 : 0;
  const int8_t legionella = ((payload[18] & 0x20) != 0 && extra == 0) ? 1 : 0;
  if (extra != this->published_hot_water_extra_) {
    this->published_hot_water_extra_ = extra;
    if (this->hot_water_extra_switch_ != nullptr)
      this->hot_water_extra_switch_->publish_state(extra == 1);
  }
  if (legionella != this->published_legionella_) {
    this->published_legionella_ = legionella;
    if (this->legionella_switch_ != nullptr)
      this->legionella_switch_->publish_state(legionella == 1);
  }
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
    this->hot_water_mode_ = (payload[28] & 0x08) != 0;
    this->operating_mode_known_ = true;
    this->update_write_entities_status_(payload);
    // Status word bit 0x0020 is set while main-screen WW Extra or legionella prevention runs.
    this->hot_water_boost_binary_sensor_->publish_state((payload[18] & 0x20) != 0);
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
    const int16_t raw = static_cast<int16_t>(read_u16_le_(payload + 9));
    if (raw != this->published_room_setpoint_) {
      this->published_room_setpoint_ = raw;
      this->last_publish_ms_[PUBLISH_ROOM_SETPOINT] = 0;
      if (this->room_setpoint_setting_ != nullptr)
        this->room_setpoint_setting_->publish_state(raw / 10.0f);
    }
    if (this->should_publish_(PUBLISH_ROOM_SETPOINT))
      this->room_setpoint_sensor_->publish_state(raw / 10.0f);
    return true;
  }

  // Full reply only: the panel also reads back 2-byte fragments after its own writes.
  if (this->register_is_(0x00, 0x45, 0x03) && payload_size >= 152) {
    const int16_t raw = static_cast<int16_t>(read_u16_le_(payload));
    const uint8_t fan_speed = payload[151];
    if (raw != this->published_hot_water_target_) {
      this->published_hot_water_target_ = raw;
      this->last_publish_ms_[PUBLISH_HOT_WATER_TARGET] = 0;
      if (this->hot_water_target_setting_ != nullptr)
        this->hot_water_target_setting_->publish_state(raw / 10.0f);
    }
    if (fan_speed != this->published_fan_speed_) {
      this->published_fan_speed_ = fan_speed;
      this->last_publish_ms_[PUBLISH_HOT_WATER_TARGET] = 0;
      if (this->fan_speed_setting_ != nullptr && fan_speed >= 1 && fan_speed <= 3)
        this->fan_speed_setting_->publish_state(static_cast<size_t>(fan_speed - 1));
    }
    if (this->should_publish_(PUBLISH_HOT_WATER_TARGET)) {
      this->hot_water_target_sensor_->publish_state(raw / 10.0f);
      this->fan_speed_text_sensor_->publish_state(fan_speed_name_(fan_speed));
    }
    return true;
  }

  if (this->register_is_(0x00, 0xF7, 0x03) && payload_size >= 8) {
    if (this->should_publish_(PUBLISH_FILTER)) {
      this->filter_change_time_sensor_->publish_state(read_u16_le_(payload + 6));
    }
    return true;
  }

  if (this->register_is_(0x01, 0xD1, 0x02) && payload_size >= 47) {
    // Offset 45 is the actual inverter frequency; offset 33 is the frequency setpoint.
    this->compressor_frequency_x10_ = read_u16_le_(payload + 45);
    if (this->should_publish_(PUBLISH_FAN_AND_COMPRESSOR)) {
      this->fan_power_sensor_->publish_state(read_u16_le_(payload + 2) / 10.0f);
      this->compressor_frequency_sensor_->publish_state(
          this->compressor_frequency_x10_ / 10.0f);
      this->compressor_target_frequency_sensor_->publish_state(read_u16_le_(payload + 33) / 10.0f);
      this->condenser_temperature_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload + 15)) / 10.0f);
      this->high_pressure_sensor_->publish_state(read_u16_le_(payload + 17) / 10.0f);
      this->low_pressure_sensor_->publish_state(read_u16_le_(payload + 19) / 10.0f);
      this->pressure_ratio_sensor_->publish_state(read_u16_le_(payload + 21) / 10.0f);
      this->update_compressor_state_();
    }
    // One flow meter serves both circuits; the controller shows 0 for the inactive one.
    if (this->operating_mode_known_ && this->should_publish_(PUBLISH_FLOW_RATES)) {
      const float flow = read_u16_le_(payload + 10) / 10.0f;
      this->heating_flow_sensor_->publish_state(this->hot_water_mode_ ? 0.0f : flow);
      this->hot_water_flow_sensor_->publish_state(this->hot_water_mode_ ? flow : 0.0f);
    }
    return true;
  }

  if (this->register_is_(0x01, 0xF9, 0x01) && payload_size >= 99) {
    if (this->should_publish_(PUBLISH_HEATING)) {
      this->calculated_flow_temperature_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload)) / 10.0f);
      this->required_heating_power_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload + 22)));
      this->active_hot_water_target_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload + 97)) / 10.0f);
    }
    return true;
  }

  if (this->register_is_(0x01, 0x40, 0x03) && payload_size >= 90) {
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
      this->target_superheat_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload + 82)) / 10.0f);
      this->superheat_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload + 86)) / 10.0f);
      this->expansion_valve_position_sensor_->publish_state(
          static_cast<int16_t>(read_u16_le_(payload + 88)) / 10.0f);
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
