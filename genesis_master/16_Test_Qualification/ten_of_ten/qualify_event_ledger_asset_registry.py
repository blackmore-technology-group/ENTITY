from pathlib import Path
import hashlib, json, subprocess, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"unit"/"test_event_ledger_asset_registry.py"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_EVENT_LEDGER_ASSET_REGISTRY_CURRENT.json"
FILES=[ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    r=subprocess.run(["python","-m","pytest",str(TEST),"-q"],cwd=ROOT,capture_output=True,text=True)
    ev={"schema":"entity-event-ledger-asset-registry-qualification-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if r.returncode==0 else "FAIL","qualification_complete":r.returncode==0,"pytest_exit_code":r.returncode,"pytest_output":((r.stdout or "")+(r.stderr or "")).strip(),"implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in FILES},"requirements":{"event_ledger":"SERS-ENTITY-002 ledger/checkpoint requirements","asset_registry":"SERS-ENTITY-002 asset registry requirements"},"limitations":[] if r.returncode==0 else ["qualification tests failed"]}
    raw=json.dumps(ev,sort_keys=True,separators=(",",":"),default=str).encode(); ev["evidence_sha256"]=hashlib.sha256(raw).hexdigest(); OUT.write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":ev["status"],"evidence":str(OUT),"evidence_sha256":ev["evidence_sha256"]},indent=2)); return r.returncode
if __name__=="__main__": raise SystemExit(main())
