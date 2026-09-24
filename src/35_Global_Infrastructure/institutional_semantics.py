from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

REGISTRY_KINDS = {
    "SCHEMA", "RIGHT", "EVENT", "CAPABILITY", "ASSET_CLASS",
    "TRUST_FRAMEWORK", "DISPUTE_AUTHORITY", "ATTESTATION_CLASS",
}
MAPPING_RELATIONS = {"EXACT", "BROADER", "NARROWER", "RELATED", "INCOMPATIBLE"}
RULE_EFFECTS = {"ALLOW", "REQUIRE", "PROHIBIT"}

def now_ms() -> int:
    return int(time.time() * 1000)

def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def digest(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon(value)
    return hashlib.sha256(raw).hexdigest()

def rid(prefix: str) -> str:
    return prefix + "-" + secrets.token_hex(12)

def _sha256(value: str) -> str:
    value = str(value).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("expected lowercase SHA-256")
    return value

class JurisdictionProfileRegistry:
    """Immutable jurisdiction/domain overlays. Profiles are policy evidence, not legal truth."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_jurisdiction_profiles.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS profiles(
                profile_id TEXT PRIMARY KEY, jurisdiction_code TEXT NOT NULL,
                domain TEXT NOT NULL, version TEXT NOT NULL, authority_entity_id TEXT NOT NULL,
                schema_sha256 TEXT NOT NULL, rules_json TEXT NOT NULL,
                effective_from_ms INTEGER NOT NULL, effective_to_ms INTEGER,
                precedence INTEGER NOT NULL, parent_profile_id TEXT,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL,
                UNIQUE(jurisdiction_code,domain,version))""")
            db.execute("""CREATE TABLE IF NOT EXISTS supersessions(
                old_profile_id TEXT PRIMARY KEY, new_profile_id TEXT NOT NULL,
                actor_entity_id TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL)""")

    @staticmethod
    def _validate_rules(rules: list[dict]) -> list[dict]:
        out = []
        for rule in rules:
            effect = str(rule.get("effect") or "").upper()
            if effect not in RULE_EFFECTS:
                raise ValueError("invalid jurisdiction rule effect")
            actions = sorted({str(a).upper() for a in (rule.get("actions") or [])})
            if not actions:
                raise ValueError("jurisdiction rule actions required")
            out.append({
                "effect": effect,
                "actions": actions,
                "conditions": dict(rule.get("conditions") or {}),
                "obligations": sorted({str(x) for x in (rule.get("obligations") or [])}),
                "authority_basis": rule.get("authority_basis"),
            })
        return out

    def register(self, authority: str, jurisdiction_code: str, domain: str, version: str,
                 schema_sha256: str, rules: list[dict], *, effective_from_ms: int,
                 effective_to_ms: int | None = None, precedence: int = 100,
                 parent_profile_id: str | None = None) -> dict:
        jurisdiction_code = str(jurisdiction_code).strip().upper()
        domain = str(domain).strip().upper()
        version = str(version).strip()
        if not jurisdiction_code or not domain or not version:
            raise ValueError("jurisdiction, domain and version required")
        schema_sha256 = _sha256(schema_sha256)
        normalized_rules = self._validate_rules(rules)
        start = int(effective_from_ms)
        end = None if effective_to_ms is None else int(effective_to_ms)
        if end is not None and end <= start:
            raise ValueError("effective_to_ms must follow effective_from_ms")
        self.identity.load_manifest(authority)
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            if parent_profile_id and not db.execute(
                "SELECT 1 FROM profiles WHERE profile_id=?", (parent_profile_id,)
            ).fetchone():
                raise ValueError("parent jurisdiction profile missing")
            old = db.execute(
                "SELECT * FROM profiles WHERE jurisdiction_code=? AND domain=? AND version=?",
                (jurisdiction_code, domain, version),
            ).fetchone()
            if old:
                expected = digest(normalized_rules)
                if old["schema_sha256"] != schema_sha256 or digest(json.loads(old["rules_json"])) != expected:
                    raise ValueError("immutable jurisdiction profile version changed")
                return dict(old)
        profile_id = "jprof3-" + digest({
            "jurisdiction": jurisdiction_code, "domain": domain, "version": version,
            "schema": schema_sha256, "rules": normalized_rules,
        })[:24]
        body = {
            "schema": "entity-v3-jurisdiction-profile-v1", "profile_id": profile_id,
            "jurisdiction_code": jurisdiction_code, "domain": domain, "version": version,
            "authority_entity_id": authority, "schema_sha256": schema_sha256,
            "rules": normalized_rules, "effective_from_ms": start, "effective_to_ms": end,
            "precedence": int(precedence), "parent_profile_id": parent_profile_id,
            "status": "ACTIVE", "created_at_ms": now_ms(),
            "legal_effect_is_deployment_specific": True,
        }
        sig = self.identity.sign(authority, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                profile_id, jurisdiction_code, domain, version, authority, schema_sha256,
                json.dumps(normalized_rules, sort_keys=True), start, end, int(precedence),
                parent_profile_id, "ACTIVE", body["created_at_ms"], json.dumps(sig, sort_keys=True),
            ))
        return dict(body, signature=sig)

    def supersede(self, actor: str, old_profile_id: str, new_profile_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            old = db.execute("SELECT * FROM profiles WHERE profile_id=?", (old_profile_id,)).fetchone()
            new = db.execute("SELECT * FROM profiles WHERE profile_id=?", (new_profile_id,)).fetchone()
            if not old or not new:
                raise KeyError("jurisdiction profile missing")
            if old["jurisdiction_code"] != new["jurisdiction_code"] or old["domain"] != new["domain"]:
                raise ValueError("supersession must stay within jurisdiction/domain")
        body = {"schema": "entity-v3-jurisdiction-supersession-v1",
                "old_profile_id": old_profile_id, "new_profile_id": new_profile_id,
                "actor_entity_id": actor, "created_at_ms": now_ms(),
                "history_rewrite_prohibited": True}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO supersessions VALUES(?,?,?,?,?)", (
                old_profile_id, new_profile_id, actor, body["created_at_ms"], json.dumps(sig, sort_keys=True)))
            db.execute("UPDATE profiles SET status='SUPERSEDED' WHERE profile_id=?", (old_profile_id,))
        return dict(body, signature=sig)

    def applicable(self, jurisdictions: list[str], domain: str, *, at_ms: int | None = None) -> list[dict]:
        at = int(at_ms or now_ms())
        codes = sorted({str(x).upper() for x in jurisdictions})
        domain = str(domain).upper()
        if not codes:
            return []
        placeholders = ",".join("?" for _ in codes)
        sql = (f"SELECT * FROM profiles WHERE jurisdiction_code IN ({placeholders}) AND domain=? "
               "AND status='ACTIVE' AND effective_from_ms<=? "
               "AND (effective_to_ms IS NULL OR effective_to_ms>=?) "
               "ORDER BY precedence DESC,jurisdiction_code,version")
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(sql, (*codes, domain, at, at)).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["rules"] = json.loads(item.pop("rules_json"))
            item["signature"] = json.loads(item.pop("signature_json"))
            out.append(item)
        return out

    def evaluate(self, jurisdictions: list[str], domain: str, action: str,
                 context: dict | None = None, *, at_ms: int | None = None) -> dict:
        action = str(action).upper()
        context = dict(context or {})
        profiles = self.applicable(jurisdictions, domain, at_ms=at_ms)
        matched = []
        for profile in profiles:
            for rule in profile["rules"]:
                if action not in rule["actions"]:
                    continue
                if any(context.get(k) != v for k, v in rule["conditions"].items()):
                    continue
                matched.append({"profile_id": profile["profile_id"],
                                "jurisdiction": profile["jurisdiction_code"], **rule})
        effects = {m["effect"] for m in matched}
        conflict = "PROHIBIT" in effects and ("ALLOW" in effects or "REQUIRE" in effects)
        if "PROHIBIT" in effects:
            decision = "DENY"
        elif "REQUIRE" in effects:
            decision = "CONDITIONAL"
        elif "ALLOW" in effects:
            decision = "ALLOW"
        else:
            decision = "DENY"
        obligations = sorted({o for m in matched for o in m.get("obligations", [])})
        return {
            "domain": str(domain).upper(), "action": action, "decision": decision,
            "jurisdictions": sorted({str(x).upper() for x in jurisdictions}),
            "matched_rules": matched, "obligations": obligations,
            "conflict_detected": conflict, "fail_closed": decision == "DENY",
            "profile_count": len(profiles), "legal_determination_not_made": True,
        }

class SemanticRegistry:
    """Versioned semantic terms and explicit crosswalks; no silent semantic equivalence."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_semantic_registry.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS namespaces(
                namespace_id TEXT PRIMARY KEY, owner_entity_id TEXT NOT NULL,
                description TEXT NOT NULL, governance_ref TEXT,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS terms(
                namespace_id TEXT NOT NULL, kind TEXT NOT NULL, term_id TEXT NOT NULL,
                version TEXT NOT NULL, definition_sha256 TEXT NOT NULL,
                definition_json TEXT NOT NULL, status TEXT NOT NULL,
                supersedes_ref TEXT, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL,
                PRIMARY KEY(namespace_id,kind,term_id,version))""")
            db.execute("""CREATE TABLE IF NOT EXISTS crosswalks(
                crosswalk_id TEXT PRIMARY KEY, actor_entity_id TEXT NOT NULL,
                source_ref TEXT NOT NULL, target_ref TEXT NOT NULL,
                relation TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                jurisdiction_scope_json TEXT NOT NULL, confidence_bps INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")

    def register_namespace(self, owner: str, namespace_id: str, description: str,
                           governance_ref: str | None = None) -> dict:
        namespace_id = str(namespace_id).strip().lower()
        if not namespace_id or len(namespace_id) > 128:
            raise ValueError("invalid namespace_id")
        self.identity.load_manifest(owner)
        body = {"schema": "entity-v3-semantic-namespace-v1", "namespace_id": namespace_id,
                "owner_entity_id": owner, "description": str(description).strip(),
                "governance_ref": governance_ref, "created_at_ms": now_ms()}
        sig = self.identity.sign(owner, body)
        with sqlite3.connect(self.path) as db:
            old = db.execute("SELECT owner_entity_id FROM namespaces WHERE namespace_id=?",
                             (namespace_id,)).fetchone()
            if old:
                if old[0] != owner:
                    raise PermissionError("namespace already owned")
                return dict(body, signature=sig, existing=True)
            db.execute("INSERT INTO namespaces VALUES(?,?,?,?,?,?)", (
                namespace_id, owner, body["description"], governance_ref,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig, existing=False)

    def register_term(self, owner: str, namespace_id: str, kind: str, term_id: str,
                      version: str, definition: dict, *, supersedes_ref: str | None = None) -> dict:
        namespace_id, kind = namespace_id.lower(), kind.upper()
        if kind not in REGISTRY_KINDS:
            raise ValueError("unsupported semantic registry kind")
        term_id, version = str(term_id).strip(), str(version).strip()
        if not term_id or not version:
            raise ValueError("term_id and version required")
        with sqlite3.connect(self.path) as db:
            ns = db.execute("SELECT owner_entity_id FROM namespaces WHERE namespace_id=?",
                            (namespace_id,)).fetchone()
            if not ns:
                raise KeyError("semantic namespace missing")
            if ns[0] != owner:
                raise PermissionError("only namespace owner may register term")
            old = db.execute("SELECT definition_sha256 FROM terms WHERE namespace_id=? AND kind=? AND term_id=? AND version=?",
                             (namespace_id, kind, term_id, version)).fetchone()
            definition_hash = digest(definition)
            if old:
                if old[0] != definition_hash:
                    raise ValueError("immutable semantic term version changed")
                return {"namespace_id": namespace_id, "kind": kind, "term_id": term_id,
                        "version": version, "definition_sha256": definition_hash, "existing": True}
        body = {"schema": "entity-v3-semantic-term-v1", "namespace_id": namespace_id,
                "kind": kind, "term_id": term_id, "version": version,
                "definition_sha256": definition_hash, "definition": dict(definition),
                "status": "ACTIVE", "supersedes_ref": supersedes_ref,
                "created_at_ms": now_ms()}
        sig = self.identity.sign(owner, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO terms VALUES(?,?,?,?,?,?,?,?,?,?)", (
                namespace_id, kind, term_id, version, definition_hash,
                json.dumps(definition, sort_keys=True), "ACTIVE", supersedes_ref,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig, existing=False)

    def term_ref(self, namespace_id: str, kind: str, term_id: str, version: str) -> str:
        return f"{namespace_id.lower()}:{kind.upper()}:{term_id}@{version}"

    def resolve(self, term_ref: str) -> dict:
        try:
            head, version = term_ref.rsplit("@", 1)
            namespace_id, kind, term_id = head.split(":", 2)
        except ValueError as exc:
            raise ValueError("invalid semantic term reference") from exc
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM terms WHERE namespace_id=? AND kind=? AND term_id=? AND version=?",
                             (namespace_id.lower(), kind.upper(), term_id, version)).fetchone()
        if not row:
            raise KeyError("semantic term not found")
        item = dict(row)
        item["definition"] = json.loads(item.pop("definition_json"))
        item["signature"] = json.loads(item.pop("signature_json"))
        item["term_ref"] = self.term_ref(namespace_id, kind, term_id, version)
        return item

    def map_terms(self, actor: str, source_ref: str, target_ref: str, relation: str,
                  evidence_sha256: str, *, jurisdiction_scope: list[str] | None = None,
                  confidence_bps: int = 10000) -> dict:
        relation = relation.upper()
        if relation not in MAPPING_RELATIONS:
            raise ValueError("invalid semantic mapping relation")
        self.resolve(source_ref); self.resolve(target_ref)
        confidence_bps = int(confidence_bps)
        if confidence_bps < 0 or confidence_bps > 10000:
            raise ValueError("invalid confidence_bps")
        evidence_sha256 = _sha256(evidence_sha256)
        body = {"schema": "entity-v3-semantic-crosswalk-v1", "crosswalk_id": rid("xwalk3"),
                "actor_entity_id": actor, "source_ref": source_ref, "target_ref": target_ref,
                "relation": relation, "evidence_sha256": evidence_sha256,
                "jurisdiction_scope": sorted({str(x).upper() for x in (jurisdiction_scope or [])}),
                "confidence_bps": confidence_bps, "created_at_ms": now_ms(),
                "mapping_is_attestation_not_identity": True,
                "silent_semantic_coercion_prohibited": True}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO crosswalks VALUES(?,?,?,?,?,?,?,?,?,?)", (
                body["crosswalk_id"], actor, source_ref, target_ref, relation,
                evidence_sha256, json.dumps(body["jurisdiction_scope"]), confidence_bps,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def mappings(self, source_ref: str, *, target_namespace: str | None = None) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM crosswalks WHERE source_ref=? ORDER BY created_at_ms,crosswalk_id",
                              (source_ref,)).fetchall()
        out = []
        for row in rows:
            if target_namespace and not row["target_ref"].startswith(target_namespace.lower() + ":"):
                continue
            item = dict(row)
            item["jurisdiction_scope"] = json.loads(item.pop("jurisdiction_scope_json"))
            item["signature"] = json.loads(item.pop("signature_json"))
            out.append(item)
        exact = [x for x in out if x["relation"] == "EXACT" and x["confidence_bps"] == 10000]
        return {"source_ref": source_ref, "mappings": out,
                "unambiguous_exact_candidate": exact[0]["target_ref"] if len(exact) == 1 else None,
                "automatic_translation_permitted": False,
                "profile_or_human_semantic_decision_required": True}

class MultiStakeholderGovernance:
    """Diversity-aware standards governance. BTG participation does not create unilateral standard authority."""
    def __init__(self, root: str | Path, identity):
        self.path = Path(root) / "entity_v3_multistakeholder_governance.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS bodies(
                body_id TEXT PRIMARY KEY, steward_entity_id TEXT NOT NULL, name TEXT NOT NULL,
                charter_sha256 TEXT NOT NULL, classes_json TEXT NOT NULL,
                approval_threshold INTEGER NOT NULL, min_approval_classes INTEGER NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS members(
                body_id TEXT NOT NULL, member_entity_id TEXT NOT NULL, stakeholder_class TEXT NOT NULL,
                status TEXT NOT NULL, admitted_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
                PRIMARY KEY(body_id,member_entity_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS proposals(
                proposal_id TEXT PRIMARY KEY, body_id TEXT NOT NULL, proposer_entity_id TEXT NOT NULL,
                change_class TEXT NOT NULL, target_ref TEXT NOT NULL, body_sha256 TEXT NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS ballots(
                proposal_id TEXT NOT NULL, voter_entity_id TEXT NOT NULL, stakeholder_class TEXT NOT NULL,
                decision TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
                PRIMARY KEY(proposal_id,voter_entity_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS conflicts(
                proposal_id TEXT NOT NULL, member_entity_id TEXT NOT NULL, recuse INTEGER NOT NULL,
                basis_sha256 TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
                PRIMARY KEY(proposal_id,member_entity_id))""")

    def create_body(self, steward: str, name: str, charter_sha256: str,
                    stakeholder_classes: list[str], *, approval_threshold: int,
                    min_approval_classes: int) -> dict:
        classes = sorted({str(x).upper() for x in stakeholder_classes})
        if len(classes) < 2:
            raise ValueError("at least two stakeholder classes required")
        approval_threshold = int(approval_threshold)
        min_approval_classes = int(min_approval_classes)
        if approval_threshold < 1 or min_approval_classes < 2 or min_approval_classes > len(classes):
            raise ValueError("invalid governance thresholds")
        charter_sha256 = _sha256(charter_sha256)
        self.identity.load_manifest(steward)
        body_id = "gov3-" + digest({"name": name, "charter": charter_sha256, "classes": classes})[:24]
        body = {"schema": "entity-v3-governance-body-v1", "body_id": body_id,
                "steward_entity_id": steward, "name": str(name), "charter_sha256": charter_sha256,
                "stakeholder_classes": classes, "approval_threshold": approval_threshold,
                "min_approval_classes": min_approval_classes, "status": "ACTIVE",
                "created_at_ms": now_ms(), "single_implementation_is_not_standard_authority": True}
        sig = self.identity.sign(steward, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO bodies VALUES(?,?,?,?,?,?,?,?,?,?)", (
                body_id, steward, str(name), charter_sha256, json.dumps(classes),
                approval_threshold, min_approval_classes, "ACTIVE", body["created_at_ms"],
                json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def add_member(self, body_id: str, steward: str, member: str, stakeholder_class: str) -> dict:
        stakeholder_class = stakeholder_class.upper()
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            body = db.execute("SELECT * FROM bodies WHERE body_id=? AND status='ACTIVE'", (body_id,)).fetchone()
        if not body:
            raise KeyError("governance body missing")
        if body["steward_entity_id"] != steward:
            raise PermissionError("only body steward may admit member")
        if stakeholder_class not in set(json.loads(body["classes_json"])):
            raise ValueError("stakeholder class not permitted")
        self.identity.load_manifest(member)
        record = {"schema": "entity-v3-governance-membership-v1", "body_id": body_id,
                  "member_entity_id": member, "stakeholder_class": stakeholder_class,
                  "status": "ACTIVE", "admitted_at_ms": now_ms()}
        sig = self.identity.sign(steward, record)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO members VALUES(?,?,?,?,?,?)", (
                body_id, member, stakeholder_class, "ACTIVE", record["admitted_at_ms"],
                json.dumps(sig, sort_keys=True)))
        return dict(record, steward_entity_id=steward, signature=sig)

    def propose(self, body_id: str, proposer: str, change_class: str,
                target_ref: str, document: Any) -> dict:
        change_class = change_class.upper()
        if change_class not in {"CORE", "PROFILE", "ONTOLOGY", "SCHEMA", "TEST", "GOVERNANCE"}:
            raise ValueError("unsupported change class")
        with sqlite3.connect(self.path) as db:
            member = db.execute("SELECT 1 FROM members WHERE body_id=? AND member_entity_id=? AND status='ACTIVE'",
                                (body_id, proposer)).fetchone()
        if not member:
            raise PermissionError("active governance membership required")
        body_hash = digest(document)
        proposal_id = "proposal3-" + digest({"body": body_id, "proposer": proposer,
                                            "target": target_ref, "sha": body_hash})[:24]
        record = {"schema": "entity-v3-multistakeholder-proposal-v1",
                  "proposal_id": proposal_id, "body_id": body_id,
                  "proposer_entity_id": proposer, "change_class": change_class,
                  "target_ref": str(target_ref), "body_sha256": body_hash,
                  "status": "OPEN", "created_at_ms": now_ms()}
        sig = self.identity.sign(proposer, record)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?)", (
                proposal_id, body_id, proposer, change_class, str(target_ref), body_hash,
                "OPEN", record["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(record, signature=sig)

    def declare_conflict(self, proposal_id: str, member: str, basis: Any, *, recuse: bool) -> dict:
        body = {"schema": "entity-v3-governance-conflict-v1", "proposal_id": proposal_id,
                "member_entity_id": member, "recuse": bool(recuse),
                "basis_sha256": digest(basis), "created_at_ms": now_ms()}
        sig = self.identity.sign(member, body)
        with sqlite3.connect(self.path) as db:
            if not db.execute("SELECT 1 FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone():
                raise KeyError("proposal missing")
            db.execute("INSERT OR REPLACE INTO conflicts VALUES(?,?,?,?,?,?)", (
                proposal_id, member, int(bool(recuse)), body["basis_sha256"],
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        return dict(body, signature=sig)

    def vote(self, proposal_id: str, voter: str, decision: str) -> dict:
        decision = decision.upper()
        if decision not in {"APPROVE", "REJECT", "ABSTAIN"}:
            raise ValueError("invalid governance decision")
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            proposal = db.execute("SELECT * FROM proposals WHERE proposal_id=? AND status='OPEN'", (proposal_id,)).fetchone()
            if not proposal:
                raise KeyError("open proposal missing")
            member = db.execute("SELECT * FROM members WHERE body_id=? AND member_entity_id=? AND status='ACTIVE'",
                                (proposal["body_id"], voter)).fetchone()
            if not member:
                raise PermissionError("active governance membership required")
            conflict = db.execute("SELECT recuse FROM conflicts WHERE proposal_id=? AND member_entity_id=?",
                                  (proposal_id, voter)).fetchone()
            if conflict and int(conflict[0]):
                raise PermissionError("member recused from proposal")
        body = {"schema": "entity-v3-governance-ballot-v1", "proposal_id": proposal_id,
                "voter_entity_id": voter, "stakeholder_class": member["stakeholder_class"],
                "decision": decision, "created_at_ms": now_ms()}
        sig = self.identity.sign(voter, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO ballots VALUES(?,?,?,?,?,?)", (
                proposal_id, voter, member["stakeholder_class"], decision,
                body["created_at_ms"], json.dumps(sig, sort_keys=True)))
        result = self.tally(proposal_id)
        return dict(body, signature=sig, proposal_status=result["status"])

    def tally(self, proposal_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            proposal = db.execute("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not proposal:
                raise KeyError("proposal missing")
            body = db.execute("SELECT * FROM bodies WHERE body_id=?", (proposal["body_id"],)).fetchone()
            ballots = db.execute("SELECT * FROM ballots WHERE proposal_id=?", (proposal_id,)).fetchall()
        approvals = [r for r in ballots if r["decision"] == "APPROVE"]
        rejects = [r for r in ballots if r["decision"] == "REJECT"]
        approval_classes = {r["stakeholder_class"] for r in approvals}
        threshold = int(body["approval_threshold"])
        min_classes = int(body["min_approval_classes"])
        if len(approvals) >= threshold and len(approval_classes) >= min_classes:
            status = "ACCEPTED"
        elif len(rejects) >= threshold:
            status = "REJECTED"
        else:
            status = "OPEN"
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE proposals SET status=? WHERE proposal_id=?", (status, proposal_id))
        return {
            "proposal_id": proposal_id, "status": status,
            "approvals": len(approvals), "rejects": len(rejects),
            "approval_classes": sorted(approval_classes),
            "approval_threshold": threshold, "min_approval_classes": min_classes,
            "diversity_requirement_met": len(approval_classes) >= min_classes,
            "single_stakeholder_class_cannot_unilaterally_adopt": min_classes > 1,
        }
