from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adam_v41.canonical import digest
from adam_v41.exact import ExactCodec, ExactObject
from adam_v41.universe import AtomicUniverse


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class AlignedClaim:
    claim_id: str
    evidence_object_id: str
    proof_id: str
    confidence: float
    sequence: int


class EvidenceAlignmentEngine:
    """Mandatory exact-to-semantic linkage for authoritative semantic claims."""

    def __init__(self, universe: AtomicUniverse, *, capability: object | None = None):
        self.universe = universe
        self.capability = capability
        self.exact = ExactCodec(universe, capability=capability)

    def ingest_evidence(self, payload: bytes, *, media_type: str, name: str | None = None) -> ExactObject:
        return self.exact.ingest(payload, media_type=media_type, name=name)

    def assert_claim(
        self,
        claim_type: str,
        value: Any,
        *,
        evidence_object_id: str,
        extractor: str,
        confidence: float,
        offsets: dict[str, Any] | None = None,
        authoritative: bool = True,
    ) -> AlignedClaim:
        if evidence_object_id not in self.universe.compounds:
            raise EvidenceError("Semantic claim lacks an existing exact-evidence object")
        if not (0.0 <= confidence <= 1.0):
            raise EvidenceError("confidence must be between 0 and 1")
        if authoritative and confidence < 0.5:
            raise EvidenceError("Low-confidence claim cannot be authoritative")
        claim_body = {
            "claim_type": claim_type,
            "value": value,
            "authoritative": authoritative,
        }
        claim_id, claim_op = self.universe.atom_op("semantic_claim", claim_body, {"claim_type": claim_type})
        proof_body = {
            "claim_id": claim_id,
            "evidence_object_id": evidence_object_id,
            "extractor": extractor,
            "confidence": round(float(confidence), 12),
            "offsets": offsets or {},
        }
        proof_id, proof_op = self.universe.atom_op("evidence_alignment_proof", proof_body)
        b1_id, b1 = self.universe.bond_op(
            claim_id, "EVIDENCED_BY", evidence_object_id, context="AUTHORITY",
            metadata={"proof_id": proof_id, "mandatory": True},
        )
        _, b2 = self.universe.bond_op(
            claim_id, "HAS_ALIGNMENT_PROOF", proof_id, context="AUTHORITY",
            metadata={"confidence": confidence},
        )
        self.universe.commit(
            [claim_op, proof_op, b1, b2],
            metadata={"action": "ASSERT_ALIGNED_SEMANTIC_CLAIM", "claim_type": claim_type},
            capability=self.capability,
        )
        if not any(b.predicate == "EVIDENCED_BY" for b in self.universe.active_bonds(source=claim_id)):
            raise EvidenceError("Alignment commit failed")
        return AlignedClaim(claim_id, evidence_object_id, proof_id, confidence, self.universe.sequence)

    def verify_claim(self, claim_id: str) -> dict[str, Any]:
        claim = self.universe.atoms.get(claim_id)
        if claim is None or claim.kind != "semantic_claim":
            raise EvidenceError("Unknown semantic claim")
        evidence = [b.target for b in self.universe.active_bonds(source=claim_id, predicate="EVIDENCED_BY")]
        proofs = [b.target for b in self.universe.active_bonds(source=claim_id, predicate="HAS_ALIGNMENT_PROOF")]
        if len(evidence) != 1 or len(proofs) != 1:
            raise EvidenceError("Claim does not have exactly one mandatory evidence/proof pair")
        proof = self.universe.atoms.get(proofs[0])
        if proof is None or proof.kind != "evidence_alignment_proof":
            raise EvidenceError("Alignment proof missing")
        if proof.value["claim_id"] != claim_id or proof.value["evidence_object_id"] != evidence[0]:
            raise EvidenceError("Alignment proof mismatch")
        return {
            "pass": True,
            "claim_id": claim_id,
            "evidence_object_id": evidence[0],
            "proof_id": proofs[0],
            "verification_digest": digest("ADAM42:EVIDENCE_VERIFY", [claim_id, evidence[0], proofs[0]]),
        }
