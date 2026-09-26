from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\15_Operations\migration\canonical_migration_config.py")
s=p.read_text(encoding="utf-8")
s=s.replace('"permissions":"authority_capabilities"','"permissions":"authority"')
p.write_text(s,encoding="utf-8")
print("patched",p)
