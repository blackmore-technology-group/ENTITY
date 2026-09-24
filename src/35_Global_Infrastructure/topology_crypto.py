from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import hashlib, json, secrets, sqlite3, time

TOPOLOGY_CLASSES = {"CORE", "REGIONAL", "EDGE", "SATELLITE", "OFFLINE"}

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

def _clock(value: dict[str, int]) -> dict[str, int]:
    out = {str(k): int(v) for k, v in value.items()}
    if any(v < 0 for v in out.values()):
        raise ValueError("vector clock values must be non-negative")
    return dict(sorted(out.items()))

class TopologyRegistry:
    """Signed infrastructure-node descriptors. Topology membership never grants sovereign authority."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_topology.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS nodes(
                node_id TEXT PRIMARY KEY, operator_entity_id TEXT NOT NULL,
                topology_class TEXT NOT NULL, jurisdiction TEXT NOT NULL,
                trust_domain TEXT NOT NULL, capabilities_json TEXT NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL)""")

    def register_node(self, operator: str, node_id: str, topology_class: str,
                      jurisdiction: str, trust_domain: str, capabilities: list[str]) -> dict:
        topology_class = topology_class.upper()
        if topology_class not in TOPOLOGY_CLASSES:
            raise ValueError("unsupported topology class")
        caps = sorted({str(x).upper() for x in capabilities})
        if not node_id or not trust_domain:
            raise ValueError("node_id and trust_domain required")
        body = {"schema": "entity-v3-topology-node-v1", "node_id": str(node_id),
                "operator_entity_id": operator, "topology_class": topology_class,
                "jurisdiction": str(jurisdiction).upper(), "trust_domain": str(trust_domain),
                "capabilities": caps, "status": "ACTIVE", "created_at_ms": now_ms(),
                "infrastructure_membership_is_not_sovereign_authority": True}
        sig = self.identity.sign(operator, body)
        with sqlite3.connect(self.path) as db:
            old = db.execute("SELECT operator_entity_id,topology_class,jurisdiction,trust_domain,capabilities_json FROM nodes WHERE node_id=?",
                             (node_id,)).fetchone()
            if old:
                existing = (old[0], old[1], old[2], old[3], json.loads(old[4]))
                desired = (operator, topology_class, body["jurisdiction"], str(trust_domain), caps)
                if existing != desired:
                    raise ValueError("immutable node registration changed")
                return dict(body, signature=sig, existing=True)
            db.execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)", (
                str(node_id), operator, topology_class, body["jurisdiction"], str(trust_domain),
                json.dumps(caps), "ACTIVE", body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig, existing=False)

class PartitionSync:
    """Signed causal checkpoints with fail-closed merge semantics for partitioned networks."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_partition_sync.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS checkpoints(
                checkpoint_id TEXT PRIMARY KEY, node_id TEXT NOT NULL,
                operator_entity_id TEXT NOT NULL, partition_id TEXT NOT NULL,
                sequence INTEGER NOT NULL, epoch INTEGER NOT NULL,
                previous_checkpoint_sha256 TEXT, state_root_sha256 TEXT NOT NULL,
                vector_clock_json TEXT NOT NULL, checkpoint_sha256 TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
                UNIQUE(node_id,partition_id,sequence))""")
            db.execute("""CREATE TABLE IF NOT EXISTS conflicts(
                conflict_id TEXT PRIMARY KEY, partition_id TEXT NOT NULL,
                checkpoint_ids_json TEXT NOT NULL, reason TEXT NOT NULL,
                detected_at_ms INTEGER NOT NULL)""")

    @staticmethod
    def dominates(left: dict[str, int], right: dict[str, int]) -> bool:
        keys = set(left) | set(right)
        ge = all(int(left.get(k, 0)) >= int(right.get(k, 0)) for k in keys)
        gt = any(int(left.get(k, 0)) > int(right.get(k, 0)) for k in keys)
        return ge and gt

    def publish(self, node_id: str, operator: str, partition_id: str, *,
                sequence: int, epoch: int, state_root_sha256: str,
                vector_clock: dict[str, int], previous_checkpoint_sha256: str | None = None) -> dict:
        state_root_sha256 = sha256_hex(state_root_sha256)
        clock = _clock(vector_clock)
        sequence = int(sequence); epoch = int(epoch)
        if sequence < 1 or epoch < 0:
            raise ValueError("invalid checkpoint sequence/epoch")
        if clock.get(node_id) != sequence:
            raise ValueError("node vector-clock component must equal checkpoint sequence")
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            last = db.execute("SELECT * FROM checkpoints WHERE node_id=? AND partition_id=? ORDER BY sequence DESC LIMIT 1",
                              (node_id, partition_id)).fetchone()
            if last:
                if sequence != int(last["sequence"]) + 1:
                    raise ValueError("checkpoint sequence must increase by one")
                if previous_checkpoint_sha256 != last["checkpoint_sha256"]:
                    raise ValueError("checkpoint chain mismatch")
            elif sequence != 1 or previous_checkpoint_sha256 is not None:
                raise ValueError("first checkpoint must be sequence 1 without previous hash")
        body = {"schema": "entity-v3-partition-checkpoint-v1", "checkpoint_id": rid("checkpoint3"),
                "node_id": node_id, "operator_entity_id": operator, "partition_id": partition_id,
                "sequence": sequence, "epoch": epoch,
                "previous_checkpoint_sha256": previous_checkpoint_sha256,
                "state_root_sha256": state_root_sha256, "vector_clock": clock,
                "created_at_ms": now_ms()}
        checkpoint_hash = digest(body)
        sig = self.identity.sign(operator, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
                body["checkpoint_id"], node_id, operator, partition_id, sequence, epoch,
                previous_checkpoint_sha256, state_root_sha256, json.dumps(clock, sort_keys=True),
                checkpoint_hash, body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, checkpoint_sha256=checkpoint_hash, signature=sig)

    def _latest(self, partition_id: str) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""SELECT c.* FROM checkpoints c JOIN (
                SELECT node_id,partition_id,MAX(sequence) AS max_seq FROM checkpoints
                WHERE partition_id=? GROUP BY node_id,partition_id
            ) x ON c.node_id=x.node_id AND c.partition_id=x.partition_id AND c.sequence=x.max_seq
            ORDER BY c.node_id""", (partition_id,)).fetchall()
        out = []
        for row in rows:
            item = dict(row); item["vector_clock"] = json.loads(item.pop("vector_clock_json"))
            item["signature"] = json.loads(item.pop("signature_json")); out.append(item)
        return out

    def merge(self, partition_id: str) -> dict:
        latest = self._latest(partition_id)
        if not latest:
            return {"partition_id": partition_id, "resolved": False, "reason": "NO_CHECKPOINTS"}
        roots = {x["state_root_sha256"] for x in latest}
        if len(roots) == 1:
            chosen = max(latest, key=lambda x: (x["epoch"], x["sequence"], x["checkpoint_id"]))
            return {"partition_id": partition_id, "resolved": True,
                    "reason": "CONVERGED_STATE", "state_root_sha256": chosen["state_root_sha256"],
                    "checkpoint_ids": sorted(x["checkpoint_id"] for x in latest),
                    "partition_conflict": False}
        dominant = []
        for candidate in latest:
            others = [x for x in latest if x["checkpoint_id"] != candidate["checkpoint_id"]]
            if all(self.dominates(candidate["vector_clock"], x["vector_clock"]) for x in others):
                dominant.append(candidate)
        if len(dominant) == 1:
            chosen = dominant[0]
            return {"partition_id": partition_id, "resolved": True,
                    "reason": "CAUSALLY_DOMINANT_CHECKPOINT",
                    "state_root_sha256": chosen["state_root_sha256"],
                    "checkpoint_id": chosen["checkpoint_id"], "partition_conflict": False}
        conflict_ids = sorted(x["checkpoint_id"] for x in latest)
        conflict_id = "partitionconflict3-" + digest({"partition": partition_id, "ids": conflict_ids})[:24]
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR IGNORE INTO conflicts VALUES(?,?,?,?,?)", (
                conflict_id, partition_id, json.dumps(conflict_ids), "CONCURRENT_DIVERGENT_STATE", now_ms()))
        return {"partition_id": partition_id, "resolved": False,
                "reason": "CONCURRENT_DIVERGENT_STATE", "conflict_id": conflict_id,
                "checkpoint_ids": conflict_ids, "partition_conflict": True,
                "automatic_last_writer_wins_prohibited": True}

class OfflineEnvelope:
    """Signed, expiry-bounded payload envelope for disconnected/edge operation."""
    @staticmethod
    def create(identity, actor: str, node_id: str, partition_id: str, sequence: int,
               payload: Any, *, expires_at_ms: int) -> dict:
        payload_sha = digest(payload)
        body = {"schema": "entity-v3-offline-envelope-v1", "envelope_id": rid("offline3"),
                "actor_entity_id": actor, "node_id": node_id, "partition_id": partition_id,
                "sequence": int(sequence), "payload_sha256": payload_sha,
                "created_at_ms": now_ms(), "expires_at_ms": int(expires_at_ms)}
        if body["expires_at_ms"] <= body["created_at_ms"]:
            raise ValueError("offline envelope expiry must be in the future")
        sig = identity.sign(actor, body)
        return dict(body, payload=payload, signature=sig)

    @staticmethod
    def verify(identity, envelope: dict, *, at_ms: int | None = None) -> dict:
        at = int(at_ms or now_ms())
        body = {k: envelope[k] for k in (
            "schema", "envelope_id", "actor_entity_id", "node_id", "partition_id",
            "sequence", "payload_sha256", "created_at_ms", "expires_at_ms")}
        if body["schema"] != "entity-v3-offline-envelope-v1":
            return {"valid": False, "reason": "SCHEMA"}
        if digest(envelope.get("payload")) != body["payload_sha256"]:
            return {"valid": False, "reason": "PAYLOAD_HASH"}
        if at > int(body["expires_at_ms"]):
            return {"valid": False, "reason": "EXPIRED"}
        manifest = identity.load_manifest(body["actor_entity_id"])
        if not identity.verify_signature(manifest, body, dict(envelope.get("signature") or {})):
            return {"valid": False, "reason": "SIGNATURE"}
        return {"valid": True, "reason": "OK", "partition_id": body["partition_id"],
                "sequence": int(body["sequence"]), "offline_evidence_is_not_automatic_merge_authority": True}

class CryptoSuiteMigration:
    """Algorithm-agility policy with explicit dual-sign transition and downgrade resistance."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_crypto_migration.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        self._verifiers: dict[str, Callable[[bytes, Any], bool]] = {}
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS suites(
                suite_id TEXT PRIMARY KEY, governance_entity_id TEXT NOT NULL,
                algorithm TEXT NOT NULL, security_bits INTEGER NOT NULL,
                verifier_sha256 TEXT NOT NULL, not_before_ms INTEGER NOT NULL,
                deprecate_at_ms INTEGER, retire_at_ms INTEGER,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS transitions(
                transition_id TEXT PRIMARY KEY, governance_entity_id TEXT NOT NULL,
                old_suite_id TEXT NOT NULL, new_suite_id TEXT NOT NULL,
                dual_sign_from_ms INTEGER NOT NULL, old_retire_at_ms INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def register_suite(self, governance_entity: str, suite_id: str, algorithm: str,
                       security_bits: int, verifier_sha256: str, *, not_before_ms: int,
                       deprecate_at_ms: int | None = None, retire_at_ms: int | None = None) -> dict:
        suite_id = suite_id.upper(); verifier_sha256 = sha256_hex(verifier_sha256)
        security_bits = int(security_bits); start = int(not_before_ms)
        dep = None if deprecate_at_ms is None else int(deprecate_at_ms)
        ret = None if retire_at_ms is None else int(retire_at_ms)
        if security_bits < 64:
            raise ValueError("security_bits below policy floor")
        if dep is not None and dep <= start:
            raise ValueError("deprecation must follow activation")
        if ret is not None and (dep is None or ret <= dep):
            raise ValueError("retirement must follow deprecation")
        body = {"schema": "entity-v3-crypto-suite-v1", "suite_id": suite_id,
                "governance_entity_id": governance_entity, "algorithm": str(algorithm),
                "security_bits": security_bits, "verifier_sha256": verifier_sha256,
                "not_before_ms": start, "deprecate_at_ms": dep, "retire_at_ms": ret,
                "status": "ACTIVE", "created_at_ms": now_ms()}
        sig = self.identity.sign(governance_entity, body)
        with sqlite3.connect(self.path) as db:
            old = db.execute("SELECT algorithm,security_bits,verifier_sha256,not_before_ms,deprecate_at_ms,retire_at_ms FROM suites WHERE suite_id=?",
                             (suite_id,)).fetchone()
            expected = (str(algorithm), security_bits, verifier_sha256, start, dep, ret)
            if old:
                if tuple(old) != expected:
                    raise ValueError("immutable crypto suite definition changed")
                return dict(body, signature=sig, existing=True)
            db.execute("INSERT INTO suites VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                suite_id, governance_entity, str(algorithm), security_bits, verifier_sha256,
                start, dep, ret, "ACTIVE", body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig, existing=False)

    def bind_verifier(self, suite_id: str, verifier_sha256: str,
                      callback: Callable[[bytes, Any], bool]) -> None:
        suite_id = suite_id.upper(); verifier_sha256 = sha256_hex(verifier_sha256)
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT verifier_sha256 FROM suites WHERE suite_id=?", (suite_id,)).fetchone()
        if not row or row[0] != verifier_sha256:
            raise PermissionError("crypto verifier hash mismatch")
        self._verifiers[suite_id] = callback

    def register_transition(self, governance_entity: str, old_suite_id: str, new_suite_id: str,
                            *, dual_sign_from_ms: int, old_retire_at_ms: int) -> dict:
        old_suite_id, new_suite_id = old_suite_id.upper(), new_suite_id.upper()
        if old_suite_id == new_suite_id:
            raise ValueError("crypto transition requires distinct suites")
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT suite_id FROM suites WHERE suite_id IN (?,?)",
                              (old_suite_id, new_suite_id)).fetchall()
        if {r[0] for r in rows} != {old_suite_id, new_suite_id}:
            raise KeyError("crypto transition suite missing")
        start, retire = int(dual_sign_from_ms), int(old_retire_at_ms)
        if retire <= start:
            raise ValueError("retirement must follow dual-sign transition")
        transition_id = "cryptotransition3-" + digest({"old": old_suite_id, "new": new_suite_id,
                                                       "start": start, "retire": retire})[:24]
        body = {"schema": "entity-v3-crypto-transition-v1", "transition_id": transition_id,
                "governance_entity_id": governance_entity, "old_suite_id": old_suite_id,
                "new_suite_id": new_suite_id, "dual_sign_from_ms": start,
                "old_retire_at_ms": retire, "created_at_ms": now_ms(),
                "downgrade_after_transition_prohibited": True}
        sig = self.identity.sign(governance_entity, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO transitions VALUES(?,?,?,?,?,?,?,?)", (
                transition_id, governance_entity, old_suite_id, new_suite_id, start,
                retire, body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def suite_state(self, suite_id: str, *, at_ms: int | None = None) -> str:
        at = int(at_ms or now_ms()); suite_id = suite_id.upper()
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT not_before_ms,deprecate_at_ms,retire_at_ms FROM suites WHERE suite_id=?",
                             (suite_id,)).fetchone()
        if not row:
            raise KeyError("crypto suite missing")
        start, dep, ret = int(row[0]), row[1], row[2]
        if at < start:
            return "NOT_YET_ACTIVE"
        if ret is not None and at >= int(ret):
            return "RETIRED"
        if dep is not None and at >= int(dep):
            return "DEPRECATED"
        return "ACTIVE"

    def required_suites(self, old_suite_id: str, new_suite_id: str, *, at_ms: int) -> list[str]:
        old_suite_id, new_suite_id = old_suite_id.upper(), new_suite_id.upper()
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT dual_sign_from_ms,old_retire_at_ms FROM transitions WHERE old_suite_id=? AND new_suite_id=? ORDER BY created_at_ms DESC LIMIT 1",
                             (old_suite_id, new_suite_id)).fetchone()
        if not row:
            raise KeyError("crypto transition missing")
        start, retire = int(row[0]), int(row[1])
        at = int(at_ms)
        if at < start:
            return [old_suite_id]
        if at < retire:
            return [old_suite_id, new_suite_id]
        return [new_suite_id]

    def verify_transition_payload(self, payload: Any, signatures: dict[str, bytes],
                                  old_suite_id: str, new_suite_id: str, *, at_ms: int) -> dict:
        required = self.required_suites(old_suite_id, new_suite_id, at_ms=at_ms)
        supplied = {str(k).upper(): bytes(v) for k, v in signatures.items()}
        missing = [suite for suite in required if suite not in supplied]
        if missing:
            return {"valid": False, "reason": "MISSING_REQUIRED_SUITE", "missing": missing,
                    "required_suites": required, "downgrade_rejected": True}
        raw = canon(payload)
        for suite in required:
            if self.suite_state(suite, at_ms=at_ms) == "RETIRED":
                return {"valid": False, "reason": "RETIRED_SUITE_REQUIRED_BY_STALE_POLICY",
                        "suite_id": suite, "required_suites": required}
            verifier = self._verifiers.get(suite)
            if verifier is None:
                return {"valid": False, "reason": "VERIFIER_UNAVAILABLE", "suite_id": suite,
                        "required_suites": required}
            if not bool(verifier(supplied[suite], raw)):
                return {"valid": False, "reason": "SIGNATURE_INVALID", "suite_id": suite,
                        "required_suites": required}
        return {"valid": True, "reason": "OK", "required_suites": required,
                "verified_suites": required, "downgrade_resistance": True}
