import json
from pathlib import Path


DASHBOARD_PATH = Path("grafana/comfortzone-ex-dashboard.json")
DATASOURCE = {"type": "influxdb", "uid": "${DS_INFLUXDB}"}


def numeric_target(ref_id: str, entity: str, alias: str) -> dict:
    measurement = f"sensor.comfortzone_ex_{entity}"
    return {
        "alias": alias,
        "datasource": DATASOURCE,
        "query": (
            f'SELECT distinct("value") FROM "{measurement}" '
            "WHERE $timeFilter GROUP BY time($__interval) fill(null) ORDER BY time ASC"
        ),
        "rawQuery": True,
        "refId": ref_id,
        "resultFormat": "time_series",
    }


def state_target(ref_id: str, domain: str, entity: str, alias: str) -> dict:
    measurement = f"{domain}.comfortzone_ex_{entity}"
    return {
        "alias": alias,
        "datasource": DATASOURCE,
        "query": (
            f'SELECT last("state") FROM "{measurement}" '
            "WHERE $timeFilter GROUP BY time($__interval) fill(previous) ORDER BY time ASC"
        ),
        "rawQuery": True,
        "refId": ref_id,
        "resultFormat": "time_series",
    }


def time_series_panel(panel_id: int, title: str, grid: dict, unit: str, targets: list[dict]) -> dict:
    return {
        "datasource": DATASOURCE,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "drawStyle": "line",
                    "fillOpacity": 8,
                    "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "lineInterpolation": "linear",
                    "lineWidth": 2,
                    "pointSize": 4,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "never",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"},
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}],
                },
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": grid,
        "id": panel_id,
        "interval": "20s",
        "options": {
            "legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "none"},
        },
        "targets": targets,
        "title": title,
        "type": "timeseries",
    }


def stat_panel(panel_id: int, title: str, grid: dict, unit: str, targets: list[dict]) -> dict:
    return {
        "datasource": DATASOURCE,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}],
                },
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": grid,
        "id": panel_id,
        "interval": "20s",
        "options": {
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showPercentChange": False,
            "textMode": "auto",
            "wideLayout": True,
        },
        "targets": targets,
        "title": title,
        "type": "stat",
    }


temperature_entities = [
    ("outdoor_temperature", "Outdoor"),
    ("flow_temperature", "Flow"),
    ("return_temperature", "Return"),
    ("indoor_temperature", "Indoor"),
    ("hot_gas_temperature", "Hot Gas"),
    ("exchanger_outlet_temperature", "Exchanger Outlet"),
    ("evaporator_inlet_temperature", "Evaporator Inlet"),
    ("exhaust_air_temperature", "Exhaust Air"),
    ("hot_water_temperature", "Hot Water"),
    ("room_setpoint", "Room Setpoint"),
    ("hot_water_target", "Hot Water Target"),
]
power_entities = [
    ("compressor_output_power", "Compressor Output"),
    ("additional_heater_power", "Additional Heater"),
    ("total_output_power", "Total Output"),
    ("compressor_input_power", "Compressor Input"),
]
energy_entities = [
    ("compressor_energy", "Compressor"),
    ("additional_heater_energy", "Additional Heater"),
    ("hot_water_energy", "Hot Water"),
]
runtime_entities = [
    ("compressor_runtime", "Compressor Runtime"),
    ("total_runtime", "Total Runtime"),
]
diagnostic_entities = [
    ("rs485_bytes", "RS485 Bytes"),
    ("valid_frames", "Valid Frames"),
    ("decoded_frames", "Decoded Frames"),
    ("unsupported_frames", "Unsupported Frames"),
    ("crc_errors", "CRC Errors"),
]


def targets(items: list[tuple[str, str]]) -> list[dict]:
    return [numeric_target(chr(65 + index), entity, alias) for index, (entity, alias) in enumerate(items)]


panels = [
    time_series_panel(1, "Temperatures and Setpoints", {"h": 11, "w": 24, "x": 0, "y": 0}, "celsius", targets(temperature_entities)),
    time_series_panel(2, "Power", {"h": 9, "w": 12, "x": 0, "y": 11}, "watt", targets(power_entities)),
    time_series_panel(
        3,
        "Compressor Frequency",
        {"h": 9, "w": 12, "x": 12, "y": 11},
        "hertz",
        [numeric_target("A", "compressor_frequency", "Compressor Frequency")],
    ),
    time_series_panel(4, "Energy", {"h": 9, "w": 12, "x": 0, "y": 20}, "kwh", targets(energy_entities)),
    time_series_panel(5, "Runtime", {"h": 9, "w": 12, "x": 12, "y": 20}, "m", targets(runtime_entities)),
    {
        "datasource": DATASOURCE,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"fillOpacity": 70, "lineWidth": 0, "spanNulls": True},
                "mappings": [
                    {"options": {"off": {"color": "red", "index": 0, "text": "Off"}, "on": {"color": "green", "index": 1, "text": "On"}}, "type": "value"}
                ],
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
            },
            "overrides": [],
        },
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 29},
        "id": 6,
        "interval": "20s",
        "options": {
            "alignValue": "left",
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "mergeValues": True,
            "rowHeight": 0.8,
            "showValue": "auto",
            "tooltip": {"mode": "single", "sort": "none"},
        },
        "targets": [
            state_target("A", "binary_sensor", "compressor_running", "Compressor Running"),
            state_target("B", "binary_sensor", "additional_heater_active", "Additional Heater Active"),
            state_target("C", "binary_sensor", "rs485_bus_online", "RS485 Bus Online"),
            state_target("D", "text_sensor", "fan_speed", "Fan Speed"),
        ],
        "title": "Operating States",
        "type": "state-timeline",
    },
    time_series_panel(7, "RS485 Counters", {"h": 9, "w": 16, "x": 0, "y": 37}, "short", targets(diagnostic_entities)),
    stat_panel(
        8,
        "Last Decoded Frame Age",
        {"h": 9, "w": 4, "x": 16, "y": 37},
        "s",
        [numeric_target("A", "last_decoded_frame_age", "Age")],
    ),
    {
        **stat_panel(
            9,
            "Protocol Coverage",
            {"h": 9, "w": 4, "x": 20, "y": 37},
            "string",
            [state_target("A", "text_sensor", "protocol_coverage", "Coverage")],
        ),
        "description": "Decoder coverage reported by the ESPHome component.",
    },
]

dashboard = {
    "__inputs": [
        {
            "name": "DS_INFLUXDB",
            "label": "InfluxDB",
            "description": "InfluxDB datasource containing Home Assistant history",
            "type": "datasource",
            "pluginId": "influxdb",
            "pluginName": "InfluxDB",
        }
    ],
    "__requires": [
        {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "10.0.0"},
        {"type": "datasource", "id": "influxdb", "name": "InfluxDB", "version": "1.0.0"},
        {"type": "panel", "id": "timeseries", "name": "Time series", "version": ""},
        {"type": "panel", "id": "stat", "name": "Stat", "version": ""},
        {"type": "panel", "id": "state-timeline", "name": "State timeline", "version": ""},
    ],
    "annotations": {"list": []},
    "description": "Comfortzone EX heat-pump telemetry received through ESPHome and Home Assistant.",
    "editable": True,
    "graphTooltip": 1,
    "id": None,
    "links": [],
    "panels": panels,
    "refresh": "1m",
    "schemaVersion": 39,
    "tags": ["comfortzone", "heat-pump", "esphome", "influxdb"],
    "templating": {"list": []},
    "time": {"from": "now-6h", "to": "now"},
    "timepicker": {},
    "timezone": "browser",
    "title": "Comfortzone EX Heat Pump",
    "uid": "comfortzone-ex",
    "version": 1,
}

DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
DASHBOARD_PATH.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
print(DASHBOARD_PATH)
