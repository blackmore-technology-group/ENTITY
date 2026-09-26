from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\unit\test_phase1_sovereignty.py")
s=p.read_text(encoding="utf-8")
s=s.replace('    assert raw not in Path(row["cipher_path"]).read_bytes()','    assert raw not in vault._storage_path(row["cipher_path"],"cipher").read_bytes()')
s=s.replace('    assert not Path(row["key_path"]).exists()','    assert not vault._storage_path(row["key_path"],"key").exists()')
p.write_text(s,encoding="utf-8")
print("patched",p)
