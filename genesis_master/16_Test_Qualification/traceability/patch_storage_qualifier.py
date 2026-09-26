from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\ten_of_ten\qualify_phase1_storage_portability.py")
s=p.read_text(encoding="utf-8")
s=s.replace('DESTRUCTIVE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json"\n','')
start=s.index('    missing=[')
end=s.index('    return run.returncode',start)
replacement='    print(json.dumps({"status":scoped["status"],"scoped_evidence_sha256":scoped_hash},indent=2))\n'
s=s[:start]+replacement+s[end:]
p.write_text(s,encoding="utf-8")
print("patched",p)
