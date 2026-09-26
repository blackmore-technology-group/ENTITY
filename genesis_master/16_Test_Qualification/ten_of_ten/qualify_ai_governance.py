from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
RUNTIME=ROOT/"10_NIKI"/"sovereign_adapted"/"Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"/"central_runtime"
EVIDENCE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_AI_GOVERNANCE_CURRENT.json"
TESTS=[
 "tests/test_niki_action_proposal_contract.py","tests/test_niki_bootstrap_handoff.py",
 "tests/test_niki_entity_context_adapter.py","tests/test_niki_evidence_boundary_reasoning.py",
 "tests/test_niki_handoffs.py","tests/test_niki_policy_overlay_controls.py",
 "tests/test_niki_reasoning_receipt.py","tests/test_niki_sers_controls.py",
]


def main()->int:
    run=subprocess.run([sys.executable,"-m","pytest",*TESTS,"-q"],cwd=str(RUNTIME),capture_output=True,text=True)
    payload={
      "schema":"entity-ai-governance-qualification-v1","generated_at_ms":int(time.time()*1000),
      "status":"PASS" if run.returncode==0 else "FAIL","pytest_exit_code":run.returncode,
      "pytest_output":(run.stdout+"\n"+run.stderr).strip(),"test_files":TESTS,
      "invariants":[
        "NIKI proposals never self-authorize","permanent bootstrap requires canonical core",
        "reasoning context is bounded/non-authoritative","evidence assurance is not silently upgraded",
        "reasoning receipts exclude hidden chain-of-thought","untrusted content cannot grant authority",
        "high-risk actions produce policy warnings","NIKI handoff fails closed when canonical authority is unavailable",
      ],
    }
    sealed=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    payload["evidence_sha256"]=hashlib.sha256(sealed).hexdigest()
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence":str(EVIDENCE),"evidence_sha256":payload["evidence_sha256"]},indent=2))
    return run.returncode


if __name__=="__main__":
    raise SystemExit(main())
