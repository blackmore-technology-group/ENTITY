from pathlib import Path
import hashlib, json, subprocess, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
E=ROOT/"16_Test_Qualification"/"evidence"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(payload,path):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return payload["evidence_sha256"]
def run_test(path):
    r=subprocess.run([sys.executable,"-m","pytest",str(path),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    return r.returncode,(r.stdout+"\n"+r.stderr).strip()

def evidence(schema,test,files,authorities,reqs,out):
    code,output=run_test(test)
    payload={"schema":schema,"generated_at_ms":int(time.time()*1000),"status":"PASS" if code==0 else "FAIL",
      "qualification_complete":code==0,"limitations":[],"qualified_authorities":authorities,
      "pytest_exit_code":code,"pytest_output":output,
      "implementation_sha256":{str(Path(p).relative_to(ROOT)):sha(p) for p in files},
      "requirements_sha256":{name:sha(path) for name,path in reqs.items()}}
    return code,seal(payload,out)
def main():
    code1,h1=evidence("entity-contracts-usage-qualification-v1",
      ROOT/"16_Test_Qualification"/"unit"/"test_contracts_usage_control.py",
      [ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py"],
      ["contracts","usage_control"],{"01_Core_Runtime":ROOT/"01_Core_Runtime"/"ENTITY_REQUIREMENTS.md"},
      E/"ENTITY_CONTRACTS_USAGE_CURRENT.json")
    code2,h2=evidence("entity-credentials-migration-qualification-v1",
      ROOT/"16_Test_Qualification"/"unit"/"test_credentials_migration.py",
      [ROOT/"04_Entity_Registry"/"credentials"/"canonical_credentials.py",ROOT/"15_Operations"/"migration"/"canonical_migration_config.py"],
      ["credentials","migration_config"],{"04_Entity_Registry":ROOT/"04_Entity_Registry"/"ENTITY_REQUIREMENTS.md","15_Operations":ROOT/"15_Operations"/"ENTITY_REQUIREMENTS.md"},
      E/"ENTITY_CREDENTIALS_MIGRATION_CURRENT.json")
    print(json.dumps({"contracts_usage_sha256":h1,"credentials_migration_sha256":h2,"status":"PASS" if code1==code2==0 else "FAIL"},indent=2))
    return max(code1,code2)
if __name__=="__main__": raise SystemExit(main())
