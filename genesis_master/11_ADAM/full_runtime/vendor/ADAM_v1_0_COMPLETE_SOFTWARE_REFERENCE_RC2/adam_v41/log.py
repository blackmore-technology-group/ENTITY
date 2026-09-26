from __future__ import annotations

import hashlib
import os
import struct
import time
from pathlib import Path
from typing import Any, Callable

from .authority import Authority
from .canonical import pack, unpack

_FRAME = struct.Struct(">I")
_DIGEST_BYTES = 32
_ZERO_ROOT = "00" * 32


class LogIntegrityError(RuntimeError):
    pass


class EventLog:
    """Signed, hash-chained, append-only event log with torn-tail truncation."""

    def __init__(self, path: Path, authority: Authority, *, base_seq: int = 0, base_root: str = _ZERO_ROOT):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self.authority = authority
        self.base_seq = int(base_seq)
        self.base_root = str(base_root)
        self.seq = self.base_seq
        self.root_hash = self.base_root
        self.recovered_torn_bytes = 0

    @staticmethod
    def _next_root(prev_root: str, event_hash: str) -> str:
        return hashlib.sha256(bytes.fromhex(prev_root) + bytes.fromhex(event_hash)).hexdigest()

    def recover(self, apply: Callable[[dict[str, Any]], None]) -> None:
        self.seq = self.base_seq
        self.root_hash = self.base_root
        self.recovered_torn_bytes = 0
        valid_end = 0
        size = self.path.stat().st_size
        with self.path.open("rb") as f:
            while True:
                start = f.tell()
                header = f.read(_FRAME.size)
                if not header:
                    valid_end = start
                    break
                if len(header) != _FRAME.size:
                    valid_end = start
                    break
                (length,) = _FRAME.unpack(header)
                if length <= 0 or length > 256 * 1024 * 1024:
                    valid_end = start
                    break
                payload = f.read(length)
                digest_bytes = f.read(_DIGEST_BYTES)
                if len(payload) != length or len(digest_bytes) != _DIGEST_BYTES:
                    valid_end = start
                    break
                actual = hashlib.sha256(payload).digest()
                if actual != digest_bytes:
                    # Corruption in the final frame is recoverable as a torn tail.
                    if f.tell() == size:
                        valid_end = start
                        break
                    raise LogIntegrityError(f"Corrupt non-tail frame at byte {start}")
                envelope = unpack(payload)
                core = envelope.get("core")
                signature = envelope.get("signature")
                if not isinstance(core, dict) or not isinstance(signature, str):
                    raise LogIntegrityError(f"Malformed frame at byte {start}")
                expected_seq = self.seq + 1
                if int(core.get("seq", -1)) != expected_seq:
                    raise LogIntegrityError(f"Sequence discontinuity at byte {start}")
                if str(core.get("prev_root")) != self.root_hash:
                    raise LogIntegrityError(f"Hash-chain discontinuity at byte {start}")
                if str(core.get("authority_id")) != self.authority.authority_id:
                    raise LogIntegrityError(f"Unexpected authority at byte {start}")
                core_bytes = pack(core)
                if not Authority.verify(self.authority.public_key_hex, core_bytes, signature):
                    raise LogIntegrityError(f"Invalid event signature at byte {start}")
                event_hash = actual.hex()
                apply(core)
                self.seq = expected_seq
                self.root_hash = self._next_root(self.root_hash, event_hash)
                valid_end = f.tell()
        if valid_end < size:
            self.recovered_torn_bytes = size - valid_end
            with self.path.open("r+b") as f:
                f.truncate(valid_end)
                f.flush()
                os.fsync(f.fileno())

    def append(self, ops: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        core = {
            "seq": self.seq + 1,
            "prev_root": self.root_hash,
            "authority_id": self.authority.authority_id,
            "time_ns": time.time_ns(),
            "metadata": metadata or {},
            "ops": ops,
        }
        core_bytes = pack(core)
        envelope = {"core": core, "signature": self.authority.sign(core_bytes)}
        payload = pack(envelope)
        digest_bytes = hashlib.sha256(payload).digest()
        frame = _FRAME.pack(len(payload)) + payload + digest_bytes
        with self.path.open("ab") as f:
            f.write(frame)
            f.flush()
            os.fsync(f.fileno())
        self.seq += 1
        self.root_hash = self._next_root(self.root_hash, digest_bytes.hex())
        return core
