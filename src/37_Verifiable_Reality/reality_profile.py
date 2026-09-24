from __future__ import annotations

CORE_PRIMITIVES = ["ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE"]
CLAIM_STATES = [
    "OBSERVED", "ASSERTED", "INFERRED", "ATTESTED", "EXTERNALLY_VERIFIED",
    "ADJUDICATED", "DISPUTED", "REVOKED", "UNKNOWN",
]
EVIDENCE_TYPES = [
    "SENSOR_OBSERVATION", "DOCUMENT", "REGISTRY_RECORD", "LAB_RESULT",
    "PAYMENT_RECORD", "IMAGE", "API_RESPONSE", "CERTIFICATE", "COURT_RECORD", "OTHER",
]
ANCHOR_TYPES = [
    "GOVERNMENT_REGISTRY", "SENSOR_NETWORK", "BANK_SETTLEMENT", "LAB_SYSTEM",
    "SUPPLY_CHAIN_SYSTEM", "CORPORATE_REGISTRY", "COURT_RECORD",
    "CERTIFICATE_AUTHORITY", "OTHER",
]
CAUSAL_NODE_TYPES = [
    "SOURCE_DATA", "DCO", "RIGHT", "LICENSE", "USAGE", "DERIVED_ASSET",
    "PRODUCT", "TRANSACTION", "REVENUE", "SETTLEMENT", "CONTRIBUTOR",
]
CAUSAL_EDGE_TYPES = [
    "ORIGINATED_FROM", "AUTHORIZED_BY", "LICENSED_AS", "USED_IN",
    "DERIVED_FROM", "PRODUCED", "GENERATED", "SETTLED_AS", "CONTRIBUTED_TO",
]

def reality_status() -> dict:
    return {
        "schema": "entity-v3-verifiable-reality-status-v1",
        "core_primitives": list(CORE_PRIMITIVES),
        "core_semantics_changed": False,
        "market_engine_preserved": True,
        "reality_claims_are_evidence_bound": True,
        "cryptographic_verification_is_not_objective_truth": True,
        "protocol_verification_is_not_objective_truth": True,
        "external_evidence_is_not_automatic_entity_authority": True,
        "claim_states": list(CLAIM_STATES),
        "doctrine": "ENTITY makes claims attributable, evidentiary, contestable, machine-verifiable and economically traceable; it does not make reality indisputable.",
    }
