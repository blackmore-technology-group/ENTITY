from __future__ import annotations

"""Memory-bounded recovery for large signed ADAM v0.41 event frames.

This module does not alter, rewrite, or re-sign historical frames. It verifies the
existing frame digest and Ed25519 signature, parses large MsgPack arrays lazily, and
applies one authoritative operation at a time at the original event sequence.

Small frames use the stock recovery path semantics. Large frames use bounded parsing
only for AtomicUniverse._apply_core, preserving the same deterministic state.
"""

from pathlib import Path
from typing import Any, Callable
import hashlib
import json
import mmap
import os
import struct
import zlib

import msgpack

_FRAME = struct.Struct(">I")
_DIGEST_BYTES = 32
_ZERO_ROOT = "00" * 32
_DEFAULT_STREAM_THRESHOLD = 8 * 1024 * 1024


class MemoryBoundRecoveryError(RuntimeError):
    pass


class _BoundedHashingReader:
    """Read at most a fixed byte limit while hashing exactly what MsgPack consumes."""

    def __init__(self, handle, limit: int):
        self.handle = handle
        self.remaining = int(limit)
        self.hasher = hashlib.sha256()

    def read(self, n: int = -1) -> bytes:
        if self.remaining <= 0:
            return b""
        if n is None or n < 0:
            n = self.remaining
        n = min(int(n), self.remaining)
        data = self.handle.read(n)
        if data:
            self.remaining -= len(data)
            self.hasher.update(data)
        return data

    def drain(self) -> None:
        while self.remaining > 0:
            block = self.read(min(4 * 1024 * 1024, self.remaining))
            if not block:
                raise MemoryBoundRecoveryError("truncated ADAM frame payload")


class _BoundedReader:
    """File-like bounded view used by msgpack.Unpacker without whole-frame buffering."""

    def __init__(self, handle, limit: int):
        self.handle = handle
        self.remaining = int(limit)

    def read(self, n: int = -1) -> bytes:
        if self.remaining <= 0:
            return b""
        if n is None or n < 0:
            n = self.remaining
        n = min(int(n), self.remaining)
        data = self.handle.read(n)
        if data:
            self.remaining -= len(data)
        return data


def _scan_signed_envelope_file(path: Path, payload_offset: int, payload_length: int):
    """Hash and structurally scan a signed envelope without buffering the frame."""
    with Path(path).open("rb") as fh:
        fh.seek(int(payload_offset))
        reader = _BoundedHashingReader(fh, int(payload_length))
        u = msgpack.Unpacker(
            reader,
            raw=False,
            strict_map_key=False,
            read_size=1024 * 1024,
            max_buffer_size=32 * 1024 * 1024,
        )
        try:
            envelope_count = u.read_map_header()
        except Exception as exc:
            raise MemoryBoundRecoveryError("Malformed ADAM envelope") from exc

        core_start = core_end = None
        signature = None
        fields: dict[str, Any] = {}
        ops_count = -1

        for _ in range(envelope_count):
            key = u.unpack()
            if key == "core":
                core_start = int(u.tell())
                try:
                    core_items = u.read_map_header()
                except Exception as exc:
                    raise MemoryBoundRecoveryError("Malformed ADAM core") from exc
                for _j in range(core_items):
                    core_key = u.unpack()
                    if core_key == "ops":
                        ops_count = int(u.read_array_header())
                        for _k in range(ops_count):
                            u.skip()
                    else:
                        fields[str(core_key)] = u.unpack()
                core_end = int(u.tell())
            elif key == "signature":
                signature = u.unpack()
            else:
                u.skip()

        reader.drain()
        if core_start is None or core_end is None or not isinstance(signature, str):
            raise MemoryBoundRecoveryError("ADAM envelope missing core/signature")
        if ops_count < 0:
            raise MemoryBoundRecoveryError("ADAM core missing ops")
        return {
            "core_offset": int(payload_offset) + core_start,
            "core_length": core_end - core_start,
            "signature": signature,
            "fields": fields,
            "ops_count": ops_count,
            "payload_sha256": reader.hasher.digest(),
        }


def _verify_mapped_core(path: Path, core_offset: int, core_length: int, public_key_hex: str, signature: str) -> bool:
    """Verify Ed25519 over the exact signed core through a zero-copy mmap view."""
    from adam_v41.authority import Authority
    with Path(path).open("rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        view = None
        try:
            view = memoryview(mm)[int(core_offset):int(core_offset) + int(core_length)]
            return Authority.verify(public_key_hex, view, signature)
        finally:
            if view is not None:
                view.release()
            mm.close()


def _iter_ops_file(path: Path, core_offset: int, core_length: int):
    """Yield one operation at a time from an already-verified signed core."""
    with Path(path).open("rb") as fh:
        fh.seek(int(core_offset))
        reader = _BoundedReader(fh, int(core_length))
        u = msgpack.Unpacker(
            reader,
            raw=False,
            strict_map_key=False,
            read_size=1024 * 1024,
            max_buffer_size=32 * 1024 * 1024,
        )
        try:
            count = u.read_map_header()
        except Exception as exc:
            raise MemoryBoundRecoveryError("Malformed ADAM core") from exc
        found = False
        for _ in range(count):
            key = u.unpack()
            if key == "ops":
                found = True
                n = u.read_array_header()
                for _i in range(n):
                    op = u.unpack()
                    if not isinstance(op, dict):
                        raise MemoryBoundRecoveryError("ADAM operation is not a map")
                    yield op
            else:
                u.skip()
        if not found:
            raise MemoryBoundRecoveryError("ADAM core missing ops")


def _extract_signed_core(payload: bytes) -> tuple[bytes, str]:
    """Return the exact packed core bytes and signature without unpacking the core."""
    u = msgpack.Unpacker(raw=False, strict_map_key=False)
    u.feed(payload)
    try:
        count = u.read_map_header()
    except Exception as exc:
        raise MemoryBoundRecoveryError("Malformed ADAM envelope") from exc

    core_start = None
    core_end = None
    signature = None
    for _ in range(count):
        key = u.unpack()
        if key == "core":
            core_start = u.tell()
            u.skip()
            core_end = u.tell()
        elif key == "signature":
            signature = u.unpack()
        else:
            u.skip()

    if core_start is None or core_end is None or not isinstance(signature, str):
        raise MemoryBoundRecoveryError("ADAM envelope missing core/signature")
    return payload[core_start:core_end], signature


def _core_fields_without_ops(core_bytes: bytes) -> tuple[dict[str, Any], int]:
    """Parse signed core metadata while skipping the potentially huge ops array."""
    u = msgpack.Unpacker(raw=False, strict_map_key=False)
    u.feed(core_bytes)
    try:
        count = u.read_map_header()
    except Exception as exc:
        raise MemoryBoundRecoveryError("Malformed ADAM core") from exc

    fields: dict[str, Any] = {}
    ops_count = -1
    for _ in range(count):
        key = u.unpack()
        if key == "ops":
            ops_count = u.read_array_header()
            for _i in range(ops_count):
                u.skip()
        else:
            fields[str(key)] = u.unpack()

    if ops_count < 0:
        raise MemoryBoundRecoveryError("ADAM core missing ops")
    return fields, ops_count


def _iter_ops(core_bytes: bytes):
    """Yield one operation at a time from an exact signed core."""
    u = msgpack.Unpacker(raw=False, strict_map_key=False)
    u.feed(core_bytes)
    count = u.read_map_header()
    found = False
    for _ in range(count):
        key = u.unpack()
        if key == "ops":
            found = True
            n = u.read_array_header()
            for _i in range(n):
                op = u.unpack()
                if not isinstance(op, dict):
                    raise MemoryBoundRecoveryError("ADAM operation is not a map")
                yield op
        else:
            u.skip()
    if not found:
        raise MemoryBoundRecoveryError("ADAM core missing ops")


def _is_atomic_apply(apply: Callable[[dict[str, Any]], None]) -> bool:
    owner = getattr(apply, "__self__", None)
    name = getattr(apply, "__name__", "")
    return owner is not None and name == "_apply_core" and owner.__class__.__name__ == "AtomicUniverse"


def install_memory_bounded_recovery(*, threshold_bytes: int = _DEFAULT_STREAM_THRESHOLD) -> None:
    """Patch adam_v41.log.EventLog.recover in-process with a bounded equivalent."""
    from adam_v41.authority import Authority
    from adam_v41.canonical import pack, unpack
    from adam_v41 import log as adam_log

    EventLog = adam_log.EventLog
    if getattr(EventLog.recover, "_entity_memory_bounded", False):
        return

    stock_recover = EventLog.recover
    LogIntegrityError = adam_log.LogIntegrityError

    def recover(self, apply: Callable[[dict[str, Any]], None]) -> None:
        self.seq = self.base_seq
        self.root_hash = self.base_root
        self.recovered_torn_bytes = 0
        valid_end = 0
        size = self.path.stat().st_size
        atomic_apply = _is_atomic_apply(apply)

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

                payload_offset = f.tell()
                frame_end = payload_offset + int(length) + _DIGEST_BYTES
                if frame_end > size:
                    valid_end = start
                    break

                # Large AtomicUniverse frames are scanned directly from disk.  This
                # avoids holding payload + core + MsgPack internal copies at once.
                if atomic_apply and length >= int(threshold_bytes):
                    try:
                        scanned = _scan_signed_envelope_file(self.path, payload_offset, length)
                    except Exception as exc:
                        raise LogIntegrityError(f"Malformed large frame at byte {start}") from exc

                    f.seek(payload_offset + int(length))
                    digest_bytes = f.read(_DIGEST_BYTES)
                    if len(digest_bytes) != _DIGEST_BYTES:
                        valid_end = start
                        break
                    actual = scanned["payload_sha256"]
                    if actual != digest_bytes:
                        if frame_end == size:
                            valid_end = start
                            break
                        raise LogIntegrityError(f"Corrupt non-tail frame at byte {start}")

                    fields = scanned["fields"]
                    signature = scanned["signature"]
                    expected_seq = self.seq + 1
                    if int(fields.get("seq", -1)) != expected_seq:
                        raise LogIntegrityError(f"Sequence discontinuity at byte {start}")
                    if str(fields.get("prev_root")) != self.root_hash:
                        raise LogIntegrityError(f"Hash-chain discontinuity at byte {start}")
                    if str(fields.get("authority_id")) != self.authority.authority_id:
                        raise LogIntegrityError(f"Unexpected authority at byte {start}")
                    if not _verify_mapped_core(
                        self.path,
                        scanned["core_offset"],
                        scanned["core_length"],
                        self.authority.public_key_hex,
                        signature,
                    ):
                        raise LogIntegrityError(f"Invalid event signature at byte {start}")

                    saw = False
                    for op in _iter_ops_file(
                        self.path, scanned["core_offset"], scanned["core_length"]
                    ):
                        saw = True
                        apply({"seq": expected_seq, "ops": [op]})
                    if not saw:
                        apply({"seq": expected_seq, "ops": []})
                    f.seek(frame_end)

                else:
                    payload = f.read(length)
                    digest_bytes = f.read(_DIGEST_BYTES)
                    if len(payload) != length or len(digest_bytes) != _DIGEST_BYTES:
                        valid_end = start
                        break

                    actual = hashlib.sha256(payload).digest()
                    if actual != digest_bytes:
                        if f.tell() == size:
                            valid_end = start
                            break
                        raise LogIntegrityError(f"Corrupt non-tail frame at byte {start}")

                    if not atomic_apply:
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
                        apply(core)
                    else:
                        try:
                            core_bytes, signature = _extract_signed_core(payload)
                            fields, _ops_count = _core_fields_without_ops(core_bytes)
                        except Exception as exc:
                            raise LogIntegrityError(f"Malformed frame at byte {start}") from exc

                        expected_seq = self.seq + 1
                        if int(fields.get("seq", -1)) != expected_seq:
                            raise LogIntegrityError(f"Sequence discontinuity at byte {start}")
                        if str(fields.get("prev_root")) != self.root_hash:
                            raise LogIntegrityError(f"Hash-chain discontinuity at byte {start}")
                        if str(fields.get("authority_id")) != self.authority.authority_id:
                            raise LogIntegrityError(f"Unexpected authority at byte {start}")
                        if not Authority.verify(self.authority.public_key_hex, core_bytes, signature):
                            raise LogIntegrityError(f"Invalid event signature at byte {start}")

                        saw = False
                        for op in _iter_ops(core_bytes):
                            saw = True
                            apply({"seq": expected_seq, "ops": [op]})
                        if not saw:
                            apply({"seq": expected_seq, "ops": []})

                event_hash = actual.hex()
                self.seq = expected_seq
                self.root_hash = self._next_root(self.root_hash, event_hash)
                valid_end = f.tell()

        if valid_end < size:
            self.recovered_torn_bytes = size - valid_end
            with self.path.open("r+b") as f:
                f.truncate(valid_end)
                f.flush()
                os.fsync(f.fileno())

    recover._entity_memory_bounded = True  # type: ignore[attr-defined]
    recover._stock_recover = stock_recover  # type: ignore[attr-defined]
    EventLog.recover = recover


_STREAM_CHECKPOINT_FORMAT = "ADAM-v0.41-streaming-checkpoint-v2"
_STREAM_RECEIPT_FORMAT = "ADAM-v0.41-streaming-checkpoint-v2-receipt"


def install_streaming_checkpoint(AtomicUniverse) -> None:
    """Install a low-peak-memory signed checkpoint writer/loader.

    The event-log root and sequence remain unchanged. The checkpoint is only a
    materialized authority state used to avoid replaying multi-gigabyte history.
    Existing v0.41 checkpoints remain readable through the stock loader.
    """

    if getattr(AtomicUniverse.write_native_checkpoint, "_entity_streaming_checkpoint", False):
        return

    from adam_v41.authority import Authority
    from adam_v41.canonical import canonicalize, sha256_bytes
    from adam_v41.universe import Atom, Bond, Compound, IntegrityError, AuthorityError

    stock_load = AtomicUniverse._load_checkpoint
    stock_write = AtomicUniverse.write_native_checkpoint

    def _write_record(packer, compressor, handle, hasher, record: dict[str, Any]) -> None:
        packed = packer.pack(canonicalize(record))
        encoded = compressor.compress(packed)
        if encoded:
            handle.write(encoded)
            hasher.update(encoded)

    def write_native_checkpoint(self, path: Path | str) -> dict[str, Any]:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        packer = msgpack.Packer(use_bin_type=True, strict_types=True)
        compressor = zlib.compressobj(level=9)
        hasher = hashlib.sha256()

        with path.open("wb") as handle:
            header = {
                "t": "header",
                "format": _STREAM_CHECKPOINT_FORMAT,
                "sequence": self.sequence,
                "root_hash": self.root_hash,
                "counts": {
                    "atoms": len(self.atoms),
                    "bonds": len(self.bonds),
                    "compounds": len(self.compounds),
                    "entity_versions": len(self.entity_versions),
                    "compound_aliases": len(self.compound_aliases),
                },
            }
            _write_record(packer, compressor, handle, hasher, header)

            for atom_id in sorted(self.atoms):
                atom = self.atoms[atom_id]
                _write_record(
                    packer, compressor, handle, hasher,
                    {
                        "t": "atom",
                        "id": atom.atom_id,
                        "kind": atom.kind,
                        "value": atom.value,
                        "metadata": atom.metadata,
                        "created_seq": atom.created_seq,
                    },
                )

            for compound_id in sorted(self.compounds):
                comp = self.compounds[compound_id]
                _write_record(
                    packer, compressor, handle, hasher,
                    {
                        "t": "compound",
                        "id": comp.compound_id,
                        "kind": comp.kind,
                        "members": comp.members,
                        "metadata": comp.metadata,
                        "created_seq": comp.created_seq,
                    },
                )

            for bond_id in sorted(self.bonds):
                bond = self.bonds[bond_id]
                _write_record(
                    packer, compressor, handle, hasher,
                    {
                        "t": "bond",
                        "id": bond.bond_id,
                        "source": bond.source,
                        "predicate": bond.predicate,
                        "target": bond.target,
                        "order": bond.order,
                        "context": bond.context,
                        "valid_from": bond.valid_from,
                        "valid_until": bond.valid_until,
                        "metadata": bond.metadata,
                        "created_seq": bond.created_seq,
                        "revoked_seq": bond.revoked_seq,
                    },
                )

            for entity_id, version in sorted(self.entity_versions.items()):
                _write_record(
                    packer, compressor, handle, hasher,
                    {"t": "entity_version", "id": entity_id, "version": int(version)},
                )

            for name, compound_id in sorted(self.compound_aliases.items()):
                _write_record(
                    packer, compressor, handle, hasher,
                    {"t": "compound_alias", "name": name, "compound_id": compound_id},
                )

            _write_record(
                packer, compressor, handle, hasher,
                {
                    "t": "end",
                    "sequence": self.sequence,
                    "root_hash": self.root_hash,
                },
            )
            tail = compressor.flush()
            if tail:
                handle.write(tail)
                hasher.update(tail)
            handle.flush()
            os.fsync(handle.fileno())

        digest_hex = hasher.hexdigest()
        receipt = {
            "format": _STREAM_RECEIPT_FORMAT,
            "sequence": self.sequence,
            "root_hash": self.root_hash,
            "payload_sha256": digest_hex,
            "authority_id": self.authority.authority_id,
            "signature": self.authority.sign(bytes.fromhex(digest_hex)),
        }
        receipt_path = path.with_suffix(path.suffix + ".receipt.json")
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        return receipt

    def _verified_receipt(self, path: Path):
        receipt_path = path.with_suffix(path.suffix + ".receipt.json")
        if not receipt_path.exists():
            raise IntegrityError("Checkpoint receipt missing")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("format") != _STREAM_RECEIPT_FORMAT:
            return None, receipt

        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                hasher.update(block)
        digest_hex = hasher.hexdigest()
        if digest_hex != receipt.get("payload_sha256"):
            raise IntegrityError("Streaming checkpoint digest mismatch")
        if receipt.get("authority_id") != self.authority.authority_id:
            raise AuthorityError("Streaming checkpoint authority mismatch")
        if not Authority.verify(
            self.authority.public_key_hex,
            bytes.fromhex(digest_hex),
            str(receipt.get("signature")),
        ):
            raise AuthorityError("Streaming checkpoint signature invalid")
        return digest_hex, receipt

    def _iter_stream_records(path: Path):
        # Bound decompressed output as well as compressed input. A few MB of highly
        # compressible checkpoint data can expand to hundreds of MB if zlib is
        # allowed to materialize the whole output of one input block at once.
        unpacker = msgpack.Unpacker(
            raw=False,
            strict_map_key=False,
            max_buffer_size=4 * 1024 * 1024,
        )
        decompressor = zlib.decompressobj()
        # Keep both compressed input and decompressed output deliberately tiny.
        # The production BTG workstation can have <1 GB free during startup and
        # zlib's output allocation can fail even when a 1 MiB cap looks small.
        output_limit = 64 * 1024

        def emit(decoded: bytes):
            if not decoded:
                return
            unpacker.feed(decoded)

        def drain_records():
            while True:
                try:
                    yield unpacker.unpack()
                except msgpack.OutOfData:
                    break

        with path.open("rb") as handle:
            while True:
                block = handle.read(64 * 1024)
                if not block:
                    break
                pending = block
                while pending:
                    decoded = decompressor.decompress(pending, output_limit)
                    pending = decompressor.unconsumed_tail
                    emit(decoded)
                    yield from drain_records()
                    if not decoded and not pending:
                        break

            # Drain any output zlib buffered because max_length was reached.
            while True:
                decoded = decompressor.decompress(b"", output_limit)
                if not decoded:
                    break
                emit(decoded)
                yield from drain_records()

            # At EOF the decompressor should have consumed the full stream. Any
            # small final flush is bounded; a non-EOF stream is rejected below.
            tail = decompressor.flush(output_limit)
            if tail:
                emit(tail)
                yield from drain_records()
            yield from drain_records()

        if not decompressor.eof:
            raise IntegrityError("Streaming checkpoint compressed payload is truncated")

    def _load_checkpoint(self, path: Path) -> None:
        path = Path(path)
        digest_hex, receipt = _verified_receipt(self, path)
        if digest_hex is None:
            return stock_load(self, path)

        # The signed receipt authenticates the SHA-256 of the complete checkpoint
        # before any record is accepted. Re-hashing every content-addressed ID during
        # ordinary startup duplicates millions of canonical hash operations and can
        # cause severe paging on large universes. Qualification can force full ID
        # recomputation with ENTITY_ADAM_CHECKPOINT_REVERIFY_IDS=1.
        reverify_ids = os.environ.get("ENTITY_ADAM_CHECKPOINT_REVERIFY_IDS", "0") == "1"
        self._reset_state()
        header = None
        end = None
        counts = {
            "atoms": 0,
            "bonds": 0,
            "compounds": 0,
            "entity_versions": 0,
            "compound_aliases": 0,
        }

        for record in _iter_stream_records(path):
            if not isinstance(record, dict):
                raise IntegrityError("Streaming checkpoint record is not a map")
            kind = record.get("t")

            if kind == "header":
                if header is not None:
                    raise IntegrityError("Duplicate streaming checkpoint header")
                if record.get("format") != _STREAM_CHECKPOINT_FORMAT:
                    raise IntegrityError("Unsupported streaming checkpoint format")
                header = record
                continue

            if header is None:
                raise IntegrityError("Streaming checkpoint data precedes header")

            if kind == "atom":
                atom_id = str(record["id"])
                atom_kind = str(record["kind"])
                value = record["value"]
                metadata = dict(record.get("metadata") or {})
                if reverify_ids and self.atom_id(atom_kind, value, metadata) != atom_id:
                    raise IntegrityError("Streaming checkpoint atom identity mismatch")
                self.atoms[atom_id] = Atom(
                    atom_id, atom_kind, value, metadata, int(record["created_seq"])
                )
                counts["atoms"] += 1
            elif kind == "compound":
                compound_id = str(record["id"])
                comp_kind = str(record["kind"])
                members = list(record["members"])
                metadata = dict(record.get("metadata") or {})
                if reverify_ids and self.compound_id(comp_kind, members, metadata) != compound_id:
                    raise IntegrityError("Streaming checkpoint compound identity mismatch")
                self.compounds[compound_id] = Compound(
                    compound_id, comp_kind, members, metadata, int(record["created_seq"])
                )
                counts["compounds"] += 1
            elif kind == "bond":
                body = {
                    "source": str(record["source"]),
                    "predicate": str(record["predicate"]),
                    "target": str(record["target"]),
                    "order": record.get("order"),
                    "context": record.get("context"),
                    "valid_from": record.get("valid_from"),
                    "valid_until": record.get("valid_until"),
                    "metadata": dict(record.get("metadata") or {}),
                }
                bond_id = str(record["id"])
                if reverify_ids and self.bond_id(body) != bond_id:
                    raise IntegrityError("Streaming checkpoint bond identity mismatch")
                self.bonds[bond_id] = Bond(
                    bond_id,
                    created_seq=int(record["created_seq"]),
                    revoked_seq=(
                        None if record.get("revoked_seq") is None
                        else int(record["revoked_seq"])
                    ),
                    **body,
                )
                counts["bonds"] += 1
            elif kind == "entity_version":
                self.entity_versions[str(record["id"])] = int(record["version"])
                counts["entity_versions"] += 1
            elif kind == "compound_alias":
                self.compound_aliases[str(record["name"])] = str(record["compound_id"])
                counts["compound_aliases"] += 1
            elif kind == "end":
                end = record
            else:
                raise IntegrityError(f"Unknown streaming checkpoint record {kind!r}")

        if header is None or end is None:
            raise IntegrityError("Streaming checkpoint header/end missing")

        expected_counts = dict(header.get("counts") or {})
        for key, actual in counts.items():
            if int(expected_counts.get(key, -1)) != actual:
                raise IntegrityError(
                    f"Streaming checkpoint {key} count mismatch: "
                    f"{actual} != {expected_counts.get(key)}"
                )

        receipt_seq = int(receipt["sequence"])
        receipt_root = str(receipt["root_hash"])
        if (
            int(header.get("sequence", -1)) != receipt_seq
            or str(header.get("root_hash")) != receipt_root
            or int(end.get("sequence", -1)) != receipt_seq
            or str(end.get("root_hash")) != receipt_root
        ):
            raise IntegrityError("Streaming checkpoint receipt/state mismatch")

        self.checkpoint_sequence = receipt_seq
        self.checkpoint_root = receipt_root

    write_native_checkpoint._entity_streaming_checkpoint = True  # type: ignore[attr-defined]
    write_native_checkpoint._stock_write = stock_write  # type: ignore[attr-defined]
    _load_checkpoint._entity_streaming_checkpoint = True  # type: ignore[attr-defined]
    _load_checkpoint._stock_load = stock_load  # type: ignore[attr-defined]
    AtomicUniverse.write_native_checkpoint = write_native_checkpoint
    AtomicUniverse._load_checkpoint = _load_checkpoint


__all__ = [
    "install_memory_bounded_recovery",
    "install_streaming_checkpoint",
    "MemoryBoundRecoveryError",
]
