from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, time, uuid

ORIGINS={"DIRECT_OBSERVATION","ENTITY_ASSERTION","COUNTERPARTY_ATTESTATION","EXTERNAL_AUTHORITATIVE_RECORD","DERIVED_INFERENCE","UNKNOWN"}
VERIFICATION={"UNVERIFIED","SELF_ASSERTED","CORROBORATED","VERIFIED","AUTHORITATIVELY_VERIFIED"}
DISPUTE={"ACTIVE","CHALLENGED","DISPUTED","ADJUDICATED","SUPERSEDED"}


def _now(): return int(time.time()*1000)
def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


@dataclass(frozen=True)
class EvidenceAssertionEnvelope:
    claim_id: str
    claim: object
    claimant: str | None
    evidence_origin: str
    evidence_references: tuple[str,...]
    confidence: float | None
    verification_level: str
    observed_at_ms: int | None
    recorded_at_ms: int
    signatures: tuple[dict,...]
    jurisdiction: str | None
    dispute_state: str
    supersedes: str | None
    schema: str = "entity-evidence-assertion-v1"

    def to_dict(self) -> dict:
        out=asdict(self); out["evidence_references"]=list(self.evidence_references); out["signatures"]=list(self.signatures)
        out["assertion_sha256"]=_hash({k:v for k,v in out.items() if k!="assertion_sha256"})
        return out


class EvidenceAssertionFactory:
    @staticmethod
    def create(claim,*,claimant: str|None,evidence_origin: str,evidence_references=None,
               confidence: float|None=None,verification_level: str="UNVERIFIED",
               observed_at_ms: int|None=None,signatures=None,jurisdiction: str|None=None,
               dispute_state: str="ACTIVE",supersedes: str|None=None) -> dict:
        origin=str(evidence_origin).upper(); level=str(verification_level).upper(); dispute=str(dispute_state).upper()
        if origin not in ORIGINS: raise ValueError("unsupported evidence origin")
        if level not in VERIFICATION: raise ValueError("unsupported verification level")
        if dispute not in DISPUTE: raise ValueError("unsupported dispute state")
        if confidence is not None and not 0.0 <= float(confidence) <= 1.0: raise ValueError("confidence must be 0..1")
        if origin=="UNKNOWN" and level!="UNVERIFIED": raise ValueError("UNKNOWN evidence cannot be represented as verified")
        if origin=="DERIVED_INFERENCE" and level in {"VERIFIED","AUTHORITATIVELY_VERIFIED"}:
            raise ValueError("derived inference requires qualifying external evidence transition before verification")
        env=EvidenceAssertionEnvelope(
            claim_id="claimenv1-"+uuid.uuid4().hex,claim=claim,claimant=claimant,evidence_origin=origin,
            evidence_references=tuple(str(x) for x in (evidence_references or [])),confidence=float(confidence) if confidence is not None else None,
            verification_level=level,observed_at_ms=observed_at_ms,recorded_at_ms=_now(),
            signatures=tuple(dict(x) for x in (signatures or [])),jurisdiction=jurisdiction,
            dispute_state=dispute,supersedes=supersedes)
        return env.to_dict()

    @staticmethod
    def transition(existing: dict,*,verification_level: str,evidence_origin: str,evidence_reference: str,
                   actor: str|None=None,signature: dict|None=None) -> dict:
        if not evidence_reference: raise ValueError("qualifying evidence reference required")
        prior_origin=str(existing.get("evidence_origin") or "UNKNOWN").upper()
        new_origin=str(evidence_origin).upper(); level=str(verification_level).upper()
        if new_origin not in ORIGINS or level not in VERIFICATION: raise ValueError("unsupported evidence transition")
        if level in {"VERIFIED","AUTHORITATIVELY_VERIFIED"} and new_origin not in {"COUNTERPARTY_ATTESTATION","EXTERNAL_AUTHORITATIVE_RECORD","DIRECT_OBSERVATION"}:
            raise ValueError("strong verification requires qualifying observed/attested/authoritative evidence")
        refs=list(existing.get("evidence_references") or []); refs.append(str(evidence_reference))
        out=EvidenceAssertionFactory.create(
            existing.get("claim"),claimant=existing.get("claimant"),evidence_origin=new_origin,
            evidence_references=refs,confidence=existing.get("confidence"),verification_level=level,
            observed_at_ms=existing.get("observed_at_ms"),signatures=[*(existing.get("signatures") or []),*([signature] if signature else [])],
            jurisdiction=existing.get("jurisdiction"),dispute_state=existing.get("dispute_state") or "ACTIVE",
            supersedes=str(existing.get("claim_id") or "") or None)
        out["transition_actor"]=actor; out["prior_evidence_origin"]=prior_origin
        return out

    @staticmethod
    def display_label(envelope: dict) -> str:
        level=str(envelope.get("verification_level") or "UNVERIFIED").upper()
        origin=str(envelope.get("evidence_origin") or "UNKNOWN").upper()
        if origin=="UNKNOWN": return "UNKNOWN"
        if origin=="DERIVED_INFERENCE": return "INFERRED"
        if level=="AUTHORITATIVELY_VERIFIED": return "AUTHORITATIVELY_VERIFIED"
        if level=="VERIFIED": return "VERIFIED"
        if origin=="COUNTERPARTY_ATTESTATION": return "COUNTERPARTY_ATTESTED"
        if origin=="DIRECT_OBSERVATION": return "OBSERVED"
        return "ASSERTED"
