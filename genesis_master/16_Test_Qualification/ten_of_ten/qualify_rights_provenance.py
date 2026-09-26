from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"unit"/"test_rights_provenance.py"
EVIDENCE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_RIGHTS_PROVENANCE_CURRENT.json"
FILES=[
    ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",
    ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py",
]

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={
        "schema":"entity-rights-provenance-qualification-v1",
        "generated_at_ms":int(time.time()*1000),
        "status":"PASS" if run.returncode==0 else "FAIL",
        "qualification_complete":run.returncode==0,
        "pytest_exit_code":run.returncode,
        "pytest_output":(run.stdout+"\n"+run.stderr).strip(),
        "implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in FILES},
        "invariants":[
            "claims are many-to-many and may conflict",
            "fractional share, territory and jurisdiction are explicit",
            "registration/signature does not establish legal truth",
            "UNKNOWN/DERIVED_INFERENCE do not silently authorize licensing",
            "independent verification is distinct from claimant assertion",
            "C2PA/provenance validity, signer trust, truth and rights remain distinct",
            "lineage preserves parent/child derivation evidence",
            "tampered signed records fail verification",
        ],
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
