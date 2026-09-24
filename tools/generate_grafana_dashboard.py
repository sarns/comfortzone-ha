import json
import re
from copy import deepcopy
from pathlib import Path


DASHBOARD_PATH = Path("grafana/comfortzone-ex-dashboard.json")


def weekly_consumption_query(measurement: str) -> str:
    return (
        'SELECT CUMULATIVE_SUM("delta") AS "consumption" FROM '
        f'(SELECT DIFFERENCE(LAST("value")) AS "delta" FROM "{measurement}" '
        "GROUP BY time($__interval) fill(null)) "
        "WHERE time >= now() - 7d AND time <= now() ORDER BY time ASC"
    )


# Home Assistant only writes to InfluxDB when a state changes, so slow-moving
# entities often have no point inside the selected range. Each series therefore
# also carries the last value recorded before the range, which keeps the line
# and the legend's last value populated.
LAST_KNOWN_LOOKBACK = "365d"


def measurement_query(measurement: str, field: str = "value") -> str:
    return (
        f'SELECT "{field}" FROM '
        f'(SELECT last("{field}") AS "{field}" FROM "{measurement}" '
        f"WHERE time < ${{__from}}ms AND time >= ${{__from}}ms - {LAST_KNOWN_LOOKBACK}), "
        f'(SELECT last("{field}") AS "{field}" FROM "{measurement}" '
        "WHERE $timeFilter GROUP BY time($__interval) fill(previous)) "
        "ORDER BY time ASC"
    )


def last_value_query(measurement: str) -> str:
    return (
        f'SELECT last("value") FROM "{measurement}" '
        f"WHERE time <= ${{__to}}ms AND time > ${{__to}}ms - {LAST_KNOWN_LOOKBACK}"
    )


dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
if dashboard.get("apiVersion") != "dashboard.grafana.app/v2" or dashboard.get("kind") != "Dashboard":
    raise RuntimeError("Expected a dashboard.grafana.app/v2 Dashboard resource")

elements = dashboard["spec"]["elements"]
energy_panel = next(
    element["spec"]
    for element in elements.values()
    if element.get("kind") == "Panel" and element.get("spec", {}).get("id") == 4
)

aliases = {
    "sensor.comfortzone_ex_compressor_energy": "Compressor",
    "sensor.comfortzone_ex_additional_heater_energy": "Additional Heater",
    "sensor.comfortzone_ex_hot_water_energy": "Hot Water",
    "sensor.shellypro3em_waermepumpe_energy": "Shelly Heat Pump",
}

updated_measurements = []
for panel_query in energy_panel["data"]["spec"]["queries"]:
    query_spec = panel_query["spec"]["query"]["spec"]
    measurement = query_spec.get("measurement")
    if measurement is None:
        match = re.search(r'FROM\s+"([^"]+)"', query_spec.get("query", ""), re.IGNORECASE)
        if match is not None:
            measurement = match.group(1)
    if measurement not in aliases:
        continue

    query_spec["alias"] = aliases[measurement]
    query_spec["query"] = weekly_consumption_query(measurement)
    query_spec["rawQuery"] = True
    query_spec["resultFormat"] = "time_series"
    updated_measurements.append(measurement)

if set(updated_measurements) != set(aliases):
    missing = sorted(set(aliases) - set(updated_measurements))
    raise RuntimeError(f"Energy measurements not found: {missing}")

query_options = energy_panel["data"]["spec"]["queryOptions"]
query_options["timeFrom"] = "now-7d"
query_options["timeTo"] = "now"
query_options["hideTimeOverride"] = False
energy_panel["description"] = (
    "Each series shows consumption relative to its first cumulative-energy "
    "value in the rolling seven-day window."
)
energy_panel["title"] = "Energy Consumption — Last 7 Days"

# Keep the calculated flow temperature with the other temperature traces.
temperature_panel = dashboard["spec"]["elements"]["panel-1"]["spec"]
temperature_queries = temperature_panel["data"]["spec"]["queries"]
calculated_flow_measurement = (
    "sensor.technikkeller_comfortzone_ex_calculated_flow_temperature"
)
calculated_flow_queries = [
    query
    for query in temperature_queries
    if "_calculated_flow_temperature"
    in query["spec"]["query"]["spec"].get("query", "")
]
if calculated_flow_queries:
    calculated_flow_query = calculated_flow_queries[0]
    calculated_flow_query["spec"]["query"]["spec"]["alias"] = "Calculated Flow"
    calculated_flow_query["spec"]["query"]["spec"]["query"] = measurement_query(
        calculated_flow_measurement
    )
    temperature_queries[:] = [
        query
        for query in temperature_queries
        if query is calculated_flow_query
        or "_calculated_flow_temperature"
        not in query["spec"]["query"]["spec"].get("query", "")
    ]
else:
    template = deepcopy(temperature_queries[-1])
    template["spec"]["refId"] = "L"
    template["spec"]["query"]["spec"]["alias"] = "Calculated Flow"
    template["spec"]["query"]["spec"]["query"] = measurement_query(
        calculated_flow_measurement
    )
    temperature_queries.append(template)


def build_timeseries_panel(
    template_panel: dict,
    panel_id: int,
    title: str,
    description: str,
    measurements: tuple[tuple[str, str, str], ...],
    unit: str,
) -> dict:
    panel = deepcopy(template_panel)
    panel["id"] = panel_id
    panel["title"] = title
    panel["description"] = description
    panel["data"]["spec"]["queries"] = []

    query_template = template_panel["data"]["spec"]["queries"][0]
    for ref_id, alias, measurement in measurements:
        query = deepcopy(query_template)
        query["spec"]["refId"] = ref_id
        query["spec"]["query"]["spec"]["alias"] = alias
        query["spec"]["query"]["spec"]["query"] = measurement_query(measurement)
        panel["data"]["spec"]["queries"].append(query)

    defaults = panel["vizConfig"]["spec"]["fieldConfig"]["defaults"]
    defaults["unit"] = unit
    panel["vizConfig"]["spec"]["options"]["legend"]["placement"] = "right"
    panel["vizConfig"]["spec"]["options"]["legend"]["displayMode"] = "table"
    panel["vizConfig"]["spec"]["options"]["legend"]["calcs"] = ["lastNotNull"]
    return {"kind": "Panel", "spec": panel}


def build_filter_panel(template_panel: dict) -> dict:
    panel = deepcopy(template_panel)
    panel["id"] = 12
    panel["title"] = "Filter Change"
    panel["description"] = "Remaining time until the next filter change."
    query = panel["data"]["spec"]["queries"][0]
    query["spec"]["refId"] = "A"
    query["spec"]["query"]["spec"]["alias"] = "Days Remaining"
    query["spec"]["query"]["spec"]["query"] = last_value_query(
        "sensor.technikkeller_comfortzone_ex_filter_change_time"
    )
    panel["vizConfig"]["spec"]["fieldConfig"]["defaults"]["unit"] = "d"
    panel["vizConfig"]["spec"]["options"]["graphMode"] = "none"
    panel["vizConfig"]["spec"]["options"]["textMode"] = "value_and_name"
    return {"kind": "Panel", "spec": panel}


ENERGY_TIMEZONE = "Europe/Berlin"


def daily_consumption_query(measurement: str) -> str:
    # The extra day before the range supplies the baseline for the first
    # daily difference in the range.
    return (
        'SELECT NON_NEGATIVE_DIFFERENCE(LAST("value")) AS "consumption" '
        f'FROM "{measurement}" '
        "WHERE time >= ${__from}ms - 1d AND time <= ${__to}ms "
        f"GROUP BY time(1d) fill(none) tz('{ENERGY_TIMEZONE}')"
    )


def daily_integrated_power_query(measurement: str) -> str:
    # Home Assistant only records changes, so the power is first resampled to a
    # held per-minute value; each minute then contributes W / 60 / 1000 kWh.
    return (
        'SELECT sum("power") / 60000 AS "energy" FROM '
        f'(SELECT mean("value") AS "power" FROM "{measurement}" '
        "GROUP BY time(1m) fill(previous)) "
        "WHERE time >= ${__from}ms AND time <= ${__to}ms "
        f"GROUP BY time(1d) fill(none) tz('{ENERGY_TIMEZONE}')"
    )


power_aliases = {
    "sensor.comfortzone_ex_compressor_output_power": "Compressor Output",
    "sensor.comfortzone_ex_additional_heater_power": "Additional Heater",
    "sensor.comfortzone_ex_total_output_power": "Total Output",
    "sensor.comfortzone_ex_compressor_input_power": "Compressor Input",
    "sensor.shellypro3em_waermepumpe_power": "Shelly Heat Pump",
}


def build_energy_bar_panel(
    template_panel: dict,
    panel_id: int,
    title: str,
    description: str,
    time_from: str,
    label: str,
    label_format: str,
    series: dict[str, str] = aliases,
    series_query=daily_consumption_query,
) -> dict:
    # Daily energy values are labelled with label_format and summed per label.
    panel = deepcopy(template_panel)
    panel["id"] = panel_id
    panel["title"] = title
    panel["description"] = description

    query_template = template_panel["data"]["spec"]["queries"][0]
    panel["data"]["spec"]["queries"] = []
    for ref_id, (measurement, alias) in zip("ABCDEFGH", series.items()):
        query = deepcopy(query_template)
        query["spec"]["refId"] = ref_id
        query["spec"]["query"]["spec"]["alias"] = alias
        query["spec"]["query"]["spec"]["query"] = series_query(measurement)
        panel["data"]["spec"]["queries"].append(query)

    panel["data"]["spec"]["queryOptions"] = {
        "hideTimeOverride": False,
        "timeFrom": time_from,
    }
    panel["data"]["spec"]["transformations"] = [
        {
            "kind": "Transformation",
            "group": "joinByField",
            "spec": {
                "id": "joinByField",
                "options": {"byField": "Time", "mode": "outer"},
            },
        },
        {
            "kind": "Transformation",
            "group": "formatTime",
            "spec": {
                "id": "formatTime",
                "options": {
                    "outputFormat": label_format,
                    "timeField": "Time",
                    "useTimezone": True,
                },
            },
        },
        {
            "kind": "Transformation",
            "group": "groupBy",
            "spec": {
                "id": "groupBy",
                "options": {
                    "fields": {
                        "Time": {"aggregations": [], "operation": "groupby"},
                        **{
                            alias: {"aggregations": ["sum"], "operation": "aggregate"}
                            for alias in series.values()
                        },
                    }
                },
            },
        },
        {
            "kind": "Transformation",
            "group": "organize",
            "spec": {
                "id": "organize",
                "options": {
                    "renameByName": {
                        "Time": label,
                        **{f"{alias} (sum)": alias for alias in series.values()},
                    }
                },
            },
        },
    ]

    panel["vizConfig"] = {
        "group": "barchart",
        "kind": "VizConfig",
        "spec": {
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "axisBorderShow": False,
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "fillOpacity": 80,
                        "gradientMode": "none",
                        "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                        "lineWidth": 1,
                        "scaleDistribution": {"type": "linear"},
                        "thresholdsStyle": {"mode": "off"},
                    },
                    "decimals": 1,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [{"color": "green", "value": 0}],
                    },
                    "unit": "kwh",
                },
                "overrides": [],
            },
            "options": {
                "barRadius": 0,
                "barWidth": 0.9,
                "fullHighlight": False,
                "groupWidth": 0.75,
                "legend": {
                    "calcs": ["sum"],
                    "displayMode": "table",
                    "placement": "right",
                    "showLegend": True,
                },
                "orientation": "vertical",
                "showValue": "auto",
                "stacking": "none",
                "tooltip": {"hideZeros": False, "mode": "multi", "sort": "none"},
                "xField": label,
                "xTickLabelRotation": 0,
                "xTickLabelSpacing": 0,
            },
        },
        "version": template_panel["vizConfig"]["version"],
    }
    return {"kind": "Panel", "spec": panel}


elements = dashboard["spec"]["elements"]
elements["panel-10"] = build_timeseries_panel(
    elements["panel-3"]["spec"],
    10,
    "Flow",
    "Heating and hot-water flow. The heating-flow mapping is provisional.",
    (
        ("A", "Heating Flow", "sensor.technikkeller_comfortzone_ex_heating_flow"),
        (
            "B",
            "Hot Water Flow",
            "sensor.technikkeller_comfortzone_ex_hot_water_flow",
        ),
    ),
    "flowlpm",
)
elements["panel-11"] = build_timeseries_panel(
    elements["panel-3"]["spec"],
    11,
    "Fan Power",
    "Ventilation fan duty percentage.",
    (("A", "Fan Power", "sensor.technikkeller_comfortzone_ex_fan_power"),),
    "percent",
)
elements["panel-12"] = build_filter_panel(elements["panel-8"]["spec"])
elements["panel-13"] = build_energy_bar_panel(
    energy_panel,
    13,
    "Monthly Energy Consumption — This Year",
    "Daily counter increases summed per calendar month for the current year.",
    "now/y",
    "Month",
    "MMM",
)
elements["panel-14"] = build_energy_bar_panel(
    energy_panel,
    14,
    "Daily Energy Consumption — Last 7 Days",
    "Counter increase per calendar day for today and the six days before.",
    "now-6d/d",
    "Day",
    "ddd DD.MM.",
)
elements["panel-15"] = build_energy_bar_panel(
    energy_panel,
    15,
    "Daily Energy from Power Readings — Last 7 Days",
    "Power readings held per minute and integrated per calendar day, "
    "for comparison with the energy counters above.",
    "now-6d/d",
    "Day",
    "ddd DD.MM.",
    power_aliases,
    daily_integrated_power_query,
)

layout_items = dashboard["spec"]["layout"]["spec"]["items"]
layout_items[:] = [
    item
    for item in layout_items
    if item["spec"]["element"]["name"]
    not in {"panel-10", "panel-11", "panel-12", "panel-13", "panel-14", "panel-15"}
]
layout_items.extend(
    [
    {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": "panel-10"},
            "height": 9,
            "width": 12,
            "x": 0,
            "y": 56,
        },
    },
    {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": "panel-11"},
            "height": 9,
            "width": 8,
            "x": 12,
            "y": 56,
        },
    },
    {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": "panel-12"},
            "height": 9,
            "width": 4,
            "x": 20,
            "y": 56,
        },
    },
    {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": "panel-13"},
            "height": 10,
            "width": 24,
            "x": 0,
            "y": 65,
        },
    },
    {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": "panel-14"},
            "height": 10,
            "width": 24,
            "x": 0,
            "y": 75,
        },
    },
    {
        "kind": "GridLayoutItem",
        "spec": {
            "element": {"kind": "ElementReference", "name": "panel-15"},
            "height": 10,
            "width": 24,
            "x": 0,
            "y": 85,
        },
    },
    ]
)

# Rewrite every per-entity query so all panels carry the last known value.
ENTITY_QUERY = re.compile(
    r'^SELECT (?:distinct|last)\("(value|state)"\) FROM "([^"]+)" WHERE \$timeFilter'
    r"(?P<grouped> GROUP BY time\(\$__interval\) fill\(\w+\))?(?: ORDER BY time ASC)?$"
)
for element in elements.values():
    for panel_query in element["spec"]["data"]["spec"]["queries"]:
        query_spec = panel_query["spec"]["query"]["spec"]
        match = ENTITY_QUERY.match(query_spec.get("query", ""))
        if match is None:
            continue
        field, measurement = match.group(1, 2)
        if match.group("grouped"):
            query_spec["query"] = measurement_query(measurement, field)
        else:
            query_spec["query"] = last_value_query(measurement)

DASHBOARD_PATH.write_text(
    json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(DASHBOARD_PATH)
