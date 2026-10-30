#!/usr/bin/env python3
"""Capture a Linux USB ACM serial device without external dependencies."""

import argparse
import datetime
import fcntl
import gzip
import os
import pathlib
import select
import signal
import struct
import sys
import termios
import time
import tty
import zlib


class StopRequested(Exception):
    pass


def request_stop(signum, frame) -> None:
    raise StopRequested(signal.Signals(signum).name)


def flush_output(output, output_is_text: bool, sync: bool) -> None:
    """Flush buffers; for gzip also emit a sync point so data on disk is readable."""
    output.flush()
    if sync and output_is_text:
        # TextIOWrapper.flush() reaches GzipFile.flush(), which uses Z_SYNC_FLUSH.
        # Call it explicitly in case a wrapper layer is added later.
        raw = getattr(output, "buffer", output)
        if isinstance(raw, gzip.GzipFile):
            raw.flush(zlib.Z_SYNC_FLUSH)


def capture(fd, args, output, output_is_text: bool) -> None:
    if args.seconds <= 0:
        deadline = None
    else:
        deadline = time.monotonic() + args.seconds

    sync_gzip = args.output is not None and output_is_text
    next_flush = time.monotonic() + args.flush_seconds
    dirty = False

    def emit(rendered: bytes) -> None:
        nonlocal dirty
        if output_is_text:
            output.write(rendered.decode("utf-8", errors="replace"))
        else:
            output.write(rendered)
        dirty = True

    pending = b""
    try:
        while deadline is None or time.monotonic() < deadline:
            timeout = 0.25 if deadline is None else min(0.25, deadline - time.monotonic())
            ready, _, _ = select.select([fd], [], [], max(timeout, 0))
            if ready:
                data = os.read(fd, 4096)
                if data:
                    if not args.timestamp_lines:
                        emit(data)
                    else:
                        pending += data
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            timestamp = datetime.datetime.now().astimezone().isoformat(
                                timespec="milliseconds"
                            )
                            emit(f"@{timestamp} ".encode() + line + b"\n")
                    if not sync_gzip:
                        output.flush()
                        dirty = False

            if sync_gzip and dirty and time.monotonic() >= next_flush:
                flush_output(output, output_is_text, True)
                dirty = False
                next_flush = time.monotonic() + args.flush_seconds
    except StopRequested as exc:
        print(f"Stopping on {exc}", file=sys.stderr)
    finally:
        if pending:
            emit(pending)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("device", nargs="?", default="/dev/ttyACM0")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument(
        "--timestamp-lines",
        action="store_true",
        help="Prefix each serial line with the host's ISO timestamp",
    )
    parser.add_argument(
        "--flush-seconds",
        type=float,
        default=10.0,
        help="Write a gzip sync point every N seconds so a hard kill loses at most "
        "this much data (default: 10)",
    )
    args = parser.parse_args()

    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), request_stop)
    # SIGINT already raises KeyboardInterrupt; route it through the same path.
    signal.signal(signal.SIGINT, request_stop)

    output = sys.stdout.buffer
    output_is_text = False
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix == ".gz":
            output = gzip.open(args.output, "wt", encoding="utf-8", newline="")
            output_is_text = True
        else:
            output = args.output.open("wb")

    fd = os.open(args.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        tty.setraw(fd)
        modem_lines = termios.TIOCM_DTR | termios.TIOCM_RTS
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack("I", modem_lines))
        capture(fd, args, output, output_is_text)
    except StopRequested as exc:
        print(f"Stopping on {exc}", file=sys.stderr)
    finally:
        os.close(fd)
        if args.output is not None:
            # Ignore further stop signals while the gzip trailer is written.
            for name in ("SIGINT", "SIGTERM", "SIGHUP"):
                if hasattr(signal, name):
                    signal.signal(getattr(signal, name), signal.SIG_IGN)
            output.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
