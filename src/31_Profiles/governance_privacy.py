from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

def now_ms(): return int(time.time() * 1000)
def canon(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
def digest(v): return hashlib.sha256(v if isinstance(v, (bytes, bytearray)) else canon(v)).hexdigest()
def rid(prefix): return prefix + "-" + secrets.token_hex(12)

class SelectiveDisclosure:
    """Salted per-claim commitments. Hidden claims remain commitments, not disclosed values."""
    @staticmethod
    def commit(claims: dict[str, Any]) -> dict:
        entries, secrets_out = {}, {}
        for key in sorted(claims):
            salt = secrets.token_hex(24)
            commitment = digest({"key": key, "value": claims[key], "salt": salt})
            entries[key] = commitment
            secrets_out[key] = {"value": claims[key], "salt": salt}
        root = digest({"claims": entries})
        return {"schema": "entity-v3-private-claims-v1", "root": root,
                "commitments": entries, "private_openings": secrets_out}

    @staticmethod
    def disclose(package: dict, keys: list[str]) -> dict:
        openings = package.get("private_openings") or {}
        revealed = {}
        for key in sorted(set(keys)):
            if key not in openings: raise KeyError(key)
            revealed[key] = openings[key]
        return {"schema": "entity-v3-selective-disclosure-v1", "root": package["root"],
                "commitments": dict(package["commitments"]), "revealed": revealed}

    @staticmethod
    def verify(proof: dict) -> dict:
        commitments = dict(proof.get("commitments") or {})
        root_ok = digest({"claims": commitments}) == proof.get("root")
        bad = []
        for key, opening in dict(proof.get("revealed") or {}).items():
            expected = digest({"key": key, "value": opening.get("value"), "salt": opening.get("salt")})
            if commitments.get(key) != expected: bad.append(key)
        return {"valid": root_ok and not bad, "root_valid": root_ok,
                "invalid_reveals": bad, "revealed_keys": sorted((proof.get("revealed") or {}).keys())}

class DisputeLedger:
    """History-preserving claim -> challenge -> ruling -> supersession -> consequence semantics."""
    KINDS = {"CLAIM", "CHALLENGE", "EVIDENCE", "RULING", "SUPERSESSION", "CONSEQUENCE"}
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_disputes.sqlite"; self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS records(
                record_id TEXT PRIMARY KEY, kind TEXT NOT NULL, actor_entity_id TEXT NOT NULL,
                subject_ref TEXT NOT NULL, target_ref TEXT, payload_json TEXT NOT NULL,
                authority_basis TEXT, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")


    def record(self, kind: str, actor: str, subject_ref: str, payload: dict,
               *, target_ref: str | None = None, authority_basis: str | None = None) -> dict:
        kind = kind.upper()
        if kind not in self.KINDS: raise ValueError("invalid dispute record kind")
        if kind in {"CHALLENGE", "RULING", "SUPERSESSION", "CONSEQUENCE"} and not target_ref:
            raise ValueError("target_ref required")
        self.identity.load_manifest(actor)
        body = {"schema": "entity-v3-dispute-record-v1", "record_id": rid("disp3"),
                "kind": kind, "actor_entity_id": actor, "subject_ref": str(subject_ref),
                "target_ref": target_ref, "payload": dict(payload),
                "authority_basis": authority_basis, "created_at_ms": now_ms(),
                "history_rewrite_prohibited": True}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?)", (
                body["record_id"], kind, actor, body["subject_ref"], target_ref,
                json.dumps(body["payload"], sort_keys=True), authority_basis,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def state(self, subject_ref: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM records WHERE subject_ref=? ORDER BY created_at_ms,record_id",
                              (subject_ref,)).fetchall()
        kinds = [r["kind"] for r in rows]
        rulings = [dict(r) for r in rows if r["kind"] == "RULING"]
        supersessions = [dict(r) for r in rows if r["kind"] == "SUPERSESSION"]
        state = "UNCONTESTED"
        if "CHALLENGE" in kinds: state = "CONTESTED"
        if rulings: state = "RULED"
        if supersessions: state = "SUPERSEDED"
        return {"subject_ref": subject_ref, "state": state, "record_count": len(rows),
                "ruling_count": len(rulings), "history_preserved": True,
                "cryptographic_validity_is_not_legal_truth": True}

class StatusTimeProfile:
    """Signed time/status objects with deterministic stale and revocation behaviour."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_status_time.sqlite"; self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS statuses(
                status_id TEXT PRIMARY KEY, subject_ref TEXT NOT NULL, issuer TEXT NOT NULL,
                state TEXT NOT NULL, epoch INTEGER NOT NULL, effective_at_ms INTEGER NOT NULL,
                expires_at_ms INTEGER NOT NULL, stale_policy TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def timestamp(self, authority: str, payload_sha256: str, *, uncertainty_ms=0) -> dict:
        body = {"schema": "entity-v3-time-attestation-v1", "authority_entity_id": authority,
                "payload_sha256": payload_sha256, "timestamp_ms": now_ms(),
                "uncertainty_ms": max(0, int(uncertainty_ms))}
        return dict(body, signature=self.identity.sign(authority, body))

    def publish_status(self, issuer: str, subject_ref: str, state: str, *, epoch: int,
                       ttl_ms: int, stale_policy="FAIL_CLOSED", effective_at_ms=None) -> dict:
        state, stale_policy = state.upper(), stale_policy.upper()
        if state not in {"ACTIVE", "SUSPENDED", "REVOKED", "COMPROMISED", "RETIRED"}:
            raise ValueError("invalid status")
        if stale_policy not in {"FAIL_CLOSED", "READ_ONLY_GRACE", "ALLOW_UNTIL_EXPIRY"}:
            raise ValueError("invalid stale policy")
        effective = int(effective_at_ms or now_ms()); expires = effective + max(1, int(ttl_ms))
        with sqlite3.connect(self.path) as db:
            latest = db.execute("SELECT COALESCE(MAX(epoch),-1) FROM statuses WHERE subject_ref=?",
                                (subject_ref,)).fetchone()[0]
            if int(epoch) <= int(latest): raise ValueError("status epoch must increase")
        body = {"schema": "entity-v3-status-v1", "status_id": rid("status3"),
                "subject_ref": subject_ref, "issuer": issuer, "state": state, "epoch": int(epoch),
                "effective_at_ms": effective, "expires_at_ms": expires, "stale_policy": stale_policy,
                "created_at_ms": now_ms()}
        sig = self.identity.sign(issuer, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO statuses VALUES(?,?,?,?,?,?,?,?,?,?)", (
                body["status_id"], subject_ref, issuer, state, int(epoch), effective, expires,
                stale_policy, body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def evaluate(self, subject_ref: str, *, at_ms=None) -> dict:
        at = int(at_ms or now_ms())
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM statuses WHERE subject_ref=? AND effective_at_ms<=? "
                             "ORDER BY epoch DESC LIMIT 1", (subject_ref, at)).fetchone()
        if not row: return {"subject_ref": subject_ref, "decision": "DENY", "reason": "NO_STATUS"}
        stale = at > int(row["expires_at_ms"]); state = row["state"]
        if state in {"REVOKED", "COMPROMISED"}:
            decision = "DENY"
        elif stale and row["stale_policy"] == "FAIL_CLOSED":
            decision = "DENY"
        elif stale and row["stale_policy"] == "READ_ONLY_GRACE":
            decision = "READ_ONLY"
        else:
            decision = "ALLOW"
        return {"subject_ref": subject_ref, "state": state, "epoch": row["epoch"],
                "stale": stale, "stale_policy": row["stale_policy"], "decision": decision}

class RecoveryQuorum:
    """Multi-party approval gate wrapped around the existing cryptographic recovery mechanism."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_recovery_quorum.sqlite"; self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS policies(
                entity_id TEXT PRIMARY KEY, approvers_json TEXT NOT NULL, threshold INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS requests(
                request_id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, reason_sha256 TEXT NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS approvals(
                request_id TEXT NOT NULL, approver TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL, PRIMARY KEY(request_id,approver))""")

    def set_policy(self, entity_id: str, approvers: list[str], threshold: int) -> dict:
        unique = sorted(set(approvers)); threshold = int(threshold)
        if threshold < 1 or threshold > len(unique): raise ValueError("invalid recovery threshold")
        for a in unique: self.identity.load_manifest(a)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO policies VALUES(?,?,?)",
                       (entity_id, json.dumps(unique), threshold))
        return {"entity_id": entity_id, "approvers": unique, "threshold": threshold}

    def request(self, entity_id: str, reason: Any) -> dict:
        request_id = rid("recovery3")
        with sqlite3.connect(self.path) as db:
            if not db.execute("SELECT 1 FROM policies WHERE entity_id=?", (entity_id,)).fetchone():
                raise KeyError("recovery quorum policy missing")
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?)",
                       (request_id, entity_id, digest(reason), "OPEN", now_ms()))
        return {"request_id": request_id, "entity_id": entity_id, "status": "OPEN"}

    def approve(self, request_id: str, approver: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            req = db.execute("SELECT * FROM requests WHERE request_id=? AND status='OPEN'",
                             (request_id,)).fetchone()
            if not req: raise KeyError("open recovery request missing")
            policy = db.execute("SELECT * FROM policies WHERE entity_id=?", (req["entity_id"],)).fetchone()
        if approver not in set(json.loads(policy["approvers_json"])):
            raise PermissionError("not a recovery approver")
        body = {"schema": "entity-v3-recovery-approval-v1", "request_id": request_id,
                "entity_id": req["entity_id"], "approver": approver, "created_at_ms": now_ms()}
        sig = self.identity.sign(approver, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO approvals VALUES(?,?,?,?)",
                       (request_id, approver, body["created_at_ms"], json.dumps(sig, sort_keys=True)))
            count = db.execute("SELECT COUNT(*) FROM approvals WHERE request_id=?", (request_id,)).fetchone()[0]
        return dict(body, signature=sig, approval_count=count, threshold=int(policy["threshold"]))

    def execute(self, request_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            req = db.execute("SELECT * FROM requests WHERE request_id=? AND status='OPEN'",
                             (request_id,)).fetchone()
            if not req: raise KeyError("open recovery request missing")
            policy = db.execute("SELECT * FROM policies WHERE entity_id=?", (req["entity_id"],)).fetchone()
            approvals = db.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,)).fetchall()
        if len(approvals) < int(policy["threshold"]):
            raise PermissionError("recovery quorum not met")
        for row in approvals:
            body = {"schema": "entity-v3-recovery-approval-v1", "request_id": request_id,
                    "entity_id": req["entity_id"], "approver": row["approver"],
                    "created_at_ms": row["created_at_ms"]}
            manifest = self.identity.load_manifest(row["approver"])
            if not self.identity.verify_signature(manifest, body, json.loads(row["signature_json"])):
                raise PermissionError("invalid recovery approval")
        result = self.identity.recover_signing_key(req["entity_id"])
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET status='EXECUTED' WHERE request_id=?", (request_id,))
        return {"request_id": request_id, "entity_id": req["entity_id"],
                "status": "EXECUTED", "manifest_revision": result["manifest_revision"],
                "quorum_verified": True}