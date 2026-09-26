from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import digest
from .universe import AtomicUniverse


@dataclass(frozen=True)
class ValenceRule:
    """A deterministic bonding rule for one predicate on one entity type."""

    predicate: str
    minimum: int = 0
    maximum: int | None = 1
    target_entity_types: tuple[str, ...] = ()
    target_atom_kinds: tuple[str, ...] = ("value",)
    allowed_values: tuple[Any, ...] | None = None
    value_type: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "target_entity_types": list(self.target_entity_types),
            "target_atom_kinds": list(self.target_atom_kinds),
            "allowed_values": None if self.allowed_values is None else list(self.allowed_values),
            "value_type": self.value_type,
        }


@dataclass(frozen=True)
class StateConstraint:
    """A simple deterministic cross-predicate implication."""

    if_predicate: str
    if_value: Any
    require_predicates: tuple[str, ...] = ()
    forbid_predicates: tuple[str, ...] = ()

    def canonical(self) -> dict[str, Any]:
        return {
            "if_predicate": self.if_predicate,
            "if_value": self.if_value,
            "require_predicates": list(self.require_predicates),
            "forbid_predicates": list(self.forbid_predicates),
        }


@dataclass(frozen=True)
class TypeSpec:
    name: str
    rules: tuple[ValenceRule, ...]
    allow_unlisted_predicates: bool = False
    version: int = 1
    constraints: tuple[StateConstraint, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def spec_id(self) -> str:
        return digest("ADAM41:TYPE_SPEC", self.canonical())

    def canonical(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "allow_unlisted_predicates": self.allow_unlisted_predicates,
            "rules": [rule.canonical() for rule in sorted(self.rules, key=lambda r: r.predicate)],
            "constraints": [constraint.canonical() for constraint in self.constraints],
            "metadata": self.metadata,
        }

    def rule_map(self) -> dict[str, ValenceRule]:
        return {rule.predicate: rule for rule in self.rules}


class TypeRegistry:
    """Versioned in-memory registry whose accepted specs can also be persisted as atoms."""

    def __init__(self) -> None:
        self._specs: dict[str, TypeSpec] = {}

    def register(self, spec: TypeSpec) -> None:
        current = self._specs.get(spec.name)
        if current is not None and current.version >= spec.version and current != spec:
            raise ValueError(f"Type {spec.name!r} already has version {current.version}")
        self._specs[spec.name] = spec

    def get(self, name: str) -> TypeSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise KeyError(f"Unregistered entity type {name!r}") from exc

    def persist(
        self, universe: AtomicUniverse, spec: TypeSpec, *, capability: object | None = None
    ) -> str:
        self.register(spec)
        atom_id, op = universe.atom_op(
            "type_spec",
            spec.canonical(),
            {"spec_id": spec.spec_id, "type_name": spec.name, "version": spec.version},
        )
        universe.commit(
            [op],
            metadata={"action": "register_type_spec", "type": spec.name, "version": spec.version},
            capability=capability,
        )
        return atom_id

    @staticmethod
    def _value_type_matches(value: Any, expected: str | None) -> bool:
        if expected is None:
            return True
        actual = type(value).__name__
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return actual == expected

    def validate_state(
        self,
        universe: AtomicUniverse,
        entity_type: str,
        state: dict[str, list[str]],
        pending_atoms: dict[str, tuple[str, Any]] | None = None,
    ) -> list[str]:
        spec = self.get(entity_type)
        rules = spec.rule_map()
        pending_atoms = pending_atoms or {}
        violations: list[str] = []

        if not spec.allow_unlisted_predicates:
            for predicate in state:
                if predicate not in rules:
                    violations.append(f"{entity_type}.{predicate}: predicate is not admitted by type spec")

        for predicate, rule in rules.items():
            targets = list(state.get(predicate, []))
            count = len(targets)
            if count < rule.minimum:
                violations.append(f"{entity_type}.{predicate}: requires at least {rule.minimum}, found {count}")
            if rule.maximum is not None and count > rule.maximum:
                violations.append(f"{entity_type}.{predicate}: permits at most {rule.maximum}, found {count}")
            for target in targets:
                atom = universe.atoms.get(target)
                compound = universe.compounds.get(target)
                pending = pending_atoms.get(target)
                if atom is None and compound is None and pending is None:
                    violations.append(f"{entity_type}.{predicate}: missing target {target}")
                    continue
                atom_kind = atom.kind if atom is not None else (pending[0] if pending is not None else None)
                atom_value = atom.value if atom is not None else (pending[1] if pending is not None else None)
                if atom_kind == "entity":
                    target_type = str(atom_value.get("type"))
                    if rule.target_entity_types and target_type not in rule.target_entity_types:
                        violations.append(
                            f"{entity_type}.{predicate}: target entity type {target_type!r} not in {rule.target_entity_types}"
                        )
                    continue
                kind = atom_kind if atom_kind is not None else f"compound:{compound.kind}"
                if rule.target_atom_kinds and kind not in rule.target_atom_kinds:
                    violations.append(f"{entity_type}.{predicate}: target kind {kind!r} not in {rule.target_atom_kinds}")
                    continue
                value = atom_value if atom_kind is not None else None
                if rule.allowed_values is not None and value not in rule.allowed_values:
                    violations.append(f"{entity_type}.{predicate}: value {value!r} not in {rule.allowed_values}")
                if not self._value_type_matches(value, rule.value_type):
                    violations.append(f"{entity_type}.{predicate}: value {value!r} is not {rule.value_type}")

        for constraint in spec.constraints:
            trigger_values = []
            for target in state.get(constraint.if_predicate, []):
                atom = universe.atoms.get(target)
                if atom is not None:
                    trigger_values.append(atom.value)
                elif target in pending_atoms:
                    trigger_values.append(pending_atoms[target][1])
            if constraint.if_value not in trigger_values:
                continue
            for required in constraint.require_predicates:
                if not state.get(required):
                    violations.append(
                        f"{entity_type}: {constraint.if_predicate}={constraint.if_value!r} requires {required}"
                    )
            for forbidden in constraint.forbid_predicates:
                if state.get(forbidden):
                    violations.append(
                        f"{entity_type}: {constraint.if_predicate}={constraint.if_value!r} forbids {forbidden}"
                    )
        return violations

    def canonical(self) -> dict[str, Any]:
        return {name: spec.canonical() for name, spec in sorted(self._specs.items())}
