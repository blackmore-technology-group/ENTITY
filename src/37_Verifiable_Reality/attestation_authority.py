from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

def now_ms() -> int:
    return int(time.time() * 1000)

def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def digest(value: Any) -> str:
    return hashlib.sha256(canon(value)).hexdigest()

def rid(prefix: str) -> str:
    return prefix + "-" + secrets.token_hex(12)

def sha256_hex(value: str) -> str:
    value = str(value).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("SHA-256 required")
    return value

class AttestationAuthorityRegistry:
    """Scoped authority to attest. An attestation remains attributed evidence, not universal truth."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_3_attestation.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS grants(
                grant_id TEXT PRIMARY KEY, grantor_entity_id TEXT NOT NULL, attestor_entity_id TEXT NOT NULL,
                scopes_json TEXT NOT NULL, expires_at_ms INTEGER, revoked INTEGER NOT NULL DEFAULT 0,
                body_json TEXT NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS attestations(
                attestation_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, attestor_entity_id TEXT NOT NULL,
                scope TEXT NOT NULL, body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
                signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL)""")

    def grant(self, grantor_entity_id: str, attestor_entity_id: str, scopes: list[str],
              authority_evidence_sha256: str, *, expires_at_ms: int | None = None) -> dict:
        self.identity.load_manifest(grantor_entity_id)
        self.identity.load_manifest(attestor_entity_id)
        scopes = sorted({str(x).upper() for x in scopes if str(x)})
        if not scopes:
            raise ValueError("attestation grant requires scopes")
        body = {
            "schema": "entity-v3-attestation-authority-grant-v1",
            "grant_id": rid("attgrant3"),
            "grantor_entity_id": grantor_entity_id,
            "attestor_entity_id": attestor_entity_id,
            "scopes": scopes,
            "authority_evidence_sha256": sha256_hex(authority_evidence_sha256),
            "expires_at_ms": None if expires_at_ms is None else int(expires_at_ms),
            "attestation_authority_is_scope_limited": True,
            "attestation_does_not_create_legal_truth": True,
            "created_at_ms": now_ms(),
        }
        sig = self.identity.sign(grantor_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO grants VALUES(?,?,?,?,?,0,?,?)", (
                body["grant_id"], grantor_entity_id, attestor_entity_id, json.dumps(scopes),
                body["expires_at_ms"], json.dumps(body, sort_keys=True), json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def revoke(self, grantor_entity_id: str, grant_id: str) -> None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT grantor_entity_id FROM grants WHERE grant_id=?", (grant_id,)).fetchone()
            if not row or row[0] != grantor_entity_id:
                raise PermissionError("grantor required")
            db.execute("UPDATE grants SET revoked=1 WHERE grant_id=?", (grant_id,))

    def _active_grant(self, attestor_entity_id: str, scope: str) -> dict:
        now = now_ms()
        scope = str(scope).upper()
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM grants WHERE attestor_entity_id=? AND revoked=0", (attestor_entity_id,)).fetchall()
        for row in rows:
            if row["expires_at_ms"] is not None and int(row["expires_at_ms"]) <= now:
                continue
            if scope in json.loads(row["scopes_json"]):
                return json.loads(row["body_json"])
        raise PermissionError("attestor lacks active scope")

    def attest(self, attestor_entity_id: str, claim_id: str, scope: str,
               evidence_refs: list[str], conclusion: str) -> dict:
        self.identity.load_manifest(attestor_entity_id)
        grant = self._active_grant(attestor_entity_id, scope)
        refs = sorted({str(x) for x in evidence_refs if str(x)})
        if not refs:
            raise ValueError("attestation requires evidence")
        body = {
            "schema": "entity-v3-attestation-v1",
            "attestation_id": rid("attest3"),
            "claim_id": str(claim_id),
            "attestor_entity_id": attestor_entity_id,
            "scope": str(scope).upper(),
            "grant_id": grant["grant_id"],
            "evidence_refs": refs,
            "conclusion": str(conclusion),
            "attestation_is_evidence_not_objective_truth": True,
            "created_at_ms": now_ms(),
        }
        body_sha = digest(body)
        sig = self.identity.sign(attestor_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO attestations VALUES(?,?,?,?,?,?,?,?)", (
                body["attestation_id"], body["claim_id"], attestor_entity_id, body["scope"],
                body_sha, json.dumps(body, sort_keys=True), json.dumps(sig, sort_keys=True), body["created_at_ms"]))
        return dict(body, body_sha256=body_sha, signature=sig)
