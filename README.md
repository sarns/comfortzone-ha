# Comfortzone EX for Home Assistant

This project reads the Comfortzone EX controller bus with a Waveshare
ESP32-S3-RS485-CAN board and publishes confirmed readings to Home Assistant
through the ESPHome native API.

The implementation is receive-only. The RS485 transmitter-enable pin is held
LOW, and the ESPHome UART is configured without a TX pin.

## Hardware and protocol

- RS485 RX: GPIO18, inverted
- RS485 receiver enable: GPIO21, held LOW
- Serial format: 19200 baud, 8N1
- Observed register family: `0B 10`
- Confirmed read registers: 6 of 22 recurring groups

## ESPHome installation

1. Copy `esphome/comfortzone-ex.yaml` and the `components` directory into an
   ESPHome configuration directory, preserving their relative layout.
2. Copy `esphome/secrets.example.yaml` to `esphome/secrets.yaml` and replace all
   placeholder values.
3. Validate and compile:

   ```text
   esphome config esphome/comfortzone-ex.yaml
   esphome compile esphome/comfortzone-ex.yaml
   ```

   On Windows, set `ESPHOME_ESP_IDF_PREFIX` to a short directory such as
   `C:\idf` if ESPHome warns that the ESP-IDF tool path exceeds the legacy
   path-length limit.

4. Install the first build through USB. Later updates can use ESPHome OTA; OTA
   preserves the Wi-Fi password because it is supplied by the ignored
   `esphome/secrets.yaml` file.
5. If the configured Wi-Fi is unavailable, connect to the
   `Comfortzone EX Setup` access point and enter the target Wi-Fi credentials.
   Copy those credentials into `esphome/secrets.yaml` before the next firmware
   build, because ESPHome's fallback-provisioned credential is tied to the
   firmware configuration hash.
6. Add the discovered `Comfortzone EX` device through Home Assistant's ESPHome
   integration and provide the API encryption key from `secrets.yaml`.

## Published entities

The component exposes nine named temperatures, room and hot-water targets,
compressor frequency, four instantaneous power readings, three lifetime energy
counters, two runtime counters, compressor/heater state, and fan speed.

Measurements are decoded continuously and published to Home Assistant once per
minute. Bus connectivity changes are published immediately.

Diagnostic entities report RS485 availability, last decoded-frame age, byte and
frame counts, CRC failures, unsupported frames, and protocol
coverage. Counter diagnostics are disabled by default in Home Assistant.

`Protocol Coverage` describes the implemented decoder, not current bus health.
Unknown registers are counted but never published under speculative names.
