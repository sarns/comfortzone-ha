#!/usr/bin/env python3
"""Capture a Linux USB ACM serial device without external dependencies."""

import argparse
import fcntl
import os
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
    args = parser.parse_args()

    fd = os.open(args.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        tty.setraw(fd)
        modem_lines = termios.TIOCM_DTR | termios.TIOCM_RTS
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack("I", modem_lines))

        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], min(0.25, deadline - time.monotonic()))
            if not ready:
                continue
            data = os.read(fd, 4096)
            if data:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
    finally:
        os.close(fd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
