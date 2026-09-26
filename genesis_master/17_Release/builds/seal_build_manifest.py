from pathlib import Path
import hashlib,json,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
M=ROOT/'17_Release'/'manifests'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ready=M/'ENTITY_BUILD_READINESS_CURRENT.json'; gate=M/'ENTITY_10_10_RELEASE_GATE_CURRENT.json'
chaos=ROOT/'16_Test_Qualification/evidence/ENTITY_ULTIMATE_CHAOS_QUALIFICATION_CURRENT.json'
reg=ROOT/'16_Test_Qualification/evidence/ENTITY_REPOSITORY_REGRESSION_CURRENT.json'
post=ROOT/'16_Test_Qualification/evidence/ENTITY_POST_CHAOS_CLOSURE_CURRENT.json'
sdk=ROOT/'16_Test_Qualification/evidence/ENTITY_BTG_APPLICATION_SDK_CURRENT.json'
r=load(ready)
if not r.get('build_ready') or r.get('status')!='BUILD_READY': raise SystemExit('build readiness not green')
payload={'schema':'entity-build-manifest-v1','generated_at_ms':int(time.time()*1000),'status':'BUILD_READY','source_root':str(ROOT),'packaging_mode':'IN_PLACE_SOURCE_BUILD','reason':'repository is ~41.8 GB and healthy local build volumes lack safe duplicate-package capacity','evidence':{str(p.relative_to(ROOT)):sha(p) for p in (ready,gate,chaos,reg,post,sdk)},'deferred_non_build_blockers':r.get('deferred_non_build_blockers',[]),'full_external_release_status':load(gate).get('status'),'claim':'ENTITY may proceed to software build from this source tree; deferred device/external-party qualification remains unclaimed.'}
raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode(); payload['evidence_sha256']=hashlib.sha256(raw).hexdigest()
out=M/'ENTITY_BUILD_MANIFEST_CURRENT.json'; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8'); out.with_suffix('.json.sha256').write_text(sha(out)+'  '+out.name+'\n',encoding='utf-8')
print(json.dumps({'status':payload['status'],'output':str(out),'evidence_sha256':payload['evidence_sha256'],'full_external_release_status':payload['full_external_release_status']},indent=2))
