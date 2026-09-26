from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); TEST=ROOT/"16_Test_Qualification"/"unit"/"test_service_state_machine.py"; IMPL=ROOT/"15_Operations"/"runtime_states"/"service_state_machine.py"; OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_FAILURE_STATE_MACHINE_CURRENT.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    r=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-failure-degradation-state-machine-qualification-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if r.returncode==0 else "FAIL","qualification_complete":r.returncode==0,"limitations":[],"qualified_authorities":["service_state_machine"],"pytest_exit_code":r.returncode,"pytest_output":(r.stdout+"\n"+r.stderr).strip(),"implementation_sha256":sha(IMPL),"requirements_sha256":sha(ROOT/"15_Operations"/"ENTITY_REQUIREMENTS.md"),"states":["NORMAL","DEGRADED","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY","QUARANTINED"],"high_impact_fail_closed":True,"unknown_operation_default_deny":True}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest(); OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence_sha256":payload["evidence_sha256"]},indent=2)); return r.returncode
if __name__=="__main__": raise SystemExit(main())
