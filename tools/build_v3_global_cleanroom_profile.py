from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V = ROOT / "protocol" / "v3" / "global_vectors"
OUT = ROOT / "protocol" / "v3" / "ENTITY_GLOBAL_CLEANROOM_PROFILE.json"
INVARIANTS = [
    "DATA_MAY_BE_PRODUCTIVE_CAPITAL",
    "INFORMATION_SCARCITY_NOT_REQUIRED",
    "SCARCITY_MUST_BE_EXPLICITLY_BOUNDED",
    "ORIGINATOR_PARTICIPATION_MUST_BE_ESTABLISHED_BY_TERMS",
    "PROVENANCE_LINKS_RIGHT_USE_DERIVATION_VALUE",
    "PROTOCOL_DOES_NOT_DETERMINE_LEGAL_TITLE",
    "PROTOCOL_DOES_NOT_DETERMINE_FAIR_VALUE",
    "PROTOCOL_DOES_NOT_DETERMINE_REGULATORY_CLASSIFICATION",
]

def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

manifest = json.loads((V / "VECTOR_MANIFEST.json").read_text(encoding="utf-8"))
rows = []
for entry in sorted(manifest["vectors"], key=lambda x: x["file"]):
    payload = json.loads((V / entry["file"]).read_text(encoding="utf-8"))
    expected = str(payload["expect"])
    rows.append({"name": pathlib.Path(entry["file"]).stem,
                 "accepted": expected == "VALID",
                 "expected": expected,
                 "ok": True})
summary = {"schema": "entity-v3.1-global-cleanroom-result-v1",
           "profile": "ENTITY-GLOBAL-INFRASTRUCTURE",
           "doctrine_invariants": INVARIANTS,
           "vectors": rows}
result_sha256 = hashlib.sha256(canon(summary)).hexdigest()
profile = {"schema": "entity-v3.1-global-cleanroom-profile-v1",
           "release_candidate": "v3.1.0",
           "base_release": "v3.0.1",
           "vector_manifest_sha256": hashlib.sha256((V / "VECTOR_MANIFEST.json").read_bytes()).hexdigest(),
           "schema_sha256": manifest["schema_sha256"],
           "valid_vectors": manifest["valid_vectors"], "invalid_vectors": manifest["invalid_vectors"],
           "doctrine_invariants": INVARIANTS,
           "expected_result_sha256": result_sha256,
           "result_schema": summary["schema"]}
OUT.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"profile": str(OUT), "expected_result_sha256": result_sha256,
                  "valid": manifest["valid_vectors"], "invalid": manifest["invalid_vectors"]}, indent=2))
