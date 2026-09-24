from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO = ROOT / "protocol" / "v3"
VECTORS = PROTO / "global_vectors"
SCHEMA_PATH = PROTO / "ENTITY_GLOBAL_INFRASTRUCTURE.schema.json"
HEX64 = "^[0-9a-f]{64}$"

def obj(schema_name: str, required: list[str], properties: dict) -> dict:
    props = {"schema": {"const": schema_name}, **properties}
    return {"type": "object", "additionalProperties": False,
            "required": ["schema", *required], "properties": props}

def s(min_len=1):
    return {"type": "string", "minLength": min_len}

def i(minimum=0):
    return {"type": "integer", "minimum": minimum}

def sha():
    return {"type": "string", "pattern": HEX64}

def nullable(inner: dict) -> dict:
    return {"anyOf": [inner, {"type": "null"}]}

rule = {"type": "object", "additionalProperties": False,
        "required": ["effect", "actions", "conditions", "obligations", "authority_basis"],
        "properties": {"effect": {"enum": ["ALLOW", "REQUIRE", "PROHIBIT"]},
                       "actions": {"type": "array", "minItems": 1, "uniqueItems": True, "items": s()},
                       "conditions": {"type": "object"},
                       "obligations": {"type": "array", "uniqueItems": True, "items": s()},
                       "authority_basis": nullable(s())}}
defs = {}
defs["jurisdiction_profile"] = obj("entity-v3-jurisdiction-profile-v1",
    ["profile_id", "jurisdiction_code", "domain", "version", "authority_entity_id",
     "schema_sha256", "rules", "effective_from_ms", "effective_to_ms", "precedence",
     "parent_profile_id", "status", "created_at_ms", "legal_effect_is_deployment_specific"],
    {"profile_id": s(), "jurisdiction_code": s(), "domain": s(), "version": s(),
     "authority_entity_id": s(), "schema_sha256": sha(),
     "rules": {"type": "array", "items": rule}, "effective_from_ms": i(),
     "effective_to_ms": nullable(i()), "precedence": {"type": "integer"},
     "parent_profile_id": nullable(s()), "status": {"const": "ACTIVE"},
     "created_at_ms": i(), "legal_effect_is_deployment_specific": {"const": True}})

defs["semantic_term"] = obj("entity-v3-semantic-term-v1",
    ["namespace_id", "kind", "term_id", "version", "definition_sha256", "definition",
     "status", "supersedes_ref", "created_at_ms"],
    {"namespace_id": s(), "kind": {"enum": ["SCHEMA", "RIGHT", "EVENT", "CAPABILITY",
      "ASSET_CLASS", "TRUST_FRAMEWORK", "DISPUTE_AUTHORITY", "ATTESTATION_CLASS"]},
     "term_id": s(), "version": s(), "definition_sha256": sha(), "definition": {"type": "object"},
     "status": {"const": "ACTIVE"}, "supersedes_ref": nullable(s()), "created_at_ms": i()})

defs["semantic_crosswalk"] = obj("entity-v3-semantic-crosswalk-v1",
    ["crosswalk_id", "actor_entity_id", "source_ref", "target_ref", "relation",
     "evidence_sha256", "jurisdiction_scope", "confidence_bps", "created_at_ms",
     "mapping_is_attestation_not_identity", "silent_semantic_coercion_prohibited"],
    {"crosswalk_id": s(), "actor_entity_id": s(), "source_ref": s(), "target_ref": s(),
     "relation": {"enum": ["EXACT", "BROADER", "NARROWER", "RELATED", "INCOMPATIBLE"]},
     "evidence_sha256": sha(), "jurisdiction_scope": {"type": "array", "uniqueItems": True, "items": s()},
     "confidence_bps": {"type": "integer", "minimum": 0, "maximum": 10000},
     "created_at_ms": i(), "mapping_is_attestation_not_identity": {"const": True},
     "silent_semantic_coercion_prohibited": {"const": True}})
defs["governance_body"] = obj("entity-v3-governance-body-v1",
    ["body_id", "steward_entity_id", "name", "charter_sha256", "stakeholder_classes",
     "approval_threshold", "min_approval_classes", "status", "created_at_ms",
     "single_implementation_is_not_standard_authority"],
    {"body_id": s(), "steward_entity_id": s(), "name": s(), "charter_sha256": sha(),
     "stakeholder_classes": {"type": "array", "minItems": 2, "uniqueItems": True, "items": s()},
     "approval_threshold": i(1), "min_approval_classes": i(2), "status": {"const": "ACTIVE"},
     "created_at_ms": i(), "single_implementation_is_not_standard_authority": {"const": True}})

defs["purpose_grant"] = obj("entity-v3-purpose-bound-access-v1",
    ["grant_id", "controller", "grantee", "resource_ref", "purposes", "actions",
     "max_uses", "expires_at_ms", "status", "created_at_ms"],
    {"grant_id": s(), "controller": s(), "grantee": s(), "resource_ref": s(),
     "purposes": {"type": "array", "minItems": 1, "uniqueItems": True, "items": s()},
     "actions": {"type": "array", "minItems": 1, "uniqueItems": True, "items": s()},
     "max_uses": i(), "expires_at_ms": i(), "status": {"const": "ACTIVE"},
     "created_at_ms": i()})

defs["retention_record"] = obj("entity-v3-retention-record-v1",
    ["record_id", "controller", "subject_ref", "payload_sha256", "storage_ref_sha256",
     "purpose", "jurisdiction", "retain_until_ms", "destruction_mode", "status",
     "created_at_ms", "raw_payload_stored_in_ledger"],
    {"record_id": s(), "controller": s(), "subject_ref": s(), "payload_sha256": sha(),
     "storage_ref_sha256": nullable(sha()), "purpose": s(), "jurisdiction": s(),
     "retain_until_ms": i(), "destruction_mode": {"enum": ["DELETE_PAYLOAD", "REDACT_SOURCE",
      "DESTROY_EXTERNAL_COPY", "LEGAL_HOLD"]}, "status": {"const": "ACTIVE"},
     "created_at_ms": i(), "raw_payload_stored_in_ledger": {"const": False}})
defs["confidential_provenance"] = obj("entity-v3-confidential-provenance-v1",
    ["edge_id", "actor", "parent_ref", "child_ref", "relationship", "evidence_sha256",
     "metadata_commitment_sha256", "encrypted_metadata", "created_at_ms",
     "confidential_metadata_not_public_provenance"],
    {"edge_id": s(), "actor": s(), "parent_ref": s(), "child_ref": s(), "relationship": s(),
     "evidence_sha256": sha(), "metadata_commitment_sha256": sha(),
     "encrypted_metadata": nullable({"type": "object"}), "created_at_ms": i(),
     "confidential_metadata_not_public_provenance": {"const": True}})

defs["topology_node"] = obj("entity-v3-topology-node-v1",
    ["node_id", "operator_entity_id", "topology_class", "jurisdiction", "trust_domain",
     "capabilities", "status", "created_at_ms", "infrastructure_membership_is_not_sovereign_authority"],
    {"node_id": s(), "operator_entity_id": s(),
     "topology_class": {"enum": ["CORE", "REGIONAL", "EDGE", "SATELLITE", "OFFLINE"]},
     "jurisdiction": s(), "trust_domain": s(),
     "capabilities": {"type": "array", "uniqueItems": True, "items": s()},
     "status": {"const": "ACTIVE"}, "created_at_ms": i(),
     "infrastructure_membership_is_not_sovereign_authority": {"const": True}})

defs["partition_checkpoint"] = obj("entity-v3-partition-checkpoint-v1",
    ["checkpoint_id", "node_id", "operator_entity_id", "partition_id", "sequence", "epoch",
     "previous_checkpoint_sha256", "state_root_sha256", "vector_clock", "created_at_ms"],
    {"checkpoint_id": s(), "node_id": s(), "operator_entity_id": s(), "partition_id": s(),
     "sequence": i(1), "epoch": i(), "previous_checkpoint_sha256": nullable(sha()),
     "state_root_sha256": sha(), "vector_clock": {"type": "object", "additionalProperties": i()},
     "created_at_ms": i()})
defs["offline_envelope"] = obj("entity-v3-offline-envelope-v1",
    ["envelope_id", "actor_entity_id", "node_id", "partition_id", "sequence",
     "payload_sha256", "created_at_ms", "expires_at_ms"],
    {"envelope_id": s(), "actor_entity_id": s(), "node_id": s(), "partition_id": s(),
     "sequence": i(), "payload_sha256": sha(), "created_at_ms": i(), "expires_at_ms": i()})

defs["proof_suite"] = obj("entity-v3-proof-suite-v1",
    ["suite_id", "governance_entity_id", "algorithm", "verifier_sha256", "security_claim",
     "status", "created_at_ms", "registration_does_not_certify_cryptographic_security"],
    {"suite_id": s(), "governance_entity_id": s(), "algorithm": s(), "verifier_sha256": sha(),
     "security_claim": s(), "status": {"const": "ACTIVE"}, "created_at_ms": i(),
     "registration_does_not_certify_cryptographic_security": {"const": True}})

defs["crypto_suite"] = obj("entity-v3-crypto-suite-v1",
    ["suite_id", "governance_entity_id", "algorithm", "security_bits", "verifier_sha256",
     "not_before_ms", "deprecate_at_ms", "retire_at_ms", "status", "created_at_ms"],
    {"suite_id": s(), "governance_entity_id": s(), "algorithm": s(),
     "security_bits": i(64), "verifier_sha256": sha(), "not_before_ms": i(),
     "deprecate_at_ms": nullable(i()), "retire_at_ms": nullable(i()),
     "status": {"const": "ACTIVE"}, "created_at_ms": i()})

defs["crypto_transition"] = obj("entity-v3-crypto-transition-v1",
    ["transition_id", "governance_entity_id", "old_suite_id", "new_suite_id",
     "dual_sign_from_ms", "old_retire_at_ms", "created_at_ms", "downgrade_after_transition_prohibited"],
    {"transition_id": s(), "governance_entity_id": s(), "old_suite_id": s(), "new_suite_id": s(),
     "dual_sign_from_ms": i(), "old_retire_at_ms": i(), "created_at_ms": i(),
     "downgrade_after_transition_prohibited": {"const": True}})
defs["data_economic_capital"] = obj("entity-v3-data-economic-capital-v1",
    ["dco_ref", "originator_entity_id", "asset_class", "provenance_root", "content_sha256",
     "metadata", "information_bytes_are_not_declared_scarce", "created_at_ms"],
    {"dco_ref": s(), "originator_entity_id": s(), "asset_class": s(),
     "provenance_root": sha(), "content_sha256": sha(), "metadata": {"type": "object"},
     "information_bytes_are_not_declared_scarce": {"const": True}, "created_at_ms": i()})

defs["bounded_economic_interest"] = obj("entity-v3-bounded-economic-interest-v1",
    ["interest_id", "dco_ref", "holder_entity_id", "actions", "quantity", "duration_ms",
     "jurisdiction", "transferable", "derivation_allowed", "participation_bps",
     "additional_bounds", "scarcity_sources", "underlying_information_remains_nonrival", "created_at_ms"],
    {"interest_id": s(), "dco_ref": s(), "holder_entity_id": s(),
     "actions": {"type": "array", "minItems": 1, "uniqueItems": True, "items": s()},
     "quantity": nullable(i(1)), "duration_ms": nullable(i(1)), "jurisdiction": nullable(s()),
     "transferable": {"type": "boolean"}, "derivation_allowed": {"type": "boolean"},
     "participation_bps": {"type": "integer", "minimum": 0, "maximum": 10000},
     "additional_bounds": {"type": "object"},
     "scarcity_sources": {"type": "array", "minItems": 1, "uniqueItems": True,
       "items": {"enum": ["RIGHT", "ENTITLEMENT", "CAPACITY", "DURATION", "JURISDICTION",
                           "USAGE_QUANTITY", "DERIVATION", "PARTICIPATION", "TRANSFERABILITY"]}},
     "underlying_information_remains_nonrival": {"const": True}, "created_at_ms": i()})

schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
          "$id": "https://entity.invalid/protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE.schema.json",
          "title": "ENTITY Global Infrastructure Profile Records",
          "oneOf": [{"$ref": f"#/$defs/{name}"} for name in defs], "$defs": defs}

VECTORS.mkdir(parents=True, exist_ok=True)
SCHEMA_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
Z = "0" * 64
base_records = {
    "valid_jurisdiction_profile": {"schema": "entity-v3-jurisdiction-profile-v1",
        "profile_id": "jprof3-example", "jurisdiction_code": "CA-BC", "domain": "DATA", "version": "1.0",
        "authority_entity_id": "ent-example", "schema_sha256": Z,
        "rules": [{"effect": "REQUIRE", "actions": ["TRAIN"], "conditions": {},
                   "obligations": ["DISCLOSURE"], "authority_basis": None}],
        "effective_from_ms": 1, "effective_to_ms": None, "precedence": 100,
        "parent_profile_id": None, "status": "ACTIVE", "created_at_ms": 1,
        "legal_effect_is_deployment_specific": True},
    "valid_semantic_term": {"schema": "entity-v3-semantic-term-v1", "namespace_id": "btg",
        "kind": "RIGHT", "term_id": "TRAIN", "version": "1.0", "definition_sha256": Z,
        "definition": {"meaning": "training"}, "status": "ACTIVE", "supersedes_ref": None,
        "created_at_ms": 1},
    "valid_topology_node": {"schema": "entity-v3-topology-node-v1", "node_id": "edge-1",
        "operator_entity_id": "ent-example", "topology_class": "EDGE", "jurisdiction": "CA-BC",
        "trust_domain": "example", "capabilities": ["SYNC", "VERIFY"], "status": "ACTIVE",
        "created_at_ms": 1, "infrastructure_membership_is_not_sovereign_authority": True},
}
base_records.update({
    "valid_purpose_grant": {"schema": "entity-v3-purpose-bound-access-v1", "grant_id": "pgrant3-example",
        "controller": "ent-controller", "grantee": "ent-user", "resource_ref": "dataset:A",
        "purposes": ["RESEARCH"], "actions": ["TRAIN"], "max_uses": 10,
        "expires_at_ms": 9999999999999, "status": "ACTIVE", "created_at_ms": 1},
    "valid_offline_envelope": {"schema": "entity-v3-offline-envelope-v1", "envelope_id": "offline3-example",
        "actor_entity_id": "ent-example", "node_id": "sat-1", "partition_id": "P1",
        "sequence": 1, "payload_sha256": Z, "created_at_ms": 1, "expires_at_ms": 2},
    "valid_crypto_transition": {"schema": "entity-v3-crypto-transition-v1",
        "transition_id": "cryptotransition3-example", "governance_entity_id": "ent-gov",
        "old_suite_id": "OLD", "new_suite_id": "NEW", "dual_sign_from_ms": 100,
        "old_retire_at_ms": 200, "created_at_ms": 1,
        "downgrade_after_transition_prohibited": True},
    "valid_data_economic_capital": {"schema": "entity-v3-data-economic-capital-v1",
        "dco_ref": "obj3-data", "originator_entity_id": "ent-originator", "asset_class": "DATASET",
        "provenance_root": Z, "content_sha256": Z, "metadata": {},
        "information_bytes_are_not_declared_scarce": True, "created_at_ms": 1},
    "valid_bounded_economic_interest": {"schema": "entity-v3-bounded-economic-interest-v1",
        "interest_id": "interest3-example", "dco_ref": "obj3-data", "holder_entity_id": "ent-holder",
        "actions": ["READ", "TRAIN"], "quantity": 100, "duration_ms": 86400000,
        "jurisdiction": "CA-BC", "transferable": True, "derivation_allowed": True,
        "participation_bps": 125, "additional_bounds": {},
        "scarcity_sources": ["DERIVATION", "DURATION", "JURISDICTION", "PARTICIPATION",
                             "RIGHT", "TRANSFERABILITY", "USAGE_QUANTITY"],
        "underlying_information_remains_nonrival": True, "created_at_ms": 1},
})

vectors = []
for name, record in base_records.items():
    vectors.append((name, "VALID", record))

invalid = {
    "invalid_jurisdiction_effect": dict(base_records["valid_jurisdiction_profile"]),
    "invalid_semantic_kind": dict(base_records["valid_semantic_term"]),
    "invalid_topology_class": dict(base_records["valid_topology_node"]),
    "invalid_purpose_empty_actions": dict(base_records["valid_purpose_grant"]),
    "invalid_offline_payload_hash": dict(base_records["valid_offline_envelope"]),
    "invalid_transition_truth_flag": dict(base_records["valid_crypto_transition"]),
    "invalid_data_capital_scarcity_flag": dict(base_records["valid_data_economic_capital"]),
    "invalid_interest_nonrival_flag": dict(base_records["valid_bounded_economic_interest"]),
}
invalid["invalid_jurisdiction_effect"]["rules"] = [{"effect": "MAYBE", "actions": ["TRAIN"], "conditions": {}, "obligations": [], "authority_basis": None}]
invalid["invalid_semantic_kind"]["kind"] = "MAGIC"
invalid["invalid_topology_class"]["topology_class"] = "PLANETARY"
invalid["invalid_purpose_empty_actions"]["actions"] = []
invalid["invalid_offline_payload_hash"]["payload_sha256"] = "not-a-sha"
invalid["invalid_transition_truth_flag"]["downgrade_after_transition_prohibited"] = False
invalid["invalid_data_capital_scarcity_flag"]["information_bytes_are_not_declared_scarce"] = False
invalid["invalid_interest_nonrival_flag"]["underlying_information_remains_nonrival"] = False
for name, record in invalid.items():
    vectors.append((name, "INVALID", record))
entries = []
for name, expectation, record in vectors:
    path = VECTORS / f"{name}.json"
    payload = {"expect": expectation, "record": record}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    entries.append({"file": path.name, "expect": expectation,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
manifest = {"schema": "entity-v3-global-vector-manifest-v1", "status": "DEVELOPMENT",
            "schema_file": SCHEMA_PATH.name,
            "schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
            "valid_vectors": sum(1 for x in entries if x["expect"] == "VALID"),
            "invalid_vectors": sum(1 for x in entries if x["expect"] == "INVALID"),
            "vectors": entries}
manifest_path = VECTORS / "VECTOR_MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
checksum_targets = [SCHEMA_PATH, manifest_path] + [VECTORS / x["file"] for x in entries]
lines = []
for path in sorted(checksum_targets, key=lambda p: p.name):
    rel = path.name if path.parent == VECTORS else f"../{path.name}"
    lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}")
(VECTORS / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"schema": str(SCHEMA_PATH), "vectors": len(entries),
                  "valid": manifest["valid_vectors"], "invalid": manifest["invalid_vectors"],
                  "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}, indent=2))
