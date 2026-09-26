from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Iterable, Mapping

from adam_v41.canonical import digest


class BondFamily(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    EVIDENTIARY = "evidentiary"
    COGNITIVE = "cognitive"
    OPERATIONAL = "operational"
    SECURITY = "security"
    PROBABILISTIC = "probabilistic"


class ConfidenceClass(str, Enum):
    AUTHORITATIVE = "authoritative"
    VERIFIED_DERIVATION = "verified_derivation"
    SUPPORTED_HYPOTHESIS = "supported_hypothesis"
    MODEL_INFERENCE = "model_inference"
    SIMULATION_ONLY = "simulation_only"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TimeScope:
    valid_from: int = 0
    valid_until: int | None = None
    observed_at: int | None = None

    def active(self, t: int) -> bool:
        return self.valid_from <= t and (self.valid_until is None or t < self.valid_until)

    def canonical(self) -> dict[str, Any]:
        return {
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True)
class FirstClassBond:
    source: str
    predicate: str
    target: str
    family: BondFamily = BondFamily.SEMANTIC
    direction: str = "forward"
    order: int | None = None
    time: TimeScope = field(default_factory=TimeScope)
    causal_parents: tuple[str, ...] = ()
    authority: str = "UNSPECIFIED"
    provenance: tuple[str, ...] = ()
    confidence: float = 1.0
    confidence_class: ConfidenceClass = ConfidenceClass.AUTHORITATIVE
    security_scope: str = "PUBLIC"
    chemistry_version: str = "v44.1"
    reaction_origin: str | None = None
    supporting_evidence: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source or not self.predicate or not self.target:
            raise ValueError("source, predicate and target are required")
        if self.direction not in {"forward", "reverse", "bidirectional", "ordered"}:
            raise ValueError("unsupported bond direction")
        if not self.authority:
            raise ValueError("bond authority may not be empty")
        if not self.security_scope or not self.chemistry_version:
            raise ValueError("security scope and chemistry version are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if self.time.valid_from < 0 or (self.time.observed_at is not None and self.time.observed_at < 0):
            raise ValueError("bond times must be non-negative")
        if self.time.valid_until is not None and self.time.valid_until <= self.time.valid_from:
            raise ValueError("valid_until must be greater than valid_from")

    def canonical(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "predicate": self.predicate,
            "target": self.target,
            "family": self.family.value,
            "direction": self.direction,
            "order": self.order,
            "time": self.time.canonical(),
            "causal_parents": sorted(self.causal_parents),
            "authority": self.authority,
            "provenance": sorted(self.provenance),
            "confidence": round(float(self.confidence), 12),
            "confidence_class": self.confidence_class.value,
            "security_scope": self.security_scope,
            "chemistry_version": self.chemistry_version,
            "reaction_origin": self.reaction_origin,
            "supporting_evidence": sorted(self.supporting_evidence),
            "metadata": dict(self.metadata),
        }

    @property
    def bond_id(self) -> str:
        return digest("ADAM44:FIRST_CLASS_BOND", self.canonical())

    def terminate(self, at: int, reaction_origin: str) -> "FirstClassBond":
        if at <= self.time.valid_from:
            raise ValueError("termination must follow bond genesis")
        return replace(
            self,
            time=replace(self.time, valid_until=at),
            reaction_origin=reaction_origin,
        )

    def as_atomic_node(self) -> dict[str, Any]:
        return {"kind": "bond_atom", "id": self.bond_id, "bond": self.canonical()}


@dataclass(frozen=True)
class HyperRole:
    role: str
    participant: str
    order: int | None = None
    required: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.role or not self.participant:
            raise ValueError("hyperbond role and participant are required")

    def canonical(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "participant": self.participant,
            "order": self.order,
            "required": self.required,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class HyperBond:
    event_type: str
    roles: tuple[HyperRole, ...]
    authority: str
    time: TimeScope = field(default_factory=TimeScope)
    provenance: tuple[str, ...] = ()
    security_scope: str = "PUBLIC"
    chemistry_version: str = "v44.1"
    causal_parents: tuple[str, ...] = ()
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type is required")
        role_names = [r.role for r in self.roles]
        if len(role_names) != len(set(role_names)):
            raise ValueError("hyperbond role names must be unique")
        if not self.roles:
            raise ValueError("a hyperbond requires at least one role")
        if not self.authority or not self.security_scope or not self.chemistry_version:
            raise ValueError("hyperbond authority, security scope and chemistry version are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("hyperbond confidence must be within [0, 1]")

    def canonical(self) -> dict[str, Any]:
        roles = sorted(self.roles, key=lambda r: (r.order is None, r.order or 0, r.role))
        return {
            "event_type": self.event_type,
            "roles": [r.canonical() for r in roles],
            "authority": self.authority,
            "time": self.time.canonical(),
            "provenance": sorted(self.provenance),
            "security_scope": self.security_scope,
            "chemistry_version": self.chemistry_version,
            "causal_parents": sorted(self.causal_parents),
            "confidence": round(float(self.confidence), 12),
            "metadata": dict(self.metadata),
        }

    @property
    def hyperbond_id(self) -> str:
        return digest("ADAM44:HYPERBOND", self.canonical())

    def as_atomic_node(self) -> dict[str, Any]:
        return {"kind": "hyperbond_atom", "id": self.hyperbond_id, "hyperbond": self.canonical()}


@dataclass(frozen=True)
class ValenceConstraint:
    predicate: str
    source_types: tuple[str, ...] = ()
    target_types: tuple[str, ...] = ()
    minimum: int = 0
    maximum: int | None = None
    families: tuple[BondFamily, ...] = ()
    require_evidence: bool = False
    require_authority: bool = True


class BondAlgebra:
    """Registry and validator for recursive first-class bonds and hyperbonds."""

    def __init__(self) -> None:
        self.bonds: dict[str, FirstClassBond] = {}
        self.hyperbonds: dict[str, HyperBond] = {}
        self.entity_types: dict[str, str] = {}
        self.constraints: dict[str, ValenceConstraint] = {}
        # Immutable bond versions are linked by supersession instead of replacing
        # a content-addressed object under an incompatible digest key.
        self.superseded_by: dict[str, str] = {}

    def declare_entity(self, entity_id: str, entity_type: str) -> None:
        if not entity_id or not entity_type:
            raise ValueError("entity id and type are required")
        previous = self.entity_types.get(entity_id)
        if previous is not None and previous != entity_type:
            raise ValueError(f"entity {entity_id} is already declared as {previous}")
        self.entity_types[entity_id] = entity_type

    def register_constraint(self, constraint: ValenceConstraint) -> None:
        if constraint.minimum < 0 or (constraint.maximum is not None and constraint.maximum < constraint.minimum):
            raise ValueError("invalid valence cardinality")
        previous = self.constraints.get(constraint.predicate)
        if previous is not None and previous != constraint:
            raise ValueError(f"constraint {constraint.predicate} is already registered")
        self.constraints[constraint.predicate] = constraint

    def _node_exists(self, node_id: str) -> bool:
        return node_id in self.entity_types or node_id in self.bonds or node_id in self.hyperbonds

    def _node_type(self, node_id: str) -> str:
        if node_id in self.entity_types:
            return self.entity_types[node_id]
        if node_id in self.bonds:
            return "BOND"
        if node_id in self.hyperbonds:
            return "HYPERBOND"
        return "UNKNOWN"

    def validate_bond(self, bond: FirstClassBond, active_bonds: Iterable[FirstClassBond] | None = None) -> list[str]:
        violations: list[str] = []
        for node_name, node_id in (("source", bond.source), ("target", bond.target)):
            if not self._node_exists(node_id):
                violations.append(f"missing {node_name} node {node_id}")
        constraint = self.constraints.get(bond.predicate)
        if constraint is None:
            return violations
        source_type = self._node_type(bond.source)
        target_type = self._node_type(bond.target)
        if constraint.source_types and source_type not in constraint.source_types:
            violations.append(f"{bond.predicate} source type {source_type} not in {constraint.source_types}")
        if constraint.target_types and target_type not in constraint.target_types:
            violations.append(f"{bond.predicate} target type {target_type} not in {constraint.target_types}")
        if constraint.families and bond.family not in constraint.families:
            violations.append(f"{bond.predicate} family {bond.family.value} not admitted")
        if constraint.require_evidence and not bond.supporting_evidence:
            violations.append(f"{bond.predicate} requires supporting evidence")
        if constraint.require_authority and bond.authority == "UNSPECIFIED":
            violations.append(f"{bond.predicate} requires authority")
        current = list(active_bonds if active_bonds is not None else self.active_bonds(bond.time.valid_from))
        count = sum(
            1
            for item in current
            if item.source == bond.source
            and item.predicate == bond.predicate
            and item.time.valid_until is None
            and item.bond_id != bond.bond_id
        ) + 1
        if constraint.maximum is not None and count > constraint.maximum:
            violations.append(f"{bond.predicate} maximum {constraint.maximum} exceeded for {bond.source}")
        return violations

    def add_bond(self, bond: FirstClassBond, *, validate: bool = True) -> str:
        if validate:
            violations = self.validate_bond(bond)
            if violations:
                raise ValueError("; ".join(violations))
        existing = self.bonds.get(bond.bond_id)
        if existing is not None and existing != bond:
            raise ValueError("content-address collision for bond")
        self.bonds[bond.bond_id] = bond
        return bond.bond_id

    def supersede_bond(self, original_id: str, successor: FirstClassBond) -> str:
        if original_id not in self.bonds:
            raise KeyError(f"unknown bond {original_id}")
        if original_id in self.superseded_by:
            raise ValueError(f"bond {original_id} is already superseded")
        if successor.time.valid_until is None:
            raise ValueError("a terminal bond version requires valid_until")
        successor_id = self.add_bond(successor, validate=False)
        self.superseded_by[original_id] = successor_id
        return successor_id

    def add_hyperbond(self, hyperbond: HyperBond) -> str:
        missing = [role.participant for role in hyperbond.roles if not self._node_exists(role.participant)]
        if missing:
            raise ValueError(f"missing hyperbond participants: {missing}")
        self.hyperbonds[hyperbond.hyperbond_id] = hyperbond
        return hyperbond.hyperbond_id

    def effective_bond_items(self) -> list[tuple[str, FirstClassBond]]:
        successor_ids = set(self.superseded_by.values())
        result: list[tuple[str, FirstClassBond]] = []
        for bond_id, bond in self.bonds.items():
            if bond_id in successor_ids:
                continue
            successor_id = self.superseded_by.get(bond_id)
            result.append((bond_id, self.bonds[successor_id] if successor_id else bond))
        return result

    def effective_bonds(self) -> list[FirstClassBond]:
        return [bond for _, bond in self.effective_bond_items()]

    def active_bond_items(self, t: int) -> list[tuple[str, FirstClassBond]]:
        return [(lineage_id, bond) for lineage_id, bond in self.effective_bond_items() if bond.time.active(t)]

    def active_bonds(self, t: int) -> list[FirstClassBond]:
        return [bond for _, bond in self.active_bond_items(t)]

    def validate_state(self, t: int) -> list[str]:
        violations: list[str] = []
        for key, bond in self.bonds.items():
            if key != bond.bond_id:
                violations.append(f"bond key/hash mismatch: {key} != {bond.bond_id}")
        for original, successor in self.superseded_by.items():
            if original not in self.bonds or successor not in self.bonds:
                violations.append(f"dangling supersession {original}->{successor}")
            elif self.bonds[successor].time.valid_until is None:
                violations.append(f"supersession successor {successor} is not terminal")
        active = self.active_bonds(t)
        for predicate, constraint in self.constraints.items():
            candidates = [
                entity_id for entity_id, entity_type in self.entity_types.items()
                if not constraint.source_types or entity_type in constraint.source_types
            ]
            for source in candidates:
                count = sum(1 for bond in active if bond.source == source and bond.predicate == predicate)
                if count < constraint.minimum:
                    violations.append(f"{predicate} minimum {constraint.minimum} not met for {source}: {count}")
                if constraint.maximum is not None and count > constraint.maximum:
                    violations.append(f"{predicate} maximum {constraint.maximum} exceeded for {source}: {count}")
        return violations

    def closure(self, roots: Iterable[str]) -> set[str]:
        pending = list(roots)
        seen: set[str] = set()
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            if not self._node_exists(node):
                raise KeyError(f"unknown node {node}")
            seen.add(node)
            if node in self.bonds:
                bond = self.bonds[node]
                pending.extend([bond.source, bond.target, *bond.causal_parents, *bond.supporting_evidence])
            elif node in self.hyperbonds:
                hb = self.hyperbonds[node]
                pending.extend(role.participant for role in hb.roles)
                pending.extend(hb.causal_parents)
        return seen

    def root(self) -> str:
        return digest(
            "ADAM44:BOND_ALGEBRA_ROOT",
            {
                "entities": self.entity_types,
                "bonds": {k: v.canonical() for k, v in sorted(self.bonds.items())},
                "hyperbonds": {k: v.canonical() for k, v in sorted(self.hyperbonds.items())},
                "superseded_by": dict(sorted(self.superseded_by.items())),
                "constraints": {
                    k: {
                        "source_types": list(v.source_types),
                        "target_types": list(v.target_types),
                        "minimum": v.minimum,
                        "maximum": v.maximum,
                        "families": [f.value for f in v.families],
                        "require_evidence": v.require_evidence,
                        "require_authority": v.require_authority,
                    }
                    for k, v in sorted(self.constraints.items())
                },
            },
        )
