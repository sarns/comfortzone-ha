# Comfortzone EX for Home Assistant

This project reads the Comfortzone EX controller bus with a Waveshare
ESP32-S3-RS485-CAN board and publishes confirmed readings to Home Assistant
through the ESPHome native API. It can also write fan speed, setpoints and the
hot-water programs.

Writing needs `allow_write: true`. Without it the firmware never transmits and
the RS485 transmitter-enable pin stays LOW.

Reference project
https://github.com/qix67/comfortzone_heatpump

## Hardware and protocol

- RS485 RX: GPIO18, not inverted (bus A/B wired to board A/B)
- RS485 TX: GPIO17
- RS485 direction: GPIO21, HIGH only while a frame is sent
- Serial format: 19200 baud, 8N1
- Observed register family: `0B 10`
- Implemented read registers: 8 of 22 recurring groups

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
the active hot-water target, calculated flow temperature, required heating
power, fan duty percentage, filter time remaining, the two flow readings,
actual and target compressor frequency, condenser temperature, high and low
pressure, pressure ratio, expansion-valve position, superheat and target
superheat, four instantaneous power readings, three lifetime energy counters,
two runtime counters, compressor/heater/hot-water-boost state, and fan speed.

The heat pump has a single flow meter. The controller shows its value as
heating flow in space-heating mode and as hot-water flow in hot-water mode, and
0 for the inactive circuit; the component does the same, using the hot-water
mode bit (`010400` byte 28, bit `0x08`).

`Hot Water Boost` is on while either of two functions runs. "WW Extra" from the
main screen heats to 55 °C. The immediate legionella prevention heats to 65 °C
and then holds that temperature until "WW Extra Zeit" (180 min) expires. The
`Active Hot Water Target` entity shows which target applies.

All register mappings were confirmed against display photos; see
`doc/variablen-uebersicht.md` and `doc/capture-analyse-2026-10-30-tests.md`.
Version 0.4.0 corrected five earlier mappings: compressor frequency (it was
the setpoint), calculated flow temperature (it was a constant 15 °C setting),
heating and hot-water flow, and fan speed. Their history before the update is
not comparable.

The flow measurements and calculated flow temperature use ESPHome's default
change-based state handling (`force_update: false`). They are evaluated once
per minute, while Home Assistant only records a new state when the value
changes.

All entities use the area-prefixed IDs `sensor.technikkeller_comfortzone_ex_*`
and `binary_sensor.technikkeller_comfortzone_ex_*`. Entities created before
2026-10-30 were renamed from `*.comfortzone_ex_*` with
`tools/ha_rename_entities.py`; their earlier InfluxDB history was copied to
the new measurement names (see `grafana/influx-copy-renamed.influxql`).

Measurements are decoded continuously and published to Home Assistant once per
minute. Bus connectivity changes are published immediately.

Diagnostic entities report RS485 availability, last decoded-frame age, byte and
frame counts, CRC failures, unsupported frames, and protocol
coverage. Counter diagnostics are disabled by default in Home Assistant.

`Protocol Coverage` describes the implemented decoder, not current bus health.
Unknown registers are counted but never published under speculative names.

## Controls

| Entity | Range | Effect |
|---|---|---|
| `Fan Speed Setting` | Low, Normal, High | Fan stage |
| `Hot Water Target Setting` | 40–55 °C, step 0.5 | Hot-water setting |
| `Room Setpoint Setting` | 18–25 °C, step 0.5 | Heating reference temperature |
| `Hot Water Extra` | on/off | "WW Extra" from the main screen, 55 °C |
| `Legionella Prevention` | on/off | Immediate legionella prevention, 65 °C |

All five were tested on the bus. Both switches start the 3.5 kW heater after
about 1.5 minutes.

Every entity shows the value read back from the bus, so a change made on the
panel also appears here. A switch turns off by itself when the heat pump ends
the program. A change takes about 2–4 s to show up.

A frame goes out directly after a panel request to one of six registers, because
the heat pump answers those at least about 45 ms later. Unacknowledged writes are
retried twice, and a request without a bus window is dropped after 30 s.

The firmware rejects values outside the ranges above. A switch cannot turn on
while the other program runs, or within 60 s after it was turned off. Turning off
is always allowed. A reboot sends nothing. See
`doc/capture-analyse-2026-11-01-schreibtest.md`.

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
filter time is displayed as a single value. The refrigerant panels show high
and low pressure with the pressure ratio, and expansion-valve position with
superheat, target superheat and condenser temperature; the compressor panel
also shows the target frequency, and the operating-state timeline includes the
hot-water boost. Enable the diagnostic entities that
are disabled by default in Home Assistant if you want the RS485 counter panel
to contain data.

Reapply the rolling seven-day energy-panel calculation after editing the JSON
with:

```powershell
.\.esphome-venv\Scripts\python.exe tools\generate_grafana_dashboard.py
```
