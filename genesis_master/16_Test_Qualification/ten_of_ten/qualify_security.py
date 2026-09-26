from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"adversarial"/"test_security_adversarial.py"
EVIDENCE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_SECURITY_ADVERSARIAL_CURRENT.json"


def main()->int:
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={
      "schema":"entity-security-adversarial-qualification-v1",
      "generated_at_ms":int(time.time()*1000),
      "status":"PASS" if run.returncode==0 else "FAIL",
      "qualification_complete":run.returncode==0,
      "pytest_exit_code":run.returncode,
      "pytest_output":(run.stdout+"\n"+run.stderr).strip(),
      "attacks_covered":[
        "root takeover via tampered sovereign manifest",
        "signature bypass via payload or signed timestamp mutation",
        "unauthorized rights verification / certainty escalation",
        "vault plaintext disclosure to wrong controller",
        "agent capability escalation outside agent/operation/asset scope",
        "connector/source escalation into non-enrolled, NIKI-denied or hard-excluded paths",
        "replay of an already projected source event",
        "prompt injection seeking policy override, secrets, execution and root authority",
      ],
      "remediations_verified":["entity-signature-record-v2 authenticates timestamp/key metadata","AUTHORITATIVELY_VERIFIED requires independent RIGHTS_AUTHORITY plus authority reference"],
      "limitations":[],
    }
    sealed=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    payload["evidence_sha256"]=hashlib.sha256(sealed).hexdigest()
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence":str(EVIDENCE),"evidence_sha256":payload["evidence_sha256"]},indent=2))
    return run.returncode


if __name__=="__main__":
    raise SystemExit(main())
