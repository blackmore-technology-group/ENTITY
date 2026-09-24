from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import base64, hashlib, json, os, secrets, sqlite3, time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def now_ms() -> int:
    return int(time.time() * 1000)

def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def digest(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon(value)
    return hashlib.sha256(raw).hexdigest()

def rid(prefix: str) -> str:
    return prefix + "-" + secrets.token_hex(12)

def sha256_hex(value: str) -> str:
    value = str(value).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("expected lowercase SHA-256")
    return value

def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

class PurposeBoundAccessRegistry:
    """Controller-signed purpose/action grants with expiry, use caps and revocation."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_purpose_access.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS grants(
                grant_id TEXT PRIMARY KEY, controller TEXT NOT NULL, grantee TEXT NOT NULL,
                resource_ref TEXT NOT NULL, purposes_json TEXT NOT NULL, actions_json TEXT NOT NULL,
                max_uses INTEGER NOT NULL, used_count INTEGER NOT NULL,
                expires_at_ms INTEGER NOT NULL, status TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS uses(
                use_id TEXT PRIMARY KEY, grant_id TEXT NOT NULL, grantee TEXT NOT NULL,
                purpose TEXT NOT NULL, action TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def grant(self, controller: str, grantee: str, resource_ref: str,
              purposes: list[str], actions: list[str], *, expires_at_ms: int,
              max_uses: int = 0) -> dict:
        purposes = sorted({str(x).upper() for x in purposes})
        actions = sorted({str(x).upper() for x in actions})
        if not purposes or not actions:
            raise ValueError("purpose and action sets required")
        if int(expires_at_ms) <= now_ms():
            raise ValueError("grant expiry must be in the future")
        body = {"schema": "entity-v3-purpose-bound-access-v1", "grant_id": rid("pgrant3"),
                "controller": controller, "grantee": grantee, "resource_ref": str(resource_ref),
                "purposes": purposes, "actions": actions, "max_uses": max(0, int(max_uses)),
                "expires_at_ms": int(expires_at_ms), "status": "ACTIVE", "created_at_ms": now_ms()}
        sig = self.identity.sign(controller, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO grants VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
                body["grant_id"], controller, grantee, str(resource_ref),
                json.dumps(purposes), json.dumps(actions), body["max_uses"], 0,
                body["expires_at_ms"], "ACTIVE", body["created_at_ms"],
                json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def revoke(self, controller: str, grant_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM grants WHERE grant_id=?", (grant_id,)).fetchone()
            if not row:
                raise KeyError("purpose grant missing")
            if row["controller"] != controller:
                raise PermissionError("only controller may revoke purpose grant")
            if row["status"] == "REVOKED":
                return {"grant_id": grant_id, "status": "REVOKED", "already_revoked": True}
        body = {"schema": "entity-v3-purpose-bound-revocation-v1", "grant_id": grant_id,
                "controller": controller, "status": "REVOKED", "created_at_ms": now_ms()}
        sig = self.identity.sign(controller, body)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE grants SET status='REVOKED' WHERE grant_id=?", (grant_id,))
        return dict(body, signature=sig, already_revoked=False)

    def authorize_use(self, grant_id: str, grantee: str, purpose: str, action: str,
                      evidence_sha256: str, *, at_ms: int | None = None) -> dict:
        at = int(at_ms or now_ms())
        purpose, action = purpose.upper(), action.upper()
        evidence_sha256 = sha256_hex(evidence_sha256)
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM grants WHERE grant_id=?", (grant_id,)).fetchone()
            if not row or row["status"] != "ACTIVE":
                raise PermissionError("inactive purpose grant")
            if row["grantee"] != grantee:
                raise PermissionError("purpose grant grantee mismatch")
            if at > int(row["expires_at_ms"]):
                raise PermissionError("purpose grant expired")
            if purpose not in set(json.loads(row["purposes_json"])):
                raise PermissionError("purpose not authorized")
            if action not in set(json.loads(row["actions_json"])):
                raise PermissionError("action not authorized")
            max_uses, used = int(row["max_uses"]), int(row["used_count"])
            if max_uses and used >= max_uses:
                raise PermissionError("purpose grant use cap exhausted")
            use_id = rid("puse3")
            body = {"schema": "entity-v3-purpose-use-v1", "use_id": use_id,
                    "grant_id": grant_id, "grantee": grantee, "purpose": purpose,
                    "action": action, "evidence_sha256": evidence_sha256,
                    "created_at_ms": at}
            sig = self.identity.sign(grantee, body)
            db.execute("INSERT INTO uses VALUES(?,?,?,?,?,?,?,?)", (
                use_id, grant_id, grantee, purpose, action, evidence_sha256,
                at, json.dumps(sig, sort_keys=True)))
            db.execute("UPDATE grants SET used_count=used_count+1 WHERE grant_id=?", (grant_id,))
        return dict(body, signature=sig, authorized=True,
                    remaining_uses=None if max_uses == 0 else max_uses - used - 1)

class SelectiveRetentionLedger:
    """Keeps evidence commitments while allowing controlled payload/storage destruction."""
    MODES = {"DELETE_PAYLOAD", "REDACT_SOURCE", "DESTROY_EXTERNAL_COPY", "LEGAL_HOLD"}
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_retention.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS records(
                record_id TEXT PRIMARY KEY, controller TEXT NOT NULL, subject_ref TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL, storage_ref_sha256 TEXT,
                purpose TEXT NOT NULL, jurisdiction TEXT NOT NULL,
                retain_until_ms INTEGER NOT NULL, destruction_mode TEXT NOT NULL,
                status TEXT NOT NULL, destruction_evidence_sha256 TEXT,
                created_at_ms INTEGER NOT NULL, destroyed_at_ms INTEGER,
                signature_json TEXT NOT NULL)""")

    def register(self, controller: str, subject_ref: str, payload_sha256: str, *,
                 purpose: str, jurisdiction: str, retain_until_ms: int,
                 destruction_mode: str, storage_ref_sha256: str | None = None) -> dict:
        mode = destruction_mode.upper()
        if mode not in self.MODES:
            raise ValueError("invalid destruction mode")
        payload_sha256 = sha256_hex(payload_sha256)
        storage_hash = None if storage_ref_sha256 is None else sha256_hex(storage_ref_sha256)
        body = {"schema": "entity-v3-retention-record-v1", "record_id": rid("retain3"),
                "controller": controller, "subject_ref": str(subject_ref),
                "payload_sha256": payload_sha256, "storage_ref_sha256": storage_hash,
                "purpose": str(purpose).upper(), "jurisdiction": str(jurisdiction).upper(),
                "retain_until_ms": int(retain_until_ms), "destruction_mode": mode,
                "status": "ACTIVE", "created_at_ms": now_ms(),
                "raw_payload_stored_in_ledger": False}
        sig = self.identity.sign(controller, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                body["record_id"], controller, str(subject_ref), payload_sha256, storage_hash,
                body["purpose"], body["jurisdiction"], body["retain_until_ms"], mode,
                "ACTIVE", None, body["created_at_ms"], None, json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def destroy(self, controller: str, record_id: str, destruction_evidence_sha256: str,
                *, at_ms: int | None = None) -> dict:
        destruction_evidence_sha256 = sha256_hex(destruction_evidence_sha256)
        at = int(at_ms or now_ms())
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM records WHERE record_id=?", (record_id,)).fetchone()
            if not row:
                raise KeyError("retention record missing")
            if row["controller"] != controller:
                raise PermissionError("only controller may destroy retained payload")
            if row["destruction_mode"] == "LEGAL_HOLD":
                raise PermissionError("legal hold prevents destruction")
            if at < int(row["retain_until_ms"]):
                raise PermissionError("retention period has not expired")
            if row["status"] == "DESTROYED":
                return {"record_id": record_id, "status": "DESTROYED", "already_destroyed": True,
                        "payload_sha256": row["payload_sha256"], "commitment_preserved": True}
        body = {"schema": "entity-v3-retention-destruction-v1", "record_id": record_id,
                "controller": controller, "payload_sha256": row["payload_sha256"],
                "destruction_evidence_sha256": destruction_evidence_sha256,
                "destroyed_at_ms": at, "commitment_preserved": True}
        sig = self.identity.sign(controller, body)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE records SET status='DESTROYED', destruction_evidence_sha256=?, destroyed_at_ms=? WHERE record_id=?",
                       (destruction_evidence_sha256, at, record_id))
        return dict(body, signature=sig, status="DESTROYED", already_destroyed=False)

    def status(self, record_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM records WHERE record_id=?", (record_id,)).fetchone()
        if not row:
            raise KeyError("retention record missing")
        return {"record_id": record_id, "status": row["status"],
                "payload_sha256": row["payload_sha256"],
                "raw_payload_stored_in_ledger": False, "commitment_preserved": True}

class ConfidentialProvenanceLedger:
    """Commitment-first provenance with optional AES-GCM protected metadata."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_confidential_provenance.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS edges(
                edge_id TEXT PRIMARY KEY, actor TEXT NOT NULL,
                parent_ref TEXT NOT NULL, child_ref TEXT NOT NULL,
                relationship TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                metadata_commitment_sha256 TEXT NOT NULL,
                encrypted_metadata_json TEXT, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL)""")

    def add_edge(self, actor: str, parent_ref: str, child_ref: str, relationship: str,
                 evidence_sha256: str, *, metadata: dict | None = None,
                 encryption_key: bytes | None = None) -> dict:
        evidence_sha256 = sha256_hex(evidence_sha256)
        metadata = dict(metadata or {})
        commitment = digest(metadata)
        encrypted = None
        if metadata:
            if encryption_key is None or len(encryption_key) not in {16, 24, 32}:
                raise ValueError("AES key required for confidential provenance metadata")
            nonce = os.urandom(12)
            aad = canon({"parent_ref": parent_ref, "child_ref": child_ref,
                         "relationship": relationship, "commitment": commitment})
            ciphertext = AESGCM(encryption_key).encrypt(nonce, canon(metadata), aad)
            encrypted = {"suite": "AES-GCM", "nonce": b64(nonce), "ciphertext": b64(ciphertext),
                         "aad_sha256": hashlib.sha256(aad).hexdigest()}
        body = {"schema": "entity-v3-confidential-provenance-v1", "edge_id": rid("cpedge3"),
                "actor": actor, "parent_ref": str(parent_ref), "child_ref": str(child_ref),
                "relationship": str(relationship).upper(), "evidence_sha256": evidence_sha256,
                "metadata_commitment_sha256": commitment, "encrypted_metadata": encrypted,
                "created_at_ms": now_ms(), "confidential_metadata_not_public_provenance": True}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?,?,?)", (
                body["edge_id"], actor, str(parent_ref), str(child_ref),
                body["relationship"], evidence_sha256, commitment,
                json.dumps(encrypted, sort_keys=True) if encrypted else None,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def reveal_metadata(self, edge_id: str, encryption_key: bytes) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM edges WHERE edge_id=?", (edge_id,)).fetchone()
        if not row:
            raise KeyError("confidential provenance edge missing")
        if not row["encrypted_metadata_json"]:
            return {"edge_id": edge_id, "metadata": {}, "commitment_valid": True}
        env = json.loads(row["encrypted_metadata_json"])
        aad = canon({"parent_ref": row["parent_ref"], "child_ref": row["child_ref"],
                     "relationship": row["relationship"],
                     "commitment": row["metadata_commitment_sha256"]})
        plaintext = AESGCM(encryption_key).decrypt(unb64(env["nonce"]), unb64(env["ciphertext"]), aad)
        metadata = json.loads(plaintext.decode("utf-8"))
        valid = digest(metadata) == row["metadata_commitment_sha256"]
        if not valid:
            raise PermissionError("confidential provenance commitment mismatch")
        return {"edge_id": edge_id, "metadata": metadata, "commitment_valid": True}

class ProofVerifierRegistry:
    """Fail-closed adapter registry for external ZK/privacy proof systems."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_proof_verifiers.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        self._callbacks: dict[str, Callable[[bytes, dict], bool]] = {}
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS suites(
                suite_id TEXT PRIMARY KEY, governance_entity_id TEXT NOT NULL,
                algorithm TEXT NOT NULL, verifier_sha256 TEXT NOT NULL,
                security_claim TEXT NOT NULL, status TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS receipts(
                receipt_id TEXT PRIMARY KEY, suite_id TEXT NOT NULL,
                verifier_entity_id TEXT NOT NULL, proof_sha256 TEXT NOT NULL,
                public_inputs_sha256 TEXT NOT NULL, accepted INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def register_suite(self, governance_entity: str, suite_id: str, algorithm: str,
                       verifier_sha256: str, security_claim: str) -> dict:
        suite_id = str(suite_id).strip().upper()
        verifier_sha256 = sha256_hex(verifier_sha256)
        if not suite_id or not algorithm:
            raise ValueError("proof suite id and algorithm required")
        body = {"schema": "entity-v3-proof-suite-v1", "suite_id": suite_id,
                "governance_entity_id": governance_entity, "algorithm": str(algorithm),
                "verifier_sha256": verifier_sha256, "security_claim": str(security_claim),
                "status": "ACTIVE", "created_at_ms": now_ms(),
                "registration_does_not_certify_cryptographic_security": True}
        sig = self.identity.sign(governance_entity, body)
        with sqlite3.connect(self.path) as db:
            old = db.execute("SELECT verifier_sha256 FROM suites WHERE suite_id=?", (suite_id,)).fetchone()
            if old and old[0] != verifier_sha256:
                raise ValueError("proof suite verifier changed without new suite id")
            if not old:
                db.execute("INSERT INTO suites VALUES(?,?,?,?,?,?,?,?)", (
                    suite_id, governance_entity, str(algorithm), verifier_sha256,
                    str(security_claim), "ACTIVE", body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig, existing=bool(old))

    def bind_runtime_verifier(self, suite_id: str, verifier_sha256: str,
                              callback: Callable[[bytes, dict], bool]) -> None:
        suite_id = suite_id.upper(); verifier_sha256 = sha256_hex(verifier_sha256)
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT verifier_sha256,status FROM suites WHERE suite_id=?", (suite_id,)).fetchone()
        if not row or row[1] != "ACTIVE":
            raise KeyError("active proof suite missing")
        if row[0] != verifier_sha256:
            raise PermissionError("runtime verifier hash does not match registered suite")
        self._callbacks[suite_id] = callback

    def verify(self, suite_id: str, verifier_entity: str, proof: bytes,
               public_inputs: dict) -> dict:
        suite_id = suite_id.upper()
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT status FROM suites WHERE suite_id=?", (suite_id,)).fetchone()
        if not row or row[0] != "ACTIVE":
            raise PermissionError("proof suite is not active")
        callback = self._callbacks.get(suite_id)
        if callback is None:
            raise RuntimeError("no runtime verifier bound; proof verification fails closed")
        accepted = bool(callback(bytes(proof), dict(public_inputs)))
        body = {"schema": "entity-v3-proof-verification-receipt-v1",
                "receipt_id": rid("zkreceipt3"), "suite_id": suite_id,
                "verifier_entity_id": verifier_entity,
                "proof_sha256": hashlib.sha256(proof).hexdigest(),
                "public_inputs_sha256": digest(public_inputs), "accepted": accepted,
                "created_at_ms": now_ms(),
                "proof_acceptance_is_suite_specific_not_universal_truth": True}
        sig = self.identity.sign(verifier_entity, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?)", (
                body["receipt_id"], suite_id, verifier_entity, body["proof_sha256"],
                body["public_inputs_sha256"], int(accepted), body["created_at_ms"],
                json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)
