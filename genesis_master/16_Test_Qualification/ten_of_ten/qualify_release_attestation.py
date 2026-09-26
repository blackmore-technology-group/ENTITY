from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"unit"/"test_release_attestation.py"
IMPL=ROOT/"17_Release"/"supply_chain"/"canonical_release_attestation.py"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_RELEASE_ATTESTATION_CURRENT.json"

def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-release-attestation-qualification-v1","generated_at_ms":int(time.time()*1000),
             "status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,
             "limitations":[],"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),
             "implementation_sha256":sha(IMPL),"requirements_sha256":sha(ROOT/"17_Release"/"ENTITY_REQUIREMENTS.md")}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence":str(OUT),"evidence_sha256":payload["evidence_sha256"]},indent=2))
    return run.returncode

if __name__=="__main__": raise SystemExit(main())
