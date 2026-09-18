import json
import re
from pathlib import Path


DASHBOARD_PATH = Path("grafana/comfortzone-ex-dashboard.json")


def weekly_consumption_query(measurement: str) -> str:
    return (
        'SELECT CUMULATIVE_SUM("delta") AS "consumption" FROM '
        f'(SELECT DIFFERENCE(LAST("value")) AS "delta" FROM "{measurement}" '
        "GROUP BY time($__interval) fill(null)) "
        "WHERE time >= now() - 7d AND time <= now() ORDER BY time ASC"
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

DASHBOARD_PATH.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
print(DASHBOARD_PATH)
