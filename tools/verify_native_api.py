import asyncio
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from aioesphomeapi import APIClient


async def main() -> None:
    secret_text = Path("esphome/secrets.yaml").read_text(encoding="utf-8")
    match = re.search(r"^api_encryption_key:\s*[\"']?([^\"'\r\n]+)", secret_text, re.MULTILINE)
    if match is None:
        raise RuntimeError("api_encryption_key is missing")

    client = APIClient(
        os.environ.get("COMFORTZONE_HOST", "comfortzone-ex.local"),
        6053,
        None,
        noise_psk=match.group(1).strip(),
        expected_name="comfortzone-ex",
    )
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    names = {entity.key: entity.name for entity in entities}
    print(f"connected entities={len(entities)} heat_pump_time_present={any(e.name == 'Heat Pump Time' for e in entities)}")

    start = time.monotonic()
    events: dict[str, list[float]] = defaultdict(list)

    def on_state(state) -> None:
        name = names.get(state.key, f"key:{state.key}")
        events[name].append(time.monotonic() - start)

    client.subscribe_states(on_state)
    observation_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 125.0
    await asyncio.sleep(observation_seconds)
    await client.disconnect()

    tracked = (
        "Outdoor Temperature",
        "Room Setpoint",
        "Hot Water Target",
        "Compressor Frequency",
        "Compressor Input Power",
        "Total Runtime",
        "RS485 Bus Online",
    )
    for name in tracked:
        stamps = events.get(name, [])
        rendered = ", ".join(f"{stamp:.1f}s" for stamp in stamps)
        print(f"{name}: updates={len(stamps)} at=[{rendered}]")


if __name__ == "__main__":
    asyncio.run(main())
