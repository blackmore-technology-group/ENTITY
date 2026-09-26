from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); EV=ROOT/"16_Test_Qualification"/"evidence"
TESTS=[ROOT/"16_Test_Qualification"/"integration"/"test_full_entity_golden_e2e.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py",ROOT/"16_Test_Qualification"/"interoperability"/"test_standards_interop.py",ROOT/"16_Test_Qualification"/"recovery"/"test_full_destructive_sovereignty.py",ROOT/"16_Test_Qualification"/"integration"/"test_independently_reproducible_transaction.py",ROOT/"16_Test_Qualification"/"integration"/"test_section172_sovereign_authority_doctrine.py",ROOT/"16_Test_Qualification"/"sovereign_domain"/"test_sovereign_domain.py"]
OUT=EV/"ENTITY_FULL_E2E_QUALIFICATION_CURRENT.json"
PREREQS={
 "privacy":EV/"ENTITY_PRIVACY_ADVERSARIAL_CURRENT.json","security":EV/"ENTITY_SECURITY_ADVERSARIAL_CURRENT.json",
 "ai_governance":EV/"ENTITY_AI_GOVERNANCE_CURRENT.json","rights_provenance":EV/"ENTITY_RIGHTS_PROVENANCE_CURRENT.json",
 "economics":EV/"ENTITY_ECONOMIC_QUALIFICATION_CURRENT.json","corporate_capital":EV/"ENTITY_CORPORATE_CAPITAL_EVIDENCE_CURRENT.json",
 "interoperability":EV/"ENTITY_STANDARDS_INTEROP_CURRENT.json","resilience":EV/"ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json",
 "independent_transaction":EV/"ENTITY_INDEPENDENT_TRANSACTION_CURRENT.json","sovereign_authority_doctrine":EV/"ENTITY_SOVEREIGN_AUTHORITY_DOCTRINE_CURRENT.json",
 "sovereign_domain_internal":EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json",
 "niki_entity_integration":ROOT/"10_NIKI"/"tests"/"evidence"/"NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json",
}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None

def sealed(path):
    data=load(path)
    if not data or data.get("status")!="PASS" or data.get("qualification_complete") is False or list(data.get("limitations") or []): return False,"status_or_limitations"
    expected=str(data.get("evidence_sha256") or ""); body=dict(data); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return expected==actual,("PASS" if expected==actual else "seal_hash_mismatch")

def main():
    checks={}; ok=True
    for name,path in PREREQS.items():
        path=Path(path); passed,reason=sealed(path); checks[name]={"pass":passed,"reason":reason,"path":str(path),"sha256":sha(path) if path.is_file() else None}; ok=ok and passed
    run=subprocess.run([sys.executable,"-m","pytest",*[str(x) for x in TESTS],"-q"],cwd=str(ROOT),capture_output=True,text=True)
    ok=ok and run.returncode==0
    payload={"schema":"entity-full-e2e-qualification-v1","scope":"ENTITY_GOLDEN_E2E_IMPLEMENTED_CANONICAL_CHAIN","generated_at_ms":int(time.time()*1000),"status":"PASS" if ok else "FAIL","qualification_complete":bool(ok),"limitations":[],"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),"prerequisite_evidence":checks,"requirements_sha256":sha(ROOT/"16_Test_Qualification"/"ENTITY_REQUIREMENTS.md"),"test_sha256":{str(p.relative_to(ROOT)):sha(p) for p in TESTS}}
    payload["demonstrated"]=["fresh Entity A/B/C creation","asset enrollment and hard provenance binding","rights claim and licensing authority","policy/consent authorization with malicious-C denial","bilateral licence offer/acceptance/activation","gateway-observed usage receipt","cryptographically provider-attested external settlement and realized value","future-use revocation while preserving historical receipt","rights dispute state","event-ledger checkpoint verification","encrypted state-loss recovery","signed portable export and independent inventory/signature validation","Section 170 corporate-capital Golden Scenario","Section 171 independently reproducible Transaction Evidence Bundle v1","isolated verifier passes while original live state is unavailable and reproduces post-restore result","Section 172 custody/storage/processing non-authority and provider replacement","DID/VC/ODRL/C2PA interoperability qualification","SERS-ENTITY-DOMAIN-001 internal provider-free sovereign-domain reference implementation","NIKI+ENTITY unified runtime with sovereign authorization boundary and preserved original NIKI route surface"]
    payload["excluded_scope"]=["two-physical-device sovereign-domain field demonstration","independent non-BTG sovereign-domain implementation interoperability","hardware-backed key commissioning","live broker/dealer, public market, custody or transfer-agent execution"]
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"scope":payload["scope"],"pytest":payload["pytest_output"],"evidence_sha256":payload["evidence_sha256"]},indent=2)); return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
