from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

from reality_profile import CLAIM_STATES, EVIDENCE_TYPES

def now_ms() -> int:
    return int(time.time() * 1000)

def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def digest(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon(value)
    return hashlib.sha256(raw).hexdigest()

def rid(prefix: str) -> str:
    return prefix + "-" + secrets.token_hex(12)

def sha256_hex(value: str, name: str = "sha256") -> str:
    value = str(value).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value

_ALLOWED_TRANSITIONS = {
    "UNKNOWN": {"OBSERVED", "ASSERTED", "INFERRED", "DISPUTED", "REVOKED"},
    "OBSERVED": {"ATTESTED", "EXTERNALLY_VERIFIED", "DISPUTED", "REVOKED"},
    "ASSERTED": {"ATTESTED", "EXTERNALLY_VERIFIED", "ADJUDICATED", "DISPUTED", "REVOKED"},
    "INFERRED": {"ATTESTED", "EXTERNALLY_VERIFIED", "DISPUTED", "REVOKED"},
    "ATTESTED": {"EXTERNALLY_VERIFIED", "ADJUDICATED", "DISPUTED", "REVOKED"},
    "EXTERNALLY_VERIFIED": {"ADJUDICATED", "DISPUTED", "REVOKED"},
    "ADJUDICATED": {"DISPUTED", "REVOKED"},
    "DISPUTED": {"ATTESTED", "EXTERNALLY_VERIFIED", "ADJUDICATED", "REVOKED"},
    "REVOKED": set(),
}

class EvidenceRegistry:
    """Immutable evidence plus typed claims. Signatures prove attribution, not objective truth."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_3_evidence.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS evidence(
                evidence_id TEXT PRIMARY KEY, source_entity_id TEXT NOT NULL, evidence_type TEXT NOT NULL,
                subject_ref TEXT NOT NULL, content_sha256 TEXT NOT NULL, body_sha256 TEXT NOT NULL,
                body_json TEXT NOT NULL, signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS claims(
                claim_id TEXT PRIMARY KEY, issuer_entity_id TEXT NOT NULL, subject_ref TEXT NOT NULL,
                predicate TEXT NOT NULL, value_sha256 TEXT NOT NULL, state TEXT NOT NULL,
                body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL, signature_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS claim_transitions(
                transition_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, actor_entity_id TEXT NOT NULL,
                from_state TEXT NOT NULL, to_state TEXT NOT NULL, reason TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL, body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
                signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL)""")

    def issue_evidence(self, source_entity_id: str, evidence_type: str, subject_ref: str,
                       content_sha256: str, *, observed_at_ms: int | None = None,
                       provenance_refs: list[str] | None = None,
                       confidentiality: str = "RESTRICTED") -> dict:
        self.identity.load_manifest(source_entity_id)
        evidence_type = str(evidence_type).upper()
        if evidence_type not in EVIDENCE_TYPES:
            raise ValueError("unsupported evidence type")
        body = {
            "schema": "entity-v3-evidence-object-v1",
            "evidence_id": rid("evidence3"),
            "source_entity_id": source_entity_id,
            "evidence_type": evidence_type,
            "subject_ref": str(subject_ref),
            "content_sha256": sha256_hex(content_sha256, "content_sha256"),
            "observed_at_ms": int(observed_at_ms if observed_at_ms is not None else now_ms()),
            "provenance_refs": sorted({str(x) for x in (provenance_refs or [])}),
            "confidentiality": str(confidentiality).upper(),
            "signature_proves_attribution_not_objective_truth": True,
            "immutable_evidence_record": True,
            "created_at_ms": now_ms(),
        }
        body_sha = digest(body)
        sig = self.identity.sign(source_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)", (
                body["evidence_id"], source_entity_id, evidence_type, body["subject_ref"],
                body["content_sha256"], body_sha, json.dumps(body, sort_keys=True),
                json.dumps(sig, sort_keys=True), body["created_at_ms"]))
        return dict(body, body_sha256=body_sha, signature=sig)

    def verify_evidence(self, evidence: dict) -> dict:
        try:
            body = {k: v for k, v in evidence.items() if k not in {"body_sha256", "signature"}}
            if body.get("schema") != "entity-v3-evidence-object-v1":
                raise ValueError("schema")
            if body.get("evidence_type") not in EVIDENCE_TYPES:
                raise ValueError("evidence_type")
            sha256_hex(body.get("content_sha256"), "content_sha256")
            if body.get("signature_proves_attribution_not_objective_truth") is not True:
                raise ValueError("truth boundary")
            if body.get("immutable_evidence_record") is not True:
                raise ValueError("immutability")
            expected = digest(body)
            if evidence.get("body_sha256") != expected:
                raise ValueError("hash")
            manifest = self.identity.load_manifest(body["source_entity_id"])
            if not self.identity.verify_signature(manifest, body, dict(evidence.get("signature") or {})):
                raise ValueError("signature")
            return {"valid": True, "evidence_id": body["evidence_id"], "body_sha256": expected,
                    "objective_truth_claimed": False}
        except Exception as exc:
            return {"valid": False, "reason": type(exc).__name__, "objective_truth_claimed": False}

    def issue_claim(self, issuer_entity_id: str, subject_ref: str, predicate: str, value: Any,
                    *, state: str = "ASSERTED", evidence_refs: list[str] | None = None,
                    confidence: float | None = None) -> dict:
        self.identity.load_manifest(issuer_entity_id)
        state = str(state).upper()
        if state not in CLAIM_STATES:
            raise ValueError("unsupported claim state")
        if state in {"ATTESTED", "EXTERNALLY_VERIFIED", "ADJUDICATED"}:
            raise ValueError("verified states require a governed transition")
        if confidence is not None and not (0.0 <= float(confidence) <= 1.0):
            raise ValueError("confidence must be between 0 and 1")
        body = {
            "schema": "entity-v3-evidence-bound-claim-v1",
            "claim_id": rid("claim3"),
            "issuer_entity_id": issuer_entity_id,
            "subject_ref": str(subject_ref),
            "predicate": str(predicate),
            "value_sha256": digest(value),
            "state": state,
            "evidence_refs": sorted({str(x) for x in (evidence_refs or [])}),
            "confidence": None if confidence is None else float(confidence),
            "claim_is_not_objective_truth": True,
            "state_is_typed_not_absolute": True,
            "created_at_ms": now_ms(),
        }
        body_sha = digest(body)
        sig = self.identity.sign(issuer_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO claims VALUES(?,?,?,?,?,?,?,?,?,?)", (
                body["claim_id"], issuer_entity_id, body["subject_ref"], body["predicate"],
                body["value_sha256"], state, body_sha, json.dumps(body, sort_keys=True),
                json.dumps(sig, sort_keys=True), body["created_at_ms"]))
        return dict(body, body_sha256=body_sha, signature=sig)

    def get_claim(self, claim_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        if not row:
            raise KeyError("claim missing")
        body = json.loads(row["body_json"])
        body["state"] = row["state"]
        return dict(body, body_sha256=row["body_sha256"], signature=json.loads(row["signature_json"]))

    def transition_claim(self, actor_entity_id: str, claim_id: str, to_state: str, reason: str,
                         *, evidence_refs: list[str] | None = None) -> dict:
        self.identity.load_manifest(actor_entity_id)
        claim = self.get_claim(claim_id)
        from_state = claim["state"]
        to_state = str(to_state).upper()
        if to_state not in CLAIM_STATES or to_state not in _ALLOWED_TRANSITIONS.get(from_state, set()):
            raise ValueError("invalid claim-state transition")
        if to_state in {"ATTESTED", "EXTERNALLY_VERIFIED", "ADJUDICATED"} and not evidence_refs:
            raise ValueError("evidence required for stronger claim state")
        body = {
            "schema": "entity-v3-claim-status-transition-v1",
            "transition_id": rid("claimtx3"),
            "claim_id": claim_id,
            "actor_entity_id": actor_entity_id,
            "from_state": from_state,
            "to_state": to_state,
            "reason": str(reason),
            "evidence_refs": sorted({str(x) for x in (evidence_refs or [])}),
            "history_rewrite_prohibited": True,
            "transition_does_not_establish_objective_truth": True,
            "created_at_ms": now_ms(),
        }
        body_sha = digest(body)
        sig = self.identity.sign(actor_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO claim_transitions VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                body["transition_id"], claim_id, actor_entity_id, from_state, to_state, body["reason"],
                json.dumps(body["evidence_refs"]), body_sha, json.dumps(body, sort_keys=True),
                json.dumps(sig, sort_keys=True), body["created_at_ms"]))
            db.execute("UPDATE claims SET state=? WHERE claim_id=?", (to_state, claim_id))
        return dict(body, body_sha256=body_sha, signature=sig)

    def claim_history(self, claim_id: str) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT body_json,body_sha256,signature_json FROM claim_transitions WHERE claim_id=? ORDER BY created_at_ms,transition_id", (claim_id,)).fetchall()
        return [dict(json.loads(r["body_json"]), body_sha256=r["body_sha256"],
                     signature=json.loads(r["signature_json"])) for r in rows]
