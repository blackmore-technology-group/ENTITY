from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from adam_v41.canonical import digest, pack
from adam_v41.universe import AtomicUniverse

from .recreation import LivingRecreationCenter, RecreationArtifact, RecreationError


@dataclass(frozen=True)
class NoveltyPlan:
    artifact_id: str
    dictionary_root: str
    dictionary_epoch: int
    atoms_total: int
    atoms_missing: tuple[str, ...]
    compounds_total: int
    compounds_missing: tuple[str, ...]
    bonds_total: int
    bonds_missing: tuple[str, ...]
    estimated_novelty_bytes: int
    full_closure_bytes: int
    plan_id: str

    @property
    def novelty_fraction(self) -> float:
        return self.estimated_novelty_bytes / max(1, self.full_closure_bytes)


class NoveltyProtocol:
    """Transfer missing atomic knowledge, not complete datasets.

    Global identities remain content hashes. A dictionary root and epoch scope
    any future local aliases, while this development implementation transfers
    canonical objects by global identity for auditability.
    """

    @staticmethod
    def _closure(universe: AtomicUniverse, artifact_id: str) -> tuple[set[str], set[str], set[str]]:
        atoms: set[str] = set()
        compounds: set[str] = set()
        bonds: set[str] = set()
        pending = [artifact_id]
        seen: set[str] = set()
        while pending:
            ref = pending.pop()
            if ref in seen:
                continue
            seen.add(ref)
            if ref in universe.atoms:
                atoms.add(ref)
            elif ref in universe.compounds:
                compounds.add(ref)
                pending.extend(str(member["ref"]) for member in universe.compounds[ref].members)
            else:
                raise RecreationError(f"closure references missing object {ref}")
            for bond in universe.active_bonds(source=ref):
                bonds.add(bond.bond_id)
                pending.append(bond.target)
        return atoms, compounds, bonds

    @staticmethod
    def _atom_bytes(universe: AtomicUniverse, atom_id: str) -> int:
        atom = universe.atoms[atom_id]
        return len(pack({"kind": atom.kind, "value": atom.value, "metadata": atom.metadata}))

    @staticmethod
    def _compound_bytes(universe: AtomicUniverse, compound_id: str) -> int:
        compound = universe.compounds[compound_id]
        return len(pack({"kind": compound.kind, "members": compound.members, "metadata": compound.metadata}))

    @staticmethod
    def _bond_bytes(universe: AtomicUniverse, bond_id: str) -> int:
        bond = universe.bonds[bond_id]
        return len(pack({
            "source": bond.source, "predicate": bond.predicate, "target": bond.target,
            "order": bond.order, "context": bond.context, "valid_from": bond.valid_from,
            "valid_until": bond.valid_until, "metadata": bond.metadata,
        }))

    def plan(self, source: LivingRecreationCenter, destination: LivingRecreationCenter, artifact_id: str, *, dictionary_epoch: int = 1) -> NoveltyPlan:
        source.artifact(artifact_id)
        atoms, compounds, bonds = self._closure(source.universe, artifact_id)
        missing_atoms = tuple(sorted(atoms - set(destination.universe.atoms)))
        missing_compounds = tuple(sorted(compounds - set(destination.universe.compounds)))
        missing_bonds = tuple(sorted(bonds - set(destination.universe.bonds)))
        full = sum(self._atom_bytes(source.universe, x) for x in atoms)
        full += sum(self._compound_bytes(source.universe, x) for x in compounds)
        full += sum(self._bond_bytes(source.universe, x) for x in bonds)
        novelty = sum(self._atom_bytes(source.universe, x) for x in missing_atoms)
        novelty += sum(self._compound_bytes(source.universe, x) for x in missing_compounds)
        novelty += sum(self._bond_bytes(source.universe, x) for x in missing_bonds)
        dictionary_root = digest("ADAM42:NOVELTY_DICTIONARY", sorted(set(destination.universe.atoms) | set(destination.universe.compounds)))
        core = {
            "artifact_id": artifact_id, "dictionary_root": dictionary_root, "dictionary_epoch": dictionary_epoch,
            "atoms_missing": missing_atoms, "compounds_missing": missing_compounds, "bonds_missing": missing_bonds,
        }
        return NoveltyPlan(
            artifact_id, dictionary_root, dictionary_epoch, len(atoms), missing_atoms,
            len(compounds), missing_compounds, len(bonds), missing_bonds,
            novelty, full, digest("ADAM42:NOVELTY_PLAN", core),
        )

    def apply(self, source: LivingRecreationCenter, destination: LivingRecreationCenter, plan: NoveltyPlan) -> RecreationArtifact:
        atoms, compounds, bonds = self._closure(source.universe, plan.artifact_id)
        if tuple(sorted(atoms - set(destination.universe.atoms))) != plan.atoms_missing:
            raise RecreationError("destination atom state changed since novelty plan")
        if tuple(sorted(compounds - set(destination.universe.compounds))) != plan.compounds_missing:
            raise RecreationError("destination compound state changed since novelty plan")
        ops: list[dict[str, Any]] = []
        for atom_id in plan.atoms_missing:
            atom = source.universe.atoms[atom_id]
            ops.append({"op": "put_atom", "atom_id": atom.atom_id, "kind": atom.kind, "value": atom.value, "metadata": atom.metadata})
        # Compound identity does not depend on insertion order. Sorting gives a
        # deterministic transfer frame; final universe verification checks closure.
        for compound_id in plan.compounds_missing:
            compound = source.universe.compounds[compound_id]
            ops.append({"op": "put_compound", "compound_id": compound.compound_id, "kind": compound.kind, "members": compound.members, "metadata": compound.metadata})
        for bond_id in plan.bonds_missing:
            bond = source.universe.bonds[bond_id]
            ops.append({
                "op": "put_bond", "bond_id": bond.bond_id, "source": bond.source,
                "predicate": bond.predicate, "target": bond.target, "order": bond.order,
                "context": bond.context, "valid_from": bond.valid_from, "valid_until": bond.valid_until,
                "metadata": bond.metadata,
            })
        destination.universe.commit(
            ops,
            metadata={"action": "APPLY_NOVELTY_PLAN", "plan_id": plan.plan_id, "artifact_id": plan.artifact_id},
            capability=destination.capability,
        )
        verification = destination.universe.verify()
        if not verification["pass"]:
            raise RecreationError(f"novelty transfer produced invalid closure: {verification}")
        destination.rebuild_index()
        artifact = destination.artifact(plan.artifact_id)
        if destination.recreate_exact(plan.artifact_id) != source.recreate_exact(plan.artifact_id):
            raise RecreationError("novelty transfer failed exact recreation")
        return artifact

    def sync(self, source: LivingRecreationCenter, destination: LivingRecreationCenter, artifact_id: str, *, dictionary_epoch: int = 1) -> tuple[NoveltyPlan, RecreationArtifact]:
        plan = self.plan(source, destination, artifact_id, dictionary_epoch=dictionary_epoch)
        return plan, self.apply(source, destination, plan)
