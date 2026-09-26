from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .canonical import digest
from .schema import TypeRegistry, TypeSpec
from .universe import AtomicUniverse, ConflictError


class ReactionError(RuntimeError):
    """A proposed world transition failed deterministic governance."""

    def __init__(self, message: str, *, violations: list[str] | None = None):
        super().__init__(message)
        self.violations = violations or [message]


@dataclass(frozen=True)
class Condition:
    role: str
    predicate: str
    operator: str
    expected: Any = None
    other_role: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "predicate": self.predicate,
            "operator": self.operator,
            "expected": self.expected,
            "other_role": self.other_role,
        }


@dataclass(frozen=True)
class Effect:
    role: str
    predicate: str
    action: str
    value: Any = None
    value_role: str | None = None
    value_arg: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "predicate": self.predicate,
            "action": self.action,
            "value": self.value,
            "value_role": self.value_role,
            "value_arg": self.value_arg,
        }


@dataclass(frozen=True)
class ReactionDefinition:
    name: str
    version: int
    roles: dict[str, str]
    actor_role: str
    required_grants: tuple[str, ...]
    conditions: tuple[Condition, ...]
    effects: tuple[Effect, ...]
    reversible: bool = False
    description: str = ""
    conservation_laws: tuple[str, ...] = (
        "IDENTITY",
        "HISTORY",
        "PROVENANCE",
        "AUTHORITY",
        "STATE_VALIDITY",
        "SIMULATION_ISOLATION",
    )

    @property
    def definition_id(self) -> str:
        return digest("ADAM41:REACTION_DEFINITION", self.canonical())

    def canonical(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "roles": dict(sorted(self.roles.items())),
            "actor_role": self.actor_role,
            "required_grants": list(self.required_grants),
            "conditions": [c.canonical() for c in self.conditions],
            "effects": [e.canonical() for e in self.effects],
            "reversible": self.reversible,
            "description": self.description,
            "conservation_laws": list(self.conservation_laws),
        }


@dataclass(frozen=True)
class ReactionIntent:
    reaction: str
    bindings: dict[str, str]
    args: dict[str, Any] = field(default_factory=dict)
    nonce: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {
            "reaction": self.reaction,
            "bindings": dict(sorted(self.bindings.items())),
            "args": self.args,
            "nonce": self.nonce,
        }


@dataclass(frozen=True)
class ReactionReceipt:
    reaction: str
    definition_id: str
    proof_id: str
    committed: bool
    sequence_before: int
    sequence_after: int
    root_before: str
    root_after: str
    projected_views: dict[str, dict[str, Any]]
    checks: tuple[str, ...]


class ReactionEngine:
    """Proof-carrying transition engine layered over the v0.40 atomic substrate.

    Learned cognition may call simulate/apply, but only this deterministic engine
    decides whether a proposal can enter the authoritative universe.
    """

    def __init__(
        self,
        universe: AtomicUniverse,
        registry: TypeRegistry | None = None,
        *,
        capability: object | None = None,
    ):
        self.universe = universe
        self.registry = registry or TypeRegistry()
        self._capability = capability
        self.definitions: dict[str, ReactionDefinition] = {}

    def register_type(self, spec: TypeSpec) -> str:
        return self.registry.persist(self.universe, spec, capability=self._capability)

    def register_reaction(self, definition: ReactionDefinition) -> str:
        current = self.definitions.get(definition.name)
        if current is not None and current.version >= definition.version and current != definition:
            raise ValueError(f"Reaction {definition.name!r} already has version {current.version}")
        self.definitions[definition.name] = definition
        atom_id, op = self.universe.atom_op(
            "reaction_definition",
            definition.canonical(),
            {"definition_id": definition.definition_id, "name": definition.name, "version": definition.version},
        )
        self.universe.commit(
            [op],
            metadata={"action": "register_reaction", "reaction": definition.name, "version": definition.version},
            capability=self._capability,
        )
        return atom_id

    def genesis_entity(self, entity_type: str, key: str, facts: dict[str, Any]) -> tuple[str, int]:
        """Create initial authoritative state only after pre-commit valence validation."""
        entity_id, entity_op = self.universe.atom_op("entity", {"type": entity_type, "key": str(key)})
        if entity_id in self.universe.atoms or self.universe.entity_versions.get(entity_id, 0) != 0:
            raise ReactionError(f"Entity {entity_type}:{key} already exists")
        ops: list[dict[str, Any] | None] = [entity_op]
        state: dict[str, list[str]] = {}
        pending_atoms: dict[str, tuple[str, Any]] = {entity_id: ("entity", {"type": entity_type, "key": str(key)})}
        for predicate, value in sorted(facts.items()):
            target_id, target_op = self.universe.atom_op("value", value, {"predicate": predicate})
            ops.append(target_op)
            pending_atoms[target_id] = ("value", value)
            body = {
                "source": entity_id,
                "predicate": predicate,
                "target": target_id,
                "order": None,
                "context": "CURRENT",
                "valid_from": None,
                "valid_until": None,
                "metadata": {"entity_type": entity_type, "reaction": "GENESIS"},
            }
            ops.append({"op": "put_bond", "bond_id": self.universe.bond_id(body), **body})
            state[predicate] = [target_id]
        violations = self.registry.validate_state(
            self.universe, entity_type, state, pending_atoms=pending_atoms
        )
        if violations:
            raise ReactionError("Genesis state violates valence", violations=violations)
        ops.append({"op": "bump_entity_version", "entity": entity_id, "previous": 0})
        self.universe.commit(
            ops,
            expected_versions={entity_id: 0},
            metadata={"action": "GENESIS", "entity_type": entity_type},
            capability=self._capability,
        )
        return entity_id, 1

    def _entity_type(self, entity_id: str) -> str:
        atom = self.universe.atoms.get(entity_id)
        if atom is None or atom.kind != "entity":
            raise ReactionError(f"Binding {entity_id!r} is not an entity atom")
        return str(atom.value.get("type"))

    def _state_refs(self, entity_id: str, *, at_seq: int | None = None) -> dict[str, list[str]]:
        state: dict[str, list[str]] = {}
        for bond in self.universe.active_bonds(source=entity_id, at_seq=at_seq):
            state.setdefault(bond.predicate, []).append(bond.target)
        return state

    def _values(self, state: dict[str, list[str]], predicate: str) -> list[Any]:
        values = []
        for target in state.get(predicate, []):
            values.append(self.universe.get_value(target))
        return values

    def _check_condition(
        self,
        condition: Condition,
        states: dict[str, dict[str, list[str]]],
        bindings: dict[str, str],
    ) -> bool:
        state = states[condition.role]
        targets = state.get(condition.predicate, [])
        values = self._values(state, condition.predicate)
        if condition.operator == "exists":
            return bool(targets)
        if condition.operator == "absent":
            return not targets
        if condition.operator == "equals":
            return any(value == condition.expected for value in values)
        if condition.operator == "not_equals":
            return all(value != condition.expected for value in values)
        if condition.operator == "truthy":
            return any(bool(value) for value in values)
        if condition.operator == "target_is_role":
            if condition.other_role is None:
                raise ReactionError("target_is_role condition lacks other_role")
            return bindings[condition.other_role] in targets
        raise ReactionError(f"Unsupported condition operator {condition.operator!r}")

    def _effect_target(self, effect: Effect, intent: ReactionIntent, ops: list[dict[str, Any] | None]) -> str:
        if effect.action == "set_role_ref":
            if effect.value_role is None:
                raise ReactionError("set_role_ref effect lacks value_role")
            return intent.bindings[effect.value_role]
        if effect.action == "set_arg":
            if effect.value_arg is None or effect.value_arg not in intent.args:
                raise ReactionError(f"Missing required reaction argument {effect.value_arg!r}")
            value = intent.args[effect.value_arg]
        else:
            value = effect.value
        target_id, atom_op = self.universe.atom_op("value", value, {"predicate": effect.predicate})
        ops.append(atom_op)
        return target_id

    def _project_and_plan(self, intent: ReactionIntent) -> tuple[ReactionDefinition, dict[str, dict[str, list[str]]], list[dict[str, Any] | None], list[str]]:
        try:
            definition = self.definitions[intent.reaction]
        except KeyError as exc:
            raise ReactionError(f"Unknown reaction {intent.reaction!r}") from exc

        violations: list[str] = []
        for role, required_type in definition.roles.items():
            entity_id = intent.bindings.get(role)
            if entity_id is None:
                violations.append(f"Missing binding for role {role!r}")
                continue
            try:
                actual_type = self._entity_type(entity_id)
            except ReactionError as exc:
                violations.extend(exc.violations)
                continue
            if actual_type != required_type:
                violations.append(f"Role {role!r} requires {required_type!r}, received {actual_type!r}")
        if violations:
            raise ReactionError("Reaction binding validation failed", violations=violations)

        states = {role: self._state_refs(entity_id) for role, entity_id in intent.bindings.items()}
        actor_state = states[definition.actor_role]
        for grant in definition.required_grants:
            predicate = f"grant::{grant}"
            if not any(bool(v) for v in self._values(actor_state, predicate)):
                violations.append(f"Actor lacks required grant {grant}")

        for condition in definition.conditions:
            if not self._check_condition(condition, states, intent.bindings):
                violations.append(
                    f"Condition failed: {condition.role}.{condition.predicate} {condition.operator} "
                    f"{condition.expected if condition.other_role is None else condition.other_role}"
                )
        if violations:
            raise ReactionError("Reaction preconditions failed", violations=violations)

        projected = copy.deepcopy(states)
        ops: list[dict[str, Any] | None] = []
        changed_roles: set[str] = set()
        for effect in definition.effects:
            entity_id = intent.bindings[effect.role]
            changed_roles.add(effect.role)
            for current in self.universe.active_bonds(source=entity_id, predicate=effect.predicate):
                ops.append({"op": "revoke_bond", "bond_id": current.bond_id})
            projected[effect.role][effect.predicate] = []
            if effect.action == "unset":
                continue
            if effect.action not in {"set_literal", "set_role_ref", "set_arg"}:
                raise ReactionError(f"Unsupported effect action {effect.action!r}")
            target = self._effect_target(effect, intent, ops)
            body = {
                "source": entity_id,
                "predicate": effect.predicate,
                "target": target,
                "order": None,
                "context": "CURRENT",
                "valid_from": None,
                "valid_until": None,
                "metadata": {
                    "reaction": definition.name,
                    "reaction_version": definition.version,
                    "definition_id": definition.definition_id,
                },
            }
            ops.append({"op": "put_bond", "bond_id": self.universe.bond_id(body), **body})
            projected[effect.role][effect.predicate] = [target]

        for role in changed_roles:
            entity_id = intent.bindings[role]
            entity_type = definition.roles[role]
            pending_atoms = {
                str(op["atom_id"]): (str(op["kind"]), op["value"])
                for op in ops
                if op is not None and op.get("op") == "put_atom"
            }
            violations.extend(
                self.registry.validate_state(
                    self.universe, entity_type, projected[role], pending_atoms=pending_atoms
                )
            )
            previous = self.universe.entity_versions.get(entity_id, 0)
            ops.append({"op": "bump_entity_version", "entity": entity_id, "previous": previous})

        if violations:
            raise ReactionError("Reaction violates valence or conservation law", violations=violations)

        checks = [
            "PASS:ROLE_TYPES",
            "PASS:AUTHORITY",
            "PASS:PRECONDITIONS",
            "PASS:IDENTITY_CONSERVATION",
            "PASS:HISTORY_CONSERVATION",
            "PASS:PROVENANCE_CONSERVATION",
            "PASS:STATE_VALIDITY",
            "PASS:SIMULATION_ISOLATION",
        ]
        return definition, projected, ops, checks

    def _projected_views(
        self,
        intent: ReactionIntent,
        projected: dict[str, dict[str, list[str]]],
        ops: list[dict[str, Any] | None],
    ) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        pending_values = {
            str(op["atom_id"]): op["value"]
            for op in ops
            if op is not None and op.get("op") == "put_atom"
        }
        for role, state in projected.items():
            entity_id = intent.bindings[role]
            atom = self.universe.atoms[entity_id]
            view: dict[str, Any] = {"_id": entity_id, "_type": atom.value["type"], "_key": atom.value["key"]}
            for predicate, targets in state.items():
                if not targets:
                    continue
                values = [
                    self.universe.get_value(target) if target in self.universe.atoms or target in self.universe.compounds
                    else pending_values[target]
                    for target in targets
                ]
                view[predicate] = values[0] if len(values) == 1 else values
            out[role] = view
        return out

    def simulate(self, intent: ReactionIntent) -> ReactionReceipt:
        sequence_before = self.universe.sequence
        root_before = self.universe.root_hash
        definition, projected, ops, checks = self._project_and_plan(intent)
        proof_payload = {
            "mode": "SIMULATION",
            "definition_id": definition.definition_id,
            "intent": intent.canonical(),
            "pre_root": root_before,
            "planned_ops_digest": digest("ADAM41:REACTION_OPS", [op for op in ops if op is not None]),
            "checks": checks,
        }
        proof_id = self.universe.atom_id("reaction_proof", proof_payload, {"authoritative": False})
        if self.universe.sequence != sequence_before or self.universe.root_hash != root_before:
            raise ReactionError("Simulation isolation failure")
        return ReactionReceipt(
            reaction=definition.name,
            definition_id=definition.definition_id,
            proof_id=proof_id,
            committed=False,
            sequence_before=sequence_before,
            sequence_after=sequence_before,
            root_before=root_before,
            root_after=root_before,
            projected_views=self._projected_views(intent, projected, ops),
            checks=tuple(checks),
        )

    def apply(self, intent: ReactionIntent) -> ReactionReceipt:
        sequence_before = self.universe.sequence
        root_before = self.universe.root_hash
        definition, projected, ops, checks = self._project_and_plan(intent)
        clean_planned_ops = [op for op in ops if op is not None]
        proof_payload = {
            "mode": "AUTHORITATIVE",
            "definition_id": definition.definition_id,
            "intent": intent.canonical(),
            "pre_root": root_before,
            "planned_ops_digest": digest("ADAM41:REACTION_OPS", clean_planned_ops),
            "checks": checks,
            "law_version": "ADAM41-CONSTITUTION-1",
        }
        proof_id, proof_op = self.universe.atom_op(
            "reaction_proof",
            proof_payload,
            {"authoritative": True, "reaction": definition.name, "definition_id": definition.definition_id},
        )
        members = [{"role": "proof", "order": 0, "ref": proof_id}]
        for order, (role, entity_id) in enumerate(sorted(intent.bindings.items()), 1):
            members.append({"role": role, "order": order, "ref": entity_id})
        instance_id, instance_op = self.universe.compound_op(
            "reaction_instance",
            members,
            {
                "reaction": definition.name,
                "version": definition.version,
                "definition_id": definition.definition_id,
                "proof_id": proof_id,
                "reversible": definition.reversible,
            },
        )
        all_ops = [proof_op, instance_op, *ops]
        expected_versions = {
            intent.bindings[effect.role]: self.universe.entity_versions.get(intent.bindings[effect.role], 0)
            for effect in definition.effects
        }
        try:
            self.universe.commit(
                all_ops,
                expected_versions=expected_versions,
                metadata={
                    "action": "reaction_commit",
                    "reaction": definition.name,
                    "reaction_version": definition.version,
                    "definition_id": definition.definition_id,
                    "reaction_instance_id": instance_id,
                    "proof_id": proof_id,
                    "checks": checks,
                },
                capability=self._capability,
            )
        except ConflictError as exc:
            raise ReactionError("Reaction lost an MVCC race", violations=[str(exc)]) from exc
        return ReactionReceipt(
            reaction=definition.name,
            definition_id=definition.definition_id,
            proof_id=proof_id,
            committed=True,
            sequence_before=sequence_before,
            sequence_after=self.universe.sequence,
            root_before=root_before,
            root_after=self.universe.root_hash,
            projected_views=self._projected_views(intent, projected, ops),
            checks=tuple(checks),
        )
