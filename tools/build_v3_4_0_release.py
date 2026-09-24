from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/"ENTITY_V3_3_0_RELEASE_MANIFEST.json"
QUAL_PATH=ROOT/"docs/qualification/ENTITY_V3_4_0_RELEASE_QUALIFICATION_2026-09-24.json"
INGEST_PATH=ROOT/"docs/qualification/ENTITY_V3_4_0_CONTINUOUS_PROVENANCE_INGEST_2026-09-24.json"
base=json.loads(BASE_PATH.read_text(encoding="utf-8")); qualification=json.loads(QUAL_PATH.read_text(encoding="utf-8")); ingest=json.loads(INGEST_PATH.read_text(encoding="utf-8"))

overlay={
 "RELEASE_NOTES_v3.4.0.md",
 "docs/qualification/ENTITY_V3_4_0_RELEASE_QUALIFICATION_2026-09-24.json",
 "docs/qualification/ENTITY_V3_4_0_RELEASE_QUALIFICATION_2026-09-24.md",
 "docs/qualification/ENTITY_V3_4_0_CONTINUOUS_PROVENANCE_INGEST_2026-09-24.json",
 "protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json",
 "protocol/v3/ENTITY_V3_4_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json",
 "profiles/registry.json",
 "src/38_Global_Passports/profile_registry.py","src/38_Global_Passports/industry_profiles.py",
 "src/38_Global_Passports/global_passport.py","src/38_Global_Passports/continuous_ingestion.py",
 "src/38_Global_Passports/global_passport_profile.py","src/38_Global_Passports/passport_conformance.py",
 "src/39_Implementation_Packages/industry_packages.py",
 "sdk/global_passport_sdk/canonical_global_passport_sdk.py","sdk/global_passport_sdk/README.md",
 "tests/test_v3_global_passports.py",
 "tools/build_v3_4_cleanroom_kit.py","tools/verify_v3_4_global_passport_release.py",
 "tools/build_v3_4_industry_packages.py","tools/verify_v3_4_implementation_packages.py",
 "tools/entity_v3_4_cli.py","tools/build_v3_4_qualification.py","tools/ingest_v3_4_release.py",
 "tools/build_v3_4_0_release.py","tools/verify_v3_4_0_release_manifest.py","tools/run_v3_4_0_release_gate.ps1",
}
missing=[rel for rel in sorted(overlay) if not (ROOT/rel).is_file()]
if missing: raise SystemExit("missing v3.4 release-critical files: "+", ".join(missing))
def sha(path:pathlib.Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
entries=[{"path":rel,"sha256":sha(ROOT/rel)} for rel in sorted(overlay)]
material="\n".join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
overlay_snapshot=hashlib.sha256(material).hexdigest()
base_snapshot=base["release_snapshot_sha256"]
release_snapshot=hashlib.sha256(f"{base_snapshot}|{overlay_snapshot}".encode()).hexdigest()
manifest={
 "schema":"entity-v3-4-0-release-manifest-v1","version":"3.4.0",
 "status":"BTG_INTERNAL_QUALIFIED_GLOBAL_PASSPORT_CONTINUOUS_PROVENANCE_RELEASE_CANDIDATE",
 "release_date":"2026-09-24","repository":"blackmore-technology-group/ENTITY","supersedes":"v3.3.0",
 "base_commit":"9c79f987207592cb6791e1a8956f23351cdfb2d3",
 "base_release_manifest_sha256":sha(BASE_PATH),"base_release_snapshot_sha256":base_snapshot,
 "qualified_source_commit":qualification["qualified_source_commit"],"qualification":qualification,
 "continuous_provenance_ingest":{"files":ingest["files"],"inventory_sha256":ingest["inventory_sha256"],
   "historical_provenance_before_v3_4_claimed":ingest["historical_provenance_before_v3_4_claimed"]},
 "external_remaining":qualification["external_remaining"],"permanent_truth_boundaries":qualification["permanent_truth_boundaries"],
 "overlay_files":entries,"overlay_snapshot_sha256":overlay_snapshot,"release_snapshot_sha256":release_snapshot,
 "implementation_package_registry_sha256":qualification["implementation_packages"]["registry_sha256"],
 "six_language_controlled_interoperability":qualification["six_language_controlled_interoperability"],
 "release_chain":{"v3.3.0_protected_base":"9c79f987207592cb6791e1a8956f23351cdfb2d3",
                  "v3.4.0_qualified_source":qualification["qualified_source_commit"]}
}
out=ROOT/"ENTITY_V3_4_0_RELEASE_MANIFEST.json"
out.write_bytes((json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode("utf-8"))
print(json.dumps({"version":manifest["version"],"status":manifest["status"],"overlay_files":len(entries),
                  "overlay_snapshot_sha256":overlay_snapshot,"release_snapshot_sha256":release_snapshot,
                  "qualified_source_commit":manifest["qualified_source_commit"]},indent=2,sort_keys=True))
