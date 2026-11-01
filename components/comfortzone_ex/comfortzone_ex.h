#pragma once

#include <cstddef>
#include <cstdint>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/number/number.h"
#include "esphome/components/select/select.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"
#include "esphome/core/gpio.h"
#include "esphome/core/helpers.h"

namespace esphome {
namespace comfortzone_ex {

class ComfortzoneExComponent;

enum TxSlot : uint8_t {
  TX_FAN,
  TX_HOT_WATER_TARGET,
  TX_ROOM_SETPOINT,
  TX_HOT_WATER_EXTRA,
  TX_LEGIONELLA,
  TX_SLOT_COUNT,
};

class FanSpeedSelect : public select::Select {
 public:
  void set_parent(ComfortzoneExComponent *parent) { this->parent_ = parent; }

 protected:
  void control(size_t index) override;
  ComfortzoneExComponent *parent_{nullptr};
};

class SetpointNumber : public number::Number {
 public:
  void set_parent(ComfortzoneExComponent *parent, TxSlot slot) {
    this->parent_ = parent;
    this->slot_ = slot;
  }

 protected:
  void control(float value) override;
  ComfortzoneExComponent *parent_{nullptr};
  TxSlot slot_{TX_HOT_WATER_TARGET};
};

class HotWaterSwitch : public switch_::Switch {
 public:
  void set_parent(ComfortzoneExComponent *parent, TxSlot slot) {
    this->parent_ = parent;
    this->slot_ = slot;
  }

 protected:
  void write_state(bool state) override;
  ComfortzoneExComponent *parent_{nullptr};
  TxSlot slot_{TX_HOT_WATER_EXTRA};
};

class ComfortzoneExComponent : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::BUS; }

  void set_receiver_enable_pin(InternalGPIOPin *pin) { this->receiver_enable_pin_ = pin; }
  void set_raw_frame_logging(bool enabled) { this->raw_frame_logging_ = enabled; }
  void set_allow_write(bool enabled) { this->allow_write_ = enabled; }

  void set_fan_speed_setting(FanSpeedSelect *value) {
    this->fan_speed_setting_ = value;
    value->set_parent(this);
  }
  void set_hot_water_target_setting(SetpointNumber *value) {
    this->hot_water_target_setting_ = value;
    value->set_parent(this, TX_HOT_WATER_TARGET);
  }
  void set_room_setpoint_setting(SetpointNumber *value) {
    this->room_setpoint_setting_ = value;
    value->set_parent(this, TX_ROOM_SETPOINT);
  }
  void set_hot_water_extra_switch(HotWaterSwitch *value) {
    this->hot_water_extra_switch_ = value;
    value->set_parent(this, TX_HOT_WATER_EXTRA);
  }
  void set_legionella_switch(HotWaterSwitch *value) {
    this->legionella_switch_ = value;
    value->set_parent(this, TX_LEGIONELLA);
  }

  // All write requests go through a queue and are sent in the next bus window.
  void request_fan_speed(size_t option_index);
  void request_setpoint(TxSlot slot, float value);
  void request_switch(TxSlot slot, bool on);

#define CZ_SENSOR_SETTER(name) \
  void set_##name##_sensor(sensor::Sensor *value) { this->name##_sensor_ = value; }

  CZ_SENSOR_SETTER(outdoor_temperature)
  CZ_SENSOR_SETTER(flow_temperature)
  CZ_SENSOR_SETTER(return_temperature)
  CZ_SENSOR_SETTER(indoor_temperature)
  CZ_SENSOR_SETTER(hot_gas_temperature)
  CZ_SENSOR_SETTER(exchanger_out_temperature)
  CZ_SENSOR_SETTER(evaporator_in_temperature)
  CZ_SENSOR_SETTER(exhaust_air_temperature)
  CZ_SENSOR_SETTER(hot_water_temperature)
  CZ_SENSOR_SETTER(room_setpoint)
  CZ_SENSOR_SETTER(hot_water_target)
  CZ_SENSOR_SETTER(compressor_frequency)
  CZ_SENSOR_SETTER(compressor_output_power)
  CZ_SENSOR_SETTER(additional_heater_power)
  CZ_SENSOR_SETTER(total_output_power)
  CZ_SENSOR_SETTER(compressor_input_power)
  CZ_SENSOR_SETTER(compressor_energy)
  CZ_SENSOR_SETTER(additional_heater_energy)
  CZ_SENSOR_SETTER(hot_water_energy)
  CZ_SENSOR_SETTER(compressor_runtime)
  CZ_SENSOR_SETTER(total_runtime)
  CZ_SENSOR_SETTER(calculated_flow_temperature)
  CZ_SENSOR_SETTER(fan_power)
  CZ_SENSOR_SETTER(filter_change_time)
  CZ_SENSOR_SETTER(heating_flow)
  CZ_SENSOR_SETTER(hot_water_flow)
  CZ_SENSOR_SETTER(compressor_target_frequency)
  CZ_SENSOR_SETTER(condenser_temperature)
  CZ_SENSOR_SETTER(high_pressure)
  CZ_SENSOR_SETTER(low_pressure)
  CZ_SENSOR_SETTER(pressure_ratio)
  CZ_SENSOR_SETTER(expansion_valve_position)
  CZ_SENSOR_SETTER(superheat)
  CZ_SENSOR_SETTER(target_superheat)
  CZ_SENSOR_SETTER(required_heating_power)
  CZ_SENSOR_SETTER(active_hot_water_target)
  CZ_SENSOR_SETTER(last_decoded_frame_age)
  CZ_SENSOR_SETTER(rs485_bytes)
  CZ_SENSOR_SETTER(valid_frames)
  CZ_SENSOR_SETTER(decoded_frames)
  CZ_SENSOR_SETTER(unsupported_frames)
  CZ_SENSOR_SETTER(crc_errors)

#undef CZ_SENSOR_SETTER

  void set_compressor_running_binary_sensor(binary_sensor::BinarySensor *value) {
    this->compressor_running_binary_sensor_ = value;
  }
  void set_additional_heater_active_binary_sensor(binary_sensor::BinarySensor *value) {
    this->additional_heater_active_binary_sensor_ = value;
  }
  void set_bus_online_binary_sensor(binary_sensor::BinarySensor *value) {
    this->bus_online_binary_sensor_ = value;
  }
  void set_hot_water_boost_binary_sensor(binary_sensor::BinarySensor *value) {
    this->hot_water_boost_binary_sensor_ = value;
  }

  void set_fan_speed_text_sensor(text_sensor::TextSensor *value) {
    this->fan_speed_text_sensor_ = value;
  }
  void set_protocol_coverage_text_sensor(text_sensor::TextSensor *value) {
    this->protocol_coverage_text_sensor_ = value;
  }

 protected:
  static constexpr size_t HEADER_SIZE = 21;
  static constexpr size_t BUFFER_SIZE = 256;
  static constexpr uint32_t BUS_STALE_MS = 30000;
  static constexpr uint32_t PUBLISH_INTERVAL_MS = 60000;
  static constexpr uint32_t DIAGNOSTIC_INTERVAL_MS = 60000;
  static constexpr size_t TX_MAX_FRAME_SIZE = 24;
  static constexpr uint32_t TX_ACK_TIMEOUT_MS = 1000;
  static constexpr uint8_t TX_MAX_ATTEMPTS = 3;
  static constexpr uint32_t TX_MIN_SPACING_MS = 1000;
  static constexpr uint32_t TX_QUEUE_TIMEOUT_MS = 30000;
  static constexpr uint32_t TX_MAX_LOOP_AGE_US = 6000;
  static constexpr uint32_t SWITCH_ON_LOCKOUT_MS = 60000;
  static constexpr int16_t SETPOINT_UNKNOWN = INT16_MIN;
  static constexpr int8_t SWITCH_UNKNOWN = -1;

  struct TxRequest {
    uint8_t frame[TX_MAX_FRAME_SIZE];
    uint8_t size;
    uint8_t attempts;
    bool queued;
    uint32_t queued_ms;
  };

  enum PublishGroup : uint8_t {
    PUBLISH_TEMPERATURES,
    PUBLISH_ROOM_SETPOINT,
    PUBLISH_HOT_WATER_TARGET,
    PUBLISH_FAN_AND_COMPRESSOR,
    PUBLISH_POWER,
    PUBLISH_COUNTERS,
    PUBLISH_HEATING,
    PUBLISH_FILTER,
    PUBLISH_FLOW_RATES,
    PUBLISH_GROUP_COUNT,
  };

  void consume_byte_(uint8_t value);
  bool header_valid_() const;
  void process_frame_();
  void log_raw_frame_() const;
  bool decode_frame_();
  bool register_is_(uint8_t a, uint8_t b, uint8_t c) const;
  bool should_publish_(PublishGroup group);
  void update_compressor_state_();
  void publish_diagnostics_();

  static uint8_t crc8_maxim_(const uint8_t *data, size_t size);
  static uint16_t read_u16_le_(const uint8_t *data);
  static uint32_t read_u32_le_(const uint8_t *data);
  static const char *fan_speed_name_(uint8_t value);

  void queue_write_(TxSlot slot, uint8_t reg0, uint8_t reg1, uint8_t reg2, const uint8_t *value, size_t size);
  void handle_tx_on_frame_();
  bool in_tx_window_() const;
  void transmit_next_();
  void check_tx_timeouts_();
  void forget_published_state_(TxSlot slot);
  void update_write_entities_status_(const uint8_t *payload);

  InternalGPIOPin *receiver_enable_pin_{nullptr};
  uint8_t frame_[BUFFER_SIZE]{};
  size_t frame_size_{0};
  size_t expected_frame_size_{0};

  uint32_t rs485_bytes_{0};
  uint32_t valid_frames_{0};
  uint32_t decoded_frames_{0};
  uint32_t unsupported_frames_{0};
  uint32_t crc_errors_{0};
  uint32_t last_decoded_frame_ms_{0};
  uint32_t last_diagnostic_ms_{0};
  uint32_t last_publish_ms_[PUBLISH_GROUP_COUNT]{};
  bool bus_online_state_{false};
  bool raw_frame_logging_{false};
  bool allow_write_{false};

  TxRequest tx_requests_[TX_SLOT_COUNT]{};
  bool tx_awaiting_ack_{false};
  TxSlot tx_active_slot_{TX_FAN};
  uint8_t tx_active_register_[3]{};
  uint32_t tx_sent_ms_{0};
  uint32_t last_loop_end_us_{0};
  uint32_t switch_off_ms_[TX_SLOT_COUNT]{};
  HighFrequencyLoopRequester high_frequency_;

  uint8_t published_fan_speed_{0};
  int16_t published_hot_water_target_{SETPOINT_UNKNOWN};
  int16_t published_room_setpoint_{SETPOINT_UNKNOWN};
  int8_t published_hot_water_extra_{SWITCH_UNKNOWN};
  int8_t published_legionella_{SWITCH_UNKNOWN};

  FanSpeedSelect *fan_speed_setting_{nullptr};
  SetpointNumber *hot_water_target_setting_{nullptr};
  SetpointNumber *room_setpoint_setting_{nullptr};
  HotWaterSwitch *hot_water_extra_switch_{nullptr};
  HotWaterSwitch *legionella_switch_{nullptr};

  uint16_t compressor_frequency_x10_{0};
  uint16_t compressor_input_power_w_{0};
  // 010400 byte 28 bit 0x08: the single flow meter currently serves the hot-water circuit.
  bool hot_water_mode_{false};
  bool operating_mode_known_{false};

#define CZ_SENSOR_MEMBER(name) sensor::Sensor *name##_sensor_{nullptr};

  CZ_SENSOR_MEMBER(outdoor_temperature)
  CZ_SENSOR_MEMBER(flow_temperature)
  CZ_SENSOR_MEMBER(return_temperature)
  CZ_SENSOR_MEMBER(indoor_temperature)
  CZ_SENSOR_MEMBER(hot_gas_temperature)
  CZ_SENSOR_MEMBER(exchanger_out_temperature)
  CZ_SENSOR_MEMBER(evaporator_in_temperature)
  CZ_SENSOR_MEMBER(exhaust_air_temperature)
  CZ_SENSOR_MEMBER(hot_water_temperature)
  CZ_SENSOR_MEMBER(room_setpoint)
  CZ_SENSOR_MEMBER(hot_water_target)
  CZ_SENSOR_MEMBER(compressor_frequency)
  CZ_SENSOR_MEMBER(compressor_output_power)
  CZ_SENSOR_MEMBER(additional_heater_power)
  CZ_SENSOR_MEMBER(total_output_power)
  CZ_SENSOR_MEMBER(compressor_input_power)
  CZ_SENSOR_MEMBER(compressor_energy)
  CZ_SENSOR_MEMBER(additional_heater_energy)
  CZ_SENSOR_MEMBER(hot_water_energy)
  CZ_SENSOR_MEMBER(compressor_runtime)
  CZ_SENSOR_MEMBER(total_runtime)
  CZ_SENSOR_MEMBER(calculated_flow_temperature)
  CZ_SENSOR_MEMBER(fan_power)
  CZ_SENSOR_MEMBER(filter_change_time)
  CZ_SENSOR_MEMBER(heating_flow)
  CZ_SENSOR_MEMBER(hot_water_flow)
  CZ_SENSOR_MEMBER(compressor_target_frequency)
  CZ_SENSOR_MEMBER(condenser_temperature)
  CZ_SENSOR_MEMBER(high_pressure)
  CZ_SENSOR_MEMBER(low_pressure)
  CZ_SENSOR_MEMBER(pressure_ratio)
  CZ_SENSOR_MEMBER(expansion_valve_position)
  CZ_SENSOR_MEMBER(superheat)
  CZ_SENSOR_MEMBER(target_superheat)
  CZ_SENSOR_MEMBER(required_heating_power)
  CZ_SENSOR_MEMBER(active_hot_water_target)
  CZ_SENSOR_MEMBER(last_decoded_frame_age)
  CZ_SENSOR_MEMBER(rs485_bytes)
  CZ_SENSOR_MEMBER(valid_frames)
  CZ_SENSOR_MEMBER(decoded_frames)
  CZ_SENSOR_MEMBER(unsupported_frames)
  CZ_SENSOR_MEMBER(crc_errors)

#undef CZ_SENSOR_MEMBER

  binary_sensor::BinarySensor *compressor_running_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *additional_heater_active_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *bus_online_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *hot_water_boost_binary_sensor_{nullptr};
  text_sensor::TextSensor *fan_speed_text_sensor_{nullptr};
  text_sensor::TextSensor *protocol_coverage_text_sensor_{nullptr};
};

}  // namespace comfortzone_ex
}  // namespace esphome
