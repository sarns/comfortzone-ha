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

## Long-term raw capture

To correlate currently unknown fields with values shown on the heat-pump
display, temporarily add this option below `comfortzone_ex:` and install the
firmware through OTA:

```yaml
  raw_frame_logging: true
```

The native API and all regular Home Assistant entities continue to work while
capture logging is enabled. Connect the ESP32 USB port to a Raspberry Pi and
record a timestamped, compressed capture for twelve hours:

```text
python3 tools/capture_usb_serial.py /dev/ttyACM0 --seconds 43200 \
  --timestamp-lines --output captures/comfortzone-long.log.gz
```

Photograph the heat-pump measurement screen at several known times, including
idle operation and active hot-water or heating cycles. Ensure that each photo
shows or records the exact local time and both displayed flow readings. Disable
`raw_frame_logging` and install the normal firmware again after the capture.

The compressed and legacy capture formats can both be summarized with:

```text
python3 tools/analyze_capture.py captures/comfortzone-long.log.gz --samples
```

## Grafana dashboard

Import `grafana/comfortzone-ex-dashboard.json` as a Grafana
`dashboard.grafana.app/v2` resource. It was exported by Grafana 13.2.1 and
contains the datasource UID from that installation. Replace the datasource
name in the JSON before importing it into another Grafana installation. The
datasource must use InfluxQL. Queries use Grafana's `$timeFilter` and
`$__interval` macros with a 20-second minimum interval; the dashboard refreshes
once per minute.

The dashboard contains all Comfortzone entities plus the added Shelly heat-pump
energy counter. Temperature measurements and setpoints share one panel, while
power, frequency, energy, runtime, operating states, and RS485 diagnostics are
grouped by compatible units. Enable the diagnostic entities that are disabled
by default in Home Assistant if you want the RS485 counter panel to contain
data.

Reapply the rolling seven-day energy-panel calculation after editing the JSON
with:

```powershell
.\.esphome-venv\Scripts\python.exe tools\generate_grafana_dashboard.py
```
