from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, json, sqlite3, time

CORE_VERSION = "3.0.0"
CORE_PRIMITIVES = ("ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE")
CORE_CAPABILITIES = (
    "canonical_serialization", "identity_object_addressing", "signature_verification",
    "authority_references", "rights_references", "event_state_transitions",
    "recovery_verification",
)

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def sha256(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canonical_json(value)
    return hashlib.sha256(raw).hexdigest()

def now_ms() -> int:
    return int(time.time() * 1000)

@dataclass(frozen=True)
class ProfileDescriptor:
    profile_id: str
    version: str
    schema_hash: str
    dependencies: tuple[str, ...] = ()
    mandatory: bool = False

class ProfileRegistry:
    """Optional versioned profiles; core conformance never implies profile conformance."""
    def __init__(self, root: str | Path):
        self.path = Path(root) / "entity_v3_profiles.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS profiles(
                profile_id TEXT NOT NULL, version TEXT NOT NULL, schema_hash TEXT NOT NULL,
                dependencies_json TEXT NOT NULL, mandatory INTEGER NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                PRIMARY KEY(profile_id,version))""")
            db.execute("""CREATE TABLE IF NOT EXISTS schemas(
                schema_id TEXT NOT NULL, version TEXT NOT NULL, schema_hash TEXT NOT NULL,
                compatibility TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                PRIMARY KEY(schema_id,version))""")

    def register(self, d: ProfileDescriptor) -> dict:
        if len(d.schema_hash) != 64:
            raise ValueError("schema_hash must be SHA-256")
        deps = tuple(sorted(set(d.dependencies)))
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            old = db.execute("SELECT * FROM profiles WHERE profile_id=? AND version=?",
                             (d.profile_id, d.version)).fetchone()
            if old:
                if old["schema_hash"] != d.schema_hash:
                    raise ValueError("immutable profile version changed")
                return dict(old)
            for dep in deps:
                pid, sep, ver = dep.partition("@")
                if not sep or not db.execute(
                    "SELECT 1 FROM profiles WHERE profile_id=? AND version=? AND status='ACTIVE'",
                    (pid, ver)).fetchone():
                    raise ValueError(f"missing profile dependency: {dep}")
            db.execute("INSERT INTO profiles VALUES(?,?,?,?,?,?,?)", (
                d.profile_id, d.version, d.schema_hash, json.dumps(deps),
                int(d.mandatory), "ACTIVE", now_ms()))
        return {"profile_id": d.profile_id, "version": d.version, "schema_hash": d.schema_hash,
                "dependencies": list(deps), "mandatory": d.mandatory, "status": "ACTIVE"}

    def negotiate(self, local: dict[str, list[str]], remote: dict[str, list[str]]) -> dict:
        selected, incompatible = {}, []
        for pid in sorted(set(local) | set(remote)):
            common = sorted(set(local.get(pid, [])) & set(remote.get(pid, [])))
            if common:
                selected[pid] = common[-1]
            elif pid in local and pid in remote:
                incompatible.append(pid)
        return {"core_version": CORE_VERSION, "selected_profiles": selected,
                "incompatible_profiles": incompatible, "core_interop_preserved": True}

    def register_schema(self, schema_id: str, version: str, document: Any,
                        compatibility: str = "IMMUTABLE") -> dict:
        compatibility = compatibility.upper()
        if compatibility not in {"IMMUTABLE", "BACKWARD", "FORWARD", "BIDIRECTIONAL"}:
            raise ValueError("invalid compatibility")
        digest = sha256(document)
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            old = db.execute("SELECT * FROM schemas WHERE schema_id=? AND version=?",
                             (schema_id, version)).fetchone()
            if old:
                if old["schema_hash"] != digest:
                    raise ValueError("immutable historical schema changed")
                return dict(old)
            db.execute("INSERT INTO schemas VALUES(?,?,?,?,?)",
                       (schema_id, version, digest, compatibility, now_ms()))
        return {"schema_id": schema_id, "version": version, "schema_hash": digest,
                "compatibility": compatibility}

class RightsOntology:
    """Canonical rights terms with deterministic precedence and deny-by-default."""
    TERMS = {
        "INSPECT": [], "READ": ["INSPECT"], "QUERY": ["INSPECT"],
        "COPY": ["READ"], "DERIVE": ["READ"], "TRAIN": ["READ"],
        "INFER": ["QUERY"], "EXECUTE": [], "MODIFY": ["READ"],
        "REDISTRIBUTE": ["COPY"], "COMMERCIALIZE": [], "SUBLICENSE": [],
        "CONTROL": [], "TRANSFER": [],
    }

    @classmethod
    def closure(cls, actions) -> set[str]:
        out = {str(a).upper() for a in actions}
        unknown = out - set(cls.TERMS)
        if unknown:
            raise ValueError(f"unknown rights terms: {sorted(unknown)}")
        changed = True
        while changed:
            changed = False
            for action in list(out):
                for implied in cls.TERMS[action]:
                    if implied not in out:
                        out.add(implied); changed = True
        return out

    @classmethod
    def evaluate(cls, rules: list[dict], action: str, context: dict | None = None) -> dict:
        action, context = str(action).upper(), dict(context or {})
        if action not in cls.TERMS:
            raise ValueError("unknown right action")
        applicable = []
        requested_closure = cls.closure([action])
        for rule in rules:
            effect = str(rule.get("effect") or "").upper()
            if effect not in {"ALLOW", "REQUIRE", "PROHIBIT"}:
                raise ValueError("invalid rights effect")
            rule_actions = {str(a).upper() for a in (rule.get("actions") or [])}
            rule_closure = cls.closure(rule_actions)
            if effect == "PROHIBIT":
                # A prohibition on a prerequisite propagates upward: e.g. READ blocks TRAIN.
                # A prohibition on a stronger action does not propagate downward: TRAIN does not block READ.
                if not (rule_actions & requested_closure):
                    continue
            elif action not in rule_closure:
                continue
            if any(context.get(k) != v for k, v in dict(rule.get("conditions") or {}).items()):
                continue
            applicable.append(rule)
        effects = {str(r["effect"]).upper() for r in applicable}
        decision = ("DENY" if "PROHIBIT" in effects else
                    "CONDITIONAL" if "REQUIRE" in effects else
                    "ALLOW" if "ALLOW" in effects else "DENY")
        obligations = [o for r in applicable for o in (r.get("obligations") or [])]
        return {"action": action, "decision": decision, "obligations": obligations,
                "applicable_rule_count": len(applicable), "deny_by_default": True}

class StandardGovernance:
    """Signed RFCs with threshold endorsement; no single implementation defines truth."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_standard_governance.sqlite"
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS rfcs(
                rfc_id TEXT PRIMARY KEY, proposer TEXT NOT NULL, body_sha256 TEXT NOT NULL,
                change_class TEXT NOT NULL, threshold INTEGER NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS endorsements(
                rfc_id TEXT NOT NULL, endorser TEXT NOT NULL, decision TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
                PRIMARY KEY(rfc_id,endorser))""")

    def propose(self, proposer: str, body: Any, change_class="PROFILE", threshold=2) -> dict:
        self.identity.load_manifest(proposer)
        digest, change_class = sha256(body), change_class.upper()
        if change_class not in {"CORE", "PROFILE", "SCHEMA", "TEST"}:
            raise ValueError("invalid change class")
        rfc_id = "rfc3-" + digest[:24]
        record = {"schema": "entity-v3-rfc-v1", "rfc_id": rfc_id, "proposer": proposer,
                  "body_sha256": digest, "change_class": change_class,
                  "threshold": max(1, int(threshold)), "status": "OPEN", "created_at_ms": now_ms()}
        sig = self.identity.sign(proposer, record)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO rfcs VALUES(?,?,?,?,?,?,?,?)", (
                rfc_id, proposer, digest, change_class, record["threshold"],
                "OPEN", record["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(record, signature=sig)

    def endorse(self, rfc_id: str, endorser: str, decision="APPROVE") -> dict:
        decision = decision.upper()
        if decision not in {"APPROVE", "REJECT"}:
            raise ValueError("invalid endorsement")
        record = {"schema": "entity-v3-rfc-endorsement-v1", "rfc_id": rfc_id,
                  "endorser": endorser, "decision": decision, "created_at_ms": now_ms()}
        sig = self.identity.sign(endorser, record)
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rfc = db.execute("SELECT * FROM rfcs WHERE rfc_id=? AND status='OPEN'", (rfc_id,)).fetchone()
            if not rfc: raise KeyError("open RFC not found")
            db.execute("INSERT OR REPLACE INTO endorsements VALUES(?,?,?,?,?)",
                       (rfc_id, endorser, decision, record["created_at_ms"], json.dumps(sig)))
            approvals = db.execute("SELECT COUNT(*) FROM endorsements WHERE rfc_id=? AND decision='APPROVE'",
                                   (rfc_id,)).fetchone()[0]
            rejects = db.execute("SELECT COUNT(*) FROM endorsements WHERE rfc_id=? AND decision='REJECT'",
                                 (rfc_id,)).fetchone()[0]
            status = "ACCEPTED" if approvals >= rfc["threshold"] else (
                     "REJECTED" if rejects >= rfc["threshold"] else "OPEN")
            db.execute("UPDATE rfcs SET status=? WHERE rfc_id=?", (status, rfc_id))
        return dict(record, signature=sig, rfc_status=status)

def core_status() -> dict:
    return {"schema": "entity-v3-core-status-v1", "core_version": CORE_VERSION,
            "primitives": list(CORE_PRIMITIVES), "core_capabilities": list(CORE_CAPABILITIES),
            "extensions_are_optional": True, "historical_schemas_immutable": True,
            "profile_negotiation": True, "deny_by_default_rights_semantics": True}