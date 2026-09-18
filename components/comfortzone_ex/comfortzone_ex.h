#pragma once

#include <cstddef>
#include <cstdint>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"
#include "esphome/core/gpio.h"

namespace esphome {
namespace comfortzone_ex {

class ComfortzoneExComponent : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::BUS; }

  void set_receiver_enable_pin(InternalGPIOPin *pin) { this->receiver_enable_pin_ = pin; }
  void set_raw_frame_logging(bool enabled) { this->raw_frame_logging_ = enabled; }

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

  enum PublishGroup : uint8_t {
    PUBLISH_TEMPERATURES,
    PUBLISH_ROOM_SETPOINT,
    PUBLISH_HOT_WATER_TARGET,
    PUBLISH_FAN_AND_COMPRESSOR,
    PUBLISH_POWER,
    PUBLISH_COUNTERS,
    PUBLISH_CALCULATED_FLOW,
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

  uint16_t compressor_frequency_x10_{0};
  uint16_t compressor_input_power_w_{0};
  uint16_t current_flow_x10_{0};
  uint16_t heating_flow_x10_{0};
  bool heating_flow_known_{false};

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
  text_sensor::TextSensor *fan_speed_text_sensor_{nullptr};
  text_sensor::TextSensor *protocol_coverage_text_sensor_{nullptr};
};

}  // namespace comfortzone_ex
}  // namespace esphome
