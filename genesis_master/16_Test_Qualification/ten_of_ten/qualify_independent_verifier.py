from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TESTS=[ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier.py",ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier_licence_usage.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py"]
IMPL=ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_INDEPENDENT_VERIFIER_CURRENT.json"

def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    run=subprocess.run([sys.executable,"-m","pytest",*[str(x) for x in TESTS],"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-independent-verifier-qualification-v2","generated_at_ms":int(time.time()*1000),
             "status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,
             "limitations":[],"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),
             "implementation_sha256":sha(IMPL),"requirements_sha256":sha(ROOT/"16_Test_Qualification"/"ENTITY_REQUIREMENTS.md")}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence":str(OUT),"evidence_sha256":payload["evidence_sha256"]},indent=2))
    return run.returncode

if __name__=="__main__": raise SystemExit(main())
