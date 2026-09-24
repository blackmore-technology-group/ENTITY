from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_MANIFEST_PATH = ROOT / "ENTITY_V3_1_0_RELEASE_MANIFEST.json"
QUAL_PATH = ROOT / "docs" / "qualification" / "ENTITY_V3_2_0_RELEASE_QUALIFICATION_2026-09-24.json"
base = json.loads(BASE_MANIFEST_PATH.read_text(encoding="utf-8-sig"))
qualification = json.loads(QUAL_PATH.read_text(encoding="utf-8"))
overlay = {
    "RELEASE_NOTES_v3.2.0.md",
    "docs/qualification/ENTITY_V3_2_0_RELEASE_QUALIFICATION_2026-09-24.json",
    "docs/qualification/ENTITY_V3_2_0_RELEASE_QUALIFICATION_2026-09-24.md",
    "protocol/v3/ENTITY_V3_2_ADOPTION_CLEANROOM_KIT.min.json",
    "src/36_Adoption_Layer/rights_passport.py",
    "src/36_Adoption_Layer/custody_connectors.py",
    "src/36_Adoption_Layer/standards_adapters.py",
    "src/36_Adoption_Layer/adoption_profile.py",
    "src/36_Adoption_Layer/adoption_conformance.py",
    "tests/test_v3_adoption_layer.py",
    "tools/build_v3_2_adoption_conformance.py",
    "tools/build_v3_2_adoption_cleanroom_profile.py",
    "tools/build_v3_2_adoption_cleanroom_kit.py",
    "tools/verify_v3_2_adoption_release.py",
    "tools/build_v3_2_0_release.py",
    "tools/verify_v3_2_0_release_manifest.py",
    "tools/run_v3_2_0_release_gate.ps1"
}
missing = [rel for rel in sorted(overlay) if not (ROOT / rel).is_file()]
if missing:
    raise SystemExit("missing v3.2 release-critical files: " + ", ".join(missing))

def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

entries = [{"path": rel, "sha256": sha(ROOT / rel)} for rel in sorted(overlay)]
material = "\n".join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
manifest = {
    "schema": "entity-v3-2-0-release-manifest-v1",
    "version": "3.2.0",
    "status": "BTG_INTERNAL_QUALIFIED_ADOPTION_RELEASE_CANDIDATE",
    "release_date": "2026-09-24",
    "repository": "blackmore-technology-group/ENTITY",
    "supersedes": "v3.1.0",
    "base_commit": "b985b7cf875bdeeadb228d4d1885395cbcaf19f1",
    "base_release_manifest_sha256": sha(BASE_MANIFEST_PATH),
    "base_release_snapshot_sha256": base["release_snapshot_sha256"],
    "qualified_source_commit": qualification["qualified_source_commit"],
    "qualification": qualification,
    "external_remaining": qualification["external_remaining"],
    "permanent_truth_boundaries": qualification["permanent_truth_boundaries"],
    "overlay_files": entries,
    "overlay_snapshot_sha256": hashlib.sha256(material).hexdigest(),
    "release_chain": {
        "v3.0.1_protected_base": "a977b013cb29504f04953c4fce33d2372e91097b",
        "v3.1.0_protected_base": "b985b7cf875bdeeadb228d4d1885395cbcaf19f1",
        "v3.2.0_qualified_source": qualification["qualified_source_commit"]
    }
}
out = ROOT / "ENTITY_V3_2_0_RELEASE_MANIFEST.json"
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "version": manifest["version"],
    "status": manifest["status"],
    "base_release_snapshot_sha256": manifest["base_release_snapshot_sha256"],
    "base_release_manifest_sha256": manifest["base_release_manifest_sha256"],
    "overlay_files": len(entries),
    "overlay_snapshot_sha256": manifest["overlay_snapshot_sha256"]
}, indent=2, sort_keys=True))
