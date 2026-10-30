#!/usr/bin/env python3
"""Rename Comfortzone EX entity IDs in Home Assistant's entity registry.

Home Assistant gave entities created after the device was assigned to an area
an area prefix (``sensor.technikkeller_comfortzone_ex_*``), while older ones
were ``sensor.comfortzone_ex_*``. This script replaces one object-ID prefix of
ESPHome entities with another through the WebSocket API
(``config/entity_registry/update``). Without ``--apply`` it only prints what it
would do. On 2026-10-30 it added the area prefix to the older entities:

    ha_rename_entities.py --url https://ha.example --from-prefix comfortzone_ex_ \
        --to-prefix technikkeller_comfortzone_ex_ --apply

Requires the ``websockets`` package. The access token is read from the file
given by ``--token-file`` (default ``~/.ha_token``) or from ``HA_TOKEN``, so it
never appears on the command line.

Renaming keeps the Home Assistant recorder history, but InfluxDB starts a new
measurement under the new entity ID.
"""

import argparse
import asyncio
import json
import os
import pathlib
import sys

import websockets


async def call(ws, msg_id: int, payload: dict) -> dict:
    await ws.send(json.dumps({"id": msg_id, **payload}))
    while True:
        reply = json.loads(await ws.recv())
        if reply.get("id") == msg_id:
            return reply


async def run(args: argparse.Namespace, token: str) -> int:
    url = args.url.rstrip("/").replace("http", "ws", 1) + "/api/websocket"
    async with websockets.connect(url, max_size=None) as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print(f"Authentication failed: {auth}", file=sys.stderr)
            return 1

        reply = await call(ws, 1, {"type": "config/entity_registry/list"})
        entries = reply["result"]
        existing = {entry["entity_id"] for entry in entries}

        plan = []
        for entry in entries:
            domain, object_id = entry["entity_id"].split(".", 1)
            if entry.get("platform") != "esphome" or not object_id.startswith(args.from_prefix):
                continue
            new_id = f"{domain}.{args.to_prefix}{object_id[len(args.from_prefix):]}"
            plan.append((entry["entity_id"], new_id))

        if not plan:
            print("Nothing to rename.")
            return 0

        failures = 0
        msg_id = 2
        for old_id, new_id in sorted(plan):
            if new_id in existing:
                print(f"SKIP  {old_id} -> {new_id} (target already exists)")
                failures += 1
                continue
            if not args.apply:
                print(f"PLAN  {old_id} -> {new_id}")
                continue
            reply = await call(
                ws,
                msg_id,
                {
                    "type": "config/entity_registry/update",
                    "entity_id": old_id,
                    "new_entity_id": new_id,
                },
            )
            msg_id += 1
            if reply.get("success"):
                print(f"DONE  {old_id} -> {new_id}")
            else:
                print(f"FAIL  {old_id} -> {new_id}: {reply.get('error')}")
                failures += 1

        if not args.apply:
            print(f"\n{len(plan)} entities; dry run only. Re-run with --apply to rename.")
        return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://homeassistant.local:8123"))
    parser.add_argument("--token-file", type=pathlib.Path, default=pathlib.Path.home() / ".ha_token")
    parser.add_argument("--from-prefix", default="technikkeller_comfortzone_ex_")
    parser.add_argument("--to-prefix", default="comfortzone_ex_")
    parser.add_argument("--apply", action="store_true", help="actually rename (default: dry run)")
    args = parser.parse_args()

    token = os.environ.get("HA_TOKEN")
    if not token and args.token_file.is_file():
        token = args.token_file.read_text(encoding="utf-8").strip()
    if not token:
        print(f"No token: set HA_TOKEN or create {args.token_file}", file=sys.stderr)
        return 2
    return asyncio.run(run(args, token))


if __name__ == "__main__":
    sys.exit(main())
