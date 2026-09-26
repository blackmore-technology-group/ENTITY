from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network'); EV=ROOT/'16_Test_Qualification'/'evidence'
TEST=ROOT/'16_Test_Qualification'/'closure'/'test_engineering_requirements_closure.py'
IMPL=ROOT/'01_Core_Runtime'/'engineering_controls'/'canonical_engineering_controls.py'
OUT=EV/'ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
run=subprocess.run([sys.executable,'-m','pytest','-q',str(TEST)],cwd=str(ROOT),capture_output=True,text=True)
status='PASS' if run.returncode==0 and '11 passed' in run.stdout else 'FAIL'
record={'schema':'entity-engineering-requirements-closure-v1','generated_at_ms':int(time.time()*1000),'status':status,'qualification_complete':status=='PASS','pytest_exit_code':run.returncode,'pytest_output':run.stdout.strip(),'implementation_sha256':sha(IMPL),'test_sha256':sha(TEST),'qualified_control_domains':['governance_authority','claim_evidence_transition','entity_nodes','hosted_sites','hosted_apps','security_privacy','public_gateway','operations_slo_telemetry_incident','provider_migration','android_sdk','apple_sdk','web_sdk','windows_sdk','adam_authority_boundary','bsie_projection_boundary','release_fail_closed','research_sandbox_promotion','archive_historical_integrity'],'invariants':['default deny','private by default','unknown is not verified','high-impact approval required','node/device authority is revocable and not root identity','replay/idempotency enforced','exclusive conflicts fail closed','publication is explicit export state','untrusted content is not authority','minimum disclosure removes secrets','telemetry minimizes sensitive identifiers','provider migration preserves sovereign roots/semantics','SDKs expose versioned explicit scopes','ADAM does not inherit root authority','BSIE observation does not imply legal rights','critical release defects block release'],'limitations':[]}
body=json.dumps(record,sort_keys=True,separators=(',',':'),default=str).encode(); record['evidence_sha256']=hashlib.sha256(body).hexdigest()
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8'); OUT.with_suffix('.json.sha256').write_text(sha(OUT)+'  '+OUT.name+'\n',encoding='utf-8')
print(json.dumps({'status':status,'evidence_sha256':record['evidence_sha256'],'output':str(OUT)},indent=2)); raise SystemExit(0 if status=='PASS' else 2)

