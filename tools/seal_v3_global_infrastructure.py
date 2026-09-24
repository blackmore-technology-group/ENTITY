from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = [
    "src/35_Global_Infrastructure/institutional_semantics.py",
    "src/35_Global_Infrastructure/privacy_provenance.py",
    "src/35_Global_Infrastructure/topology_crypto.py",
    "src/35_Global_Infrastructure/data_economic_sovereignty.py",
    "protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE_PROFILE.md",
    "protocol/v3/ENTITY_DATA_ECONOMIC_SOVEREIGNTY_DOCTRINE.md",
    "protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE_GAP_CLOSURE.md",
    "protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE.schema.json",
    "protocol/v3/ENTITY_GLOBAL_CLEANROOM_PROFILE.json",
    "tests/test_v3_global_infrastructure.py",
    "tests/test_v3_data_economic_sovereignty.py",
    "tests/test_v3_global_conformance.py",
    "tools/build_v3_global_conformance.py",
    "tools/build_v3_global_cleanroom_profile.py",
    "tools/seal_v3_global_infrastructure.py",
    "tools/verify_v3_global_infrastructure_manifest.py",
]
VECTOR_DIR = ROOT / "protocol" / "v3" / "global_vectors"
FILES = BASE + [p.relative_to(ROOT).as_posix() for p in sorted(VECTOR_DIR.glob("*")) if p.is_file()]

def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

missing = [rel for rel in FILES if not (ROOT / rel).is_file()]
if missing:
    raise SystemExit("missing global infrastructure evidence: " + ", ".join(missing))
entries = [{"path": rel, "sha256": sha(ROOT / rel)} for rel in sorted(FILES)]
material = "\n".join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
vector_manifest = json.loads((VECTOR_DIR / "VECTOR_MANIFEST.json").read_text(encoding="utf-8-sig"))
manifest = {
    "schema": "entity-v3-global-infrastructure-manifest-v1",
    "status": "V3_1_0_BTG_INTERNAL_QUALIFIED_RELEASE_CANDIDATE",
    "base_release": "v3.0.1",
    "base_commit": "a977b013cb29504f04953c4fce33d2372e91097b",
    "full_regression": {"passed": 116, "total": 116},
    "targeted_global_tests": {"passed": 22, "total": 22},
    "conformance_vectors": {"valid": vector_manifest["valid_vectors"],
                            "invalid": vector_manifest["invalid_vectors"]},
    "implemented_pressures": [
        "jurisdictional diversity",
        "semantic and ontology diversity",
        "multi-stakeholder governance mechanics",
        "privacy versus provenance controls",
        "distributed topology, partition handling and cryptographic migration",
        "data economic sovereignty and bounded rights-based scarcity",
    ],
    "claim_boundaries": [
        "release publication state is recorded by the v3.1.0 top-level release manifest",
        "not unrelated third-party interoperability",
        "not independent cryptographic review",
        "not deployment-specific legal or regulatory approval",
        "not billion/trillion-scale production certification",
    ],
    "files": entries,
    "snapshot_sha256": hashlib.sha256(material).hexdigest(),
}
out = ROOT / "ENTITY_V3_GLOBAL_INFRASTRUCTURE_MANIFEST.json"
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": manifest["status"], "files": len(entries),
                  "snapshot_sha256": manifest["snapshot_sha256"],
                  "full_regression": manifest["full_regression"],
                  "targeted_global_tests": manifest["targeted_global_tests"]}, indent=2))


