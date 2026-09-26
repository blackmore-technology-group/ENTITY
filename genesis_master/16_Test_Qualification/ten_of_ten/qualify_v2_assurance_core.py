from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"unit"/"test_v2_assurance_core.py"
EVIDENCE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_V2_ASSURANCE_CORE_CURRENT.json"
FILES=[
 ROOT/"01_Core_Runtime"/"information_projection"/"canonical_projection.py",
 ROOT/"04_Entity_Registry"/"evidence_assertions"/"canonical_evidence.py",
 ROOT/"04_Entity_Registry"/"rights_ontology"/"ENTITY_RIGHTS_ONTOLOGY_v1.json",
 ROOT/"04_Entity_Registry"/"rights_ontology"/"canonical_ontology.py",
 ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-v2-assurance-core-qualification-v1","generated_at_ms":int(time.time()*1000),
      "status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,
      "pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),
      "implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in FILES},
      "requirements":{"information_projection":"SERS-ENTITY-002-124","evidence_assertion":"SERS-ENTITY-002-125","rights_ontology":"SERS-ENTITY-002-126"},
      "invariants":[
        "sensitive transfers use minimum-disclosure projection",
        "metadata permission never implies content permission",
        "restricted external disclosure fails closed",
        "unknown rights require review instead of disclosure",
        "UNKNOWN and DERIVED_INFERENCE cannot silently become VERIFIED",
        "strong evidence transitions require qualifying observed/attested/authoritative evidence",
        "rights ontology verification and dispute state remain separate"
      ],
      "limitations":[]}
    sealed=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    payload["evidence_sha256"]=hashlib.sha256(sealed).hexdigest()
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence":str(EVIDENCE),"evidence_sha256":payload["evidence_sha256"]},indent=2))
    return run.returncode

if __name__=="__main__": raise SystemExit(main())
