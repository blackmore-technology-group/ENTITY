from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from adam_v41.canonical import digest
from .bond_algebra import BondAlgebra, BondFamily, ConfidenceClass, FirstClassBond, HyperBond, HyperRole, TimeScope


@dataclass(frozen=True)
class BondTemplate:
    source: str
    predicate: str
    target: str
    family: BondFamily = BondFamily.SEMANTIC
    security_scope: str = "PUBLIC"
    require_evidence_var: str | None = None

    @staticmethod
    def _resolve(value: str, bindings: Mapping[str, str]) -> str:
        return bindings[value[1:]] if value.startswith("$") else value

    def instantiate(self, bindings: Mapping[str, str], *, authority: str, time: int, reaction_id: str) -> FirstClassBond:
        evidence: tuple[str, ...] = ()
        if self.require_evidence_var:
            evidence = (bindings[self.require_evidence_var],)
        return FirstClassBond(
            source=self._resolve(self.source, bindings),
            predicate=self.predicate,
            target=self._resolve(self.target, bindings),
            family=self.family,
            authority=authority,
            time=TimeScope(valid_from=time, observed_at=time),
            reaction_origin=reaction_id,
            supporting_evidence=evidence,
            security_scope=self.security_scope,
        )


@dataclass(frozen=True)
class HyperBondTemplate:
    event_type: str
    roles: tuple[tuple[str, str], ...]
    security_scope: str = "PUBLIC"

    def instantiate(self, bindings: Mapping[str, str], *, authority: str, time: int, causal_parents: tuple[str, ...]) -> HyperBond:
        return HyperBond(
            event_type=self.event_type,
            roles=tuple(HyperRole(role, bindings[value[1:]] if value.startswith("$") else value) for role, value in self.roles),
            authority=authority,
            time=TimeScope(valid_from=time, observed_at=time),
            causal_parents=causal_parents,
            security_scope=self.security_scope,
        )


@dataclass(frozen=True)
class ConstitutionalLaw:
    name: str
    kind: str
    params: Mapping[str, Any] = field(default_factory=dict)

    def evaluate(self, before: BondAlgebra, after: BondAlgebra, context: Mapping[str, Any]) -> tuple[bool, str]:
        if self.kind == "identity_conservation":
            ok = before.entity_types.items() <= after.entity_types.items()
            return ok, "entity identities must not disappear"
        if self.kind == "history_conservation":
            before_ids = set(before.bonds) | set(before.hyperbonds)
            after_ids = set(after.bonds) | set(after.hyperbonds)
            ok = before_ids <= after_ids
            return ok, "historical bond objects must remain addressable"
        if self.kind == "authority_required":
            ok = bool(context.get("authority")) and context.get("authority") != "UNSPECIFIED"
            return ok, "a committing authority is required"
        if self.kind == "evidence_required_for_predicate":
            predicate = str(self.params["predicate"])
            new_ids = set(after.bonds) - set(before.bonds)
            missing = [bid for bid in new_ids if after.bonds[bid].predicate == predicate and not after.bonds[bid].supporting_evidence]
            return not missing, f"{predicate} requires evidence"
        if self.kind == "root_changed":
            return before.root() != after.root(), "reaction must change state"
        if self.kind == "no_model_self_approval":
            proposer = context.get("proposer")
            approvers = set(context.get("approvers", ()))
            return proposer not in approvers, "model proposer may not approve its own reaction"
        raise ValueError(f"unknown law kind {self.kind}")


@dataclass(frozen=True)
class ReactionDefinition:
    name: str
    required: tuple[BondTemplate, ...] = ()
    forbidden: tuple[BondTemplate, ...] = ()
    break_bonds: tuple[BondTemplate, ...] = ()
    form_bonds: tuple[BondTemplate, ...] = ()
    form_hyperbond: HyperBondTemplate | None = None
    required_capabilities: tuple[str, ...] = ()
    laws: tuple[str, ...] = ()
    version: int = 1

    @property
    def reaction_type_id(self) -> str:
        return digest("ADAM44:REACTION_DEFINITION", self.canonical())

    def canonical(self) -> dict[str, Any]:
        def bt(item: BondTemplate) -> dict[str, Any]:
            return {
                "source": item.source,
                "predicate": item.predicate,
                "target": item.target,
                "family": item.family.value,
                "security_scope": item.security_scope,
                "require_evidence_var": item.require_evidence_var,
            }
        return {
            "name": self.name,
            "required": [bt(x) for x in self.required],
            "forbidden": [bt(x) for x in self.forbidden],
            "break_bonds": [bt(x) for x in self.break_bonds],
            "form_bonds": [bt(x) for x in self.form_bonds],
            "form_hyperbond": None if self.form_hyperbond is None else {
                "event_type": self.form_hyperbond.event_type,
                "roles": list(self.form_hyperbond.roles),
                "security_scope": self.form_hyperbond.security_scope,
            },
            "required_capabilities": list(self.required_capabilities),
            "laws": list(self.laws),
            "version": self.version,
        }


@dataclass(frozen=True)
class ReactionIntent:
    reaction_name: str
    bindings: Mapping[str, str]
    actor: str
    authority: str
    capabilities: tuple[str, ...]
    expected_root: str
    proposer: str = "human"
    approvers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReactionProof:
    reaction_id: str
    reaction_type_id: str
    previous_root: str
    new_root: str
    law_results: tuple[tuple[str, bool, str], ...]
    formed_bonds: tuple[str, ...]
    terminated_bonds: tuple[str, ...]
    hyperbond_id: str | None
    actor: str
    authority: str
    logical_time: int

    @property
    def proof_id(self) -> str:
        return digest("ADAM44:REACTION_PROOF", self.canonical())

    def canonical(self) -> dict[str, Any]:
        return {
            "reaction_id": self.reaction_id,
            "reaction_type_id": self.reaction_type_id,
            "previous_root": self.previous_root,
            "new_root": self.new_root,
            "law_results": [list(item) for item in self.law_results],
            "formed_bonds": list(self.formed_bonds),
            "terminated_bonds": list(self.terminated_bonds),
            "hyperbond_id": self.hyperbond_id,
            "actor": self.actor,
            "authority": self.authority,
            "logical_time": self.logical_time,
        }


@dataclass
class Worldline:
    entity_id: str
    genesis_root: str
    states: list[tuple[int, str, str]] = field(default_factory=list)

    def append(self, logical_time: int, root: str, reaction_id: str) -> None:
        if self.states and logical_time <= self.states[-1][0]:
            raise ValueError("worldline time must increase")
        self.states.append((logical_time, root, reaction_id))


class PhysicsError(RuntimeError):
    pass


class AtomicPhysicsKernel:
    """Deterministic bounded physics kernel. All mutations pass through reactions."""

    def __init__(self, algebra: BondAlgebra | None = None) -> None:
        self.algebra = algebra or BondAlgebra()
        self.reactions: dict[str, ReactionDefinition] = {}
        self.laws: dict[str, ConstitutionalLaw] = {}
        self.logical_time = 0
        self.proofs: dict[str, ReactionProof] = {}
        self.worldlines: dict[str, Worldline] = {}
        self._committing = False

    @property
    def root(self) -> str:
        return digest("ADAM44:PHYSICS_ROOT", {"time": self.logical_time, "algebra": self.algebra.root(), "proofs": sorted(proof.reaction_id for proof in self.proofs.values())})

    def declare_entity(self, entity_id: str, entity_type: str) -> None:
        if self.logical_time != 0 or self.proofs:
            raise PhysicsError("entity genesis after start must occur through a reaction")
        self.algebra.declare_entity(entity_id, entity_type)
        self.worldlines[entity_id] = Worldline(entity_id, self.root)

    def seed_bond(self, bond: FirstClassBond) -> str:
        if self.logical_time != 0 or self.proofs:
            raise PhysicsError("seed bonds are only allowed at genesis")
        return self.algebra.add_bond(bond)

    def register_law(self, law: ConstitutionalLaw) -> None:
        if self.logical_time or self.proofs:
            raise PhysicsError("law registration is frozen after the first commit")
        previous = self.laws.get(law.name)
        if previous is not None and previous != law:
            raise PhysicsError(f"law {law.name} is already registered")
        self.laws[law.name] = law

    def register_reaction(self, definition: ReactionDefinition) -> None:
        if self.logical_time or self.proofs:
            raise PhysicsError("reaction registration is frozen after the first commit")
        previous = self.reactions.get(definition.name)
        if previous is not None and previous != definition:
            raise PhysicsError(f"reaction {definition.name} is already registered")
        self.reactions[definition.name] = definition

    @staticmethod
    def _match(template: BondTemplate, bond: FirstClassBond, bindings: Mapping[str, str]) -> bool:
        def resolve(value: str) -> str:
            return bindings.get(value[1:], "__MISSING__") if value.startswith("$") else value
        return bond.source == resolve(template.source) and bond.predicate == template.predicate and bond.target == resolve(template.target) and bond.time.valid_until is None

    def _copy_algebra(self) -> BondAlgebra:
        clone = BondAlgebra()
        clone.bonds = dict(self.algebra.bonds)
        clone.hyperbonds = dict(self.algebra.hyperbonds)
        clone.entity_types = dict(self.algebra.entity_types)
        clone.constraints = dict(self.algebra.constraints)
        clone.superseded_by = dict(self.algebra.superseded_by)
        return clone

    def simulate(self, intent: ReactionIntent) -> tuple[BondAlgebra, ReactionProof]:
        if intent.expected_root != self.root:
            raise PhysicsError("stale universe root")
        try:
            definition = self.reactions[intent.reaction_name]
        except KeyError as exc:
            raise PhysicsError(f"unknown reaction {intent.reaction_name}") from exc
        missing_caps = set(definition.required_capabilities) - set(intent.capabilities)
        if missing_caps:
            raise PhysicsError(f"missing capabilities: {sorted(missing_caps)}")
        active = [b for b in self.algebra.bonds.values() if b.time.valid_until is None]
        for template in definition.required:
            if not any(self._match(template, bond, intent.bindings) for bond in active):
                raise PhysicsError(f"required bond missing: {template}")
        for template in definition.forbidden:
            if any(self._match(template, bond, intent.bindings) for bond in active):
                raise PhysicsError(f"forbidden bond present: {template}")

        next_time = self.logical_time + 1
        reaction_id = digest("ADAM44:REACTION_INTENT", {
            "definition": definition.reaction_type_id,
            "bindings": dict(intent.bindings),
            "actor": intent.actor,
            "authority": intent.authority,
            "capabilities": sorted(intent.capabilities),
            "proposer": intent.proposer,
            "approvers": sorted(intent.approvers),
            "previous_root": self.root,
            "time": next_time,
        })
        after = self._copy_algebra()
        terminated: list[str] = []
        for template in definition.break_bonds:
            for bond_id, bond in after.active_bond_items(self.logical_time):
                if self._match(template, bond, intent.bindings):
                    terminated_bond = bond.terminate(next_time, reaction_id)
                    # Preserve the original immutable object and link it to a terminal
                    # version. Content-addressed dictionary keys always match payloads.
                    after.supersede_bond(bond_id, terminated_bond)
                    terminated.append(bond_id)
        formed: list[str] = []
        for template in definition.form_bonds:
            bond = template.instantiate(intent.bindings, authority=intent.authority, time=next_time, reaction_id=reaction_id)
            violations = after.validate_bond(bond)
            if violations:
                raise PhysicsError("; ".join(violations))
            after.bonds[bond.bond_id] = bond
            formed.append(bond.bond_id)
        hyperbond_id: str | None = None
        if definition.form_hyperbond:
            hyperbond = definition.form_hyperbond.instantiate(
                intent.bindings,
                authority=intent.authority,
                time=next_time,
                causal_parents=tuple(formed + terminated),
            )
            missing = [r.participant for r in hyperbond.roles if not after._node_exists(r.participant)]
            if missing:
                raise PhysicsError(f"missing hyperbond participants: {missing}")
            after.hyperbonds[hyperbond.hyperbond_id] = hyperbond
            hyperbond_id = hyperbond.hyperbond_id

        state_violations = after.validate_state(next_time)
        if state_violations:
            raise PhysicsError("; ".join(state_violations))

        context = {
            "authority": intent.authority,
            "actor": intent.actor,
            "proposer": intent.proposer,
            "approvers": intent.approvers,
        }
        law_results: list[tuple[str, bool, str]] = []
        for law_name in definition.laws:
            law = self.laws[law_name]
            ok, message = law.evaluate(self.algebra, after, context)
            law_results.append((law_name, ok, message))
            if not ok:
                raise PhysicsError(f"law {law_name} failed: {message}")

        new_root = digest("ADAM44:PHYSICS_ROOT", {
            "time": next_time,
            "algebra": after.root(),
            "proofs": sorted([*(proof.reaction_id for proof in self.proofs.values()), reaction_id]),
        })
        proof = ReactionProof(
            reaction_id=reaction_id,
            reaction_type_id=definition.reaction_type_id,
            previous_root=self.root,
            new_root=new_root,
            law_results=tuple(law_results),
            formed_bonds=tuple(formed),
            terminated_bonds=tuple(terminated),
            hyperbond_id=hyperbond_id,
            actor=intent.actor,
            authority=intent.authority,
            logical_time=next_time,
        )
        return after, proof

    def commit(self, intent: ReactionIntent) -> ReactionProof:
        if self._committing:
            raise PhysicsError("nested commit denied")
        self._committing = True
        try:
            after, proof = self.simulate(intent)
            self.algebra = after
            self.logical_time = proof.logical_time
            self.proofs[proof.proof_id] = proof
            affected: set[str] = set()
            for bond_id in (*proof.formed_bonds, *proof.terminated_bonds):
                bond = self.algebra.bonds[bond_id]
                affected.update([bond.source, bond.target])
            if proof.hyperbond_id:
                affected.update(role.participant for role in self.algebra.hyperbonds[proof.hyperbond_id].roles)
            for entity_id in affected:
                if entity_id in self.worldlines:
                    self.worldlines[entity_id].append(self.logical_time, proof.new_root, proof.reaction_id)
            return proof
        finally:
            self._committing = False

    def state_at(self, logical_time: int) -> list[FirstClassBond]:
        if logical_time < 0 or logical_time > self.logical_time:
            raise ValueError("invalid logical time")
        return self.algebra.active_bonds(logical_time)

    def branch(self) -> "AtomicPhysicsKernel":
        clone = AtomicPhysicsKernel(self._copy_algebra())
        clone.reactions = dict(self.reactions)
        clone.laws = dict(self.laws)
        clone.logical_time = self.logical_time
        clone.proofs = dict(self.proofs)
        clone.worldlines = {k: Worldline(v.entity_id, v.genesis_root, list(v.states)) for k, v in self.worldlines.items()}
        return clone
