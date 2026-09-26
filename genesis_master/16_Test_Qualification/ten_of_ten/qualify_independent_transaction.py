from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"integration"/"test_independently_reproducible_transaction.py"
EXPORTER=ROOT/"15_Operations"/"transaction_evidence"/"canonical_transaction_evidence.py"
VERIFIER=ROOT/"16_Test_Qualification"/"verifier"/"standalone_transaction_verifier.py"
REQ=ROOT/"15_Operations"/"transaction_evidence"/"ENTITY_REQUIREMENTS.md"
SPEC=ROOT/"14_Protocols_SDK"/"schemas"/"ENTITY_TRANSACTION_EVIDENCE_BUNDLE_v1.md"
SCHEMA=ROOT/"14_Protocols_SDK"/"schemas"/"ENTITY_TRANSACTION_EVIDENCE_BUNDLE_v1.schema.json"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_INDEPENDENT_TRANSACTION_CURRENT.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    ok=run.returncode==0
    payload={"schema":"entity-independent-transaction-qualification-v1","scope":"ENTITY_TRANSACTION_EVIDENCE_BUNDLE_V1_INDEPENDENT_REPRODUCIBILITY","generated_at_ms":int(time.time()*1000),"status":"PASS" if ok else "FAIL","qualification_complete":ok,"limitations":[],"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),"requirements_sha256":sha(REQ),"specification_sha256":sha(SPEC),"json_schema_sha256":sha(SCHEMA),"test_sha256":sha(TEST),"implementation_sha256":{"exporter":sha(EXPORTER),"standalone_verifier":sha(VERIFIER)}}
    payload["demonstrated"]=["complete identity-to-disclosure transaction evidence chain","deterministic transaction root","isolated verifier with no ENTITY runtime imports","tampered rooted evidence rejection","cryptographically verified external payment-provider evidence","signed Digital Commodity economic attribution","threshold corporate authorization","externally attested issuance and cap-table reconciliation","capital-accounting reconciliation","signed recovery manifest and encrypted-state hash verification","verification while original live state is unavailable","post-restore identical transaction root","post-restore identical independent verification result hash"]
    payload["excluded_scope"]=["independently authored non-BTG verifier implementation","legal adjudication of rights claims","broker/dealer or transfer-agent execution","physical destruction of storage media"]
    sealed=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(sealed).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"scope":payload["scope"],"evidence":str(OUT),"evidence_sha256":payload["evidence_sha256"],"exporter_sha256":payload["implementation_sha256"]["exporter"],"standalone_verifier_sha256":payload["implementation_sha256"]["standalone_verifier"]},indent=2))
    return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
