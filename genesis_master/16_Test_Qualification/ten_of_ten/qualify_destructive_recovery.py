from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TESTS=[ROOT/"16_Test_Qualification"/"unit"/"test_phase1_sovereignty.py",ROOT/"16_Test_Qualification"/"recovery"/"test_full_destructive_sovereignty.py",ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py"]
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json"
FILES=[ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py",ROOT/"08_Data_Vaults"/"canonical_encrypted_vault.py",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py",ROOT/"15_Operations"/"migration"/"canonical_migration_config.py",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py",ROOT/"21_Corporate_Capital"/"capital_structure"/"canonical_corporate_capital.py"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    run=subprocess.run([sys.executable,"-m","pytest",*[str(x) for x in TESTS],"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-destructive-sovereignty-qualification-v2","scope":"FULL_CANONICAL_STATE_BACKUP_RESTORE_AND_INDEPENDENT_VALIDATION","generated_at_ms":int(time.time()*1000),"status":"PASS" if run.returncode==0 else "FAIL","qualification_complete":run.returncode==0,"pytest_exit_code":run.returncode,"pytest_output":(run.stdout+"\n"+run.stderr).strip(),"implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in FILES},"limitations":[]}
    payload["demonstrated"]=["identity and historical signature restore","policy/capability/vault restore","asset registry recovery","rights/claims graph recovery","provenance graph recovery","event ledger and checkpoint recovery","contracts/licences recovery","usage receipt recovery","settlement and realized-value recovery","migration configuration recovery","corporate-capital encrypted restore and standalone validation","signed portable export and independent file-inventory verification"]
    payload["recovery_semantics"]="live state path is made unavailable and recovery recreates a fresh state namespace solely from encrypted backup; physical media destruction is not claimed"
    payload["requirements_sha256"]={"01_Core_Runtime":sha(ROOT/"01_Core_Runtime"/"ENTITY_REQUIREMENTS.md"),"04_Entity_Registry":sha(ROOT/"04_Entity_Registry"/"ENTITY_REQUIREMENTS.md"),"08_Data_Vaults":sha(ROOT/"08_Data_Vaults"/"ENTITY_REQUIREMENTS.md"),"15_Operations":sha(ROOT/"15_Operations"/"ENTITY_REQUIREMENTS.md"),"21_Corporate_Capital":sha(ROOT/"21_Corporate_Capital"/"ENTITY_REQUIREMENTS.md")}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"scope":payload["scope"],"evidence_sha256":payload["evidence_sha256"]},indent=2)); return run.returncode

if __name__=="__main__": raise SystemExit(main())
