from pathlib import Path
import hashlib, importlib.util, json, shutil, time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
PKG_ROOT=ROOT/'17_Release'/'packages'
RELEASE_ID='ENTITY_INTERNAL_QUALIFIED_2026-09-17'
OUT=PKG_ROOT/RELEASE_ID
OUT.mkdir(parents=True,exist_ok=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def copy(rel):
    src=ROOT/rel; dst=OUT/Path(rel).name; shutil.copy2(src,dst)
    return {'source':str(rel),'package_file':dst.name,'sha256':sha(dst),'bytes':dst.stat().st_size}
spec=importlib.util.spec_from_file_location('release_attestation',ROOT/'17_Release'/'supply_chain'/'canonical_release_attestation.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
source_roots=['00_Governance','01_Core_Runtime','02_Peer_Network','03_Public_Internet_Bridge','04_Entity_Registry','05_Entity_Nodes','06_Hosted_Sites','07_Hosted_Apps','08_Data_Vaults','09_Spatial_AR_Dashboard','11_ADAM','12_BSIE','13_Security','14_Protocols_SDK','15_Operations','16_Test_Qualification','17_Release','18_Research_Design','19_Sandbox','20_Archive','21_Corporate_Capital','22_Sovereign_Domain']
att=mod.create_release_attestation(ROOT,OUT/'supply_chain',RELEASE_ID,source_roots=source_roots)
artifacts=[]
for rel in [
    '17_Release/manifests/ENTITY_BUILD_MANIFEST_CURRENT.json','17_Release/manifests/ENTITY_BUILD_READINESS_CURRENT.json',
    '17_Release/manifests/ENTITY_10_10_RELEASE_GATE_CURRENT.json','16_Test_Qualification/traceability/MASTER_RTM.json',
    '16_Test_Qualification/evidence/ENTITY_GENESIS_PROOF_CURRENT.json','16_Test_Qualification/evidence/ENTITY_REPOSITORY_REGRESSION_CURRENT.json',
    '16_Test_Qualification/evidence/ENTITY_ULTIMATE_CHAOS_QUALIFICATION_CURRENT.json','16_Test_Qualification/evidence/ENTITY_POST_CHAOS_CLOSURE_CURRENT.json',
    '16_Test_Qualification/evidence/ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json',
    '16_Test_Qualification/evidence/ENTITY_BTG_APPLICATION_SDK_CURRENT.json',
    '16_Test_Qualification/evidence/ENTITY_OPEN_SDK_CURRENT.json']:
    artifacts.append(copy(rel))
ready=load(ROOT/'17_Release/manifests/ENTITY_BUILD_READINESS_CURRENT.json')
if not ready.get('build_ready'): raise SystemExit('build readiness not green')
manifest={'schema':'entity-qualified-source-build-v1','release_id':RELEASE_ID,'generated_at_ms':int(time.time()*1000),'status':'BUILT','build_mode':'IN_PLACE_CANONICAL_SOURCE_RUNTIME','source_root':str(ROOT),'source_tree_duplicated':False,'source_roots_covered':source_roots,'artifacts':artifacts,'supply_chain_manifest':att['manifest_ref'],'external_validation_pending':ready.get('deferred_non_build_blockers',[]),'claim':'Qualified internally executable ENTITY source/runtime build. External device/third-party milestones are explicitly not claimed as passed.'}
body=json.dumps(manifest,sort_keys=True,separators=(',',':'),default=str).encode(); manifest['evidence_sha256']=hashlib.sha256(body).hexdigest()
out=OUT/'ENTITY_QUALIFIED_BUILD_PACKAGE.json'; out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(OUT/'ENTITY_QUALIFIED_BUILD_PACKAGE.json.sha256').write_text(sha(out)+'  '+out.name+'\n',encoding='utf-8')
print(json.dumps({'status':'BUILT','release_id':RELEASE_ID,'output':str(OUT),'manifest':str(out),'evidence_sha256':manifest['evidence_sha256'],'supply_chain':att['manifest_ref']},indent=2))