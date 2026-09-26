from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import pack
from .universe import AtomicUniverse, IntegrityError


@dataclass(frozen=True)
class ChemistryProposal:
    name: str
    fields: tuple[str, ...]
    support: int
    estimated_raw_bytes: int
    estimated_compound_bytes: int
    estimated_gain_bytes: int
    accepted: bool
    reason: str


class AtomicBrain:
    """Deterministic learning prototype for schema/compound discovery.

    This is deliberately not a neural model. It proves the learn-test-commit loop
    before introducing probabilistic cognition.
    """

    def __init__(self, universe: AtomicUniverse, *, capability: object | None = None):
        self.universe = universe
        self.capability = capability

    def ingest_records(self, records: Iterable[dict[str, Any]], *, entity_type: str, id_field: str) -> list[str]:
        rows = [dict(record) for record in records]
        batch = []
        for record in rows:
            if id_field not in record:
                raise ValueError(f"Missing id field {id_field}")
            facts = {k: v for k, v in record.items() if k != id_field}
            batch.append((str(record[id_field]), facts))
        return self.universe.assert_entities_batch(entity_type, batch, capability=self.capability)

    def discover_compounds(
        self,
        records: Iterable[dict[str, Any]],
        *,
        name_prefix: str = "LEARNED",
        min_support: int = 3,
    ) -> list[ChemistryProposal]:
        rows = [dict(r) for r in records]
        patterns = Counter(tuple(sorted(r.keys())) for r in rows)
        proposals: list[ChemistryProposal] = []
        for index, (fields, support) in enumerate(patterns.most_common(), 1):
            matching = [r for r in rows if tuple(sorted(r.keys())) == fields]
            raw_bytes = sum(len(pack(r)) for r in matching)
            recipe = [{"role": field, "order": i, "ref": self.universe.atom_id("predicate", field)} for i, field in enumerate(fields)]
            estimate = len(pack({"fields": fields})) + support * max(1, len(fields)) * 4
            gain = raw_bytes - estimate
            name = f"{name_prefix}_{index}_{'_'.join(fields)}"
            accepted = support >= min_support and gain > 0
            reason = "accepted: repeated structure reduces estimated representation cost" if accepted else "rejected: insufficient support or no estimated gain"
            if accepted:
                ops = []
                for field in fields:
                    _, op = self.universe.atom_op("predicate", field)
                    ops.append(op)
                compound_id, compound_op = self.universe.compound_op(
                    "learned_schema",
                    recipe,
                    {"name": name, "support": support, "fields": list(fields), "estimated_gain_bytes": gain},
                )
                ops.append(compound_op)
                ops.append({"op": "alias_compound", "name": name, "compound_id": compound_id})
                self.universe.commit(
                    ops, metadata={"action": "promote_compound", "name": name}, capability=self.capability
                )
                # Deterministic validation: every matching record must be expressible by exactly these fields.
                for row in matching:
                    if tuple(sorted(row.keys())) != fields:
                        raise IntegrityError("Learned compound validation failed")
            proposals.append(ChemistryProposal(name, fields, support, raw_bytes, estimate, gain, accepted, reason))
        return proposals
