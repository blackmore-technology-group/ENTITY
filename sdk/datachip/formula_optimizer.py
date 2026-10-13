"""Opt-in bounded, deterministic segment-aware formula compiler.

Same entity-datachip-formula-v0.2 wire format as formula_chip.py.
This module does NOT replace the canonical compiler or authorize exports.
It recognizes periodic subregions within mixed byte streams and deduplicates
identical 1MiB segments while retaining all irreducible entropy.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from typing import Any
from .formula_chip import (
    MAX_OUTPUT, MAX_LITERAL, MAX_NODES, MAX_CHILDREN, _write_formula
)
from .processor import DataChipError

def pack_segmented_formula_bytes(data: bytes, target: str | Path, *,
                                 segment_bytes: int = 1 << 20) -> dict[str, Any]:
    """Pack up to 64MiB with exact-v0.2 representation and bounded work.

    segment_bytes is deliberately restricted to 64KiB..1MiB and power-of-two
    for deterministic checkpoints and conservative parser resource accounting.
    The compiler never drops entropy; output is verified by _write_formula.
    """
    if type(data) is not bytes:
        raise TypeError("data must be immutable bytes")
    if len(data) > MAX_OUTPUT:
        raise DataChipError("input exceeds formula cap")
    if (type(segment_bytes) is not int or segment_bytes < 65536 or
            segment_bytes > MAX_LITERAL or segment_bytes & (segment_bytes - 1)):
        raise ValueError("segment size must be power-of-two in [64KiB,1MiB]")
    nodes: list[dict[str, Any]] = []
    entropy: dict[str, bytes] = {}
    atom_memo: dict[bytes, int] = {}
    leaf_memo: dict[str, int] = {}
    segment_memo: dict[str, int] = {}

    def put(node: dict[str, Any]) -> int:
        if len(nodes) >= MAX_NODES:
            raise DataChipError("formula node cap exceeded")
        nodes.append(node)
        return len(nodes) - 1

    def leaf(part: bytes) -> int:
        if len(part) == 0:
            return put({"op": "CONCAT", "bytes": 0, "children": []})
        if len(part) == 1:
            if part in atom_memo:
                return atom_memo[part]
            ident = put({"op": "ATOM", "bytes": 1, "atom": part[0]})
            atom_memo[part] = ident
            return ident
        if len(part) > MAX_LITERAL:
            raise DataChipError("entropy leaf too large")
        digest = sha256(part).hexdigest()
        existing = leaf_memo.get(digest)
        if existing is not None:
            return existing
        entropy[digest] = part
        ident = put({"op": "ENTROPY", "bytes": len(part), "sha256": digest})
        leaf_memo[digest] = ident
        return ident

    def segment(part: bytes) -> int:
        digest = sha256(part).hexdigest()
        existing = segment_memo.get(digest)
        if existing is not None:
            return existing
        if len(part) < 8:
            ident = leaf(part)
        else:
            probe = part[:min(8192, len(part))]
            period = 0
            for p in range(1, min(4096, len(part)//4) + 1):
                if probe[p:] == probe[:-p] and part[p:] == part[:-p]:
                    period = p
                    break
            if period == 0:
                ident = leaf(part)
            else:
                basis = leaf(part[:period])
                whole, remaining = divmod(len(part), period)
                children = []
                if whole:
                    children.append(put({"op": "REPEAT", "bytes": whole * period,
                                         "child": basis, "count": whole}))
                if remaining:
                    children.append(leaf(part[:remaining]))
                ident = children[0] if len(children) == 1 else put({
                    "op": "CONCAT", "bytes": len(part), "children": children})
        segment_memo[digest] = ident
        return ident

    roots = [segment(data[start:start + segment_bytes])
             for start in range(0, len(data), segment_bytes)]
    if not roots:
        root = put({"op": "CONCAT", "bytes": 0, "children": []})
    elif len(roots) == 1:
        root = roots[0]
    else:
        if len(roots) > MAX_CHILDREN:
            raise DataChipError("too many segments")
        root = put({"op": "CONCAT", "bytes": len(data), "children": roots})
    return _write_formula(nodes, root, entropy, target, sha256(data).hexdigest(),
                          len(data))
