import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import binary_sensor, sensor, text_sensor, uart
from esphome.const import (
    CONF_ID,
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_DURATION,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_FREQUENCY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_RUNNING,
    DEVICE_CLASS_TEMPERATURE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    UNIT_CELSIUS,
    UNIT_HERTZ,
    UNIT_KILOWATT_HOURS,
    UNIT_MINUTE,
    UNIT_SECOND,
    UNIT_WATT,
)

DEPENDENCIES = ["uart"]
AUTO_LOAD = ["binary_sensor", "sensor", "text_sensor"]

CONF_RECEIVER_ENABLE_PIN = "receiver_enable_pin"
CONF_RAW_FRAME_LOGGING = "raw_frame_logging"

TEMPERATURE_KEYS = (
    "outdoor_temperature",
    "flow_temperature",
    "return_temperature",
    "indoor_temperature",
    "hot_gas_temperature",
    "exchanger_out_temperature",
    "evaporator_in_temperature",
    "exhaust_air_temperature",
    "hot_water_temperature",
)

SETPOINT_KEYS = ("room_setpoint", "hot_water_target")

POWER_KEYS = (
    "compressor_output_power",
    "additional_heater_power",
    "total_output_power",
    "compressor_input_power",
)

ENERGY_KEYS = (
    "compressor_energy",
    "additional_heater_energy",
    "hot_water_energy",
)

RUNTIME_KEYS = ("compressor_runtime", "total_runtime")

DIAGNOSTIC_COUNTER_KEYS = (
    "rs485_bytes",
    "valid_frames",
    "decoded_frames",
    "unsupported_frames",
    "crc_errors",
)

comfortzone_ex_ns = cg.esphome_ns.namespace("comfortzone_ex")
ComfortzoneExComponent = comfortzone_ex_ns.class_(
    "ComfortzoneExComponent", cg.Component, uart.UARTDevice
)


def temperature_schema():
    return sensor.sensor_schema(
        unit_of_measurement=UNIT_CELSIUS,
        accuracy_decimals=1,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    )


def power_schema():
    return sensor.sensor_schema(
        unit_of_measurement=UNIT_WATT,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_POWER,
        state_class=STATE_CLASS_MEASUREMENT,
    )


CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(ComfortzoneExComponent),
            cv.Required(CONF_RECEIVER_ENABLE_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_RAW_FRAME_LOGGING, default=False): cv.boolean,
            **{cv.Required(key): temperature_schema() for key in TEMPERATURE_KEYS},
            **{cv.Required(key): temperature_schema() for key in SETPOINT_KEYS},
            cv.Required("compressor_frequency"): sensor.sensor_schema(
                unit_of_measurement=UNIT_HERTZ,
                accuracy_decimals=1,
                device_class=DEVICE_CLASS_FREQUENCY,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            **{cv.Required(key): power_schema() for key in POWER_KEYS},
            **{
                cv.Required(key): sensor.sensor_schema(
                    unit_of_measurement=UNIT_KILOWATT_HOURS,
                    accuracy_decimals=2,
                    device_class=DEVICE_CLASS_ENERGY,
                    state_class=STATE_CLASS_TOTAL_INCREASING,
                )
                for key in ENERGY_KEYS
            },
            **{
                cv.Required(key): sensor.sensor_schema(
                    unit_of_measurement=UNIT_MINUTE,
                    accuracy_decimals=0,
                    device_class=DEVICE_CLASS_DURATION,
                    state_class=STATE_CLASS_TOTAL_INCREASING,
                )
                for key in RUNTIME_KEYS
            },
            cv.Required("last_decoded_frame_age"): sensor.sensor_schema(
                unit_of_measurement=UNIT_SECOND,
                accuracy_decimals=0,
                device_class=DEVICE_CLASS_DURATION,
                state_class=STATE_CLASS_MEASUREMENT,
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            ),
            **{
                cv.Required(key): sensor.sensor_schema(
                    accuracy_decimals=0,
                    state_class=STATE_CLASS_TOTAL_INCREASING,
                    entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
                )
                for key in DIAGNOSTIC_COUNTER_KEYS
            },
            cv.Required("compressor_running"): binary_sensor.binary_sensor_schema(
                device_class=DEVICE_CLASS_RUNNING,
            ),
            cv.Required("additional_heater_active"): binary_sensor.binary_sensor_schema(),
            cv.Required("bus_online"): binary_sensor.binary_sensor_schema(
                device_class=DEVICE_CLASS_CONNECTIVITY,
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            ),
            cv.Required("fan_speed"): text_sensor.text_sensor_schema(),
            cv.Required("protocol_coverage"): text_sensor.text_sensor_schema(
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            ),
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    pin = await cg.gpio_pin_expression(config[CONF_RECEIVER_ENABLE_PIN])
    cg.add(var.set_receiver_enable_pin(pin))
    cg.add(var.set_raw_frame_logging(config[CONF_RAW_FRAME_LOGGING]))

    for key in TEMPERATURE_KEYS + SETPOINT_KEYS + POWER_KEYS + ENERGY_KEYS + RUNTIME_KEYS:
        entity = await sensor.new_sensor(config[key])
        cg.add(getattr(var, f"set_{key}_sensor")(entity))

    for key in ("compressor_frequency", "last_decoded_frame_age") + DIAGNOSTIC_COUNTER_KEYS:
        entity = await sensor.new_sensor(config[key])
        cg.add(getattr(var, f"set_{key}_sensor")(entity))

    for key in ("compressor_running", "additional_heater_active", "bus_online"):
        entity = await binary_sensor.new_binary_sensor(config[key])
        cg.add(getattr(var, f"set_{key}_binary_sensor")(entity))

    for key in ("fan_speed", "protocol_coverage"):
        entity = await text_sensor.new_text_sensor(config[key])
        cg.add(getattr(var, f"set_{key}_text_sensor")(entity))
