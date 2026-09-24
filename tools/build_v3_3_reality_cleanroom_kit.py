from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "37_Verifiable_Reality"
PROTO = ROOT / "protocol" / "v3"
OUT = PROTO / "ENTITY_V3_3_REALITY_CLEANROOM_KIT.min.json"
SCHEMA = PROTO / "ENTITY_VERIFIABLE_REALITY.schema.json"

spec = importlib.util.spec_from_file_location("reality_profile", SRC / "reality_profile.py")
profile = importlib.util.module_from_spec(spec); sys.modules["reality_profile"] = profile; spec.loader.exec_module(profile)
spec = importlib.util.spec_from_file_location("reality_conformance", SRC / "reality_conformance.py")
conf = importlib.util.module_from_spec(spec); sys.modules["reality_conformance"] = conf; spec.loader.exec_module(conf)

Z = "0" * 64
PRIMITIVES = ["ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE"]

def canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def sha(value) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon(value)
    return hashlib.sha256(raw).hexdigest()

valid = {
    "evidence": {"schema":"entity-v3-evidence-object-v1","evidence_type":"DOCUMENT","content_sha256":Z,"signature_proves_attribution_not_objective_truth":True,"immutable_evidence_record":True},
    "claim": {"schema":"entity-v3-evidence-bound-claim-v1","state":"ASSERTED","value_sha256":Z,"evidence_refs":["evidence:1"],"claim_is_not_objective_truth":True,"state_is_typed_not_absolute":True},
    "transition": {"schema":"entity-v3-claim-status-transition-v1","from_state":"ASSERTED","to_state":"EXTERNALLY_VERIFIED","evidence_refs":["snapshot:1"],"history_rewrite_prohibited":True,"transition_does_not_establish_objective_truth":True},
    "grant": {"schema":"entity-v3-attestation-authority-grant-v1","scopes":["LAB_CALIBRATION"],"authority_evidence_sha256":Z,"attestation_authority_is_scope_limited":True,"attestation_does_not_create_legal_truth":True},
    "attestation": {"schema":"entity-v3-attestation-v1","grant_id":"grant:1","scope":"LAB_CALIBRATION","evidence_refs":["certificate:1"],"attestation_is_evidence_not_objective_truth":True},
    "anchor": {"schema":"entity-v3-external-reality-anchor-v1","anchor_type":"GOVERNMENT_REGISTRY","endpoint_descriptor_sha256":Z,"credentials_included":False,"external_system_is_not_automatic_entity_authority":True},
    "snapshot": {"schema":"entity-v3-external-reality-snapshot-v1","record_sha256":Z,"verifier_evidence_refs":["transport:1"],"external_record_is_evidence_not_protocol_truth":True,"record_may_be_contested_or_superseded":True},
    "causal_node": {"schema":"entity-v3-causal-economic-node-v1","node_type":"REVENUE","evidence_refs":["sale:1"],"event_refs":["event:1"],"economic_observation":{"amount":100,"currency":"CAD","market_observation_is_not_accounting_fair_value":True,"protocol_does_not_determine_legal_entitlement":True}},
    "causal_edge": {"schema":"entity-v3-causal-economic-edge-v1","edge_type":"GENERATED","from_node_id":"product:A","to_node_id":"revenue:B","evidence_refs":["sale:1"],"authority_refs":["authority:1"],"participation_rule_refs":["eopp:1"],"causality_is_evidence_bound_not_assumed":True,"economic_attribution_is_not_accounting_fair_value":True},
    "status": {"schema":"entity-v3-verifiable-reality-status-v1","core_primitives":PRIMITIVES,"core_semantics_changed":False,"market_engine_preserved":True,"reality_claims_are_evidence_bound":True,"cryptographic_verification_is_not_objective_truth":True,"protocol_verification_is_not_objective_truth":True},
}

invalid = {name: json.loads(json.dumps(record)) for name, record in valid.items()}
invalid["evidence"]["signature_proves_attribution_not_objective_truth"] = False
invalid["claim"]["claim_is_not_objective_truth"] = False
invalid["transition"]["to_state"] = "ASSERTED"
invalid["grant"]["scopes"] = []
invalid["attestation"]["evidence_refs"] = []
invalid["anchor"]["external_system_is_not_automatic_entity_authority"] = False
invalid["snapshot"]["external_record_is_evidence_not_protocol_truth"] = False
invalid["causal_node"]["economic_observation"]["market_observation_is_not_accounting_fair_value"] = False
invalid["causal_edge"]["evidence_refs"] = []
invalid["status"]["cryptographic_verification_is_not_objective_truth"] = False

cases = []
for name, record in valid.items():
    cases.append({"id":f"valid_{name}","expect":"VALID","record":record})
for name, record in invalid.items():
    cases.append({"id":f"invalid_{name}","expect":"INVALID","record":record})
cases.sort(key=lambda x: x["id"])

transcript = []
for case in cases:
    actual = "VALID" if conf.validate_reality_record(case["record"]) else "INVALID"
    if actual != case["expect"]:
        raise SystemExit(f"builder semantic mismatch: {case['id']} expected {case['expect']} got {actual}")
    transcript.append({"id":case["id"],"actual":actual})

schema = {
    "$schema":"https://json-schema.org/draft/2020-12/schema",
    "$id":"https://entity.invalid/protocol/v3/ENTITY_VERIFIABLE_REALITY.schema.json",
    "title":"ENTITY v3.3 Verifiable Reality Records",
    "description":"Evidence, typed claims, scoped attestations, external reality anchors and causal economic attribution. Schema validation never implies objective truth.",
    "type":"object",
    "required":["schema"],
    "properties":{"schema":{"type":"string"}},
    "x-entity-truth-boundary":"Cryptographic/protocol validity proves record integrity and semantics, not objective real-world truth."
}
SCHEMA.parent.mkdir(parents=True, exist_ok=True)
SCHEMA.write_bytes((json.dumps(schema, indent=2, sort_keys=True) + "\n").encode("utf-8"))

kit = {
    "schema":"entity-v3.3-verifiable-reality-cleanroom-kit-v1",
    "version":"3.3.0",
    "base_release":"v3.2.0",
    "base_commit":"512665096cef3771a3a8307d6dc955015ee0efbc",
    "doctrine":"Claims are attributable, evidentiary, contestable and machine-verifiable; ENTITY does not make reality indisputable.",
    "valid_vectors":10,
    "invalid_vectors":10,
    "cases":cases,
    "expected_result_sha256":sha(transcript),
    "schema_sha256":sha(SCHEMA.read_bytes()),
}
OUT.write_bytes((json.dumps(kit, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
print(json.dumps({"vectors":len(cases),"valid":10,"invalid":10,"expected_result_sha256":kit["expected_result_sha256"],"kit_sha256":sha(OUT.read_bytes()),"schema_sha256":kit["schema_sha256"]}, indent=2))
