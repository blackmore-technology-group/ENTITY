from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
conf=load("v34_kit_conf",ROOT/"src/38_Global_Passports/passport_conformance.py")
Z="0"*64; O="1"*64; T="2"*64
CORE=["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"]
def profile(pid,kind="INDUSTRY",public=True):
    return {"schema":"entity-v3-global-profile-v1","profile_ref":pid+"@1.0","profile_id":pid,"version":"1.0","kind":kind,"schema_sha256":Z,"profile_is_not_authority":True,"standards_mapping_is_not_normative_equivalence":True,"public_unclassified":public}
def stack(refs):
    return {"schema":"entity-v3-profile-stack-resolution-v1","profile_refs":refs,"profile_hashes":[O for _ in refs],"fail_closed":True,"profile_composition_does_not_create_authority":True,"standards_mapping_is_not_normative_equivalence":True}
def passport(refs,mappings=None):
    return {"schema":"entity-v3-global-passport-v1","core_primitives":CORE,"rights_passport_id":"passport3-example","rights_passport_sha256":T,"profile_stack":stack(refs),"standards_mappings":mappings or [],"economic_state":{"state":"POTENTIAL","amount_units":0,"currency":"UNSPECIFIED","market_observation_is_not_accounting_fair_value":True},"one_passport_many_profiles":True,"profile_composition_does_not_create_authority":True,"standards_mapping_is_not_normative_equivalence":True,"evidence_does_not_establish_objective_truth":True,"legal_effect_is_deployment_specific":True,"underlying_information_remains_nonrival":True}
def status():
    return {"schema":"entity-v3-global-passport-profile-status-v1","core_primitives":CORE,"core_semantics_changed":False,"market_engine_preserved":True,"one_passport_many_profiles":True,"evidence_truth_boundary_preserved":True}
def ingest():
    return {"schema":"entity-v3-continuous-ingest-result-v1","files":3,"inventory_sha256":Z,"content_addressed":True,"custody_is_not_authority":True,"economic_value_invented":False}

cases=[]
def add(cid,expect,record): cases.append({"id":cid,"expect":expect,"record":record})
add("valid_status","VALID",status())
add("valid_global_profile","VALID",profile("entity-profile:global","GLOBAL"))
add("valid_healthcare_profile","VALID",profile("entity-profile:healthcare"))
add("valid_finance_profile","VALID",profile("entity-profile:finance"))
add("valid_manufacturing_profile","VALID",profile("entity-profile:manufacturing"))
add("valid_ai_profile","VALID",profile("entity-profile:ai"))
add("valid_robotics_profile","VALID",profile("entity-profile:robotics"))
add("valid_defence_profile","VALID",profile("entity-profile:defence-public",public=True))
add("valid_stack_multi","VALID",stack(["entity-profile:global@1.0","entity-profile:healthcare@1.0","entity-profile:ai@1.0"]))
add("valid_passport_ai","VALID",passport(["entity-profile:global@1.0","entity-profile:ai@1.0"]))
add("valid_passport_finance_mapping","VALID",passport(["entity-profile:global@1.0","entity-profile:finance@1.0"],[{"standard":"ISO-20022","normative_equivalence_claimed":False}]))
add("valid_ingest","VALID",ingest())
x=status(); x["core_semantics_changed"]=True; add("invalid_status_core_change","INVALID",x)
x=profile("entity-profile:ai"); x["profile_is_not_authority"]=False; add("invalid_profile_authority","INVALID",x)
x=profile("entity-profile:ai"); x["kind"]="UNKNOWN"; add("invalid_profile_kind","INVALID",x)
x=profile("entity-profile:defence-public",public=False); add("invalid_defence_not_public","INVALID",x)
x=stack(["entity-profile:ai@1.0"]); add("invalid_stack_missing_global","INVALID",x)
x=stack(["entity-profile:global@1.0"]); x["profile_hashes"]=["bad"]; add("invalid_stack_bad_hash","INVALID",x)
x=passport(["entity-profile:global@1.0"]); x["evidence_does_not_establish_objective_truth"]=False; add("invalid_passport_truth","INVALID",x)
x=passport(["entity-profile:global@1.0"],[{"standard":"FHIR","normative_equivalence_claimed":True}]); add("invalid_passport_equivalence","INVALID",x)
x=passport(["entity-profile:global@1.0"]); x["underlying_information_remains_nonrival"]=False; add("invalid_passport_scarcity","INVALID",x)
x=passport(["entity-profile:global@1.0"]); x["core_primitives"]=["ENTITY","TOKEN"]; add("invalid_passport_core","INVALID",x)
x=ingest(); x["files"]=-1; add("invalid_ingest_negative_files","INVALID",x)
x=ingest(); x["economic_value_invented"]=True; add("invalid_ingest_fake_value","INVALID",x)

cases.sort(key=lambda x:x["id"])
for case in cases:
    actual="VALID" if conf.validate_global_passport_record(case["record"]) else "INVALID"
    if actual!=case["expect"]: raise SystemExit(f"vector expectation mismatch {case['id']}: {actual}")
rows=[{"id":c["id"],"actual":"VALID" if conf.validate_global_passport_record(c["record"]) else "INVALID"} for c in cases]
result_sha=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
schema_path=ROOT/"protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json"
kit={"schema":"entity-v3.4-global-passport-cleanroom-kit-v1","version":"3.4.1","base_release":"v3.4.0",
     "base_commit":"2db5bff64507b8d67642122a5ff2fc73dfef9152","schema_sha256":hashlib.sha256(schema_path.read_bytes()).hexdigest(),
     "doctrine":"One ENTITY Passport. Many jurisdictions, industries, standards and contexts. No new sovereignty silos.",
     "valid_vectors":sum(c["expect"]=="VALID" for c in cases),"invalid_vectors":sum(c["expect"]=="INVALID" for c in cases),
     "expected_result_sha256":result_sha,"cases":cases}
out=ROOT/"protocol/v3/ENTITY_V3_4_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json"
out.write_bytes(json.dumps(kit,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
print(json.dumps({"kit":str(out),"cases":len(cases),"valid":kit["valid_vectors"],"invalid":kit["invalid_vectors"],
                  "schema_sha256":kit["schema_sha256"],"expected_result_sha256":result_sha,
                  "kit_sha256":hashlib.sha256(out.read_bytes()).hexdigest()},indent=2))
