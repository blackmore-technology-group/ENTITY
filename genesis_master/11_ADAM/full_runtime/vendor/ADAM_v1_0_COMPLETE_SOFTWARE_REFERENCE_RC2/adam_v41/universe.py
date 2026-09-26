from __future__ import annotations

import copy
import json
import threading
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .authority import Authority
from .canonical import digest, pack
from .log import EventLog, LogIntegrityError


class IntegrityError(RuntimeError):
    pass


class ConflictError(RuntimeError):
    pass


class AuthorityError(RuntimeError):
    pass


@dataclass(frozen=True)
class Atom:
    atom_id: str
    kind: str
    value: Any
    metadata: dict[str, Any]
    created_seq: int


@dataclass(frozen=True)
class Bond:
    bond_id: str
    source: str
    predicate: str
    target: str
    order: int | None
    context: str | None
    valid_from: int | None
    valid_until: int | None
    metadata: dict[str, Any]
    created_seq: int
    revoked_seq: int | None = None


@dataclass(frozen=True)
class Compound:
    compound_id: str
    kind: str
    members: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_seq: int


class AtomicUniverse:
    """Event-sourced atomic universe with exact and semantic structures."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.authority = Authority(self.root / "authority")
        self._lock = threading.RLock()
        self._commit_guard_token: object | None = None
        self._reset_state()
        self.checkpoint_sequence = 0
        self.checkpoint_root = "00" * 32
        if (self.root / "checkpoint.a41").exists():
            self._load_checkpoint(self.root / "checkpoint.a41")
        self.log = EventLog(
            self.root / "universe.a41log",
            self.authority,
            base_seq=self.checkpoint_sequence,
            base_root=self.checkpoint_root,
        )
        try:
            self.log.recover(self._apply_core)
        except LogIntegrityError as exc:
            raise IntegrityError(str(exc)) from exc
        self._write_manifest()

    def _reset_state(self) -> None:
        self.atoms: dict[str, Atom] = {}
        self.bonds: dict[str, Bond] = {}
        self.compounds: dict[str, Compound] = {}
        self.entity_versions: dict[str, int] = {}
        self.compound_aliases: dict[str, str] = {}

    def enable_commit_guard(self) -> object:
        """Require an unforgeable in-process capability for future commits.

        This is an API containment mechanism, not a process or hardware security
        boundary. Production authority must isolate the kernel in a separate
        service/process and protect keys in HSM/KMS.
        """
        with self._lock:
            if self._commit_guard_token is None:
                self._commit_guard_token = object()
            return self._commit_guard_token

    @property
    def commit_guard_enabled(self) -> bool:
        return self._commit_guard_token is not None

    @property
    def sequence(self) -> int:
        return self.log.seq

    @property
    def root_hash(self) -> str:
        return self.log.root_hash

    def _write_manifest(self) -> None:
        manifest = {
            "format": "ADAM-v0.41-construction-native-universe",
            "sequence": self.sequence,
            "root_hash": self.root_hash,
            "authority_id": self.authority.authority_id,
            "atoms": len(self.atoms),
            "bonds": len(self.bonds),
            "compounds": len(self.compounds),
            "recovered_torn_bytes": self.log.recovered_torn_bytes,
            "checkpoint_sequence": self.checkpoint_sequence,
            "checkpoint_root": self.checkpoint_root,
        }
        (self.root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def atom_id(kind: str, value: Any, metadata: dict[str, Any] | None = None) -> str:
        return digest("ADAM41:ATOM", {"kind": kind, "value": value, "metadata": metadata or {}})

    @staticmethod
    def compound_id(kind: str, members: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> str:
        return digest("ADAM41:COMPOUND", {"kind": kind, "members": members, "metadata": metadata or {}})

    @staticmethod
    def bond_id(body: dict[str, Any]) -> str:
        return digest("ADAM41:BOND", body)

    def atom_op(self, kind: str, value: Any, metadata: dict[str, Any] | None = None) -> tuple[str, dict[str, Any] | None]:
        metadata = metadata or {}
        atom_id = self.atom_id(kind, value, metadata)
        if atom_id in self.atoms:
            return atom_id, None
        return atom_id, {"op": "put_atom", "atom_id": atom_id, "kind": kind, "value": value, "metadata": metadata}

    def compound_op(
        self, kind: str, members: list[dict[str, Any]], metadata: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any] | None]:
        metadata = metadata or {}
        normalized = copy.deepcopy(members)
        compound_id = self.compound_id(kind, normalized, metadata)
        if compound_id in self.compounds:
            return compound_id, None
        return compound_id, {
            "op": "put_compound",
            "compound_id": compound_id,
            "kind": kind,
            "members": normalized,
            "metadata": metadata,
        }

    def bond_op(
        self,
        source: str,
        predicate: str,
        target: str,
        *,
        order: int | None = None,
        context: str | None = None,
        valid_from: int | None = None,
        valid_until: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        body = {
            "source": source,
            "predicate": predicate,
            "target": target,
            "order": order,
            "context": context,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "metadata": metadata or {},
        }
        bond_id = self.bond_id(body)
        existing = self.bonds.get(bond_id)
        if existing and existing.revoked_seq is None:
            return bond_id, None
        return bond_id, {"op": "put_bond", "bond_id": bond_id, **body}

    def commit(
        self,
        ops: Iterable[dict[str, Any] | None],
        *,
        expected_versions: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
        capability: object | None = None,
    ) -> int:
        if self._commit_guard_token is not None and capability is not self._commit_guard_token:
            raise AuthorityError("Authoritative commit requires the active kernel capability")
        clean_ops = [copy.deepcopy(op) for op in ops if op is not None]
        if not clean_ops:
            return self.sequence
        with self._lock:
            for entity, expected in (expected_versions or {}).items():
                actual = self.entity_versions.get(entity, 0)
                if actual != expected:
                    raise ConflictError(f"MVCC conflict for {entity}: expected {expected}, actual {actual}")
            core = self.log.append(clean_ops, metadata)
            self._apply_core(core)
            self._write_manifest()
            return self.sequence

    def _apply_core(self, core: dict[str, Any]) -> None:
        seq = int(core["seq"])
        for op in core.get("ops", []):
            kind = op.get("op")
            if kind == "put_atom":
                expected = self.atom_id(str(op["kind"]), op["value"], dict(op.get("metadata", {})))
                if expected != op["atom_id"]:
                    raise IntegrityError("Atom identity mismatch")
                self.atoms.setdefault(
                    expected,
                    Atom(expected, str(op["kind"]), op["value"], dict(op.get("metadata", {})), seq),
                )
            elif kind == "put_compound":
                expected = self.compound_id(str(op["kind"]), list(op["members"]), dict(op.get("metadata", {})))
                if expected != op["compound_id"]:
                    raise IntegrityError("Compound identity mismatch")
                self.compounds.setdefault(
                    expected,
                    Compound(expected, str(op["kind"]), list(op["members"]), dict(op.get("metadata", {})), seq),
                )
            elif kind == "put_bond":
                body = {k: op.get(k) for k in ("source", "predicate", "target", "order", "context", "valid_from", "valid_until", "metadata")}
                body["metadata"] = dict(body.get("metadata") or {})
                expected = self.bond_id(body)
                if expected != op["bond_id"]:
                    raise IntegrityError("Bond identity mismatch")
                self.bonds[expected] = Bond(expected, created_seq=seq, revoked_seq=None, **body)
            elif kind == "revoke_bond":
                bond_id = str(op["bond_id"])
                current = self.bonds.get(bond_id)
                if current is None:
                    raise IntegrityError(f"Cannot revoke missing bond {bond_id}")
                if current.revoked_seq is None:
                    self.bonds[bond_id] = Bond(**{**current.__dict__, "revoked_seq": seq})
            elif kind == "bump_entity_version":
                entity = str(op["entity"])
                expected_previous = int(op["previous"])
                if self.entity_versions.get(entity, 0) != expected_previous:
                    raise IntegrityError(f"Entity version discontinuity for {entity}")
                self.entity_versions[entity] = expected_previous + 1
            elif kind == "alias_compound":
                self.compound_aliases[str(op["name"])] = str(op["compound_id"])
            else:
                raise IntegrityError(f"Unknown operation {kind!r}")

    def get_value(self, ref_id: str) -> Any:
        if ref_id in self.atoms:
            return self.atoms[ref_id].value
        if ref_id in self.compounds:
            return self.compounds[ref_id]
        raise KeyError(ref_id)

    def active_bonds(
        self,
        *,
        source: str | None = None,
        predicate: str | None = None,
        target: str | None = None,
        at_seq: int | None = None,
    ) -> list[Bond]:
        seq = self.sequence if at_seq is None else int(at_seq)
        result = []
        for bond in self.bonds.values():
            if bond.created_seq > seq or (bond.revoked_seq is not None and bond.revoked_seq <= seq):
                continue
            if source is not None and bond.source != source:
                continue
            if predicate is not None and bond.predicate != predicate:
                continue
            if target is not None and bond.target != target:
                continue
            result.append(bond)
        return sorted(result, key=lambda b: (b.predicate, b.order if b.order is not None else -1, b.bond_id))

    def assert_entity(
        self,
        entity_type: str,
        entity_key: str,
        facts: dict[str, Any],
        *,
        expected_version: int | None = None,
        context: str = "CURRENT",
        capability: object | None = None,
    ) -> tuple[str, int]:
        entity_id, entity_atom = self.atom_op("entity", {"type": entity_type, "key": str(entity_key)})
        version = self.entity_versions.get(entity_id, 0)
        if expected_version is not None and expected_version != version:
            raise ConflictError(f"MVCC conflict for {entity_id}: expected {expected_version}, actual {version}")
        ops: list[dict[str, Any] | None] = [entity_atom]
        for predicate, value in sorted(facts.items()):
            target_id, target_op = self.atom_op("value", value, {"predicate": predicate})
            current_bonds = [
                b for b in self.active_bonds(source=entity_id, predicate=predicate) if b.context == context
            ]
            # Unchanged facts retain their existing bond; changed facts are atomically rebonded.
            if any(b.target == target_id for b in current_bonds):
                continue
            ops.append(target_op)
            for current in current_bonds:
                ops.append({"op": "revoke_bond", "bond_id": current.bond_id})
            body = {
                "source": entity_id,
                "predicate": predicate,
                "target": target_id,
                "order": None,
                "context": context,
                "valid_from": None,
                "valid_until": None,
                "metadata": {"entity_type": entity_type},
            }
            bond_id = self.bond_id(body)
            ops.append({"op": "put_bond", "bond_id": bond_id, **body})
        ops.append({"op": "bump_entity_version", "entity": entity_id, "previous": version})
        self.commit(
            ops,
            expected_versions={entity_id: version},
            metadata={"action": "assert_entity", "entity_type": entity_type},
            capability=capability,
        )
        return entity_id, version + 1

    def assert_entities_batch(
        self,
        entity_type: str,
        records: list[tuple[str, dict[str, Any]]],
        *,
        context: str = "CURRENT",
        capability: object | None = None,
    ) -> list[str]:
        """Atomically ingest a batch of new entities with shared atom deduplication."""
        if not records:
            return []
        ops: list[dict[str, Any]] = []
        local_atoms: set[str] = set(self.atoms)
        local_bonds: set[str] = set()
        expected_versions: dict[str, int] = {}
        entity_ids: list[str] = []
        seen_entities: set[str] = set()

        def add_atom(kind: str, value: Any, metadata: dict[str, Any] | None = None) -> str:
            meta = metadata or {}
            atom_id = self.atom_id(kind, value, meta)
            if atom_id not in local_atoms:
                ops.append({"op": "put_atom", "atom_id": atom_id, "kind": kind, "value": value, "metadata": meta})
                local_atoms.add(atom_id)
            return atom_id

        for entity_key, facts in records:
            entity_id = add_atom("entity", {"type": entity_type, "key": str(entity_key)})
            if entity_id in seen_entities:
                raise ValueError(f"Duplicate entity in batch: {entity_key}")
            seen_entities.add(entity_id)
            entity_ids.append(entity_id)
            version = self.entity_versions.get(entity_id, 0)
            if version != 0 or self.active_bonds(source=entity_id):
                raise ConflictError("Batch path currently accepts only new entities")
            expected_versions[entity_id] = version
            for predicate, value in sorted(facts.items()):
                target_id = add_atom("value", value, {"predicate": predicate})
                body = {
                    "source": entity_id,
                    "predicate": predicate,
                    "target": target_id,
                    "order": None,
                    "context": context,
                    "valid_from": None,
                    "valid_until": None,
                    "metadata": {"entity_type": entity_type},
                }
                bond_id = self.bond_id(body)
                if bond_id not in local_bonds and bond_id not in self.bonds:
                    ops.append({"op": "put_bond", "bond_id": bond_id, **body})
                    local_bonds.add(bond_id)
            ops.append({"op": "bump_entity_version", "entity": entity_id, "previous": version})
        self.commit(
            ops,
            expected_versions=expected_versions,
            metadata={"action": "assert_entities_batch", "entity_type": entity_type, "count": len(records)},
            capability=capability,
        )
        return entity_ids

    def entity_view(self, entity_id: str, *, at_seq: int | None = None) -> dict[str, Any]:
        atom = self.atoms.get(entity_id)
        if atom is None or atom.kind != "entity":
            raise KeyError(entity_id)
        out = {"_id": entity_id, "_type": atom.value["type"], "_key": atom.value["key"]}
        for bond in self.active_bonds(source=entity_id, at_seq=at_seq):
            out[bond.predicate] = self.get_value(bond.target)
        return out

    def verify(self) -> dict[str, Any]:
        dangling = []
        for bond in self.bonds.values():
            if bond.source not in self.atoms and bond.source not in self.compounds:
                dangling.append((bond.bond_id, "source"))
            if bond.target not in self.atoms and bond.target not in self.compounds:
                dangling.append((bond.bond_id, "target"))
        bad_compounds = []
        for comp in self.compounds.values():
            for member in comp.members:
                ref = member.get("ref")
                if ref not in self.atoms and ref not in self.compounds:
                    bad_compounds.append((comp.compound_id, ref))
        return {
            "pass": not dangling and not bad_compounds,
            "sequence": self.sequence,
            "root_hash": self.root_hash,
            "atoms": len(self.atoms),
            "bonds": len(self.bonds),
            "compounds": len(self.compounds),
            "dangling": dangling,
            "bad_compounds": bad_compounds,
            "journal_bytes": (self.root / "universe.a41log").stat().st_size,
            "recovered_torn_bytes": self.log.recovered_torn_bytes,
            "checkpoint_sequence": self.checkpoint_sequence,
            "checkpoint_root": self.checkpoint_root,
        }

    def native_packed_state_bytes(self, *, compress: bool = True) -> bytes:
        """Alias-packed physical projection containing all atoms, bonds and compounds.

        Full hashes are retained once in the reference dictionary; bonds use compact
        integer aliases. This is the v0.40 analogue of a native periodic table.
        """
        refs = sorted(set(self.atoms) | set(self.compounds))
        alias = {ref: i for i, ref in enumerate(refs)}
        kinds = sorted({a.kind for a in self.atoms.values()} | {c.kind for c in self.compounds.values()})
        kind_alias = {value: i for i, value in enumerate(kinds)}
        predicates = sorted({b.predicate for b in self.bonds.values()})
        pred_alias = {value: i for i, value in enumerate(predicates)}
        contexts = sorted({b.context for b in self.bonds.values() if b.context is not None})
        context_alias = {value: i for i, value in enumerate(contexts)}
        roles = sorted({str(m.get("role", "")) for c in self.compounds.values() for m in c.members})
        role_alias = {value: i for i, value in enumerate(roles)}
        state = {
            "format": "ADAM-v0.41-native-alias-packed-state",
            "root": self.root_hash,
            "refs": refs,
            "kinds": kinds,
            "predicates": predicates,
            "contexts": contexts,
            "roles": roles,
            "atoms": [
                [alias[a.atom_id], kind_alias[a.kind], a.value, a.metadata, a.created_seq]
                for a in sorted(self.atoms.values(), key=lambda x: x.atom_id)
            ],
            "bonds": [
                [
                    alias[b.source], pred_alias[b.predicate], alias[b.target], b.order,
                    None if b.context is None else context_alias[b.context],
                    b.valid_from, b.valid_until, b.metadata, b.created_seq, b.revoked_seq,
                ]
                for b in sorted(self.bonds.values(), key=lambda x: x.bond_id)
            ],
            "compounds": [
                [
                    alias[c.compound_id], kind_alias[c.kind],
                    [
                        [role_alias[str(m.get("role", ""))], m.get("order"), alias[str(m["ref"])], m.get("length")]
                        for m in c.members
                    ],
                    c.metadata, c.created_seq,
                ]
                for c in sorted(self.compounds.values(), key=lambda x: x.compound_id)
            ],
            "entity_versions": [[alias[k], v] for k, v in sorted(self.entity_versions.items())],
        }
        raw = pack(state)
        return zlib.compress(raw, level=9) if compress else raw

    def native_factored_state_bytes(self, *, compress: bool = True) -> bytes:
        """Compound-factor active entity bonds into schema rows.

        This is the construction-native physical form: a repeated bond topology is
        stored once as a schema compound and each entity stores only ordered targets.
        """
        refs = sorted(set(self.atoms) | set(self.compounds))
        alias = {ref: i for i, ref in enumerate(refs)}
        kinds = sorted({a.kind for a in self.atoms.values()} | {c.kind for c in self.compounds.values()})
        kind_alias = {value: i for i, value in enumerate(kinds)}
        predicates = sorted({b.predicate for b in self.bonds.values()})
        pred_alias = {value: i for i, value in enumerate(predicates)}
        contexts = sorted({b.context for b in self.bonds.values() if b.context is not None})
        context_alias = {value: i for i, value in enumerate(contexts)}
        roles = sorted({str(m.get("role", "")) for c in self.compounds.values() for m in c.members})
        role_alias = {value: i for i, value in enumerate(roles)}

        schemas: list[list[Any]] = []
        schema_index: dict[tuple[Any, ...], int] = {}
        rows: list[list[Any]] = []
        factored_ids: set[str] = set()
        for atom_id, atom in sorted(self.atoms.items()):
            if atom.kind != "entity":
                continue
            active = [b for b in self.active_bonds(source=atom_id) if b.context == "CURRENT"]
            if not active:
                continue
            active.sort(key=lambda b: b.predicate)
            entity_type = str(atom.value.get("type"))
            key = (entity_type, "CURRENT", tuple(b.predicate for b in active))
            idx = schema_index.get(key)
            if idx is None:
                idx = len(schemas)
                schema_index[key] = idx
                schemas.append([entity_type, context_alias["CURRENT"], [pred_alias[b.predicate] for b in active]])
            rows.append([alias[atom_id], idx, [[alias[b.target], b.created_seq] for b in active]])
            factored_ids.update(b.bond_id for b in active)

        residual = []
        for b in sorted(self.bonds.values(), key=lambda x: x.bond_id):
            if b.bond_id in factored_ids:
                continue
            residual.append([
                alias[b.source], pred_alias[b.predicate], alias[b.target], b.order,
                None if b.context is None else context_alias[b.context],
                b.valid_from, b.valid_until, b.metadata, b.created_seq, b.revoked_seq,
            ])
        state = {
            "format": "ADAM-v0.41-native-factored-state",
            "sequence": self.sequence,
            "root": self.root_hash,
            "refs": refs,
            "kinds": kinds,
            "predicates": predicates,
            "contexts": contexts,
            "roles": roles,
            "atoms": [
                [alias[a.atom_id], kind_alias[a.kind], a.value, a.metadata, a.created_seq]
                for a in sorted(self.atoms.values(), key=lambda x: x.atom_id)
            ],
            "schemas": schemas,
            "entity_rows": rows,
            "residual_bonds": residual,
            "compounds": [
                [
                    alias[c.compound_id], kind_alias[c.kind],
                    [[role_alias[str(m.get("role", ""))], m.get("order"), alias[str(m["ref"])], m.get("length")] for m in c.members],
                    c.metadata, c.created_seq,
                ]
                for c in sorted(self.compounds.values(), key=lambda x: x.compound_id)
            ],
            "entity_versions": [[alias[k], v] for k, v in sorted(self.entity_versions.items())],
            "compound_aliases": dict(sorted(self.compound_aliases.items())),
        }
        raw = pack(state)
        return zlib.compress(raw, level=9) if compress else raw

    def _load_checkpoint(self, path: Path) -> None:
        from .authority import Authority
        from .canonical import sha256_bytes, unpack
        receipt_path = path.with_suffix(path.suffix + ".receipt.json")
        if not receipt_path.exists():
            raise IntegrityError("Checkpoint receipt missing")
        payload = path.read_bytes()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        digest_hex = sha256_bytes(payload)
        if digest_hex != receipt.get("payload_sha256"):
            raise IntegrityError("Checkpoint digest mismatch")
        if receipt.get("authority_id") != self.authority.authority_id:
            raise AuthorityError("Checkpoint authority mismatch")
        if not Authority.verify(self.authority.public_key_hex, bytes.fromhex(digest_hex), str(receipt.get("signature"))):
            raise AuthorityError("Checkpoint signature invalid")
        try:
            state = unpack(zlib.decompress(payload))
        except Exception as exc:
            raise IntegrityError("Checkpoint decode failed") from exc
        if state.get("format") != "ADAM-v0.41-native-factored-state":
            raise IntegrityError("Unsupported checkpoint format")
        refs = list(state["refs"]); kinds = list(state["kinds"]); predicates = list(state["predicates"]); contexts = list(state["contexts"]); roles = list(state["roles"])
        self._reset_state()
        for row in state["atoms"]:
            ref = refs[int(row[0])]; kind = kinds[int(row[1])]; value = row[2]; metadata = dict(row[3]); created_seq = int(row[4])
            if self.atom_id(kind, value, metadata) != ref:
                raise IntegrityError("Checkpoint atom identity mismatch")
            self.atoms[ref] = Atom(ref, kind, value, metadata, created_seq)
        for row in state["compounds"]:
            ref = refs[int(row[0])]; kind = kinds[int(row[1])]; metadata = dict(row[3]); created_seq = int(row[4])
            members = []
            for m in row[2]:
                member = {"role": roles[int(m[0])], "order": m[1], "ref": refs[int(m[2])]}
                if m[3] is not None:
                    member["length"] = m[3]
                members.append(member)
            if self.compound_id(kind, members, metadata) != ref:
                raise IntegrityError("Checkpoint compound identity mismatch")
            self.compounds[ref] = Compound(ref, kind, members, metadata, created_seq)
        for row in state.get("residual_bonds", []):
            body = {
                "source": refs[int(row[0])], "predicate": predicates[int(row[1])], "target": refs[int(row[2])],
                "order": row[3], "context": None if row[4] is None else contexts[int(row[4])],
                "valid_from": row[5], "valid_until": row[6], "metadata": dict(row[7]),
            }
            bond_id = self.bond_id(body)
            self.bonds[bond_id] = Bond(bond_id, created_seq=int(row[8]), revoked_seq=None if row[9] is None else int(row[9]), **body)
        for row in state.get("entity_rows", []):
            source = refs[int(row[0])]; schema = state["schemas"][int(row[1])]; entity_type = str(schema[0]); context = contexts[int(schema[1])]; pred_ids = list(schema[2])
            if len(pred_ids) != len(row[2]):
                raise IntegrityError("Checkpoint factored row width mismatch")
            for pred_idx, target_info in zip(pred_ids, row[2]):
                body = {
                    "source": source, "predicate": predicates[int(pred_idx)], "target": refs[int(target_info[0])],
                    "order": None, "context": context, "valid_from": None, "valid_until": None,
                    "metadata": {"entity_type": entity_type},
                }
                bond_id = self.bond_id(body)
                self.bonds[bond_id] = Bond(bond_id, created_seq=int(target_info[1]), revoked_seq=None, **body)
        self.entity_versions = {refs[int(k)]: int(v) for k, v in state.get("entity_versions", [])}
        self.compound_aliases = dict(state.get("compound_aliases", {}))
        self.checkpoint_sequence = int(receipt["sequence"])
        self.checkpoint_root = str(receipt["root_hash"])
        if self.checkpoint_sequence != int(state.get("sequence")) or self.checkpoint_root != str(state.get("root")):
            raise IntegrityError("Checkpoint receipt/state mismatch")

    def compact_authority(self) -> dict[str, Any]:
        """Create a signed factored checkpoint and start a new delta log."""
        with self._lock:
            checkpoint = self.root / "checkpoint.a41"
            tmp = self.root / "checkpoint.a41.tmp"
            receipt = self.write_native_checkpoint(tmp)
            tmp_receipt = tmp.with_suffix(tmp.suffix + ".receipt.json")
            final_receipt = checkpoint.with_suffix(checkpoint.suffix + ".receipt.json")
            tmp.replace(checkpoint)
            tmp_receipt.replace(final_receipt)
            log_path = self.root / "universe.a41log"
            log_path.write_bytes(b"")
            self.checkpoint_sequence = self.sequence
            self.checkpoint_root = self.root_hash
            self.log = EventLog(log_path, self.authority, base_seq=self.checkpoint_sequence, base_root=self.checkpoint_root)
            self._write_manifest()
            return receipt

    def write_native_checkpoint(self, path: Path | str) -> dict[str, Any]:
        from .canonical import sha256_bytes
        path = Path(path)
        payload = self.native_factored_state_bytes(compress=True)
        path.write_bytes(payload)
        digest_hex = sha256_bytes(payload)
        signature = self.authority.sign(bytes.fromhex(digest_hex))
        receipt = {
            "format": "ADAM-v0.41-native-checkpoint-receipt",
            "sequence": self.sequence,
            "root_hash": self.root_hash,
            "payload_sha256": digest_hex,
            "authority_id": self.authority.authority_id,
            "signature": signature,
        }
        path.with_suffix(path.suffix + ".receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
        )
        return receipt

    def compact_state_bytes(self) -> bytes:
        state = {
            "atoms": {k: {"kind": v.kind, "value": v.value, "metadata": v.metadata} for k, v in sorted(self.atoms.items())},
            "bonds": {
                k: {
                    "source": v.source,
                    "predicate": v.predicate,
                    "target": v.target,
                    "order": v.order,
                    "context": v.context,
                    "valid_from": v.valid_from,
                    "valid_until": v.valid_until,
                    "metadata": v.metadata,
                    "created_seq": v.created_seq,
                    "revoked_seq": v.revoked_seq,
                }
                for k, v in sorted(self.bonds.items())
            },
            "compounds": {k: {"kind": v.kind, "members": v.members, "metadata": v.metadata} for k, v in sorted(self.compounds.items())},
            "entity_versions": dict(sorted(self.entity_versions.items())),
            "root_hash": self.root_hash,
        }
        return pack(state)
