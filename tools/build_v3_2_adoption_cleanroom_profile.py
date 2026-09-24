from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
V = ROOT / "protocol" / "v3" / "adoption_vectors"
OUT = ROOT / "protocol" / "v3" / "ENTITY_ADOPTION_CLEANROOM_PROFILE.json"
INVARIANTS = [
    "CORE_PRIMITIVES_UNCHANGED",
    "MARKET_ENGINE_PRESERVED",
    "RIGHTS_ARE_TRADED_NOT_BYTES",
    "PROVIDER_CUSTODY_IS_NOT_AUTHORITY",
    "EXTERNAL_STANDARDS_ARE_NOT_ENTITY_AUTHORITY",
    "LEGAL_CLASSIFICATION_IS_EXTERNAL_ASSERTION",
    "RESOLVER_IS_NOT_AUTHORITY",
    "NO_SILENT_SEMANTIC_EQUIVALENCE",
]

def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def sha(value):
    return hashlib.sha256(value).hexdigest()

manifest = json.loads((V / "VECTOR_MANIFEST.json").read_text(encoding="utf-8"))
rows = []
for entry in sorted(manifest["vectors"], key=lambda x: x["file"]):
    payload = json.loads((V / entry["file"]).read_text(encoding="utf-8"))
    expected = str(payload["expect"])
    rows.append({"name": pathlib.Path(entry["file"]).stem,
                 "accepted": expected == "VALID", "expected": expected, "ok": True})
summary = {"schema":"entity-v3.2-adoption-cleanroom-result-v1",
           "profile":"ENTITY-ADOPTION-LAYER","adoption_invariants":INVARIANTS,
           "vectors":rows}
result_sha256 = sha(canon(summary))
profile = {"schema":"entity-v3.2-adoption-cleanroom-profile-v1",
           "release_candidate":"v3.2.0","base_release":"v3.1.0",
           "vector_manifest_sha256":sha((V / "VECTOR_MANIFEST.json").read_bytes()),
           "schema_sha256":manifest["schema_sha256"],"valid_vectors":8,"invalid_vectors":8,
           "adoption_invariants":INVARIANTS,"expected_result_sha256":result_sha256,
           "result_schema":summary["schema"]}
OUT.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"profile":str(OUT),"expected_result_sha256":result_sha256,"valid":8,"invalid":8}, indent=2))
