from __future__ import annotations

import hashlib
import json
from typing import Any

import msgpack


def canonicalize(value: Any) -> Any:
    """Return a recursively deterministic, msgpack-safe value."""
    if isinstance(value, dict):
        return {str(k): canonicalize(value[k]) for k in sorted(value, key=lambda x: str(x))}
    if isinstance(value, (list, tuple)):
        return [canonicalize(v) for v in value]
    if isinstance(value, set):
        return [canonicalize(v) for v in sorted(value, key=repr)]
    if isinstance(value, (str, bytes, int, float, bool)) or value is None:
        return value
    raise TypeError(f"Unsupported canonical type: {type(value)!r}")


def pack(value: Any) -> bytes:
    return msgpack.packb(canonicalize(value), use_bin_type=True, strict_types=True)


def unpack(data: bytes) -> Any:
    return msgpack.unpackb(data, raw=False, strict_map_key=False)


def digest(domain: str, value: Any) -> str:
    h = hashlib.sha256()
    h.update(domain.encode("utf-8"))
    h.update(b"\0")
    h.update(pack(value))
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
