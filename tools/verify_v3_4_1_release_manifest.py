from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"ENTITY_V3_4_1_RELEASE_MANIFEST.json"
BASE=ROOT/"ENTITY_V3_4_0_RELEASE_MANIFEST.json"
manifest=json.loads(PATH.read_text(encoding="utf-8"))
base=json.loads(BASE.read_text(encoding="utf-8")); errors=[]
def sha(path:pathlib.Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
if manifest.get("version")!="3.4.1": errors.append("version")
if sha(BASE)!=manifest.get("base_release_manifest_sha256"): errors.append("base_manifest")
if base.get("release_snapshot_sha256")!=manifest.get("base_release_snapshot_sha256"): errors.append("base_snapshot")
for entry in manifest.get("overlay_files",[]):
 path=ROOT/entry["path"]
 if not path.is_file(): errors.append("missing:"+entry["path"]); continue
 if sha(path)!=entry["sha256"]: errors.append("hash:"+entry["path"])
material="\n".join(f"{x['path']}|{x['sha256']}" for x in sorted(manifest.get("overlay_files",[]),key=lambda x:x["path"])).encode()
overlay_root=hashlib.sha256(material).hexdigest()
if overlay_root!=manifest.get("overlay_snapshot_sha256"): errors.append("overlay_snapshot")
release_root=hashlib.sha256(f"{manifest.get('base_release_snapshot_sha256')}|{overlay_root}".encode()).hexdigest()
if release_root!=manifest.get("release_snapshot_sha256"): errors.append("release_snapshot")
q=manifest.get("qualification") or {}
if q.get("qualified_source_commit")!="04d7386c70ef1665ea44824d16e1bb09f5329ca8": errors.append("qualified_source")
if q.get("regression")!={"environment":"_venv_entity_v3","passed":185,"total":185}: errors.append("regression")
if q.get("targeted_protocol_origin_tests",{}).get("passed")!=8: errors.append("origin_tests")
if q.get("targeted_global_passport_tests",{}).get("passed")!=33: errors.append("global_tests")
conf=q.get("global_passport_conformance") or {}
if conf.get("sealed_kit_sha256")!="f95c2b347da97742fed3f20611f0eec2fd3df48694fed9494fb07163c537cfb7": errors.append("kit_sha")
if conf.get("schema_sha256")!="3d72b4e67ec9929c5d960cee8fc52db35d85ba5103e361f3a61a8f5078079c5d": errors.append("schema_sha")
if conf.get("expected_result_sha256")!="ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba": errors.append("result_sha")
langs=q.get("six_language_controlled_interoperability",{}).get("implementations",{})
if set(langs)!={"rust","typescript","go","csharp","java","swift"}: errors.append("six_language_set")
if any(v.get("conclusion")!="success" for v in langs.values()): errors.append("six_language_result")
if q.get("six_language_controlled_interoperability",{}).get("independent_third_party_interoperability") is not False: errors.append("claim_boundary")
if q.get("implementation_packages",{}).get("packages")!=6: errors.append("packages")
origin=q.get("protocol_origin") or {}
if origin.get("historical_release_anchors")!=9 or origin.get("automatic_protocol_royalty_bps")!=0: errors.append("origin_boundary")
migration=q.get("v3_4_0_migration") or {}
if not all(migration.get(k) is True for k in ("user_entity_unchanged","user_objects_unchanged","rights_passports_unchanged","historical_global_passport_verifies")): errors.append("migration")
econ=q.get("data_economy_lineage") or {}
if econ.get("status")!="PASS" or econ.get("protocol_tax_bps")!=0 or econ.get("trade_capture_reconciliation_complete") is not True: errors.append("economic_lineage")
post=manifest.get("post_tag_release_origin") or {}
if post.get("required") is not True or post.get("artifact")!="ENTITY_CURRENT_RELEASE_ORIGIN.json": errors.append("post_tag_origin")
result={"valid":not errors,"version":manifest.get("version"),"status":manifest.get("status"),
 "overlay_files":len(manifest.get("overlay_files",[])),"overlay_snapshot_sha256":overlay_root,
 "release_snapshot_sha256":release_root,"qualified_source_commit":manifest.get("qualified_source_commit"),
 "regression":q.get("regression"),"six_language":"PASS" if not any(e.startswith("six_language") for e in errors) else "FAIL",
 "implementation_packages":q.get("implementation_packages",{}).get("packages"),"errors":errors}
print(json.dumps(result,indent=2,sort_keys=True))
sys.exit(0 if not errors else 2)