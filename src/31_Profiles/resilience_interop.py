from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

def now_ms(): return int(time.time() * 1000)
def canon(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
def digest(v): return hashlib.sha256(v if isinstance(v, (bytes, bytearray)) else canon(v)).hexdigest()
def rid(prefix): return prefix + "-" + secrets.token_hex(12)

class FederatedResolutionProfile:
    """Multiple signed resolver observations, quorum selection and split-view detection."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_federated_resolution.sqlite"; self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS views(
                view_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, resolver TEXT NOT NULL,
                version INTEGER NOT NULL, epoch INTEGER NOT NULL, resolution_sha256 TEXT NOT NULL,
                expires_at_ms INTEGER NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL)""")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_resolution_equivocation "
                       "ON views(object_id,resolver,version,epoch,resolution_sha256)")

    def observe(self, resolver: str, object_id: str, resolution_record: dict,
                *, epoch: int, ttl_ms: int) -> dict:
        self.identity.load_manifest(resolver)
        version = int(resolution_record.get("version") or 0)
        if version < 1: raise ValueError("resolution version required")
        body = {"schema": "entity-v3-resolver-view-v1", "view_id": rid("view3"),
                "object_id": object_id, "resolver": resolver, "version": version,
                "epoch": int(epoch), "resolution_sha256": digest(resolution_record),
                "expires_at_ms": now_ms() + max(1, int(ttl_ms)), "created_at_ms": now_ms()}
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT DISTINCT resolution_sha256 FROM views "
                              "WHERE object_id=? AND resolver=? AND version=? AND epoch=?",
                              (object_id, resolver, version, int(epoch))).fetchall()
            if rows and any(r[0] != body["resolution_sha256"] for r in rows):
                raise ValueError("resolver equivocation detected")
        sig = self.identity.sign(resolver, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO views VALUES(?,?,?,?,?,?,?,?,?)", (
                body["view_id"], object_id, resolver, version, int(epoch),
                body["resolution_sha256"], body["expires_at_ms"], body["created_at_ms"],
                json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def resolve_quorum(self, object_id: str, *, minimum_resolvers=2, at_ms=None) -> dict:
        at = int(at_ms or now_ms())
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM views WHERE object_id=? AND expires_at_ms>=? "
                              "ORDER BY version DESC,epoch DESC,created_at_ms DESC",
                              (object_id, at)).fetchall()
        grouped = {}
        seen_resolver_version = {}
        equivocation = False
        for row in rows:
            key_re = (row["resolver"], row["version"], row["epoch"])
            prev = seen_resolver_version.get(key_re)
            if prev and prev != row["resolution_sha256"]: equivocation = True
            seen_resolver_version[key_re] = row["resolution_sha256"]
            key = (row["version"], row["epoch"], row["resolution_sha256"])
            grouped.setdefault(key, set()).add(row["resolver"])
        candidates = [(len(v), k, v) for k, v in grouped.items()]
        candidates.sort(key=lambda x: (-x[0], -x[1][0], -x[1][1], x[1][2]))
        if equivocation:
            return {"object_id": object_id, "resolved": False, "reason": "EQUIVOCATION"}
        if not candidates or candidates[0][0] < int(minimum_resolvers):
            return {"object_id": object_id, "resolved": False, "reason": "QUORUM_NOT_MET"}
        count, (version, epoch, sha), resolvers = candidates[0]
        return {"object_id": object_id, "resolved": True, "version": version, "epoch": epoch,
                "resolution_sha256": sha, "resolver_count": count,
                "resolvers": sorted(resolvers), "resolver_is_not_authority": True}

class AgentDelegationProfile:
    """Sub-agent authority with depth/capability/budget/time attenuation and kill semantics."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_agent_delegation.sqlite"; self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS grants(
                grant_id TEXT PRIMARY KEY, principal TEXT NOT NULL, grantor TEXT NOT NULL,
                grantee TEXT NOT NULL, parent_grant_id TEXT, depth INTEGER NOT NULL,
                max_depth INTEGER NOT NULL, capabilities_json TEXT NOT NULL,
                budget_units INTEGER NOT NULL, spent_units INTEGER NOT NULL,
                expires_at_ms INTEGER NOT NULL, policy_sha256 TEXT NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def grant(self, principal: str, grantor: str, grantee: str, capabilities: list[str], *,
              max_depth=0, budget_units=0, expires_at_ms: int, policy_sha256: str,
              parent_grant_id: str | None = None) -> dict:
        caps = sorted({str(c).upper() for c in capabilities})
        depth = 0
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            if parent_grant_id:
                parent = db.execute("SELECT * FROM grants WHERE grant_id=? AND status='ACTIVE'",
                                    (parent_grant_id,)).fetchone()
                if not parent: raise KeyError("active parent grant missing")
                if parent["grantee"] != grantor or parent["principal"] != principal:
                    raise PermissionError("delegation chain mismatch")
                depth = int(parent["depth"]) + 1
                if depth > int(parent["max_depth"]): raise PermissionError("delegation depth exceeded")
                if not set(caps).issubset(set(json.loads(parent["capabilities_json"]))):
                    raise PermissionError("capability escalation prohibited")
                remaining = int(parent["budget_units"]) - int(parent["spent_units"])
                if int(budget_units) > remaining: raise PermissionError("budget escalation prohibited")
                if int(expires_at_ms) > int(parent["expires_at_ms"]):
                    raise PermissionError("time escalation prohibited")
        body = {"schema": "entity-v3-agent-delegation-v1", "grant_id": rid("agentgrant3"),
                "principal": principal, "grantor": grantor, "grantee": grantee,
                "parent_grant_id": parent_grant_id, "depth": depth, "max_depth": int(max_depth),
                "capabilities": caps, "budget_units": max(0, int(budget_units)),
                "expires_at_ms": int(expires_at_ms), "policy_sha256": policy_sha256,
                "status": "ACTIVE", "created_at_ms": now_ms()}
        sig = self.identity.sign(grantor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO grants VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                body["grant_id"], principal, grantor, grantee, parent_grant_id, depth,
                int(max_depth), json.dumps(caps), body["budget_units"], 0,
                body["expires_at_ms"], policy_sha256, "ACTIVE", body["created_at_ms"],
                json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def consume(self, grant_id: str, capability: str, units=1, *, at_ms=None) -> dict:
        at, units, capability = int(at_ms or now_ms()), max(0, int(units)), capability.upper()
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM grants WHERE grant_id=?", (grant_id,)).fetchone()
            if not row or row["status"] != "ACTIVE": raise PermissionError("inactive grant")
            if at > int(row["expires_at_ms"]): raise PermissionError("grant expired")
            if capability not in set(json.loads(row["capabilities_json"])):
                raise PermissionError("capability not delegated")
            if int(row["spent_units"]) + units > int(row["budget_units"]):
                raise PermissionError("delegated budget exhausted")
            spent = int(row["spent_units"]) + units
            db.execute("UPDATE grants SET spent_units=? WHERE grant_id=?", (spent, grant_id))
        return {"grant_id": grant_id, "authorized": True, "capability": capability,
                "consumed_units": units, "spent_units": spent,
                "remaining_units": int(row["budget_units"]) - spent}

    def kill(self, grant_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            queue, revoked = [grant_id], []
            while queue:
                current = queue.pop(0)
                db.execute("UPDATE grants SET status='REVOKED' WHERE grant_id=?", (current,))
                revoked.append(current)
                queue.extend(r[0] for r in db.execute(
                    "SELECT grant_id FROM grants WHERE parent_grant_id=? AND status='ACTIVE'",
                    (current,)).fetchall())
        return {"root_grant_id": grant_id, "revoked_grants": revoked, "kill_propagated": True}

class PhysicalBindingProfile:
    """Physical↔digital binding with hardware evidence, custody and clone suspicion."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_physical_binding.sqlite"; self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS bindings(
                binding_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, actor TEXT NOT NULL,
                hardware_fingerprint TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS custody(
                event_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, from_entity TEXT,
                to_entity TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def bind(self, actor: str, object_id: str, hardware_fingerprint: str, evidence_sha256: str) -> dict:
        with sqlite3.connect(self.path) as db:
            conflict = db.execute("SELECT object_id FROM bindings WHERE hardware_fingerprint=? "
                                  "AND status='ACTIVE' AND object_id<>?",
                                  (hardware_fingerprint, object_id)).fetchall()
        if conflict:
            return {"bound": False, "clone_suspected": True,
                    "conflicting_object_ids": sorted({r[0] for r in conflict})}
        body = {"schema": "entity-v3-physical-binding-v1", "binding_id": rid("bind3"),
                "object_id": object_id, "actor": actor, "hardware_fingerprint": hardware_fingerprint,
                "evidence_sha256": evidence_sha256, "status": "ACTIVE", "created_at_ms": now_ms()}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO bindings VALUES(?,?,?,?,?,?,?,?)", (
                body["binding_id"], object_id, actor, hardware_fingerprint, evidence_sha256,
                "ACTIVE", body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig, bound=True, clone_suspected=False)

    def custody_transfer(self, actor: str, object_id: str, from_entity: str | None,
                         to_entity: str, evidence_sha256: str) -> dict:
        body = {"schema": "entity-v3-custody-event-v1", "event_id": rid("custody3"),
                "object_id": object_id, "from_entity": from_entity, "to_entity": to_entity,
                "evidence_sha256": evidence_sha256, "created_at_ms": now_ms(),
                "custody_is_not_ownership": True}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO custody VALUES(?,?,?,?,?,?,?)", (
                body["event_id"], object_id, from_entity, to_entity, evidence_sha256,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, actor=actor, signature=sig)

class AttributionMethodology:
    @staticmethod
    def receipt(object_id: str, evaluator: str, methodology: str, version: str,
                allocations_bps: dict[str, int], *, confidence_bps: int, evidence_refs=None) -> dict:
        total = sum(int(v) for v in allocations_bps.values())
        if total > 10000 or any(int(v) < 0 for v in allocations_bps.values()):
            raise ValueError("invalid attribution allocation")
        return {"schema": "entity-v3-attribution-methodology-v1", "object_id": object_id,
                "evaluator": evaluator, "methodology": methodology, "methodology_version": version,
                "allocations_bps": dict(sorted(allocations_bps.items())),
                "confidence_bps": max(0, min(10000, int(confidence_bps))),
                "evidence_refs": sorted(evidence_refs or []),
                "methodology_is_not_universal_truth": True}

class SettlementAdapterRegistry:
    KINDS = {"FIAT_BANK", "INTERNAL_ACCOUNTING", "CREDIT", "TOKEN", "INVOICE",
             "GOVERNMENT_RAIL", "ZERO_VALUE"}
    def __init__(self): self.adapters = {}
    def register(self, name: str, kind: str, capabilities: list[str]) -> dict:
        kind = kind.upper()
        if kind not in self.KINDS: raise ValueError("unsupported settlement adapter kind")
        self.adapters[name] = {"name": name, "kind": kind,
                               "capabilities": sorted(set(capabilities))}
        return dict(self.adapters[name])
    def route(self, kind: str) -> list[dict]:
        kind = kind.upper()
        return [dict(v) for v in self.adapters.values() if v["kind"] == kind]

class AdmissionController:
    """Reputation-neutral fixed-window resource quota."""
    def __init__(self, limit: int, window_ms: int):
        self.limit, self.window_ms, self.counters = max(1, int(limit)), max(1, int(window_ms)), {}
    def admit(self, subject: str, *, cost=1, at_ms=None) -> dict:
        at, cost = int(at_ms or now_ms()), max(1, int(cost))
        bucket = at // self.window_ms; key = (subject, bucket)
        used = self.counters.get(key, 0)
        allowed = used + cost <= self.limit
        if allowed: self.counters[key] = used + cost
        return {"subject": subject, "allowed": allowed, "used": self.counters.get(key, used),
                "limit": self.limit, "window_id": bucket, "reputation_used": False}

class DegradationStateMachine:
    RULES = {
        "NORMAL": {"VERIFY", "WRITE", "RESOLVE", "SETTLE", "TRADE"},
        "OFFLINE_VERIFY": {"VERIFY"},
        "STALE_READ": {"VERIFY", "RESOLVE"},
        "READ_ONLY": {"VERIFY", "RESOLVE"},
        "RECOVERY": {"VERIFY", "RECOVER"},
    }
    def __init__(self): self.state = "NORMAL"
    def transition(self, state: str) -> dict:
        state = state.upper()
        if state not in self.RULES: raise ValueError("invalid degradation state")
        self.state = state
        return {"state": state, "allowed_operations": sorted(self.RULES[state])}

    def permits(self, operation: str) -> bool:
        return operation.upper() in self.RULES[self.state]

class MerkleBatcher:
    @staticmethod
    def leaf(value: Any) -> bytes: return hashlib.sha256(canon(value)).digest()
    @classmethod
    def root(cls, values: list[Any]) -> str:
        nodes = [cls.leaf(v) for v in values]
        if not nodes: return hashlib.sha256(b"").hexdigest()
        while len(nodes) > 1:
            if len(nodes) % 2: nodes.append(nodes[-1])
            nodes = [hashlib.sha256(nodes[i] + nodes[i+1]).digest() for i in range(0, len(nodes), 2)]
        return nodes[0].hex()
    @classmethod
    def proof(cls, values: list[Any], index: int) -> dict:
        if index < 0 or index >= len(values): raise IndexError(index)
        nodes = [cls.leaf(v) for v in values]; idx = index; siblings = []
        while len(nodes) > 1:
            if len(nodes) % 2: nodes.append(nodes[-1])
            sib = idx - 1 if idx % 2 else idx + 1
            siblings.append({"side": "LEFT" if idx % 2 else "RIGHT", "hash": nodes[sib].hex()})
            nodes = [hashlib.sha256(nodes[i] + nodes[i+1]).digest() for i in range(0, len(nodes), 2)]
            idx //= 2
        return {"index": index, "leaf": cls.leaf(values[index]).hex(),
                "siblings": siblings, "root": nodes[0].hex()}
    @staticmethod
    def verify(proof: dict) -> bool:
        node = bytes.fromhex(proof["leaf"])
        for s in proof["siblings"]:
            other = bytes.fromhex(s["hash"])
            node = hashlib.sha256((other + node) if s["side"] == "LEFT" else (node + other)).digest()
        return node.hex() == proof["root"]

class LegacyBridgeRegistry:
    """Explicit mappings from legacy systems; mapping is evidence, never silent authority transfer."""
    SUPPORTED = {"OAUTH", "OIDC", "X509", "DID_VC", "DNS", "C2PA", "ERP", "PKI", "SUPPLY_CHAIN", "DATABASE"}
    @staticmethod
    def map(external_system: str, external_id: str, entity_ref: str, *,
            evidence_sha256: str, verifier: str | None = None) -> dict:
        system = external_system.upper()
        if system not in LegacyBridgeRegistry.SUPPORTED: raise ValueError("unsupported legacy bridge")
        return {"schema": "entity-v3-legacy-bridge-v1", "external_system": system,
                "external_id": external_id, "entity_ref": entity_ref,
                "evidence_sha256": evidence_sha256, "verifier": verifier,
                "legacy_identifier_is_not_entity_authority": True}