from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_MANIFEST_PATH = ROOT / "ENTITY_V3_2_0_RELEASE_MANIFEST.json"
QUAL_PATH = ROOT / "docs" / "qualification" / "ENTITY_V3_3_0_RELEASE_QUALIFICATION_2026-09-24.json"
base = json.loads(BASE_MANIFEST_PATH.read_text(encoding="utf-8"))
qualification = json.loads(QUAL_PATH.read_text(encoding="utf-8"))
overlay = {
    "README.md",
    "START_HERE.md",
    "CONTRIBUTING.md",
    "docs/ENGINEERING_EVIDENCE.md",
    "docs/INTEROPERABILITY_CHALLENGE.md",
    "RELEASE_NOTES_v3.3.0.md",
    "docs/qualification/ENTITY_V3_3_0_RELEASE_QUALIFICATION_2026-09-24.json",
    "docs/qualification/ENTITY_V3_3_0_RELEASE_QUALIFICATION_2026-09-24.md",
    "protocol/v3/ENTITY_V3_3_REALITY_CLEANROOM_KIT.min.json",
    "protocol/v3/ENTITY_VERIFIABLE_REALITY.schema.json",
    "src/37_Verifiable_Reality/attestation_authority.py",
    "src/37_Verifiable_Reality/causal_economic_graph.py",
    "src/37_Verifiable_Reality/evidence_objects.py",
    "src/37_Verifiable_Reality/reality_anchors.py",
    "src/37_Verifiable_Reality/reality_conformance.py",
    "src/37_Verifiable_Reality/reality_profile.py",
    "tests/test_v3_verifiable_reality.py",
    "tools/build_v3_3_reality_cleanroom_kit.py",
    "tools/verify_v3_3_reality_release.py",
    "tools/build_v3_3_0_release.py",
    "tools/verify_v3_3_0_release_manifest.py",
    "tools/run_v3_3_0_release_gate.ps1",
}
missing=[rel for rel in sorted(overlay) if not (ROOT/rel).is_file()]
if missing:
    raise SystemExit("missing v3.3 release-critical files: "+", ".join(missing))

def sha(path:pathlib.Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
entries=[{"path":rel,"sha256":sha(ROOT/rel)} for rel in sorted(overlay)]
material="\n".join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
overlay_snapshot=hashlib.sha256(material).hexdigest()
base_snapshot=base["overlay_snapshot_sha256"]
release_snapshot=hashlib.sha256(f"{base_snapshot}|{overlay_snapshot}".encode()).hexdigest()
manifest={
    "schema":"entity-v3-3-0-release-manifest-v1","version":"3.3.0",
    "status":"BTG_INTERNAL_QUALIFIED_VERIFIABLE_REALITY_RELEASE_CANDIDATE",
    "release_date":"2026-09-24","repository":"blackmore-technology-group/ENTITY","supersedes":"v3.2.0",
    "base_commit":"512665096cef3771a3a8307d6dc955015ee0efbc",
    "base_release_manifest_sha256":sha(BASE_MANIFEST_PATH),
    "base_release_snapshot_sha256":base_snapshot,
    "qualified_source_commit":qualification["qualified_source_commit"],
    "qualification":qualification,
    "external_remaining":qualification["external_remaining"],
    "permanent_truth_boundaries":qualification["permanent_truth_boundaries"],
    "overlay_files":entries,"overlay_snapshot_sha256":overlay_snapshot,"release_snapshot_sha256":release_snapshot,
    "release_chain":{"v3.1.0_protected_base":"b985b7cf875bdeeadb228d4d1885395cbcaf19f1","v3.2.0_protected_base":"512665096cef3771a3a8307d6dc955015ee0efbc","v3.3.0_qualified_source":qualification["qualified_source_commit"]}
}
out=ROOT/"ENTITY_V3_3_0_RELEASE_MANIFEST.json"
out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"version":manifest["version"],"status":manifest["status"],"base_release_snapshot_sha256":base_snapshot,"overlay_files":len(entries),"overlay_snapshot_sha256":overlay_snapshot,"release_snapshot_sha256":release_snapshot},indent=2,sort_keys=True))
