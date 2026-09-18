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
- Implemented read registers: 9 of 22 recurring groups

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
calculated flow temperature, fan duty percentage, filter time remaining, the
two flow readings, compressor frequency, four instantaneous power readings,
three lifetime energy counters, two runtime counters, compressor/heater state,
and fan speed.

The heating-flow register is included as a provisional mapping. It currently
matches the small idle flow shown by the controller and falls to zero during
hot-water production, but it still needs confirmation during active space
heating. The hot-water-flow field is already matched to the controller's
displayed hot-water flow during a hot-water cycle.

The five additional measurements use ESPHome's default change-based state
handling (`force_update: false`). They are evaluated once per minute, while
Home Assistant only records a new state when the value changes.

Home Assistant assigned these newly discovered entities the area-prefixed IDs
`sensor.technikkeller_comfortzone_ex_*`. The Grafana queries use those actual
InfluxDB measurement names; the older entities retain their original IDs
without the area prefix.

Measurements are decoded continuously and published to Home Assistant once per
minute. Bus connectivity changes are published immediately.

Diagnostic entities report RS485 availability, last decoded-frame age, byte and
frame counts, CRC failures, unsupported frames, and protocol
coverage. Counter diagnostics are disabled by default in Home Assistant.

`Protocol Coverage` describes the implemented decoder, not current bus health.
Unknown registers are counted but never published under speculative names.

## Confirm the heating-flow mapping later

When outdoor temperatures are low enough for space heating:

1. Leave the ESP32 connected and let the normal firmware run.
2. When the display shows a non-zero **Heizungsdurchfluss**, photograph the
   screen and note the exact local time to the nearest second.
3. Repeat once while space heating is idle or off, and once during an active
   hot-water cycle if possible.
4. Compare the photo with the ESP32 capture at those timestamps. The
   `Heating Flow` entity should match the display during space heating, while
   `Hot Water Flow` should match the hot-water value during the hot-water cycle.
5. If the values do not match, enable `raw_frame_logging` temporarily, repeat
   the timed photos, and adjust only the provisional heating-flow offset.

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
power, frequency, energy, runtime, fan and flow values, operating states, and
RS485 diagnostics are grouped into separate panels. Heating and hot-water flow
share one panel, fan power has its own percentage panel, and the remaining
filter time is displayed as a single value. Enable the diagnostic entities that
are disabled by default in Home Assistant if you want the RS485 counter panel
to contain data.

Reapply the rolling seven-day energy-panel calculation after editing the JSON
with:

```powershell
.\.esphome-venv\Scripts\python.exe tools\generate_grafana_dashboard.py
```
