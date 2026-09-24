from __future__ import annotations
from typing import Any
import hashlib, json

SUPPORTED_STANDARDS = {"ODRL", "W3C_VC", "DID", "GAIA_X", "IDS"}

def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def digest(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon(value)
    return hashlib.sha256(raw).hexdigest()

def _action(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("id") or value.get("@id") or value.get("name") or ""
    value = str(value)
    if ":" in value:
        value = value.rsplit(":", 1)[-1]
    if "/" in value:
        value = value.rsplit("/", 1)[-1]
    return value.replace("-", "_").upper()

class StandardsAdapters:
    """Explicit translation envelopes. Mapping is evidence, never silent semantic identity."""
    @staticmethod
    def import_odrl(policy: dict) -> dict:
        rules = []
        for field, effect in (("permission", "ALLOW"), ("prohibition", "PROHIBIT")):
            entries = policy.get(field) or []
            if isinstance(entries, dict):
                entries = [entries]
            for item in entries:
                actions = item.get("action") or []
                if not isinstance(actions, list):
                    actions = [actions]
                normalized = sorted({a for a in (_action(x) for x in actions) if a})
                if not normalized:
                    raise ValueError("ODRL rule action required")
                duties = item.get("duty") or []
                if isinstance(duties, dict):
                    duties = [duties]
                obligations = sorted({
                    _action(d.get("action") if isinstance(d, dict) else d)
                    for d in duties if _action(d.get("action") if isinstance(d, dict) else d)
                })
                rules.append({"effect": effect, "actions": normalized,
                              "conditions": {}, "obligations": obligations,
                              "right_refs": []})
        if not rules:
            raise ValueError("ODRL policy has no supported permission/prohibition")
        return {
            "schema": "entity-v3-standards-mapping-v1",
            "source_standard": "ODRL",
            "source_sha256": digest(policy),
            "mapped_rights": sorted(rules, key=lambda x: (x["effect"], x["actions"])),
            "mapping_relation": "EXPLICIT_TRANSLATION",
            "silent_semantic_equivalence": False,
            "external_standard_is_not_entity_authority": True,
        }

    @staticmethod
    def export_odrl(rights: list[dict], target_uid: str) -> dict:
        policy = {"@context": "https://www.w3.org/ns/odrl.jsonld",
                  "type": "Set", "uid": str(target_uid), "permission": [], "prohibition": []}
        for rule in rights:
            effect = str(rule.get("effect") or "").upper()
            if effect not in {"ALLOW", "PROHIBIT"}:
                continue
            target = "permission" if effect == "ALLOW" else "prohibition"
            item = {"target": str(target_uid),
                    "action": [str(x).lower() for x in sorted(set(rule.get("actions") or []))]}
            obligations = sorted(set(rule.get("obligations") or []))
            if obligations:
                item["duty"] = [{"action": x.lower()} for x in obligations]
            policy[target].append(item)
        return policy

    @staticmethod
    def credential_evidence(credential: dict) -> dict:
        issuer = credential.get("issuer")
        if isinstance(issuer, dict):
            issuer = issuer.get("id")
        subject = credential.get("credentialSubject") or {}
        subject_id = subject.get("id") if isinstance(subject, dict) else None
        return {
            "schema": "entity-v3-external-credential-evidence-v1",
            "source_standard": "W3C_VC",
            "credential_sha256": digest(credential),
            "issuer_ref": issuer,
            "subject_ref": subject_id,
            "proof_present": bool(credential.get("proof")),
            "credential_is_evidence_not_entity_authority": True,
        }

    @staticmethod
    def did_evidence(did_document: dict) -> dict:
        return {
            "schema": "entity-v3-external-identifier-evidence-v1",
            "source_standard": "DID",
            "external_id": str(did_document.get("id") or ""),
            "document_sha256": digest(did_document),
            "external_identifier_is_not_entity_authority": True,
        }

    @staticmethod
    def dataspace_mapping(source_standard: str, document: dict, *,
                          policy_refs: list[str] | None = None,
                          semantic_crosswalk_refs: list[str] | None = None) -> dict:
        source_standard = str(source_standard).upper()
        if source_standard not in {"GAIA_X", "IDS"}:
            raise ValueError("data-space adapter supports GAIA_X or IDS")
        return {
            "schema": "entity-v3-standards-mapping-v1",
            "source_standard": source_standard,
            "source_sha256": digest(document),
            "policy_refs": sorted(set(policy_refs or [])),
            "semantic_crosswalk_refs": sorted(set(semantic_crosswalk_refs or [])),
            "mapping_relation": "EXPLICIT_CROSSWALK",
            "silent_semantic_equivalence": False,
            "external_standard_is_not_entity_authority": True,
        }

    @staticmethod
    def supported() -> list[str]:
        return sorted(SUPPORTED_STANDARDS)
