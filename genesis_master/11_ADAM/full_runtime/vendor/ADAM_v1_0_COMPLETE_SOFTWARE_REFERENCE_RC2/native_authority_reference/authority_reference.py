from __future__ import annotations

import hashlib
import os
import struct
import sys
from pathlib import Path

MAGIC = b"A43F"
HEADER = struct.Struct(">4sIQ32s32s")
DOMAIN = b"ADAM43:NATIVE_FRAME\0"
ZERO_ROOT = b"\0" * 32


def frame_root(sequence: int, previous: bytes, payload: bytes) -> bytes:
    return hashlib.sha256(DOMAIN + sequence.to_bytes(8, "big") + previous + payload).digest()


def replay(path: Path) -> tuple[int, bytes]:
    sequence, root = 0, ZERO_ROOT
    if not path.exists():
        return sequence, root
    with path.open("rb") as handle:
        while True:
            header = handle.read(HEADER.size)
            if not header:
                return sequence, root
            if len(header) != HEADER.size:
                raise ValueError("truncated frame header")
            magic, payload_len, frame_sequence, previous, recorded = HEADER.unpack(header)
            if magic != MAGIC or frame_sequence != sequence + 1 or previous != root:
                raise ValueError("frame chain mismatch")
            payload = handle.read(payload_len)
            if len(payload) != payload_len:
                raise ValueError("truncated frame payload")
            computed = frame_root(frame_sequence, root, payload)
            if computed != recorded:
                raise ValueError("frame digest mismatch")
            sequence, root = frame_sequence, computed


def append(path: Path, sequence: int, root: bytes, payload: bytes) -> bytes:
    next_root = frame_root(sequence, root, payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab", buffering=0) as handle:
        handle.write(HEADER.pack(MAGIC, len(payload), sequence, root, next_root))
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return next_root


def decode_hex(value: str) -> bytes:
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("bad hex") from exc


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} LOG_PATH", file=sys.stderr)
        return 64
    path = Path(argv[1])
    try:
        sequence, root = replay(path)
    except ValueError:
        print(f"integrity failure while replaying {path}", file=sys.stderr)
        return 65
    print(f"READY ADAM43-NATIVE-FRAMING-REFERENCE {sequence}", flush=True)
    for raw in sys.stdin:
        line = raw.rstrip("\r\n")
        if line == "QUIT":
            print("OK BYE", flush=True)
            return 0
        if line in {"ROOT", "VERIFY"}:
            if line == "VERIFY":
                try:
                    sequence, root = replay(path)
                except ValueError:
                    print("ERR INTEGRITY", flush=True)
                    continue
            print(f"OK {sequence} {root.hex()}", flush=True)
            continue
        if line.startswith("HASH "):
            try:
                payload = decode_hex(line[5:])
            except ValueError:
                print("ERR BAD_HEX", flush=True)
                continue
            print(f"OK {hashlib.sha256(payload).hexdigest()}", flush=True)
            continue
        if line.startswith("APPEND "):
            body = line[7:]
            if " " in body:
                expected_hex, payload_hex = body.split(" ", 1)
                try:
                    expected = decode_hex(expected_hex)
                except ValueError:
                    print("ERR BAD_APPEND", flush=True)
                    continue
                if len(expected) != 32:
                    print("ERR BAD_APPEND", flush=True)
                    continue
                if expected != root:
                    print("ERR STALE_ROOT", flush=True)
                    continue
            else:
                payload_hex = body
            try:
                payload = decode_hex(payload_hex)
                root = append(path, sequence + 1, root, payload)
                sequence += 1
            except (ValueError, OSError):
                print("ERR WRITE_FAILED", flush=True)
                continue
            print(f"OK {sequence} {root.hex()}", flush=True)
            continue
        print("ERR UNKNOWN_COMMAND", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
