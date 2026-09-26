from __future__ import annotations

from typing import Any

from .universe import AtomicUniverse, IntegrityError


class SemanticCodec:
    """Immutable recursive JSON chemistry linked to semantic compounds."""

    def __init__(self, universe: AtomicUniverse, *, capability: object | None = None):
        self.universe = universe
        self.capability = capability

    def ingest(self, value: Any) -> str:
        ops: list[dict[str, Any] | None] = []

        def walk(node: Any) -> str:
            if isinstance(node, dict):
                members = []
                for order, key in enumerate(sorted(node)):
                    child = walk(node[key])
                    members.append({"role": str(key), "order": order, "ref": child})
                ref, op = self.universe.compound_op("json_object", members)
                ops.append(op)
                return ref
            if isinstance(node, list):
                members = []
                for order, item in enumerate(node):
                    child = walk(item)
                    members.append({"role": "item", "order": order, "ref": child})
                ref, op = self.universe.compound_op("json_array", members)
                ops.append(op)
                return ref
            kind = "json_null" if node is None else f"json_{type(node).__name__}"
            ref, op = self.universe.atom_op(kind, node)
            ops.append(op)
            return ref

        root = walk(value)
        self.universe.commit(ops, metadata={"action": "ingest_semantic_json"}, capability=self.capability)
        if self.reconstruct(root) != value:
            raise IntegrityError("Semantic JSON reconstruction mismatch")
        return root

    def reconstruct(self, ref: str) -> Any:
        atom = self.universe.atoms.get(ref)
        if atom is not None:
            if atom.kind.startswith("json_"):
                return atom.value
            raise IntegrityError(f"Unexpected semantic atom kind {atom.kind}")
        compound = self.universe.compounds.get(ref)
        if compound is None:
            raise KeyError(ref)
        ordered = sorted(compound.members, key=lambda x: int(x.get("order", 0)))
        if compound.kind == "json_object":
            return {str(m["role"]): self.reconstruct(str(m["ref"])) for m in ordered}
        if compound.kind == "json_array":
            return [self.reconstruct(str(m["ref"])) for m in ordered]
        raise IntegrityError(f"Unsupported semantic compound {compound.kind}")
