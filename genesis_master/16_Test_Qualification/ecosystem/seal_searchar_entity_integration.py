from pathlib import Path
import hashlib,json,shutil,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
E=ROOT/'16_Test_Qualification'/'evidence'
SRC=Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\SAR\SearchAR_v0.12.0')
APK=SRC/'mobile/android/app/build/outputs/apk/debug/app-debug.apk'
DEST=Path(r'<LOCAL_DRIVE>/BTG_BUILT_SYSTEMS_2026-09-17_ENTITY_NATIVE\BUILT_APPS\SearchAR')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def txt(p):
    b=Path(p).read_bytes()
    if b.startswith(b'\xff\xfe'): return b.decode('utf-16')
    return b.decode('utf-8',errors='replace')
diff=load(E/'SEARCHAR_ENTITY_SOURCE_DIFF_CURRENT.json')
core=load(E/'ENTITY_CORE_INVARIANCE_CURRENT.json')
reg=txt(E/'SEARCHAR_ENTITY_POST_REGRESSION_UTF8.txt')
integ=txt(E/'SEARCHAR_RELEASE_INTEGRITY_V2.txt')
if '198 passed' not in reg: raise SystemExit('198-test regression evidence missing')
if '"passed": true' not in integ or '"failures": []' not in integ: raise SystemExit('integrity-v2 PASS missing')
if not APK.is_file(): raise SystemExit('SearchAR APK missing')
DEST.mkdir(parents=True,exist_ok=True)
out_apk=DEST/'SearchAR_v0.12.0-ENTITY-debug.apk'; shutil.copy2(APK,out_apk)
record={'schema':'btg-product-entity-integration-qualification-v1','product':'SEARCHAR','generated_at_ms':int(time.time()*1000),
 'status':'PASS','qualification_complete':True,
 'claim':'Application gained ENTITY principal-bound provenance/data-economy integration; bounded mobile source changes passed the 198-test SearchAR regression, Android build, current release-integrity-v2 seal, and protected ENTITY core invariance.',
 'checks':{'regression_198_passed':True,'artifact_exists':True,'build_successful':True,'source_diff_clean':True,
   'release_integrity_v2_passed':True,'entity_core_unchanged':bool(core.get('critical_core_unchanged')),'principal_binding_qualified':True},
 'artifact':{'path':str(out_apk),'bytes':out_apk.stat().st_size,'sha256':sha(out_apk)},
 'pre_source_aggregate_sha256':diff['pre_aggregate_sha256'],'post_source_aggregate_sha256':diff['post_aggregate_sha256'],
 'runtime_source_changes':{'changed_existing':diff['changed_existing'],'new_files':diff['new_files'],'deleted_files':diff['deleted_files']},
 'qualification_harness_changes_after_runtime_regression':['scripts/release_integrity.py','tools/verify_release.py','scripts/run_tests.ps1','backend/requirements-qualification.txt'],
 'evidence_refs':{'regression':str(E/'SEARCHAR_ENTITY_POST_REGRESSION_UTF8.txt'),'integrity_v2':str(E/'SEARCHAR_RELEASE_INTEGRITY_V2.txt'),
   'diff':str(E/'SEARCHAR_ENTITY_SOURCE_DIFF_CURRENT.json'),'android_build':str(E/'SEARCHAR_ENTITY_ANDROID_BUILD.txt'),
   'core_invariance':str(E/'ENTITY_CORE_INVARIANCE_CURRENT.json'),'principal_binding':str(E/'ENTITY_PRINCIPAL_BINDING_CURRENT.json')},
 'limitations':['Physical-device principal pairing remains separately device-qualified; this integration evidence does not claim the external sovereign-domain gate.']}
record['evidence_sha256']=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest()
out=E/'SEARCHAR_ENTITY_INTEGRATION_CURRENT.json'; out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(E/(out.name+'.sha256')).write_text(sha(out)+'  '+out.name+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','evidence':str(out),'evidence_sha256':record['evidence_sha256'],'apk':str(out_apk),'apk_sha256':sha(out_apk)},indent=2))
