from pathlib import Path
import hashlib, json, subprocess, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TESTS=[
    ROOT/"16_Test_Qualification"/"unit"/"test_canonical_asset_ledger.py",
    ROOT/"16_Test_Qualification"/"recovery"/"test_destructive_sovereignty_extended.py",
]
IMPLEMENTATIONS=[
    ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py",
    ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py",
    ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",
    ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py",
]
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_ASSET_LEDGER_CURRENT.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    cmd=["pytest","-q",*[str(x) for x in TESTS]]
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    evidence={"schema":"entity-asset-ledger-qualification-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,"pytest_exit_code":run.returncode,"pytest_output":((run.stdout or "")+(run.stderr or "")).strip(),"implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in IMPLEMENTATIONS},"requirements":["SERS-ENTITY-002-17/18 asset and claims separation","SERS-ENTITY-002-54 provenance graph","SERS-ENTITY-002-100 invariants","SERS-ENTITY-002-107 cryptographic qualification","SERS-ENTITY-002-133 destructive sovereignty"],"invariants":["registration does not infer ownership","raw private payload bytes are not written to shared ledger","signed hash-chain tampering fails verification","signed Merkle checkpoints validate restored event ranges","asset state changes do not rewrite provenance","restored accounting remains balanced"],"limitations":[] if run.returncode==0 else ["qualification tests failed"]}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    canonical=json.dumps(evidence,sort_keys=True,separators=(",",":"),default=str).encode()
    evidence["evidence_sha256"]=hashlib.sha256(canonical).hexdigest()
    OUT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":evidence["status"],"evidence":str(OUT),"evidence_sha256":evidence["evidence_sha256"],"file_sha256":sha(OUT)},indent=2))
    return run.returncode

if __name__=="__main__": raise SystemExit(main())
