from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

EFFECTS = {"ALLOW", "REQUIRE", "PROHIBIT"}
PRIVACY_PROFILES = {
    "PUBLIC_PROVENANCE", "SELECTIVE_DISCLOSURE", "CONFIDENTIAL_PROVENANCE",
    "ZERO_KNOWLEDGE_QUALIFICATION", "PSEUDONYMOUS_RELATIONSHIP", "RESTRICTED_DISCLOSURE",
}
CORE_PRIMITIVES = ("ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE")

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

def normalize_rules(rules: list[dict]) -> list[dict]:
    out = []
    for raw in rules:
        effect = str(raw.get("effect") or "").upper()
        if effect not in EFFECTS:
            raise ValueError("invalid right rule effect")
        actions = sorted({str(x).upper() for x in (raw.get("actions") or [])})
        if not actions or any(not x for x in actions):
            raise ValueError("right rule requires actions")
        out.append({
            "effect": effect,
            "actions": actions,
            "conditions": dict(raw.get("conditions") or {}),
            "obligations": sorted({str(x) for x in (raw.get("obligations") or [])}),
            "right_refs": sorted({str(x) for x in (raw.get("right_refs") or [])}),
        })
    return sorted(out, key=lambda x: (x["effect"], x["actions"], canon(x["conditions"])))

def normalize_locator(locator: dict) -> dict:
    item = dict(locator)
    if item.get("provider_is_authority") is not False:
        raise ValueError("custody provider must not be declared authority")
    item["content_sha256"] = sha256_hex(item.get("content_sha256"), "content_sha256")
    if not str(item.get("provider") or "") or not str(item.get("locator") or ""):
        raise ValueError("custody locator requires provider and locator")
    if item.get("credentials_included") not in {False, None}:
        raise ValueError("rights passport must not embed provider credentials")
    item["credentials_included"] = False
    return dict(sorted(item.items()))

class RightsPassportRegistry:
    """Signed, immutable versions describing rights around an existing ENTITY object."""
    def __init__(self, root: str | Path, identity, fabric=None):
        self.path = Path(root) / "entity_v3_2_rights_passports.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        self.fabric = fabric
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS passports(
                passport_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, controller_entity_id TEXT NOT NULL,
                version TEXT NOT NULL, passport_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
                status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
                UNIQUE(object_id,version))""")
            db.execute("""CREATE TABLE IF NOT EXISTS supersessions(
                old_passport_id TEXT PRIMARY KEY, new_passport_id TEXT NOT NULL,
                actor_entity_id TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL)""")

    def issue(self, controller: str, object_id: str, rights: list[dict], *,
              version: str = "1.0", authority_refs: list[str] | None = None,
              jurisdiction_profile_refs: list[str] | None = None,
              semantic_refs: list[str] | None = None, custody: list[dict] | None = None,
              provenance_refs: list[str] | None = None, disclosure_refs: list[str] | None = None,
              privacy_profile: str = "SELECTIVE_DISCLOSURE",
              economic_terms: dict | None = None, legal_classification: dict | None = None) -> dict:
        self.identity.load_manifest(controller)
        if self.fabric is not None:
            obj = self.fabric.get_object(object_id)
            if obj["controller_entity_id"] != controller:
                raise PermissionError("object controller must issue rights passport")
        privacy_profile = str(privacy_profile).upper()
        if privacy_profile not in PRIVACY_PROFILES:
            raise ValueError("unsupported privacy profile")
        normalized_rights = normalize_rules(list(rights or []))
        if not normalized_rights:
            raise ValueError("rights passport requires at least one right rule")
        normalized_custody = [normalize_locator(x) for x in (custody or [])]
        legal = dict(legal_classification or {})
        if legal and legal.get("protocol_determines_legal_status") is not False:
            raise ValueError("legal classification must remain an external assertion")
        if legal:
            legal["protocol_determines_legal_status"] = False
        terms = dict(economic_terms or {})
        if terms.get("underlying_information_remains_nonrival") is False:
            raise ValueError("passport cannot declare information bytes economically scarce")
        terms["underlying_information_remains_nonrival"] = True
        terms["market_observation_is_not_accounting_fair_value"] = True
        body = {
            "schema": "entity-v3-rights-passport-v1",
            "passport_id": rid("passport3"),
            "object_id": str(object_id),
            "controller_entity_id": controller,
            "version": str(version),
            "core_primitives": list(CORE_PRIMITIVES),
            "authority_refs": sorted({str(x) for x in (authority_refs or [])}),
            "rights": normalized_rights,
            "jurisdiction_profile_refs": sorted({str(x) for x in (jurisdiction_profile_refs or [])}),
            "semantic_refs": sorted({str(x) for x in (semantic_refs or [])}),
            "custody": normalized_custody,
            "provenance_refs": sorted({str(x) for x in (provenance_refs or [])}),
            "disclosure_refs": sorted({str(x) for x in (disclosure_refs or [])}),
            "privacy_profile": privacy_profile,
            "economic_terms": terms,
            "legal_classification": legal,
            "status": "ACTIVE",
            "created_at_ms": now_ms(),
            "provider_custody_is_not_authority": True,
            "underlying_data_not_silently_transferred": True,
            "legal_effect_is_deployment_specific": True,
        }
        passport_hash = digest(body)
        sig = self.identity.sign(controller, body)
        try:
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT INTO passports VALUES(?,?,?,?,?,?,?,?,?)", (
                    body["passport_id"], body["object_id"], controller, body["version"], passport_hash,
                    json.dumps(body, sort_keys=True), "ACTIVE", body["created_at_ms"],
                    json.dumps(sig, sort_keys=True)))
        except sqlite3.IntegrityError as exc:
            raise ValueError("immutable rights passport version already exists") from exc
        return dict(body, passport_sha256=passport_hash, signature=sig)

    def get(self, passport_id: str) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM passports WHERE passport_id=?", (passport_id,)).fetchone()
        if not row:
            raise KeyError("rights passport missing")
        body = json.loads(row["body_json"])
        return dict(body, passport_sha256=row["passport_sha256"],
                    signature=json.loads(row["signature_json"]))

    def verify(self, passport: dict) -> dict:
        try:
            body = {k: v for k, v in passport.items() if k not in {"passport_sha256", "signature"}}
            if body.get("schema") != "entity-v3-rights-passport-v1":
                raise ValueError("schema")
            if body.get("core_primitives") != list(CORE_PRIMITIVES):
                raise ValueError("core primitives")
            if body.get("provider_custody_is_not_authority") is not True:
                raise ValueError("custody boundary")
            if body.get("underlying_data_not_silently_transferred") is not True:
                raise ValueError("transfer boundary")
            if body.get("legal_effect_is_deployment_specific") is not True:
                raise ValueError("legal boundary")
            normalize_rules(list(body.get("rights") or []))
            for locator in body.get("custody") or []:
                normalize_locator(locator)
            expected = digest(body)
            if passport.get("passport_sha256") != expected:
                raise ValueError("hash")
            manifest = self.identity.load_manifest(body["controller_entity_id"])
            if not self.identity.verify_signature(manifest, body, dict(passport.get("signature") or {})):
                raise ValueError("signature")
            return {"valid": True, "passport_id": body["passport_id"],
                    "passport_sha256": expected, "truth_boundary_preserved": True}
        except Exception as exc:
            return {"valid": False, "reason": type(exc).__name__,
                    "truth_boundary_preserved": True}

    def supersede(self, actor: str, old_passport_id: str, new_passport_id: str) -> dict:
        old, new = self.get(old_passport_id), self.get(new_passport_id)
        if old["object_id"] != new["object_id"] or old["controller_entity_id"] != actor:
            raise PermissionError("same object/controller required for passport supersession")
        body = {"schema": "entity-v3-rights-passport-supersession-v1",
                "old_passport_id": old_passport_id, "new_passport_id": new_passport_id,
                "actor_entity_id": actor, "created_at_ms": now_ms(),
                "history_rewrite_prohibited": True}
        sig = self.identity.sign(actor, body)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO supersessions VALUES(?,?,?,?,?)", (
                old_passport_id, new_passport_id, actor, body["created_at_ms"],
                json.dumps(sig, sort_keys=True)))
            db.execute("UPDATE passports SET status='SUPERSEDED' WHERE passport_id=?",
                       (old_passport_id,))
        return dict(body, signature=sig)
