from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]; PATH=ROOT/"ENTITY_V3_4_0_RELEASE_MANIFEST.json"; BASE=ROOT/"ENTITY_V3_3_0_RELEASE_MANIFEST.json"
manifest=json.loads(PATH.read_text(encoding="utf-8")); base=json.loads(BASE.read_text(encoding="utf-8")); errors=[]
def sha(path:pathlib.Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
if sha(BASE)!=manifest.get("base_release_manifest_sha256"): errors.append("base_manifest")
if base.get("release_snapshot_sha256")!=manifest.get("base_release_snapshot_sha256"): errors.append("base_snapshot")
for entry in manifest.get("overlay_files",[]):
    path=ROOT/entry["path"]
    if not path.is_file(): errors.append("missing:"+entry["path"]); continue
    actual=sha(path)
    if actual!=entry["sha256"]: errors.append("hash:"+entry["path"])
material="\n".join(f"{x['path']}|{x['sha256']}" for x in sorted(manifest.get("overlay_files",[]),key=lambda x:x["path"])).encode()
overlay_root=hashlib.sha256(material).hexdigest()
if overlay_root!=manifest.get("overlay_snapshot_sha256"): errors.append("overlay_snapshot")
release_root=hashlib.sha256(f"{manifest.get('base_release_snapshot_sha256')}|{overlay_root}".encode()).hexdigest()
if release_root!=manifest.get("release_snapshot_sha256"): errors.append("release_snapshot")
q=manifest.get("qualification") or {}; ingest=manifest.get("continuous_provenance_ingest") or {}
if q.get("version")!="3.4.0" or q.get("regression",{}).get("passed")!=177 or q.get("targeted_global_passport_tests",{}).get("passed")!=33: errors.append("qualification_summary")
if q.get("qualified_source_commit")!="854529e6cb88e77f29cce581beb74b530768224c": errors.append("qualified_source")
if q.get("global_passport_conformance",{}).get("expected_result_sha256")!="ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba": errors.append("conformance_result")
if ingest.get("files")!=21 or ingest.get("historical_provenance_before_v3_4_claimed") is not False: errors.append("ingest_summary")
langs=q.get("six_language_controlled_interoperability",{}).get("implementations",{})
if set(langs)!={"rust","typescript","go","csharp","java","swift"}: errors.append("six_language_set")
if q.get("six_language_controlled_interoperability",{}).get("independent_third_party_interoperability") is not False: errors.append("independence_boundary")
result={"valid":not errors,"version":manifest.get("version"),"status":manifest.get("status"),
        "overlay_files":len(manifest.get("overlay_files",[])),"overlay_snapshot_sha256":overlay_root,
        "release_snapshot_sha256":release_root,"qualified_source_commit":manifest.get("qualified_source_commit"),"errors":errors}
print(json.dumps(result,indent=2,sort_keys=True)); sys.exit(0 if not errors else 2)
