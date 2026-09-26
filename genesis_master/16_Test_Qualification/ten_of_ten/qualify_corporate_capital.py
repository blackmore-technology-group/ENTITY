from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TESTS=[ROOT/"16_Test_Qualification"/"corporate_capital"/"test_corporate_capital_evidence.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_corporate_capital_external_integration.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py"]
IMPLS={
 "capital_structure":ROOT/"21_Corporate_Capital"/"capital_structure"/"canonical_corporate_capital.py",
 "external_authorities":ROOT/"21_Corporate_Capital"/"external_authorities"/"canonical_external_authority.py",
 "instrument_classification":ROOT/"21_Corporate_Capital"/"jurisdiction"/"canonical_instrument_classification.py",
 "corporate_actions":ROOT/"21_Corporate_Capital"/"corporate_actions"/"canonical_corporate_actions.py",
 "capital_accounting":ROOT/"21_Corporate_Capital"/"accounting"/"canonical_capital_accounting.py",
 "portable_state":ROOT/"15_Operations"/"backups"/"canonical_portable_state.py",
 "independent_verifier":ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py"}
REQ=ROOT/"21_Corporate_Capital"/"ENTITY_REQUIREMENTS.md"
EVIDENCE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_CORPORATE_CAPITAL_EVIDENCE_CURRENT.json"
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    run=subprocess.run([sys.executable,"-m","pytest",*[str(x) for x in TESTS],"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-corporate-capital-evidence-qualification-v3","scope":"CORPORATE_CAPITAL_SECTION_170_GOLDEN_SCENARIO","generated_at_ms":int(time.time()*1000),"status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),"implementation_sha256":{k:sha(v) for k,v in IMPLS.items()},"requirements_sha256":sha(REQ)}
    payload["invariants"]=["usage cannot issue equity","Digital Commodity economic events are individually signed and evidence-hash bound","external capital evidence is signature/subject/type bound","unknown jurisdiction policy fails closed to review","shareholder snapshots reconcile to outstanding shares","corporate action evidence is bound to exact action/class/post-capitalization","external accounting journals balance by currency","accounting does not prove legal ownership or cash","provider-confirmed settlement is required for verified external cash","modelled valuation remains separate from signed external market observation","issuance dilution and transfer are explicitly reconciled","tampered corporate-action evidence is rejected","encrypted backup restores capital state after live-state loss","portable export is signed and hash-inventoried","restored and exported capital/action/accounting records pass standalone independent verification","regulated execution remains disabled"]
    payload["excluded_scope"]=["legally effective securities issuance by ENTITY core","broker/dealer execution","public securities trading","custody","market making","clearing and settlement","live transfer-agent integration","authoritative legal classification"]
    payload["limitations"]=[]
    sealed=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(sealed).hexdigest()
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True); EVIDENCE.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"scope":payload["scope"],"evidence":str(EVIDENCE),"evidence_sha256":payload["evidence_sha256"]},indent=2)); return run.returncode

if __name__=="__main__": raise SystemExit(main())
