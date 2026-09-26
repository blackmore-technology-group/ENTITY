from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes


@dataclass(frozen=True)
class SecurityDomain:
    domain_id: str
    classification: str
    permitted_jurisdictions: tuple[str, ...]
    permitted_authorities: tuple[str, ...]
    deduplication_policy: str = "DOMAIN_ONLY"
    retention_policy: str = "RETAIN"

    @property
    def policy_id(self) -> str:
        return digest("ADAM50:SECURITY_DOMAIN", self.__dict__)


@dataclass(frozen=True)
class PurposeCapability:
    subject: str
    purposes: tuple[str, ...]
    scopes: tuple[str, ...]
    predicates: tuple[str, ...]
    expires_at: int
    issuer: str
    nonce: str
    signature: bytes = b""

    def unsigned(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "purposes": list(self.purposes),
            "scopes": list(self.scopes),
            "predicates": list(self.predicates),
            "expires_at": self.expires_at,
            "issuer": self.issuer,
            "nonce": self.nonce,
        }

    @property
    def capability_id(self) -> str:
        return digest("ADAM50:PURPOSE_CAPABILITY", {**self.unsigned(), "signature": self.signature})


class CapabilityAuthority:
    def __init__(self, issuer: str, private_key: Ed25519PrivateKey | None = None) -> None:
        self.issuer = issuer
        self._private = private_key or Ed25519PrivateKey.generate()
        self.public_key = self._private.public_key()

    def issue(self, *, subject: str, purposes: Iterable[str], scopes: Iterable[str], predicates: Iterable[str], expires_at: int) -> PurposeCapability:
        cap = PurposeCapability(
            subject=subject,
            purposes=tuple(sorted(set(purposes))),
            scopes=tuple(sorted(set(scopes))),
            predicates=tuple(sorted(set(predicates))),
            expires_at=expires_at,
            issuer=self.issuer,
            nonce=os.urandom(16).hex(),
        )
        signature = self._private.sign(canonical_json_bytes(cap.unsigned()))
        return PurposeCapability(**{**cap.__dict__, "signature": signature})

    @staticmethod
    def verify(capability: PurposeCapability, public_key: Ed25519PublicKey, *, now: int, purpose: str, scope: str,
               predicate: str | None = None, subject: str | None = None) -> bool:
        try:
            public_key.verify(capability.signature, canonical_json_bytes(capability.unsigned()))
        except InvalidSignature:
            return False
        if capability.expires_at <= now:
            return False
        if purpose not in capability.purposes or scope not in capability.scopes:
            return False
        if predicate is not None and predicate not in capability.predicates and "*" not in capability.predicates:
            return False
        if subject is not None and capability.subject != subject:
            return False
        return True


@dataclass(frozen=True)
class EncryptedAtom:
    atom_id: str
    domain_id: str
    nonce: bytes
    ciphertext: bytes
    plaintext_hash: str
    key_version: int
    jurisdiction: str
    metadata: Mapping[str, Any]


class DomainKeyVault:
    """Development reference for envelope-key custody and cryptographic erasure."""

    def __init__(self) -> None:
        self._keys: dict[tuple[str, int], bytearray] = {}
        self._active_version: dict[str, int] = {}
        self.erased_domains: set[str] = set()

    def create_domain_key(self, domain_id: str) -> int:
        version = self._active_version.get(domain_id, 0) + 1
        self._keys[(domain_id, version)] = bytearray(AESGCM.generate_key(bit_length=256))
        self._active_version[domain_id] = version
        self.erased_domains.discard(domain_id)
        return version

    def has_active(self, domain_id: str) -> bool:
        return domain_id in self._active_version and domain_id not in self.erased_domains

    def active(self, domain_id: str) -> tuple[int, bytes]:
        if domain_id in self.erased_domains:
            raise KeyError("domain key was cryptographically erased")
        version = self._active_version[domain_id]
        return version, self.key_for_version(domain_id, version)

    def key_for_version(self, domain_id: str, version: int) -> bytes:
        if domain_id in self.erased_domains:
            raise KeyError("domain key was cryptographically erased")
        return bytes(self._keys[(domain_id, version)])

    def rotate(self, domain_id: str) -> int:
        return self.create_domain_key(domain_id)

    def destroy_domain(self, domain_id: str) -> None:
        for key_id, key in list(self._keys.items()):
            if key_id[0] != domain_id:
                continue
            for i in range(len(key)):
                key[i] = 0
            del self._keys[key_id]
        self._active_version.pop(domain_id, None)
        self.erased_domains.add(domain_id)


class SovereignAtomStore:
    def __init__(self, vault: DomainKeyVault | None = None) -> None:
        self.vault = vault or DomainKeyVault()
        self.domains: dict[str, SecurityDomain] = {}
        self.atoms: dict[str, EncryptedAtom] = {}
        self.placements: dict[str, tuple[str, ...]] = {}

    def register_domain(self, domain: SecurityDomain) -> str:
        if not domain.domain_id or not domain.permitted_jurisdictions or not domain.permitted_authorities:
            raise ValueError("security domain id, jurisdictions and authorities are required")
        if domain.deduplication_policy not in {"GLOBAL_PUBLIC", "DOMAIN_ONLY", "NO_DEDUPE"}:
            raise ValueError("unsupported deduplication policy")
        previous = self.domains.get(domain.domain_id)
        if previous is not None and previous != domain:
            raise ValueError(f"security domain {domain.domain_id} is already registered")
        self.domains[domain.domain_id] = domain
        if not self.vault.has_active(domain.domain_id):
            self.vault.create_domain_key(domain.domain_id)
        return domain.policy_id

    def put(self, plaintext: bytes, *, domain_id: str, jurisdiction: str, authority: str,
            metadata: Mapping[str, Any] | None = None) -> str:
        domain = self.domains[domain_id]
        if jurisdiction not in domain.permitted_jurisdictions:
            raise PermissionError("jurisdiction is not permitted")
        if authority not in domain.permitted_authorities:
            raise PermissionError("authority is not permitted")
        version, key = self.vault.active(domain_id)
        nonce = os.urandom(12)
        metadata = dict(metadata or {})
        plaintext_hash = sha256_bytes(plaintext)
        identity_material = {
            "hash": plaintext_hash,
            "domain": domain_id,
            "jurisdiction": jurisdiction,
            "metadata": metadata,
            "policy_id": domain.policy_id,
        }
        if domain.deduplication_policy == "NO_DEDUPE":
            identity_material["nonce"] = nonce.hex()
        atom_id = digest("ADAM50:ENCRYPTED_ATOM", identity_material)
        aad = canonical_json_bytes({
            "atom_id": atom_id,
            "domain_id": domain_id,
            "key_version": version,
            "jurisdiction": jurisdiction,
            "metadata": metadata,
            "policy_id": domain.policy_id,
        })
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
        self.atoms[atom_id] = EncryptedAtom(atom_id, domain_id, nonce, ciphertext, plaintext_hash, version, jurisdiction, metadata)
        self.placements[atom_id] = (jurisdiction,)
        return atom_id

    def get(self, atom_id: str, *, authority: str, jurisdiction: str) -> bytes:
        atom = self.atoms[atom_id]
        domain = self.domains[atom.domain_id]
        if authority not in domain.permitted_authorities:
            raise PermissionError("authority is not permitted")
        if jurisdiction not in domain.permitted_jurisdictions:
            raise PermissionError("cross-jurisdiction hydration denied")
        if jurisdiction not in self.placements.get(atom_id, ()):
            raise PermissionError("atom is not placed in the requested jurisdiction")
        key = self.vault.key_for_version(atom.domain_id, atom.key_version)
        aad = canonical_json_bytes({
            "atom_id": atom.atom_id,
            "domain_id": atom.domain_id,
            "key_version": atom.key_version,
            "jurisdiction": atom.jurisdiction,
            "metadata": dict(atom.metadata),
            "policy_id": domain.policy_id,
        })
        plaintext = AESGCM(key).decrypt(atom.nonce, atom.ciphertext, aad)
        if sha256_bytes(plaintext) != atom.plaintext_hash:
            raise ValueError("plaintext integrity failure")
        return plaintext

    def erase_domain(self, domain_id: str, *, authority: str) -> None:
        domain = self.domains[domain_id]
        if authority not in domain.permitted_authorities:
            raise PermissionError("authority is not permitted")
        self.vault.destroy_domain(domain_id)


@dataclass(frozen=True)
class ClosureNode:
    node_id: str
    security_scope: str
    predicate: str | None = None
    dependencies: tuple[str, ...] = ()
    inferable_scopes: tuple[str, ...] = ()


class InferenceClosureAuthorizer:
    """Authorizes the full dependency and inference closure, not only requested roots."""

    def __init__(self) -> None:
        self.nodes: dict[str, ClosureNode] = {}

    def add(self, node: ClosureNode) -> None:
        self.nodes[node.node_id] = node

    def closure(self, roots: Iterable[str]) -> set[str]:
        stack = list(roots)
        seen: set[str] = set()
        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            if node_id not in self.nodes:
                raise KeyError(f"unknown closure node {node_id}")
            seen.add(node_id)
            stack.extend(self.nodes[node_id].dependencies)
        return seen

    def authorize(self, roots: Iterable[str], capability: PurposeCapability, public_key: Ed25519PublicKey,
                  *, now: int, purpose: str, subject: str) -> set[str]:
        closure = self.closure(roots)
        for node_id in closure:
            node = self.nodes[node_id]
            if not CapabilityAuthority.verify(
                capability,
                public_key,
                now=now,
                purpose=purpose,
                scope=node.security_scope,
                predicate=node.predicate,
                subject=subject,
            ):
                raise PermissionError(f"closure authorization denied at {node_id}")
            for inferred_scope in node.inferable_scopes:
                if inferred_scope not in capability.scopes:
                    raise PermissionError(f"inference could reveal unauthorized scope {inferred_scope}")
        return closure


@dataclass(frozen=True)
class WitnessStatement:
    witness_id: str
    sequence: int
    universe_root: str
    previous_statement: str | None
    signature: bytes

    @property
    def statement_id(self) -> str:
        return digest("ADAM50:WITNESS_STATEMENT", {
            "witness_id": self.witness_id,
            "sequence": self.sequence,
            "universe_root": self.universe_root,
            "previous_statement": self.previous_statement,
            "signature": self.signature,
        })


class WitnessNode:
    def __init__(self, witness_id: str) -> None:
        self.witness_id = witness_id
        self._private = Ed25519PrivateKey.generate()
        self.public_key = self._private.public_key()
        self.statements: list[WitnessStatement] = []

    def witness(self, universe_root: str) -> WitnessStatement:
        sequence = len(self.statements) + 1
        previous = self.statements[-1].statement_id if self.statements else None
        payload = {"witness_id": self.witness_id, "sequence": sequence, "universe_root": universe_root, "previous_statement": previous}
        statement = WitnessStatement(self.witness_id, sequence, universe_root, previous, self._private.sign(canonical_json_bytes(payload)))
        self.statements.append(statement)
        return statement

    def verify_statement(self, statement: WitnessStatement) -> bool:
        if statement.witness_id != self.witness_id:
            return False
        payload = {
            "witness_id": statement.witness_id,
            "sequence": statement.sequence,
            "universe_root": statement.universe_root,
            "previous_statement": statement.previous_statement,
        }
        try:
            self.public_key.verify(statement.signature, canonical_json_bytes(payload))
        except (InvalidSignature, ValueError):
            return False
        return any(existing.statement_id == statement.statement_id for existing in self.statements)

    def verify_chain(self) -> bool:
        previous = None
        for expected_sequence, statement in enumerate(self.statements, 1):
            if statement.sequence != expected_sequence or statement.previous_statement != previous:
                return False
            payload = {"witness_id": statement.witness_id, "sequence": statement.sequence, "universe_root": statement.universe_root, "previous_statement": statement.previous_statement}
            try:
                self.public_key.verify(statement.signature, canonical_json_bytes(payload))
            except InvalidSignature:
                return False
            previous = statement.statement_id
        return True


class WitnessQuorum:
    def __init__(self, witnesses: Iterable[WitnessNode], threshold: int) -> None:
        self.witnesses = list(witnesses)
        self.threshold = threshold
        if threshold < 1 or threshold > len(self.witnesses):
            raise ValueError("invalid witness threshold")

    def certify(self, universe_root: str) -> tuple[WitnessStatement, ...]:
        statements = tuple(w.witness(universe_root) for w in self.witnesses)
        if len(statements) < self.threshold:
            raise RuntimeError("witness threshold not met")
        return statements

    def verify(self, root: str, statements: Iterable[WitnessStatement]) -> bool:
        valid = 0
        seen: set[str] = set()
        by_id = {w.witness_id: w for w in self.witnesses}
        for statement in statements:
            witness = by_id.get(statement.witness_id)
            if witness is None or statement.witness_id in seen or statement.universe_root != root:
                continue
            if witness.verify_chain() and witness.verify_statement(statement):
                seen.add(statement.witness_id)
                valid += 1
        return valid >= self.threshold
