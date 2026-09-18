#!/usr/bin/env python3
"""Capture a Linux USB ACM serial device without external dependencies."""

import argparse
import datetime
import fcntl
import gzip
import os
import pathlib
import select
import struct
import sys
import termios
import time
import tty


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
    args = parser.parse_args()

    if args.seconds <= 0:
        deadline = None
    else:
        deadline = time.monotonic() + args.seconds

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

        pending = b""
        while deadline is None or time.monotonic() < deadline:
            timeout = 0.25 if deadline is None else min(0.25, deadline - time.monotonic())
            ready, _, _ = select.select([fd], [], [], timeout)
            if not ready:
                continue
            data = os.read(fd, 4096)
            if not data:
                continue

            if not args.timestamp_lines:
                if output_is_text:
                    output.write(data.decode("utf-8", errors="replace"))
                else:
                    output.write(data)
                output.flush()
                continue

            pending += data
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                timestamp = datetime.datetime.now().astimezone().isoformat(
                    timespec="milliseconds"
                )
                rendered = f"@{timestamp} ".encode() + line + b"\n"
                if output_is_text:
                    output.write(rendered.decode("utf-8", errors="replace"))
                else:
                    output.write(rendered)
                output.flush()

        if pending:
            if output_is_text:
                output.write(pending.decode("utf-8", errors="replace"))
            else:
                output.write(pending)
            output.flush()
    finally:
        os.close(fd)
        if args.output is not None:
            output.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
