from __future__ import annotations
import hashlib, importlib.util, json, os, pathlib, shutil, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
STATE=pathlib.Path(os.environ.get("ENTITY_V34_INGEST_STATE", str(ROOT.parent/"_ENTITY_V3_4_RELEASE_INGEST_STATE")))
OUT=ROOT/"docs/qualification/ENTITY_V3_4_0_CONTINUOUS_PROVENANCE_INGEST_2026-09-24.json"

def load(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel); mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

identity_mod=load("ing34_identity","src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod=load("ing34_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
rights_mod=load("ing34_rights","src/36_Adoption_Layer/rights_passport.py")
reality_profile=load("reality_profile","src/37_Verifiable_Reality/reality_profile.py")
evidence_mod=load("ing34_evidence","src/37_Verifiable_Reality/evidence_objects.py")
profile_mod=load("ing34_profiles","src/38_Global_Passports/profile_registry.py")
industry_mod=load("ing34_industry","src/38_Global_Passports/industry_profiles.py")
global_mod=load("ing34_global","src/38_Global_Passports/global_passport.py")
ingest_mod=load("ing34_ingest","src/38_Global_Passports/continuous_ingestion.py")

if STATE.exists(): shutil.rmtree(STATE)
identity=identity_mod.EntityIdentityVault(STATE); fabric=fabric_mod.UniversalTransactionFabric(STATE,identity)
controller=identity.create("ENTITY v3.4 Release Provenance","organization")["entity_id"]
evidence=evidence_mod.EvidenceRegistry(STATE,identity); rights=rights_mod.RightsPassportRegistry(STATE,identity,fabric)
profiles=profile_mod.GlobalProfileRegistry(STATE,identity); industry_mod.install_builtin_profiles(profiles,controller)
passports=global_mod.GlobalPassportRegistry(STATE,identity,fabric,rights,profiles)
ingestion=ingest_mod.ContinuousProvenanceEngine(STATE,identity,fabric,evidence,rights,passports)
FILES=[
 "src/38_Global_Passports/profile_registry.py",
 "src/38_Global_Passports/industry_profiles.py",
 "src/38_Global_Passports/global_passport.py",
 "src/38_Global_Passports/continuous_ingestion.py",
 "src/38_Global_Passports/global_passport_profile.py",
 "src/38_Global_Passports/passport_conformance.py",
 "src/39_Implementation_Packages/industry_packages.py",
 "sdk/global_passport_sdk/canonical_global_passport_sdk.py",
 "sdk/global_passport_sdk/README.md",
 "protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json",
 "protocol/v3/ENTITY_V3_4_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json",
 "profiles/registry.json",
 "profiles/ENTITY_V3_4_IMPLEMENTATION_PACKAGES.json",
 "tools/build_v3_4_cleanroom_kit.py",
 "tools/verify_v3_4_global_passport_release.py",
 "tools/build_v3_4_industry_packages.py",
 "tools/entity_v3_4_cli.py",
 "tests/test_v3_global_passports.py",
 "docs/qualification/ENTITY_V3_4_0_RELEASE_QUALIFICATION_2026-09-24.json",
 "docs/qualification/ENTITY_V3_4_0_RELEASE_QUALIFICATION_2026-09-24.md",
 "RELEASE_NOTES_v3.4.0.md",
]
records=[]
for rel in FILES:
    path=ROOT/rel
    if not path.is_file(): raise SystemExit(f"missing release-ingest file: {rel}")
    item=ingestion.ingest_file(path,controller,["entity-profile:global@1.0","entity-profile:ai@1.0"],logical_path=rel,version="3.4.0")
    checked=passports.verify(item["global_passport"])
    if not checked["valid"]: raise SystemExit(f"passport verification failed: {rel}")
    records.append({
      "path":rel,
      "content_sha256":item["object"]["content_sha256"],
      "object_id":item["object"]["object_id"],
      "evidence_id":item["evidence"]["evidence_id"],
      "rights_passport_id":item["rights_passport"]["passport_id"],
      "global_passport_id":item["global_passport"]["passport_id"],
      "global_passport_sha256":item["global_passport"]["body_sha256"],
      "passport_valid":True,
      "economic_value_invented":False,
      "custody_is_not_authority":True})

material="\n".join(f"{r['content_sha256']}  {r['path']}" for r in records).encode()
report={
 "schema":"entity-v3-4-continuous-provenance-release-ingest-v1",
 "version":"3.4.0","date":"2026-09-24",
 "qualified_source_commit":"854529e6cb88e77f29cce581beb74b530768224c",
 "controller_entity_id":controller,
 "profile_refs":["entity-profile:global@1.0","entity-profile:ai@1.0"],
 "files":len(records),"inventory_sha256":hashlib.sha256(material).hexdigest(),"records":records,
 "content_addressed":True,"custody_is_not_authority":True,"provider_credentials_included":False,
 "economic_value_invented":False,"historical_provenance_before_v3_4_claimed":False,
 "claim_boundary":"This campaign proves v3.4 release artifacts were registered under the new continuous-provenance workflow; it does not reconstruct or certify pre-v3.4 history."
}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"files":report["files"],"inventory_sha256":report["inventory_sha256"],"state":str(STATE),"report":str(OUT)},indent=2))
