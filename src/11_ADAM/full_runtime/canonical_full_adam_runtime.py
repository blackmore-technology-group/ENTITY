from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib, json, os, sys

HERE = Path(__file__).resolve().parent
PIN_PATH = HERE / "ADAM_REFERENCE_PIN.json"


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _load_adam_modules():
    explicit = os.environ.get("ENTITY_ADAM_V1_ROOT")
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(HERE / "vendor" / "ADAM_v1_0_COMPLETE_SOFTWARE_REFERENCE_RC2")
    root = next((p for p in candidates if (p / "adam_v1" / "runtime.py").is_file()), None)
    if root is None:
        raise FileNotFoundError(
            "Full ADAM v1.0 source is required. Set ENTITY_ADAM_V1_ROOT to the verified "
            "ADAM_v1_0_COMPLETE_SOFTWARE_REFERENCE_RC2 source root."
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from adam_v1 import ArtificialLivingUniverseV1Candidate
    from adam_v41.universe import AtomicUniverse
    from adam_v41.reactions import ReactionEngine, ReactionDefinition, ReactionIntent, Effect
    from adam_v41.schema import TypeSpec
    from adam_v42.evidence import EvidenceAlignmentEngine
    return ArtificialLivingUniverseV1Candidate, AtomicUniverse, ReactionEngine, ReactionDefinition, ReactionIntent, Effect, TypeSpec, EvidenceAlignmentEngine


class EntityFullAdamRuntime:
    """ENTITY-authorized bridge into the full ADAM v1.0 software reference.

    ENTITY remains the sovereignty/authorization root. ADAM owns atomic evidence and
    state-transition mechanics. NIKI may consume bounded projections only.
    """

    VERSION = "2.0.0-alpha1"
    ADAM_VERSION = "1.0.0-rc2"
    REACTION = "ENTITY_AUTHORIZED_TRANSITION"

    def __init__(self, state_dir: str | Path, *, authorization_verifier: Callable[[Mapping[str, Any]], bool], enable_network_reference: bool = False) -> None:
        if authorization_verifier is None:
            raise ValueError("ENTITY authorization verifier is required")
        self.state = Path(state_dir)
        self.state.mkdir(parents=True, exist_ok=True)
        self.authorization_verifier = authorization_verifier
        self.reference_pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
        modules = _load_adam_modules()
        ArtificialLivingUniverseV1Candidate, AtomicUniverse, ReactionEngine, ReactionDefinition, ReactionIntent, Effect, TypeSpec, EvidenceAlignmentEngine = modules
        self._ReactionDefinition = ReactionDefinition
        self._ReactionIntent = ReactionIntent
        self._Effect = Effect
        self._TypeSpec = TypeSpec
        self.full = ArtificialLivingUniverseV1Candidate.create(self.state / "full_adam_candidate", enable_network_reference=enable_network_reference)
        self.atomic = AtomicUniverse(self.state / "entity_atomic_universe")
        self._capability = self.atomic.enable_commit_guard()
        self.reactions = ReactionEngine(self.atomic, capability=self._capability)
        self.evidence = EvidenceAlignmentEngine(self.atomic, capability=self._capability)
        self._install_entity_schema()

    def _install_entity_schema(self) -> None:
        spec = self._TypeSpec(name="entity_record", rules=(), allow_unlisted_predicates=True, version=1, metadata={"authority_root": "ENTITY", "state_engine": "ADAM"})
        self.reactions.register_type(spec)
        self.reactions.register_reaction(self._ReactionDefinition(
            name=self.REACTION, version=1, roles={"subject": "entity_record"}, actor_role="subject",
            required_grants=(), conditions=(), reversible=False,
            description="Mirror an ENTITY-authorized state transition into ADAM atomic history.",
            effects=(
                self._Effect("subject", "last_event_id", "set_arg", value_arg="event_id"),
                self._Effect("subject", "last_event_type", "set_arg", value_arg="event_type"),
                self._Effect("subject", "last_event_digest", "set_arg", value_arg="event_digest"),
                self._Effect("subject", "last_authority_digest", "set_arg", value_arg="authority_digest"),
                self._Effect("subject", "last_result_digest", "set_arg", value_arg="result_digest"),
                self._Effect("subject", "last_evidence_object", "set_arg", value_arg="evidence_object_id"),
                self._Effect("subject", "last_claim_id", "set_arg", value_arg="claim_id"),
            ),
        ))

    def _entity_atom_id(self, entity_id: str) -> str:
        return self.atomic.atom_id("entity", {"type": "entity_record", "key": str(entity_id)})

    def register_entity(self, entity_id: str, *, entity_kind: str = "ENTITY") -> dict[str, Any]:
        atom_id = self._entity_atom_id(entity_id)
        if atom_id in self.atomic.atoms:
            return {"entity_id": str(entity_id), "adam_entity_atom_id": atom_id, "existing": True, "version": self.atomic.entity_versions.get(atom_id, 0)}
        atom_id, version = self.reactions.genesis_entity("entity_record", str(entity_id), {"entity_id": str(entity_id), "entity_kind": str(entity_kind), "authority_root": "ENTITY"})
        return {"entity_id": str(entity_id), "adam_entity_atom_id": atom_id, "existing": False, "version": version}

    def record_authorized_transition(self, *, entity_id: str, event_type: str, event: Mapping[str, Any], authorization_receipt: Mapping[str, Any], result: Any = None, entity_kind: str = "ENTITY") -> dict[str, Any]:
        auth = dict(authorization_receipt)
        if not self.authorization_verifier(auth):
            raise PermissionError("ENTITY authorization verification failed; ADAM commit denied")
        entity = self.register_entity(entity_id, entity_kind=entity_kind)
        event_doc = {"schema": "entity-adam-authorized-transition-v1", "entity_id": str(entity_id), "event_type": str(event_type), "event": dict(event), "authorization_receipt": auth, "result": result}
        event_digest = _sha(event_doc); authority_digest = _sha(auth); result_digest = _sha(result); event_id = "adam-event-" + event_digest[:40]
        exact = self.evidence.ingest_evidence(_canon(event_doc), media_type="application/vnd.blackmore.entity-adam-transition+json", name=event_id + ".json")
        claim = self.evidence.assert_claim("ENTITY_AUTHORIZED_TRANSITION", {"entity_id": str(entity_id), "event_id": event_id, "event_type": str(event_type), "event_digest": event_digest}, evidence_object_id=exact.object_id, extractor="ENTITY_FULL_ADAM_BRIDGE_V1", confidence=1.0, authoritative=True)
        receipt = self.reactions.apply(self._ReactionIntent(reaction=self.REACTION, bindings={"subject": entity["adam_entity_atom_id"]}, args={"event_id": event_id, "event_type": str(event_type), "event_digest": event_digest, "authority_digest": authority_digest, "result_digest": result_digest, "evidence_object_id": exact.object_id, "claim_id": claim.claim_id}, nonce=event_id))
        return {"schema": "entity-adam-transition-receipt-v1", "entity_id": str(entity_id), "event_id": event_id, "event_digest": event_digest, "authority_digest": authority_digest, "result_digest": result_digest, "exact_evidence_object_id": exact.object_id, "claim_id": claim.claim_id, "claim_verification": self.evidence.verify_claim(claim.claim_id), "reaction": receipt.reaction, "reaction_proof_id": receipt.proof_id, "sequence_before": receipt.sequence_before, "sequence_after": receipt.sequence_after, "root_before": receipt.root_before, "root_after": receipt.root_after, "checks": list(receipt.checks), "committed": receipt.committed}

    def reconstruct_evidence(self, object_id: str) -> bytes:
        return self.evidence.exact.reconstruct(object_id)

    def project_reasoning_context(self, entity_id: str) -> dict[str, Any]:
        atom_id = self._entity_atom_id(entity_id)
        if atom_id not in self.atomic.atoms:
            return {"schema": "niki-adam-context-v2", "entity_id": str(entity_id), "exists": False, "authority_transferred_to_niki": False}
        view = self.atomic.entity_view(atom_id)
        safe = {k: v for k, v in view.items() if k.startswith("_") or k.startswith("last_") or k in {"entity_id", "entity_kind", "authority_root"}}
        return {"schema": "niki-adam-context-v2", "entity_id": str(entity_id), "exists": True, "atomic_root": self.atomic.root_hash, "atomic_sequence": self.atomic.sequence, "state": safe, "raw_content_included": False, "authority_transferred_to_niki": False}

    def verify(self) -> dict[str, Any]:
        atomic = self.atomic.verify()
        claims = [self.evidence.verify_claim(atom_id) for atom_id, atom in self.atomic.atoms.items() if atom.kind == "semantic_claim" and isinstance(atom.value, dict) and atom.value.get("claim_type") == "ENTITY_AUTHORIZED_TRANSITION"]
        return {"schema": "entity-adam-full-runtime-verification-v1", "pass": bool(atomic.get("pass")) and all(c.get("pass") for c in claims), "atomic_universe": atomic, "aligned_transition_claims": len(claims), "full_candidate": self.full.local_status(), "authority_root": "ENTITY", "executor_state_engine": "ADAM"}

    def close(self) -> None:
        self.full.close()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close()


def niki_project_adam_context_v2(*, runtime: EntityFullAdamRuntime, entity_id: str) -> dict[str, Any]:
    return runtime.project_reasoning_context(entity_id)


def entity_record_adam_transition_v1(*, runtime: EntityFullAdamRuntime, **kwargs: Any) -> dict[str, Any]:
    return runtime.record_authorized_transition(**kwargs)


def entity_verify_adam_state_v1(*, runtime: EntityFullAdamRuntime) -> dict[str, Any]:
    return runtime.verify()
