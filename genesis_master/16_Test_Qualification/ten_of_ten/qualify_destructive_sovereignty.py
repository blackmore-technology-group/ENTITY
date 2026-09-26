from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); E=ROOT/"16_Test_Qualification"/"evidence"; TEST=ROOT/"16_Test_Qualification"/"recovery"/"test_phase1_full_destructive_sovereignty.py"
FILES=[ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py",
ROOT/"04_Entity_Registry"/"credentials"/"canonical_credentials.py",ROOT/"08_Data_Vaults"/"canonical_data_source_gateway.py",ROOT/"08_Data_Vaults"/"canonical_encrypted_vault.py",
ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py",
ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py",
ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py",ROOT/"15_Operations"/"migration"/"canonical_migration_config.py",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    r=subprocess.run([sys.executable,"-m","pytest",str(TEST),"-q"],cwd=str(ROOT),capture_output=True,text=True)
    payload={"schema":"entity-destructive-sovereignty-qualification-v2","generated_at_ms":int(time.time()*1000),
      "status":"PASS" if r.returncode==0 else "FAIL","qualification_complete":r.returncode==0,"limitations":[],
      "pytest_exit_code":r.returncode,"pytest_output":(r.stdout+"\n"+r.stderr).strip(),
      "demonstrated":["root identity recovery","key/revocation history","credentials","asset registry","rights/claims graph","policy and consent","provenance","contracts/licences","usage receipts","ledger/checkpoint evidence","economic/accounting history","migration configuration","encrypted vault content","external dependency distinction"],
      "implementation_sha256":{str(p.relative_to(ROOT)):sha(p) for p in FILES},
      "requirements_sha256":{"01_Core_Runtime":sha(ROOT/"01_Core_Runtime"/"ENTITY_REQUIREMENTS.md"),"04_Entity_Registry":sha(ROOT/"04_Entity_Registry"/"ENTITY_REQUIREMENTS.md"),"08_Data_Vaults":sha(ROOT/"08_Data_Vaults"/"ENTITY_REQUIREMENTS.md"),"15_Operations":sha(ROOT/"15_Operations"/"ENTITY_REQUIREMENTS.md")}}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    out=E/"ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json"; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence_sha256":payload["evidence_sha256"],"output":str(out)},indent=2)); return r.returncode
if __name__=="__main__": raise SystemExit(main())
