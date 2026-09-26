from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\23_Independent_Interop_Cleanroom\run_conformance.py")
s=p.read_text(encoding='utf-8')
s=s.replace("v=json.loads(p.read_text(encoding='utf-8')); ok,reason=C.validate(v['name'],v['material'],identity)","v=json.loads(p.read_text(encoding='utf-8')); trust=v.get('trust_material') or identity; ok,reason=C.validate(v['name'],v['material'],trust)")
p.write_text(s,encoding='utf-8'); print('runner trust material patched')
