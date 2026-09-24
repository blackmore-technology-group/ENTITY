from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

from reality_profile import ANCHOR_TYPES

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

class ExternalRealityAnchorRegistry:
    """References external authoritative systems without importing their authority into ENTITY."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_3_reality_anchors.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS anchors(
                anchor_id TEXT PRIMARY KEY, operator_entity_id TEXT NOT NULL, anchor_type TEXT NOT NULL,
                body_json TEXT NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS snapshots(
                snapshot_id TEXT PRIMARY KEY, anchor_id TEXT NOT NULL, external_record_id TEXT NOT NULL,
                record_sha256 TEXT NOT NULL, body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
                signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL)""")

    def register(self, operator_entity_id: str, anchor_type: str, endpoint_descriptor_sha256: str,
                 *, jurisdiction: str = "", trust_profile_ref: str = "") -> dict:
        self.identity.load_manifest(operator_entity_id)
        anchor_type = str(anchor_type).upper()
        if anchor_type not in ANCHOR_TYPES:
            raise ValueError("unsupported anchor type")
        body = {
            "schema": "entity-v3-external-reality-anchor-v1",
            "anchor_id": rid("anchor3"),
            "operator_entity_id": operator_entity_id,
            "anchor_type": anchor_type,
            "endpoint_descriptor_sha256": sha256_hex(endpoint_descriptor_sha256),
            "jurisdiction": str(jurisdiction),
            "trust_profile_ref": str(trust_profile_ref),
            "credentials_included": False,
            "external_system_is_not_automatic_entity_authority": True,
            "created_at_ms": now_ms(),
        }
        sig = self.identity.sign(operator_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO anchors VALUES(?,?,?,?,?)", (
                body["anchor_id"], operator_entity_id, anchor_type,
                json.dumps(body, sort_keys=True), json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def snapshot(self, operator_entity_id: str, anchor_id: str, external_record_id: str,
                 record_sha256: str, *, retrieval_method: str = "API",
                 verifier_evidence_refs: list[str] | None = None) -> dict:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT operator_entity_id FROM anchors WHERE anchor_id=?", (anchor_id,)).fetchone()
        if not row or row[0] != operator_entity_id:
            raise PermissionError("anchor operator required")
        body = {
            "schema": "entity-v3-external-reality-snapshot-v1",
            "snapshot_id": rid("snapshot3"),
            "anchor_id": anchor_id,
            "external_record_id": str(external_record_id),
            "record_sha256": sha256_hex(record_sha256),
            "retrieval_method": str(retrieval_method).upper(),
            "verifier_evidence_refs": sorted({str(x) for x in (verifier_evidence_refs or [])}),
            "external_record_is_evidence_not_protocol_truth": True,
            "record_may_be_contested_or_superseded": True,
            "created_at_ms": now_ms(),
        }
        body_sha = digest(body)
        sig = self.identity.sign(operator_entity_id, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?)", (
                body["snapshot_id"], anchor_id, body["external_record_id"], body["record_sha256"],
                body_sha, json.dumps(body, sort_keys=True), json.dumps(sig, sort_keys=True), body["created_at_ms"]))
        return dict(body, body_sha256=body_sha, signature=sig)
