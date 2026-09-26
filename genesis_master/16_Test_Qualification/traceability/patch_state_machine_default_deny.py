from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\15_Operations\runtime_states\service_state_machine.py")
s=p.read_text(encoding="utf-8")
s=s.replace('RECOVERY_OPS={"RECOVERY_BEGIN","RESTORE","MIGRATE","DISPUTE","QUARANTINE"}\n','RECOVERY_OPS={"RECOVERY_BEGIN","RESTORE","MIGRATE","DISPUTE","QUARANTINE"}\nNORMAL_OPS=READ_ONLY|RECOVERY_OPS|HIGH_IMPACT|{"ASSET_REGISTER","POLICY_EVALUATE","CONSENT_GRANT","LICENSE_OFFER","LICENSE_ACCEPT","USAGE_RECORD","PROVENANCE_APPEND","CREDENTIAL_VERIFY","CONNECTOR_READ"}\n')
s=s.replace('if state=="NORMAL": allowed="ALL"','if state=="NORMAL": allowed=NORMAL_OPS')
s=s.replace('allowed=policy["allowed_operations"]=="ALL" or op in policy["allowed_operations"]','allowed=op in policy["allowed_operations"]')
p.write_text(s,encoding="utf-8"); print("patched",p)
