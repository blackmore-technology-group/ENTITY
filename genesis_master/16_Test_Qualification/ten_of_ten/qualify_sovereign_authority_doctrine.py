from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"integration"/"test_section172_sovereign_authority_doctrine.py"
IMPL=ROOT/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py"
REQ=ROOT/"04_Entity_Registry"/"relationships"/"ENTITY_SUBSYSTEM_REQUIREMENTS.md"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_SOVEREIGN_AUTHORITY_DOCTRINE_CURRENT.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True); ok=run.returncode==0
    payload={"schema":"entity-sovereign-authority-doctrine-qualification-v1","scope":"SERS_ENTITY_003_SECTION_172_PROVIDER_NON_AUTHORITY_AND_REPLACEABILITY","generated_at_ms":int(time.time()*1000),"status":"PASS" if ok else "FAIL","qualification_complete":ok,"limitations":[],"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),"implementation_sha256":sha(IMPL),"requirements_sha256":sha(REQ),"invariants":["custody is not authority","storage is not ownership","processing is not consent","access is not a licence","economic participation requires explicit basis","provider authority is explicit and revocable","provider replacement preserves sovereign Entity root","provider replacement preserves sovereign authority semantics"]}
    payload["excluded_scope"]=["legal adjudication of ownership","remote deletion guarantees outside available evidence","physical destruction of former provider copies"]
    sealed=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(sealed).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"scope":payload["scope"],"evidence":str(OUT),"evidence_sha256":payload["evidence_sha256"]},indent=2)); return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
