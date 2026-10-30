#!/usr/bin/env python3
"""Find where values read from display photos live in timestamped RS485 captures.

Photo CSV columns: timestamp,label,value,unit (several rows per photo/timestamp).
For every register, payload byte offset, integer type and scale the decoded value
is compared with the displayed value; candidates are ranked per label.
"""

import argparse
import bisect
import collections
import csv
import datetime as dt
import gzip
import json
import pathlib
import re
import sys
import zlib

HEADER_SIZE = 21

# (name, size, byteorder, signed)
TYPES = [
    ("s16le", 2, "little", True),
    ("u16le", 2, "little", False),
    ("s8", 1, "little", True),
    ("u8", 1, "little", False),
    ("s32le", 4, "little", True),
    ("u32le", 4, "little", False),
    ("s16be", 2, "big", True),
    ("u16be", 2, "big", False),
]
TYPE_RANK = {spec[0]: index for index, spec in enumerate(TYPES)}
TYPE_WIDTH = {spec[0]: spec[1] for spec in TYPES}
SCALES = [(1, "1"), (10, "0.1"), (100, "0.01")]  # (divisor, label)
DIVISOR = {label: divisor for divisor, label in SCALES}

# Mappings already implemented in components/comfortzone_ex/comfortzone_ex.cpp:
# (register, payload offset, width in bytes, scale label) -> name
KNOWN: dict[tuple[str, int, int, str], str] = {}
for _i, _name in zip(
    [0, 1, 2, 3, 4, 5, 6, 7, 24],
    ["outdoor", "flow", "return", "indoor", "hot_gas", "exchanger_out",
     "evaporator_in", "exhaust_air", "hot_water"],
):
    KNOWN[("010400", 52 + 2 * _i, 2, "0.1")] = f"{_name} temperature"
KNOWN.update({
    ("008902", 9, 2, "0.1"): "room setpoint",
    ("004503", 0, 2, "0.1"): "hot water target",
    ("002804", 70, 2, "0.1"): "calculated flow temperature",
    ("00F703", 6, 2, "1"): "filter change time",
    ("01D102", 2, 2, "0.1"): "fan power",
    ("01D102", 3, 1, "1"): "fan speed",
    ("01D102", 10, 2, "0.1"): "current flow",
    ("01D102", 33, 2, "0.1"): "compressor frequency",
    ("01F901", 18, 2, "0.1"): "heating flow (provisional)",
    ("014003", 0, 2, "1"): "compressor output power",
    ("014003", 2, 4, "1"): "additional heater power",
    ("014003", 6, 4, "1"): "total output power",
    ("014003", 14, 2, "1"): "compressor input power",
    ("052800", 4, 4, "0.01"): "compressor energy",
    ("052800", 8, 4, "0.01"): "additional heater energy",
    ("052800", 12, 4, "0.01"): "hot water energy",
    ("052800", 16, 4, "1"): "compressor runtime",
    ("052800", 20, 4, "1"): "total runtime",
})


def crc8_maxim(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8C if crc & 1 else 0)
    return crc


def parse_time(text: str, default_tz) -> float:
    text = text.strip().replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    stamp = dt.datetime.fromisoformat(text)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=default_tz) if default_tz else stamp.astimezone()
    return stamp.timestamp()


def read_text_lines(path: pathlib.Path):
    """Yield lines; tolerate truncated gzip files."""
    if path.suffix == ".gz":
        capture = gzip.open(path, "rt", encoding="utf-8", errors="replace")
    else:
        capture = open(path, "rt", encoding="utf-8", errors="replace")
    with capture:
        try:
            for line in capture:
                yield line
        except (EOFError, OSError, zlib.error) as error:
            print(f"warning: {path} truncated/corrupt ({error}); "
                  "continuing with data read so far", file=sys.stderr)


TS_RE = re.compile(r"^\s*(?:\x1b\[[0-9;]*m)*@(\S+)")
FRAME_RE = re.compile(r"\bframe=([0-9A-Fa-f]+)")


def load_replies(path: pathlib.Path):
    """Return ({register: (times, payloads)}, default_tz, stats)."""
    registers: dict[str, tuple[list[float], list[bytes]]] = {}
    default_tz = None
    stats = collections.Counter()
    for line in read_text_lines(path):
        match = FRAME_RE.search(line)
        if not match:
            continue
        stats["frames"] += 1
        stamp = TS_RE.match(line)
        if not stamp:
            stats["untimed"] += 1
            continue
        try:
            frame = bytes.fromhex(match.group(1))
            when_dt = dt.datetime.fromisoformat(stamp.group(1).replace("Z", "+00:00"))
        except ValueError:
            stats["bad"] += 1
            continue
        if default_tz is None and when_dt.tzinfo is not None:
            default_tz = when_dt.tzinfo
        if when_dt.tzinfo is None:
            when_dt = when_dt.astimezone()
        if (
            len(frame) < HEADER_SIZE + 1
            or frame[10] != len(frame)
            or frame[11] != ord("r")
            or frame[-1] != crc8_maxim(frame[:-1])
        ):
            stats["skipped"] += 1
            continue
        register = frame[18:21].hex().upper()
        times, payloads = registers.setdefault(register, ([], []))
        times.append(when_dt.timestamp())
        payloads.append(frame[HEADER_SIZE:-1])
        stats["replies"] += 1
    return registers, default_tz, stats


def sort_register(times: list, payloads: list) -> None:
    if any(a > b for a, b in zip(times, times[1:])):
        order = sorted(range(len(times)), key=times.__getitem__)
        times[:] = [times[i] for i in order]
        payloads[:] = [payloads[i] for i in order]


def decimals_of(text: str) -> int:
    text = text.strip()
    return len(text.split(".", 1)[1]) if "." in text else 0


def load_photos(path: pathlib.Path, default_tz, shift: float):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for number, record in enumerate(csv.DictReader(handle), start=2):
            try:
                text = record["value"].strip()
                rows.append({
                    "time": parse_time(record["timestamp"], default_tz) + shift,
                    "stamp": record["timestamp"].strip(),
                    "label": record["label"].strip(),
                    "value": float(text),
                    "decimals": decimals_of(text),
                    "unit": (record.get("unit") or "").strip(),
                })
            except (KeyError, ValueError, AttributeError) as error:
                print(f"warning: {path}:{number}: skipped row ({error})", file=sys.stderr)
    return rows


def frames_near(registers, when, window, max_age):
    """Payloads per register: frames within +-window plus latest before `when`."""
    result = {}
    for register, (times, payloads) in registers.items():
        low = bisect.bisect_left(times, when - window)
        high = bisect.bisect_right(times, when + window)
        picked = list(range(low, high))
        before = bisect.bisect_right(times, when) - 1
        if before >= 0 and when - times[before] <= max_age and before not in picked:
            picked.insert(0, before)
        if picked:
            latest = before if before in picked else picked[0]
            result[register] = ([payloads[i] for i in picked], payloads[latest])
    return result


def raw_values(payloads, latest):
    """{(offset, type): (set of raws, raw in latest frame)} for one register."""
    table = {}
    unique = list(dict.fromkeys(payloads))
    longest = max(len(p) for p in unique)
    for name, size, order, signed in TYPES:
        for offset in range(max(longest - size + 1, 0)):
            raws = set()
            for payload in unique:
                if offset + size <= len(payload):
                    raws.add(int.from_bytes(payload[offset:offset + size], order,
                                            signed=signed))
            last = (int.from_bytes(latest[offset:offset + size], order, signed=signed)
                    if offset + size <= len(latest) else None)
            table[(offset, name)] = (raws, last)
    return table


def fmt(value) -> str:
    return f"{value:.5g}" if value is not None else "-"


def correlate(args, registers, photos):
    by_label = collections.defaultdict(list)
    for row in photos:
        by_label[row["label"]].append(row)

    cache: dict[float, dict] = {}
    # candidates[label][(register, offset, type, scale)] = {row index: matched decoded}
    candidates = {label: {} for label in by_label}
    for label, rows in by_label.items():
        for index, row in enumerate(rows):
            if row["time"] not in cache:
                near = frames_near(registers, row["time"], args.window, args.max_age)
                cache[row["time"]] = {reg: raw_values(*data) for reg, data in near.items()}
            value = row["value"]
            tol = args.tolerance if args.tolerance is not None else 0.5 * 10 ** -row["decimals"]
            for register, table in cache[row["time"]].items():
                for (offset, name), (raws, _last) in table.items():
                    for divisor, scale_label in SCALES:
                        hit = None
                        for raw in raws:
                            decoded = raw / divisor
                            if abs(decoded - value) <= tol + 1e-9 and (
                                    hit is None or abs(decoded - value) < abs(hit - value)):
                                hit = decoded
                        if hit is not None:
                            key = (register, offset, name, scale_label)
                            candidates[label].setdefault(key, {})[index] = hit

    results = {}
    for label, rows in by_label.items():
        total = len(rows)
        distinct_disp = {round(r["value"], 6) for r in rows}
        ranked = []
        for key, hits in candidates[label].items():
            matched_vals = {round(rows[i]["value"], 6) for i in hits}
            err = sum(abs(hits[i] - rows[i]["value"]) for i in hits) / len(hits)
            ranked.append((key, hits, matched_vals, err))
        # more photos matched, more distinct displayed values matched (penalizes
        # constant fields), smaller error, then simplest type.
        ranked.sort(key=lambda item: (
            -len(item[1]), -len(item[2]), round(item[3], 9),
            (item[0][0], item[0][1], TYPE_WIDTH[item[0][2]], item[0][3]) not in KNOWN,
            TYPE_RANK[item[0][2]], item[0][0], item[0][1]))

        merged = []
        signatures = {}
        for key, hits, matched_vals, err in ranked:
            register, offset, name, scale_label = key
            signature = (register, offset, scale_label, tuple(sorted(hits.items())))
            if signature in signatures:
                signatures[signature]["aliases"].append(name)
                continue
            if len(merged) >= args.top:
                continue
            entry = {
                "register": register, "offset": offset, "type": name,
                "scale": scale_label, "matched": len(hits), "total": total,
                "distinct_matched_values": len(matched_vals),
                "mean_abs_error": err,
                "known": KNOWN.get((register, offset, TYPE_WIDTH[name], scale_label)),
                "aliases": [],
                "confident": len(hits) >= args.min_photos
                and (len(distinct_disp) < 2 or len(matched_vals) >= 2),
                "_hits": hits,
            }
            signatures[signature] = entry
            merged.append(entry)

        for entry in merged:  # per-row decoded values, including misses
            values = []
            for index, row in enumerate(rows):
                decoded = entry["_hits"].get(index)
                matched = decoded is not None
                if not matched:
                    table = cache[row["time"]].get(entry["register"], {})
                    last = table.get((entry["offset"], entry["type"]), (None, None))[1]
                    decoded = last / DIVISOR[entry["scale"]] if last is not None else None
                values.append({"time": row["stamp"], "displayed": row["value"],
                               "decoded": decoded, "match": matched})
            entry["rows"] = values
            del entry["_hits"]
        results[label] = {
            "rows": total,
            "displayed_values": sorted(distinct_disp),
            "constant": len(distinct_disp) < 2,
            "unit": rows[0]["unit"],
            "candidates": merged,
        }
    return results


def print_results(results, min_photos):
    for label, info in results.items():
        shown = ", ".join(fmt(v) for v in info["displayed_values"][:8])
        print(f"\n=== {label} [{info['unit']}]  rows={info['rows']}  "
              f"displayed values: {shown}")
        if info["rows"] < min_photos:
            print(f"  note: only {info['rows']} photo(s); need >= {min_photos} for a "
                  "confident result")
        if info["constant"]:
            print("  WARNING: displayed value is the same in all photos; correlation "
                  "is weak (constant fields match too)")
        if not info["candidates"]:
            print("  no candidates matched")
            continue
        print(f"  {'#':>2} {'register':8} {'off':>3} {'type':6} {'scale':5} "
              f"{'match':>7} {'conf':4}  known")
        for rank, cand in enumerate(info["candidates"], start=1):
            alias = f"  (also {'/'.join(cand['aliases'])})" if cand["aliases"] else ""
            print(f"  {rank:>2} {cand['register']:8} {cand['offset']:>3} "
                  f"{cand['type']:6} {cand['scale']:5} "
                  f"{cand['matched']:>3}/{cand['total']:<3} "
                  f"{'yes' if cand['confident'] else 'no':4}  "
                  f"{('KNOWN: ' + cand['known']) if cand['known'] else ''}{alias}")
            line = "  ".join(
                f"{r['displayed']:g}->{fmt(r['decoded'])}{'' if r['match'] else '?'}"
                for r in cand["rows"][:10])
            print(f"       shown->decoded: {line}")


def list_registers(registers):
    print(f"{'register':8} {'frames':>7} {'payload lengths':16} first..last")
    for register, (times, payloads) in sorted(registers.items()):
        lengths = collections.Counter(len(p) for p in payloads)
        text = ",".join(f"{n}x{c}" if len(lengths) > 1 else str(n)
                        for n, c in sorted(lengths.items()))
        first = dt.datetime.fromtimestamp(times[0]).strftime("%H:%M:%S")
        last = dt.datetime.fromtimestamp(times[-1]).strftime("%H:%M:%S")
        print(f"{register:8} {len(payloads):>7} {text:16} {first}..{last}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=pathlib.Path, nargs="+",
                        help="timestamped capture(s), text or .gz")
    parser.add_argument("--photos", type=pathlib.Path,
                        help="CSV: timestamp,label,value,unit")
    parser.add_argument("--list-registers", action="store_true")
    parser.add_argument("--window", type=float, default=5.0,
                        help="accept frames within +-WINDOW s of the photo (default 5)")
    parser.add_argument("--max-age", type=float, default=15.0,
                        help="max age of latest frame before the photo (default 15 s)")
    parser.add_argument("--time-shift", type=float, default=0.0,
                        help="seconds added to photo times to get capture time")
    parser.add_argument("--tolerance", type=float,
                        help="absolute tolerance (default: half of last displayed digit)")
    parser.add_argument("--min-photos", type=int, default=2)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--json", type=pathlib.Path, help="write results as JSON")
    args = parser.parse_args()

    registers: dict[str, tuple[list[float], list[bytes]]] = {}
    default_tz = None
    for path in args.capture:
        part, tz, stats = load_replies(path)
        default_tz = default_tz or tz
        for register, (times, payloads) in part.items():
            merged = registers.setdefault(register, ([], []))
            merged[0].extend(times)
            merged[1].extend(payloads)
        print(f"{path}: {stats['frames']} frames, {stats['replies']} timed 'r' replies"
              f" ({stats['untimed']} without timestamp, {stats['skipped']} non-reply/"
              f"invalid)", file=sys.stderr)
    for times, payloads in registers.values():
        sort_register(times, payloads)
    if not registers:
        print("error: no timestamped reply frames found", file=sys.stderr)
        return 1

    if args.list_registers:
        list_registers(registers)
        if not args.photos:
            return 0
    if not args.photos:
        parser.error("--photos is required unless --list-registers is given")

    photos = load_photos(args.photos, default_tz, args.time_shift)
    if not photos:
        print("error: no usable photo rows", file=sys.stderr)
        return 1
    start = min(t[0] for t, _ in registers.values())
    end = max(t[-1] for t, _ in registers.values())
    outside = sum(1 for p in photos
                  if not start - args.window <= p["time"] <= end + args.window)
    if outside:
        print(f"warning: {outside} photo row(s) lie outside the capture time range",
              file=sys.stderr)

    results = correlate(args, registers, photos)
    print_results(results, args.min_photos)
    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
