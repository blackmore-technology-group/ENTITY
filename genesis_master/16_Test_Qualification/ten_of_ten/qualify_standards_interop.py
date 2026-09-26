from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST=ROOT/"16_Test_Qualification"/"interoperability"/"test_standards_interop.py"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_STANDARDS_INTEROP_CURRENT.json"
FILES={
 "standards_adapter":ROOT/"14_Protocols_SDK"/"protocol_specs"/"canonical_standards_interop.py",
 "reference_client":ROOT/"14_Protocols_SDK"/"reference_clients"/"standards_reference_client.py",
 "c2patool":ROOT/"14_Protocols_SDK"/"c2pa"/"c2patool-v0.27.22"/"c2patool"/"c2patool.exe"}

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def main():
    run=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-standards-interoperability-qualification-v1","scope":"DID_CORE_V1_VC20_ODRL22_C2PA_VALIDATION","generated_at_ms":int(time.time()*1000),"status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),"implementation_sha256":{k:sha(v) for k,v in FILES.items()},"requirements_sha256":sha(ROOT/"14_Protocols_SDK"/"ENTITY_REQUIREMENTS.md"),"limitations":[]}
    payload["demonstrated"]=["DID Core-compatible controller document projection and independent relationship validation","VC Data Model 2.0 required-field validation and ENTITY signed extension verification","external VC 2.0 import remains UNVERIFIED_EXTERNAL_STATE until separately verified","ODRL 2.2 profile export/import preserves permission/prohibition semantics","real c2patool validates claim signature and hashes while signer trust remains separately represented"]
    payload["excluded_scope"]=["registration or external resolution of did:entity DID method","claim of W3C Data Integrity cryptosuite conformance for ENTITY signature records","network-dependent third-party resolver certification","C2PA signer trust beyond configured trust anchors","legal or factual truth inferred from standards validity"]
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"scope":payload["scope"],"evidence_sha256":payload["evidence_sha256"]},indent=2)); return run.returncode

if __name__=="__main__": raise SystemExit(main())
