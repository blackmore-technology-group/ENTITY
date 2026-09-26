from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"unit"/"test_phase1_sovereignty.py"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_PHASE1_STORAGE_PORTABILITY_CURRENT.json"
FILES=[ROOT/"08_Data_Vaults"/"canonical_data_source_gateway.py",ROOT/"08_Data_Vaults"/"canonical_encrypted_vault.py",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py"]

def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def seal(payload:dict,path:Path):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return payload["evidence_sha256"]

def main()->int:
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    common={"generated_at_ms":int(time.time()*1000),"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),
            "implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in FILES}}
    scoped=dict(common, schema="entity-phase1-storage-portability-qualification-v1",status="PASS" if run.returncode==0 else "FAIL",
                qualification_complete=run.returncode==0,limitations=[],qualified_authorities=["data_sources","data_vault","portable_state"],
                requirements_sha256={"08_Data_Vaults":sha(ROOT/"08_Data_Vaults"/"ENTITY_REQUIREMENTS.md"),"15_Operations":sha(ROOT/"15_Operations"/"ENTITY_REQUIREMENTS.md")})
    scoped_hash=seal(scoped,OUT)
    print(json.dumps({"status":scoped["status"],"scoped_evidence_sha256":scoped_hash},indent=2))
    return run.returncode

if __name__=="__main__": raise SystemExit(main())
