from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .universe import AtomicUniverse


@dataclass(frozen=True)
class Match:
    source: str
    predicate: str
    target: str
    value: Any


class AtomicQueryEngine:
    def __init__(self, universe: AtomicUniverse):
        self.universe = universe

    def match(
        self,
        *,
        source: str | None = None,
        predicate: str | None = None,
        target: str | None = None,
        where: Callable[[Any], bool] | None = None,
        at_seq: int | None = None,
    ) -> list[Match]:
        out = []
        for bond in self.universe.active_bonds(source=source, predicate=predicate, target=target, at_seq=at_seq):
            value = self.universe.get_value(bond.target)
            if where is None or where(value):
                out.append(Match(bond.source, bond.predicate, bond.target, value))
        return out

    def entities_where(self, entity_type: str, predicate: str, test: Callable[[Any], bool]) -> list[dict[str, Any]]:
        result = []
        for atom_id, atom in self.universe.atoms.items():
            if atom.kind == "entity" and atom.value.get("type") == entity_type:
                matches = self.match(source=atom_id, predicate=predicate, where=test)
                if matches:
                    result.append(self.universe.entity_view(atom_id))
        return result

    def over_budget(self, entity_type: str = "project") -> list[dict[str, Any]]:
        out = []
        for atom_id, atom in self.universe.atoms.items():
            if atom.kind != "entity" or atom.value.get("type") != entity_type:
                continue
            view = self.universe.entity_view(atom_id)
            if "budget" in view and "cost" in view and float(view["cost"]) > float(view["budget"]):
                out.append(view)
        return out
