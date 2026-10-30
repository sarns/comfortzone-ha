#!/usr/bin/env python3
"""Analyze Comfortzone write frames (panel -> heat pump) and bus timing.

Input is a sniffer log (text or .gz) with lines like
  @2026-09-18T09:01:58.315+02:00 ... CZRAW uptime_ms=71116 frame=<HEX>

Modes (combinable):
  default           write analysis: heartbeats, one-off writes, set/clear flags
  --around TIME     all frames within +-SPAN seconds of TIME (ISO or hh:mm:ss)
  --diff-register R payload byte changes of 'r' replies for register R (6 hex)
  --timing          bus timing statistics (note: log time, not wire time)
  --no-writes       suppress the default write analysis
"""

import argparse
import datetime as dt
import gzip
import pathlib
import re
import statistics
import sys
import zlib

PANEL = bytes.fromhex("41444452")
PUMP = bytes.fromhex("656FDE02")
BAUD_BYTES_PER_S = 19200 / 10  # 8N1 = 10 bits per byte

LINE_RE = re.compile(
    r"^(?:@(?P<ts>\S+)\s)?.*?uptime_ms=(?P<up>\d+).*?frame=(?P<frame>[0-9A-Fa-f]+)"
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def crc8_maxim(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8C if crc & 1 else 0)
    return crc


class Frame:
    def __init__(self, raw: bytes, uptime_ms: int, ts):
        self.raw = raw
        self.up = uptime_ms / 1000.0
        self.ts = ts  # datetime or None
        self.cmd = chr(raw[11])
        self.dest = raw[0:4]
        self.src = raw[6:10]
        self.reg = raw[18:21]
        self.payload = raw[21:-1]

    @property
    def reg_hex(self) -> str:
        return self.reg.hex().upper()

    @property
    def dur(self) -> float:
        """Approximate wire duration in seconds."""
        return len(self.raw) / BAUD_BYTES_PER_S

    @property
    def direction(self) -> str:
        if self.src == PANEL and self.dest == PUMP:
            return "P>H"
        if self.src == PUMP and self.dest == PANEL:
            return "H>P"
        return "???"

    def stamp(self) -> str:
        if self.ts is not None:
            return self.ts.strftime("%H:%M:%S.") + f"{self.ts.microsecond // 1000:03d}"
        return f"up{self.up:10.3f}"


def read_text(path: pathlib.Path) -> str:
    if path.suffix != ".gz":
        return path.read_text(encoding="utf-8", errors="replace")
    # Tolerate truncated gzip: decompress as far as possible.
    chunks = []
    try:
        with gzip.open(path, "rb") as f:
            while True:
                block = f.read(65536)
                if not block:
                    break
                chunks.append(block)
    except (EOFError, zlib.error, OSError) as exc:
        print(f"warning: gzip truncated/damaged ({type(exc).__name__}); "
              f"using data read so far", file=sys.stderr)
    return b"".join(chunks).decode("utf-8", errors="replace")


def load_frames(path: pathlib.Path) -> list[Frame]:
    frames = []
    bad = 0
    for line in read_text(path).splitlines():
        m = LINE_RE.match(ANSI_RE.sub("", line))
        if not m:
            continue
        try:
            raw = bytes.fromhex(m["frame"])
        except ValueError:
            bad += 1
            continue
        if len(raw) < 22 or raw[10] != len(raw) or raw[-1] != crc8_maxim(raw[:-1]):
            bad += 1
            continue
        ts = None
        if m["ts"]:
            try:
                ts = dt.datetime.fromisoformat(m["ts"])
            except ValueError:
                ts = None
        frames.append(Frame(raw, int(m["up"]), ts))
    if bad:
        print(f"warning: skipped {bad} invalid frame lines", file=sys.stderr)
    return frames


def hx(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def interpret(data: bytes) -> str:
    parts = []
    if len(data) == 1:
        parts.append(f"u8={data[0]}")
    elif len(data) == 2:
        parts.append(f"u16le={int.from_bytes(data, 'little')}")
    return " ".join(parts)


def op_prefix(reg: bytes) -> tuple[str, str]:
    """Return (operation name, 'base' string) per upstream qix67 convention."""
    nib = reg[0] >> 4
    name = {0x8: "SET-BITS (OR)", 0x4: "CLEAR-BITS (AND)", 0x0: "plain"}.get(
        nib, f"prefix 0x{nib:X}?")
    base = f"{reg[0] & 0x0F:X}{reg[1]:02X}{reg[2]:02X}"
    return name, base


def pct(values, p):
    s = sorted(values)
    if not s:
        return float("nan")
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def stats_line(values, unit=1000.0, suffix="ms") -> str:
    if not values:
        return "n=0"
    return (f"n={len(values):5d} min={min(values)*unit:8.1f} "
            f"med={statistics.median(values)*unit:8.1f} "
            f"p95={pct(values, 95)*unit:8.1f} max={max(values)*unit:8.1f} {suffix}")


# ---------------------------------------------------------------- writes

def pair_writes(frames):
    """Return list of (W frame, ack frame or None)."""
    pairs = []
    pending = None
    for f in frames:
        if f.cmd == "W":
            if pending is not None:
                pairs.append((pending, None))
            pending = f
        elif f.cmd == "w" and pending is not None:
            if f.reg == pending.reg:
                pairs.append((pending, f))
                pending = None
    if pending is not None:
        pairs.append((pending, None))
    return pairs


def write_line(w: Frame, ack) -> str:
    opname, base = op_prefix(w.reg)
    ackstr = f"ack={ack.payload.hex().upper() or '-'}" if ack else "ack=MISSING"
    flag = ""
    if w.reg[0] >> 4 in (0x8, 0x4):
        flag = f"  <<<<<< {opname} base={base} mask={hx(w.payload)}"
    return (f"{w.stamp()}  reg={w.reg_hex}  val={hx(w.payload)} "
            f"({interpret(w.payload)})  {ackstr}  op={opname.split()[0]} base={base}{flag}")


def is_periodic(times) -> tuple[bool, float]:
    if len(times) < 4:
        return False, 0.0
    ivs = [b - a for a, b in zip(times, times[1:])]
    med = statistics.median(ivs)
    if med <= 0:
        return False, med
    mad = statistics.median(abs(i - med) for i in ivs)
    return mad / med < 0.25, med


def analyze_writes(frames):
    pairs = pair_writes(frames)
    print(f"== Writes: {len(pairs)} W frames "
          f"({sum(1 for _, a in pairs if a)} acknowledged)")
    by_reg: dict[str, list] = {}
    for w, a in pairs:
        by_reg.setdefault(w.reg_hex, []).append((w, a))

    heartbeat, oneoff = {}, []
    for reg, items in by_reg.items():
        ok, med = is_periodic([w.up for w, _ in items])
        if ok:
            heartbeat[reg] = (items, med)
        else:
            oneoff.extend(items)

    print("\n== Heartbeat writes (periodic)")
    if not heartbeat:
        print("  none")
    for reg, (items, med) in sorted(heartbeat.items()):
        payloads = [w.payload for w, _ in items]
        distinct = sorted(set(payloads))
        acks = sorted({a.payload.hex().upper() if a else "MISSING" for _, a in items})
        line = (f"  {reg}  count={len(items)} median_interval={med:.2f}s "
                f"len={len(payloads[0])}B distinct_values={len(distinct)} "
                f"acks={','.join(acks)}")
        print(line)
        if len(distinct) == 1:
            print(f"      constant value: {hx(distinct[0])}")
        elif len({len(p) for p in payloads}) == 1:
            changing = [i for i in range(len(payloads[0]))
                        if len({p[i] for p in payloads}) > 1]
            fixed = {i: payloads[0][i] for i in range(len(payloads[0]))
                     if i not in changing}
            print(f"      changing byte positions: {changing}; "
                  f"constant: " + ", ".join(f"[{i}]={v:02X}" for i, v in fixed.items()))
            for i in changing:
                vals = [p[i] for p in payloads]
                steps = {(b - a) & 0xFF for a, b in zip(vals, vals[1:])}
                extra = f" (step {steps.pop()} mod 256)" if len(steps) == 1 else ""
                print(f"      byte[{i}]: {len(set(vals))} distinct, "
                      f"first={vals[0]:02X} last={vals[-1]:02X}{extra}")
        else:
            print("      payload length varies")

    oneoff.sort(key=lambda x: x[0].up)
    print(f"\n== One-off writes ({len(oneoff)}), chronological")
    if not oneoff:
        print("  none")
    for w, a in oneoff:
        print("  " + write_line(w, a))

    flagged = [(w, a) for w, a in pairs if w.reg[0] >> 4 in (0x8, 0x4)]
    print(f"\n== Set/clear-bit writes (prefix 0x8_ / 0x4_): {len(flagged)}")
    for w, a in flagged:
        print("  !!! " + write_line(w, a))
    if not flagged:
        print("  none in this capture")


# ---------------------------------------------------------------- around

def parse_time(text: str, frames) -> float:
    """Return the uptime (s) corresponding to TIME."""
    stamped = [f for f in frames if f.ts is not None]
    if not stamped:
        sys.exit("--around needs ISO timestamps in the capture")
    ref = stamped[0].ts
    try:
        target = dt.datetime.fromisoformat(text)
        if target.tzinfo is None:
            target = target.replace(tzinfo=ref.tzinfo)
    except ValueError:
        m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?", text)
        if not m:
            sys.exit(f"cannot parse time: {text}")
        micro = int((m[4] or "0").ljust(6, "0")[:6])
        target = ref.replace(hour=int(m[1]), minute=int(m[2]),
                             second=int(m[3] or 0), microsecond=micro)
    best = min(stamped, key=lambda f: abs((f.ts - target).total_seconds()))
    return best.up + (target - best.ts).total_seconds()


def show_around(frames, text, span):
    center = parse_time(text, frames)
    sel = [f for f in frames if abs(f.up - center) <= span]
    print(f"== Frames within +-{span:g}s of {text}: {len(sel)}")
    prev = None
    for f in sel:
        dtm = f"+{(f.up - prev) * 1000:6.0f}ms" if prev is not None else " " * 9
        prev = f.up
        pay = hx(f.payload[:16]) + (" ..." if len(f.payload) > 16 else "")
        mark = ""
        if f.cmd in "Ww" and f.reg[0] >> 4 in (0x8, 0x4):
            mark = "  <<< SET/CLEAR"
        print(f"  {f.stamp()} {dtm} {f.direction} {f.cmd} {f.reg_hex} "
              f"[{len(f.payload):2d}B] {pay}{mark}")


# ---------------------------------------------------------------- diff

def diff_register(frames, reg, bits):
    reg = reg.upper().replace(" ", "")
    reps = [f for f in frames if f.cmd == "r" and f.reg_hex == reg]
    print(f"== Register {reg}: {len(reps)} 'r' replies")
    if not reps:
        return
    prev = reps[0]
    print(f"  initial {prev.stamp()}  [{len(prev.payload)}B] {hx(prev.payload)}")
    changes = 0
    for cur in reps[1:]:
        a, b = prev.payload, cur.payload
        if len(a) != len(b):
            print(f"  {cur.stamp()}  length change {len(a)} -> {len(b)}")
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                changes += 1
                s = f"  {cur.stamp()}  byte[{i}] {a[i]:02X} -> {b[i]:02X}"
                if bits:
                    x = a[i] ^ b[i]
                    flips = [f"bit{k}:{(a[i] >> k) & 1}->{(b[i] >> k) & 1}"
                             for k in range(8) if x >> k & 1]
                    s += f"  ({a[i]:08b} -> {b[i]:08b})  " + " ".join(flips)
                print(s)
        prev = cur
    print(f"  total byte changes: {changes}")


# ---------------------------------------------------------------- timing

def analyze_timing(frames):
    print("== Bus timing")
    print("  Note: timestamps are when the log line was emitted (frame end at best,"
          "\n  plus ESPHome/UART/logging jitter), NOT wire time. Wire duration is"
          "\n  estimated as len*10 bit / 19200 baud = 0.52 ms/byte (e.g. 24 B = 12.5 ms)."
          "\n  Gaps below assume the log stamp marks the END of a frame, so the gap"
          "\n  before frame N = t(N) - dur(N) - t(N-1). Resolution ~1 ms.")
    # request -> reply latency
    print("\n  Request -> reply latency (reply start - request end):")
    lat: dict[str, list] = {}
    req = None
    gaps_after_reply, anchors = [], []
    for f in frames:
        if f.cmd in "RW":
            req = f
        elif f.cmd in "rw" and req is not None and f.reg == req.reg:
            lat.setdefault(req.cmd + "->" + f.cmd, []).append(
                (f.up - f.dur) - req.up)
            req = None
    for k, v in sorted(lat.items()):
        print(f"    {k}  {stats_line(v)}")
    # per-register latency for R->r, show slowest
    perreg: dict[str, list] = {}
    req = None
    for f in frames:
        if f.cmd == "R":
            req = f
        elif f.cmd == "r" and req is not None and f.reg == req.reg:
            perreg.setdefault(req.reg_hex, []).append((f.up - f.dur) - req.up)
            req = None
    slow = sorted(perreg.items(), key=lambda kv: -statistics.median(kv[1]))[:3]
    print("    slowest R->r registers (median): " + ", ".join(
        f"{r}={statistics.median(v)*1000:.0f}ms(n={len(v)})" for r, v in slow))

    # reply end -> next panel request start
    prev = None
    allgaps = []  # (gap, preceding frame, next frame)
    for f in frames:
        if prev is not None:
            gap = (f.up - f.dur) - prev.up
            allgaps.append((gap, prev, f))
            if prev.cmd in "rw" and f.cmd in "RW":
                gaps_after_reply.append(gap)
        prev = f
    print("\n  Gap: end of heat-pump reply -> start of next panel request:")
    print("    " + stats_line(gaps_after_reply))
    small = [g for g in gaps_after_reply if g < 0.3]
    print("    (without gaps > 300 ms) " + stats_line(small))
    neg = sum(1 for g in gaps_after_reply if g < 0)
    if neg:
        print(f"    {neg} negative gaps = log jitter (stamp not exactly frame end)")

    # cycle length: anchor on the R register most often following the longest gaps
    long_gaps = [x for x in allgaps if x[0] > 0.3]
    print(f"\n  Long idle gaps (> 300 ms): {len(long_gaps)}")
    pre: dict[str, int] = {}
    nxt: dict[str, int] = {}
    for g, a, b in long_gaps:
        pre[f"{a.cmd} {a.reg_hex}"] = pre.get(f"{a.cmd} {a.reg_hex}", 0) + 1
        nxt[f"{b.cmd} {b.reg_hex}"] = nxt.get(f"{b.cmd} {b.reg_hex}", 0) + 1
    if long_gaps:
        print("    preceded by (cmd reg: count): " + ", ".join(
            f"{k}:{v}" for k, v in sorted(pre.items(), key=lambda kv: -kv[1])[:8]))
        print("    followed by: " + ", ".join(
            f"{k}:{v}" for k, v in sorted(nxt.items(), key=lambda kv: -kv[1])[:8]))
        gv = [g for g, _, _ in long_gaps]
        print("    gap length: " + stats_line(gv))
        if len(long_gaps) <= 25:
            for g, a, b in long_gaps:
                print(f"      {a.stamp()} {a.cmd} {a.reg_hex} --{g*1000:6.0f}ms--> "
                      f"{b.cmd} {b.reg_hex}")
    # polling cycle: intervals of the most frequently requested register
    reqs: dict[str, list] = {}
    for f in frames:
        if f.cmd == "R":
            reqs.setdefault(f.reg_hex, []).append(f.up)
    if reqs:
        anchor, times = max(reqs.items(), key=lambda kv: len(kv[1]))
        cyc = [y - x for x, y in zip(times, times[1:])]
        nreq = sum(len(v) for v in reqs.values())
        print("\n  Polling cycle (successive requests of most frequent register "
              f"{anchor}): " + stats_line(cyc))
        print(f"    {nreq / len(times):.1f} read requests per cycle, "
              f"{len(reqs)} distinct read registers")

    mid = [x for x in allgaps if 0.1 < x[0] <= 0.3]
    print(f"\n  Medium gaps (100-300 ms): {len(mid)}")
    if mid:
        cnt: dict[str, int] = {}
        for _, a, _ in mid:
            key = f"{a.cmd} {a.reg_hex}"
            cnt[key] = cnt.get(key, 0) + 1
        print("    preceded by: " + ", ".join(
            f"{k}:{v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:8]))

    allg = [g for g, _, _ in allgaps]
    print("\n  All inter-frame gaps (any pair): " + stats_line(allg))

    print("\n== Conclusion")
    if gaps_after_reply:
        pos = [g for g in gaps_after_reply if g > 0]
        rec = 0.040
        frac = 100 * sum(1 for g in gaps_after_reply if g > rec) / len(gaps_after_reply)
        print(f"  Reply -> next panel request: median "
              f"{statistics.median(gaps_after_reply)*1000:.0f} ms, 1st pct (positive) "
              f"{pct(pos or gaps_after_reply, 1)*1000:.0f} ms, "
              f"min {min(gaps_after_reply)*1000:.0f} ms (negatives = log jitter).")
        print(f"  Recommended: listen-before-talk, transmit only after >= "
              f"{rec*1000:.0f} ms of verified silence following a heat-pump reply "
              f"(upstream value); {frac:.0f}% of reply->request gaps exceed this, "
              f"but the panel may still start at any time, so abort/retry on collision.")
    span = frames[-1].up - frames[0].up
    if long_gaps:
        print(f"  Long (> 300 ms) gaps: {len(long_gaps)} in {span:.0f} s "
              f"(one per {span/len(long_gaps):.0f} s) -- too rare to rely on.")
    else:
        print("  No long (> 300 ms) idle gaps -- do not wait for one.")
    if allg:
        print(f"  Largest regular gap: {max(allg)*1000:.0f} ms; the bus is "
              f"continuously polled (no ~1.1 s cycle pause unless listed above).")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", type=pathlib.Path)
    ap.add_argument("--around", metavar="TIME", help="ISO timestamp or hh:mm:ss")
    ap.add_argument("--span", type=float, default=60.0, help="seconds (default 60)")
    ap.add_argument("--diff-register", metavar="REG", help="e.g. 010400")
    ap.add_argument("--bits", action="store_true", help="bit-level diff output")
    ap.add_argument("--timing", action="store_true", help="bus timing statistics")
    ap.add_argument("--no-writes", action="store_true")
    args = ap.parse_args()

    frames = load_frames(args.capture)
    if not frames:
        print("no valid frames found", file=sys.stderr)
        return 1
    span = frames[-1].up - frames[0].up
    print(f"Loaded {len(frames)} valid frames, {frames[0].stamp()} .. "
          f"{frames[-1].stamp()} ({span:.0f} s)")

    selective = args.around or args.diff_register or args.timing
    if not selective and not args.no_writes:
        analyze_writes(frames)
    if args.around:
        show_around(frames, args.around, args.span)
    if args.diff_register:
        diff_register(frames, args.diff_register, args.bits)
    if args.timing:
        analyze_timing(frames)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
