from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import sha256_bytes
from .universe import AtomicUniverse, IntegrityError

# Deterministic gear table generated from SHA-256 labels rather than random process state.
_GEAR = [int.from_bytes(__import__("hashlib").sha256(f"ADAM41-GEAR-{i}".encode()).digest()[:8], "big") for i in range(256)]


@dataclass(frozen=True)
class ExactObject:
    object_id: str
    content_hash: str
    size: int
    chunks: int
    media_type: str
    name: str | None


class ExactCodec:
    """Exact byte chemistry using content-defined chunks and ordered compound recipes."""

    def __init__(self, universe: AtomicUniverse, *, capability: object | None = None):
        self.universe = universe
        self.capability = capability

    @staticmethod
    def chunk(data: bytes, min_size: int = 256, avg_size: int = 1024, max_size: int = 4096) -> list[bytes]:
        if not data:
            return [b""]
        mask = avg_size - 1
        if avg_size & mask:
            raise ValueError("avg_size must be a power of two")
        chunks: list[bytes] = []
        start = 0
        rolling = 0
        for i, byte in enumerate(data):
            rolling = ((rolling << 1) + _GEAR[byte]) & 0xFFFFFFFFFFFFFFFF
            length = i + 1 - start
            if length >= min_size and ((rolling & mask) == 0 or length >= max_size):
                chunks.append(data[start : i + 1])
                start = i + 1
                rolling = 0
        if start < len(data):
            chunks.append(data[start:])
        return chunks

    def ingest(self, data: bytes, *, media_type: str = "application/octet-stream", name: str | None = None) -> ExactObject:
        ops = []
        members = []
        for order, chunk in enumerate(self.chunk(data)):
            atom_id, op = self.universe.atom_op("exact_chunk", chunk)
            ops.append(op)
            members.append({"role": "chunk", "order": order, "ref": atom_id, "length": len(chunk)})
        metadata = {"content_hash": sha256_bytes(data), "size": len(data), "media_type": media_type, "name": name}
        object_id, compound_op = self.universe.compound_op("exact_object", members, metadata)
        ops.append(compound_op)
        self.universe.commit(
            ops,
            metadata={"action": "ingest_exact", "content_hash": metadata["content_hash"]},
            capability=self.capability,
        )
        rebuilt = self.reconstruct(object_id)
        if rebuilt != data:
            raise IntegrityError("Exact reconstruction failed after ingestion")
        return ExactObject(object_id, metadata["content_hash"], len(data), len(members), media_type, name)

    def reconstruct(self, object_id: str) -> bytes:
        compound = self.universe.compounds.get(object_id)
        if compound is None or compound.kind != "exact_object":
            raise KeyError(object_id)
        ordered = sorted(compound.members, key=lambda x: int(x["order"]))
        parts = []
        for member in ordered:
            atom = self.universe.atoms.get(str(member["ref"]))
            if atom is None or atom.kind != "exact_chunk" or not isinstance(atom.value, bytes):
                raise IntegrityError("Exact object references invalid chunk")
            if len(atom.value) != int(member["length"]):
                raise IntegrityError("Chunk length mismatch")
            parts.append(atom.value)
        data = b"".join(parts)
        if len(data) != int(compound.metadata["size"]) or sha256_bytes(data) != compound.metadata["content_hash"]:
            raise IntegrityError("Exact object checksum mismatch")
        return data
