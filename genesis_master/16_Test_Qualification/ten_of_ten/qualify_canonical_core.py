from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); CORE=ROOT/"01_Core_Runtime"
TESTS=[ROOT/"16_Test_Qualification/unit/test_canonical_core_runtime.py",ROOT/"16_Test_Qualification/integration/test_release_closure_authorities.py::test_tpm_hardware_custody_and_portable_recovery",ROOT/"16_Test_Qualification/integration/test_release_closure_authorities.py::test_canonical_service_full_domain_surface"]
EVIDENCE=ROOT/"16_Test_Qualification/evidence/ENTITY_CANONICAL_CORE_QUALIFICATION_CURRENT.json"
FILES=[CORE/"identity/canonical_identity.py",CORE/"policy_engine/canonical_policy.py",CORE/"permissions/canonical_permissions.py",CORE/"api/canonical_service.py",ROOT/"13_Security/key_management/canonical_hardware_keys.py",ROOT/"13_Security/key_management/canonical_key_management.py",ROOT/"15_Operations/backups/canonical_portable_state.py"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tpm_status():
    p=ROOT/'13_Security/key_management/canonical_hardware_keys.py'; s=importlib.util.spec_from_file_location('core_hw_qual',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.commissioning_status()

def main():
    args=[sys.executable,'-m','pytest',*map(str,TESTS),'-q']; run=subprocess.run(args,cwd=str(ROOT),capture_output=True,text=True); tpm=tpm_status()
    limitations=[]
    if not tpm.get('commissioned'): limitations.append('hardware-backed root/recovery key protection not commissioned')
    if run.returncode!=0: limitations.append('canonical core/service API qualification failed')
    payload={'schema':'entity-canonical-core-qualification-v3','generated_at_ms':int(time.time()*1000),'status':'PASS' if not limitations else 'FAIL','scope':'ROOT_OWNED_CANONICAL_CORE_FOUNDATION_V2_2','pytest_exit_code':run.returncode,'pytest_output':(run.stdout+'\n'+run.stderr).strip(),'requirements_sha256':sha(CORE/'ENTITY_REQUIREMENTS.md'),'implementation_sha256':{str(p.relative_to(ROOT)):sha(p) for p in FILES},'tpm_commissioning':tpm,'limitations':limitations}
    payload['evidence_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(); EVIDENCE.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'limitations':limitations,'evidence_sha256':payload['evidence_sha256']},indent=2)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
