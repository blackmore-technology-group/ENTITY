from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO = ROOT / "protocol" / "v3"
VECTORS = PROTO / "adoption_vectors"
SCHEMA_PATH = PROTO / "ENTITY_ADOPTION_LAYER.schema.json"
Z = "0" * 64
PRIMITIVES = ["ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE"]
LIFECYCLE = ["DCO", "INSTRUMENT", "LISTING", "DISCLOSURE", "ORDER_RFQ_AUCTION",
             "PRICE_DISCOVERY", "TRADE", "CLEARING", "SETTLEMENT", "ENTITLEMENT",
             "USAGE", "DERIVED_OUTPUT", "ECONOMIC_CONSEQUENCE"]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def obj(schema_name: str, required: list[str], properties: dict) -> dict:
    return {"type": "object", "required": ["schema", *required],
            "properties": {"schema": {"const": schema_name}, **properties}}

def s(): return {"type": "string", "minLength": 1}
def b(value): return {"const": value}
def sh(): return {"type": "string", "pattern": "^[0-9a-f]{64}$"}

rights_rule = {"type": "object", "required": ["effect", "actions"],
               "properties": {"effect": {"enum": ["ALLOW", "REQUIRE", "PROHIBIT"]},
                              "actions": {"type": "array", "minItems": 1, "uniqueItems": True,
                                          "items": {"type": "string", "pattern": "^[A-Z0-9_]+$"}}}}
defs = {
    "rights_passport": obj("entity-v3-rights-passport-v1",
        ["core_primitives", "rights", "provider_custody_is_not_authority",
         "underlying_data_not_silently_transferred", "legal_effect_is_deployment_specific"],
        {"core_primitives": {"const": PRIMITIVES}, "rights": {"type": "array", "minItems": 1, "items": rights_rule},
         "provider_custody_is_not_authority": b(True), "underlying_data_not_silently_transferred": b(True),
         "legal_effect_is_deployment_specific": b(True)}),
    "custody_locator": obj("entity-v3-custody-locator-v1",
        ["entity_object_id", "provider", "locator", "content_sha256", "provider_is_authority",
         "credentials_included", "entity_identity_changes_with_provider"],
        {"entity_object_id": s(), "provider": {"enum": ["AWS_S3","AZURE_BLOB","GOOGLE_CLOUD_STORAGE","SNOWFLAKE","DATABRICKS","POSTGRESQL","SQL_SERVER","LOCAL_FILESYSTEM","HTTP_API"]},
         "locator": s(), "content_sha256": sh(), "provider_is_authority": b(False),
         "credentials_included": b(False), "entity_identity_changes_with_provider": b(False)}),
    "standards_mapping": obj("entity-v3-standards-mapping-v1",
        ["source_standard", "source_sha256", "silent_semantic_equivalence", "external_standard_is_not_entity_authority"],
        {"source_standard": {"enum": ["ODRL","W3C_VC","DID","GAIA_X","IDS"]}, "source_sha256": sh(),
         "silent_semantic_equivalence": b(False), "external_standard_is_not_entity_authority": b(True)}),
    "credential_evidence": obj("entity-v3-external-credential-evidence-v1",
        ["source_standard", "credential_sha256", "credential_is_evidence_not_entity_authority"],
        {"source_standard": {"const": "W3C_VC"}, "credential_sha256": sh(),
         "credential_is_evidence_not_entity_authority": b(True)}),
    "resolver_deployment": obj("entity-v3-resolver-deployment-v1",
        ["mode", "minimum_resolvers", "resolver_is_not_authority", "single_provider_dependency_prohibited", "fail_closed"],
        {"mode": {"const": "FEDERATED"}, "minimum_resolvers": {"type": "integer", "minimum": 2},
         "resolver_is_not_authority": b(True), "single_provider_dependency_prohibited": b(True), "fail_closed": b(True)}),
    "exchange_adoption": obj("entity-v3-exchange-adoption-profile-v1",
        ["market_engine_preserved", "rights_are_traded_not_bytes", "market_lifecycle"],
        {"market_engine_preserved": b(True), "rights_are_traded_not_bytes": b(True), "market_lifecycle": {"const": LIFECYCLE}}),
    "adoption_status": obj("entity-v3-adoption-profile-status-v1",
        ["core_primitives", "core_semantics_changed", "market_engine_preserved"],
        {"core_primitives": {"const": PRIMITIVES}, "core_semantics_changed": b(False), "market_engine_preserved": b(True)}),
    "legal_assertion": obj("entity-v3-legal-classification-assertion-v1",
        ["asserted_by", "classification", "classification_is_assertion_not_protocol_legal_truth"],
        {"asserted_by": s(), "classification": s(), "classification_is_assertion_not_protocol_legal_truth": b(True)}),
}
schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
          "$id": "https://entity.invalid/protocol/v3/ENTITY_ADOPTION_LAYER.schema.json",
          "title": "ENTITY v3.2 Adoption Layer Records",
          "oneOf": [{"$ref": f"#/$defs/{name}"} for name in defs], "$defs": defs}

valid = {
    "valid_rights_passport": {"schema":"entity-v3-rights-passport-v1","core_primitives":PRIMITIVES,
        "rights":[{"effect":"ALLOW","actions":["DERIVE","TRAIN"]}],
        "provider_custody_is_not_authority":True,"underlying_data_not_silently_transferred":True,
        "legal_effect_is_deployment_specific":True},
    "valid_custody_locator": {"schema":"entity-v3-custody-locator-v1","entity_object_id":"obj3-data",
        "provider":"SNOWFLAKE","locator":"DB.SCHEMA.DATA","content_sha256":Z,
        "provider_is_authority":False,"credentials_included":False,"entity_identity_changes_with_provider":False},
    "valid_standards_mapping": {"schema":"entity-v3-standards-mapping-v1","source_standard":"ODRL",
        "source_sha256":Z,"silent_semantic_equivalence":False,"external_standard_is_not_entity_authority":True},
    "valid_credential_evidence": {"schema":"entity-v3-external-credential-evidence-v1","source_standard":"W3C_VC",
        "credential_sha256":Z,"credential_is_evidence_not_entity_authority":True},
    "valid_resolver_deployment": {"schema":"entity-v3-resolver-deployment-v1","mode":"FEDERATED","minimum_resolvers":2,
        "resolver_is_not_authority":True,"single_provider_dependency_prohibited":True,"fail_closed":True},
    "valid_exchange_adoption": {"schema":"entity-v3-exchange-adoption-profile-v1","market_engine_preserved":True,
        "rights_are_traded_not_bytes":True,"market_lifecycle":LIFECYCLE},
    "valid_adoption_status": {"schema":"entity-v3-adoption-profile-status-v1","core_primitives":PRIMITIVES,
        "core_semantics_changed":False,"market_engine_preserved":True},
    "valid_legal_assertion": {"schema":"entity-v3-legal-classification-assertion-v1","asserted_by":"ent-gov",
        "classification":"CONTRACTUAL_USAGE_RIGHT","classification_is_assertion_not_protocol_legal_truth":True},
}
invalid = {name.replace("valid_", "invalid_"): dict(value) for name, value in valid.items()}
invalid["invalid_rights_passport"]["core_primitives"] = ["ENTITY","RIGHT","EVENT","VALUE"]
invalid["invalid_custody_locator"]["provider_is_authority"] = True
invalid["invalid_standards_mapping"]["silent_semantic_equivalence"] = True
invalid["invalid_credential_evidence"]["credential_is_evidence_not_entity_authority"] = False
invalid["invalid_resolver_deployment"]["minimum_resolvers"] = 1
invalid["invalid_exchange_adoption"]["rights_are_traded_not_bytes"] = False
invalid["invalid_adoption_status"]["core_semantics_changed"] = True
invalid["invalid_legal_assertion"]["classification_is_assertion_not_protocol_legal_truth"] = False

VECTORS.mkdir(parents=True, exist_ok=True)
SCHEMA_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
entries = []
for name, expectation, record in [(n,"VALID",r) for n,r in valid.items()] + [(n,"INVALID",r) for n,r in invalid.items()]:
    path = VECTORS / f"{name}.json"
    path.write_text(json.dumps({"expect":expectation,"record":record}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    entries.append({"file":path.name,"expect":expectation,"sha256":sha(path.read_bytes())})
entries.sort(key=lambda x: x["file"])
manifest = {"schema":"entity-v3.2-adoption-vector-manifest-v1","status":"DEVELOPMENT",
            "schema_file":SCHEMA_PATH.name,"schema_sha256":sha(SCHEMA_PATH.read_bytes()),
            "valid_vectors":8,"invalid_vectors":8,"vectors":entries}
manifest_path = VECTORS / "VECTOR_MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
checksum_targets = [SCHEMA_PATH, manifest_path] + [VECTORS / x["file"] for x in entries]
lines = []
for path in sorted(checksum_targets, key=lambda p: str(p)):
    rel = path.name if path.parent == VECTORS else f"../{path.name}"
    lines.append(f"{sha(path.read_bytes())}  {rel}")
(VECTORS / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"vectors":16,"valid":8,"invalid":8,"manifest_sha256":sha(manifest_path.read_bytes())}, indent=2))
