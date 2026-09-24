from __future__ import annotations
from typing import Any
import re

from reality_profile import (
    CORE_PRIMITIVES, CLAIM_STATES, EVIDENCE_TYPES, ANCHOR_TYPES,
    CAUSAL_NODE_TYPES, CAUSAL_EDGE_TYPES,
)

HEX64 = re.compile(r"^[0-9a-f]{64}$")

def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))

def _refs(value: Any, *, nonempty: bool = False) -> bool:
    return (isinstance(value, list) and (not nonempty or bool(value))
            and all(isinstance(x, str) and x for x in value)
            and value == sorted(set(value)))

def validate_reality_record(record: dict) -> bool:
    if not isinstance(record, dict):
        return False
    schema = record.get("schema")
    if schema == "entity-v3-evidence-object-v1":
        return (record.get("evidence_type") in EVIDENCE_TYPES
                and _sha(record.get("content_sha256"))
                and record.get("signature_proves_attribution_not_objective_truth") is True
                and record.get("immutable_evidence_record") is True)
    if schema == "entity-v3-evidence-bound-claim-v1":
        return (record.get("state") in CLAIM_STATES
                and _sha(record.get("value_sha256"))
                and _refs(record.get("evidence_refs", []))
                and record.get("claim_is_not_objective_truth") is True
                and record.get("state_is_typed_not_absolute") is True)
    if schema == "entity-v3-claim-status-transition-v1":
        return (record.get("from_state") in CLAIM_STATES
                and record.get("to_state") in CLAIM_STATES
                and record.get("from_state") != record.get("to_state")
                and _refs(record.get("evidence_refs", []))
                and record.get("history_rewrite_prohibited") is True
                and record.get("transition_does_not_establish_objective_truth") is True)
    if schema == "entity-v3-attestation-authority-grant-v1":
        return (_refs(record.get("scopes"), nonempty=True)
                and _sha(record.get("authority_evidence_sha256"))
                and record.get("attestation_authority_is_scope_limited") is True
                and record.get("attestation_does_not_create_legal_truth") is True)
    if schema == "entity-v3-attestation-v1":
        return (bool(record.get("grant_id")) and bool(record.get("scope"))
                and _refs(record.get("evidence_refs"), nonempty=True)
                and record.get("attestation_is_evidence_not_objective_truth") is True)
    if schema == "entity-v3-external-reality-anchor-v1":
        return (record.get("anchor_type") in ANCHOR_TYPES
                and _sha(record.get("endpoint_descriptor_sha256"))
                and record.get("credentials_included") is False
                and record.get("external_system_is_not_automatic_entity_authority") is True)
    if schema == "entity-v3-external-reality-snapshot-v1":
        return (_sha(record.get("record_sha256"))
                and _refs(record.get("verifier_evidence_refs", []))
                and record.get("external_record_is_evidence_not_protocol_truth") is True
                and record.get("record_may_be_contested_or_superseded") is True)
    if schema == "entity-v3-causal-economic-node-v1":
        observation = record.get("economic_observation") or {}
        return (record.get("node_type") in CAUSAL_NODE_TYPES
                and _refs(record.get("evidence_refs", []))
                and _refs(record.get("event_refs", []))
                and (not observation or (
                    observation.get("market_observation_is_not_accounting_fair_value") is True
                    and observation.get("protocol_does_not_determine_legal_entitlement") is True)))
    if schema == "entity-v3-causal-economic-edge-v1":
        return (record.get("edge_type") in CAUSAL_EDGE_TYPES
                and record.get("from_node_id") != record.get("to_node_id")
                and _refs(record.get("evidence_refs"), nonempty=True)
                and _refs(record.get("authority_refs", []))
                and _refs(record.get("participation_rule_refs", []))
                and record.get("causality_is_evidence_bound_not_assumed") is True
                and record.get("economic_attribution_is_not_accounting_fair_value") is True)
    if schema == "entity-v3-verifiable-reality-status-v1":
        return (record.get("core_primitives") == CORE_PRIMITIVES
                and record.get("core_semantics_changed") is False
                and record.get("market_engine_preserved") is True
                and record.get("reality_claims_are_evidence_bound") is True
                and record.get("cryptographic_verification_is_not_objective_truth") is True
                and record.get("protocol_verification_is_not_objective_truth") is True)
    return False
