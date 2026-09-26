from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\unit\test_v2_assurance_core.py")
s=p.read_text(encoding="utf-8")
s=s.replace("import importlib.util, json","import importlib.util, json, sys")
old='mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod'
new='mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod'
if old not in s: raise SystemExit("loader target not found")
p.write_text(s.replace(old,new),encoding="utf-8")
