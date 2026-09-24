from __future__ import annotations
from typing import Any
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")
PRIMITIVES = ["ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE"]
PROVIDERS = {
    "AWS_S3", "AZURE_BLOB", "GOOGLE_CLOUD_STORAGE", "SNOWFLAKE", "DATABRICKS",
    "POSTGRESQL", "SQL_SERVER", "LOCAL_FILESYSTEM", "HTTP_API",
}
STANDARDS = {"ODRL", "W3C_VC", "DID", "GAIA_X", "IDS"}
LIFECYCLE = [
    "DCO", "INSTRUMENT", "LISTING", "DISCLOSURE", "ORDER_RFQ_AUCTION",
    "PRICE_DISCOVERY", "TRADE", "CLEARING", "SETTLEMENT", "ENTITLEMENT",
    "USAGE", "DERIVED_OUTPUT", "ECONOMIC_CONSEQUENCE",
]

def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))

def _rules(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for rule in value:
        if not isinstance(rule, dict) or rule.get("effect") not in {"ALLOW", "REQUIRE", "PROHIBIT"}:
            return False
        actions = rule.get("actions")
        if not isinstance(actions, list) or not actions or actions != sorted(set(actions)):
            return False
        if any(not isinstance(x, str) or not x or x != x.upper() for x in actions):
            return False
    return True

def validate_adoption_record(r: dict) -> bool:
    if not isinstance(r, dict):
        return False
    schema = r.get("schema")
    if schema == "entity-v3-rights-passport-v1":
        return (r.get("core_primitives") == PRIMITIVES and _rules(r.get("rights"))
                and r.get("provider_custody_is_not_authority") is True
                and r.get("underlying_data_not_silently_transferred") is True
                and r.get("legal_effect_is_deployment_specific") is True)
    if schema == "entity-v3-custody-locator-v1":
        return (r.get("provider") in PROVIDERS and _sha(r.get("content_sha256"))
                and r.get("provider_is_authority") is False
                and r.get("credentials_included") is False
                and r.get("entity_identity_changes_with_provider") is False)
    if schema == "entity-v3-standards-mapping-v1":
        return (r.get("source_standard") in STANDARDS
                and _sha(r.get("source_sha256"))
                and r.get("silent_semantic_equivalence") is False
                and r.get("external_standard_is_not_entity_authority") is True)
    if schema == "entity-v3-external-credential-evidence-v1":
        return (r.get("source_standard") == "W3C_VC" and _sha(r.get("credential_sha256"))
                and r.get("credential_is_evidence_not_entity_authority") is True)
    if schema == "entity-v3-resolver-deployment-v1":
        return (r.get("mode") == "FEDERATED" and type(r.get("minimum_resolvers")) is int
                and r["minimum_resolvers"] >= 2 and r.get("resolver_is_not_authority") is True
                and r.get("single_provider_dependency_prohibited") is True
                and r.get("fail_closed") is True)
    if schema == "entity-v3-exchange-adoption-profile-v1":
        return (r.get("market_engine_preserved") is True and r.get("rights_are_traded_not_bytes") is True
                and r.get("market_lifecycle") == LIFECYCLE)
    if schema == "entity-v3-adoption-profile-status-v1":
        return (r.get("core_primitives") == PRIMITIVES and r.get("core_semantics_changed") is False
                and r.get("market_engine_preserved") is True)
    if schema == "entity-v3-legal-classification-assertion-v1":
        return (bool(r.get("asserted_by")) and bool(r.get("classification"))
                and r.get("classification_is_assertion_not_protocol_legal_truth") is True)
    return False
