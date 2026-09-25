from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/"ENTITY_V3_4_0_RELEASE_MANIFEST.json"
QUAL_PATH=ROOT/"docs/qualification/ENTITY_V3_4_1_RELEASE_QUALIFICATION_2026-09-25.json"
base=json.loads(BASE_PATH.read_text(encoding="utf-8"))
qualification=json.loads(QUAL_PATH.read_text(encoding="utf-8"))
overlay={
 "RELEASE_NOTES_v3.4.1.md",
 "docs/qualification/ENTITY_HISTORICAL_RELEASE_LINEAGE_INGEST_2026-09-25.json",
 "docs/qualification/ENTITY_V3_4_1_RELEASE_QUALIFICATION_2026-09-25.json",
 "docs/qualification/ENTITY_V3_4_1_RELEASE_QUALIFICATION_2026-09-25.md",
 "protocol/origin/ENTITY_PROTOCOL_ORIGIN_BUNDLE.json","protocol/origin/README.md",
 "protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json",
 "protocol/v3/ENTITY_V3_4_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json",
 "sdk/global_passport_sdk/canonical_global_passport_sdk.py",
 "src/01_Core_Runtime/identity/canonical_identity.py",
 "src/38_Global_Passports/continuous_ingestion.py","src/38_Global_Passports/global_passport.py",
 "src/38_Global_Passports/profile_registry.py","src/38_Global_Passports/protocol_origin.py",
 "tests/test_v3_protocol_origin_lineage.py",
 "tools/entity_v3_4_cli.py","tools/build_v3_4_cleanroom_kit.py",
 "tools/verify_v3_4_global_passport_release.py","tools/build_release_origin_attestation.py",
}
overlay |= {
 "tools/build_v3_4_1_qualification.py","tools/build_v3_4_1_release.py",
 "tools/verify_v3_4_1_release_manifest.py","tools/run_v3_4_1_release_gate.ps1",
}
missing=[rel for rel in sorted(overlay) if not (ROOT/rel).is_file()]
if missing: raise SystemExit("missing v3.4.1 release-critical files: "+", ".join(missing))
def sha(path:pathlib.Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
entries=[{"path":rel,"sha256":sha(ROOT/rel)} for rel in sorted(overlay)]
material="\n".join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
overlay_snapshot=hashlib.sha256(material).hexdigest()
base_snapshot=base["release_snapshot_sha256"]
release_snapshot=hashlib.sha256(f"{base_snapshot}|{overlay_snapshot}".encode()).hexdigest()
manifest={
 "schema":"entity-v3-4-1-release-manifest-v1","version":"3.4.1",
 "status":"BTG_INTERNAL_QUALIFIED_PROTOCOL_ORIGIN_LINEAGE_SOVEREIGN_BOOTSTRAP_PATCH",
 "release_date":"2026-09-25","repository":"blackmore-technology-group/ENTITY",
 "supersedes":"v3.4.0","base_commit":"2db5bff64507b8d67642122a5ff2fc73dfef9152",
 "base_release_manifest_sha256":sha(BASE_PATH),"base_release_snapshot_sha256":base_snapshot,
 "qualified_source_commit":qualification["qualified_source_commit"],"qualification":qualification,
 "overlay_files":entries,"overlay_snapshot_sha256":overlay_snapshot,
 "release_snapshot_sha256":release_snapshot,
 "global_passport_conformance":qualification["global_passport_conformance"],
 "six_language_controlled_interoperability":qualification["six_language_controlled_interoperability"],
 "implementation_packages":qualification["implementation_packages"],
 "protocol_origin":qualification["protocol_origin"],
 "migration":qualification["v3_4_0_migration"],
 "data_economy_lineage":qualification["data_economy_lineage"],
 "post_tag_release_origin":{"required":True,"artifact":"ENTITY_CURRENT_RELEASE_ORIGIN.json",
   "reason":"exact tag commit/tree cannot be self-referentially signed inside the same commit"},
 "external_remaining":qualification["external_remaining"],
 "release_chain":{"v3.4.0_protected_base":"2db5bff64507b8d67642122a5ff2fc73dfef9152",
   "v3.4.1_qualified_source":qualification["qualified_source_commit"]}
}
out=ROOT/"ENTITY_V3_4_1_RELEASE_MANIFEST.json"
out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"version":manifest["version"],"overlay_files":len(entries),
 "overlay_snapshot_sha256":overlay_snapshot,"release_snapshot_sha256":release_snapshot,
 "qualified_source_commit":manifest["qualified_source_commit"]},indent=2,sort_keys=True))
