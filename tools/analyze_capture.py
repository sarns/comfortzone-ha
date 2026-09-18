#!/usr/bin/env python3
"""Extract and summarize valid Comfortzone frames from sniffer text output."""

import argparse
import collections
import gzip
import pathlib
import re


def crc8_maxim(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8C if crc & 1 else 0)
    return crc


def extract_frames(data: bytes) -> list[bytes]:
    frames = []
    offset = 0
    while offset + 21 <= len(data):
        header = data[offset : offset + 21]
        destination = header[0:4]
        complement = bytes(value ^ 0xFF for value in destination)
        size = header[10]
        if (
            header[4] == crc8_maxim(destination)
            and header[5] == crc8_maxim(complement)
            and header[11] in b"RWrw"
            and 22 <= size <= 255
            and offset + size <= len(data)
        ):
            frame = data[offset : offset + size]
            if frame[-1] == crc8_maxim(frame[:-1]):
                frames.append(frame)
                offset += size
                continue
        offset += 1
    return frames


def read_capture(path: pathlib.Path) -> bytes:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as capture:
            text = capture.read()
    else:
        text = path.read_text(encoding="utf-8", errors="replace")

    raw_log_frames = re.findall(r"\bCZRAW\b[^\r\n]*\bframe=([0-9A-Fa-f]+)", text)
    if raw_log_frames:
        return b"".join(bytes.fromhex(frame) for frame in raw_log_frames)

    return bytes(
        int(value, 16)
        for value in re.findall(
            r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{2}(?![0-9A-Fa-f])", text
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=pathlib.Path)
    parser.add_argument("--samples", action="store_true")
    args = parser.parse_args()

    byte_values = read_capture(args.capture)
    frames = extract_frames(byte_values)

    groups: dict[tuple[str, int, str], list[bytes]] = collections.defaultdict(list)
    for frame in frames:
        register = " ".join(f"{value:02X}" for value in frame[12:21])
        groups[(register, len(frame), chr(frame[11]))].append(frame)

    print(f"Parsed {len(frames)} CRC-valid frames from {len(byte_values)} bytes")
    for (register, size, command), matching in sorted(groups.items()):
        print(f"{command} len={size:3d} count={len(matching):3d} reg={register}")
        if args.samples and command.islower():
            payload = matching[-1][21:-1]
            print("  payload=" + " ".join(f"{value:02X}" for value in payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
