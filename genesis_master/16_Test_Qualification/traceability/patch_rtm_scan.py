from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\traceability\build_rtm.py")
s=p.read_text(encoding="utf-8")
s=s.replace("import csv, hashlib, json, re, time","import csv, hashlib, json, os, re, time")
old='''    for path in sorted(ROOT.rglob("*.md")):
        if path.name not in REQ_NAMES: continue
        lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
'''
new='''    candidates=[]
    excluded={"build",".pytest_cache","__pycache__","node_modules","dist","target"}
    for base,dirs,files in os.walk(ROOT,topdown=True,onerror=lambda _: None):
        dirs[:]=[d for d in dirs if d not in excluded]
        for name in files:
            if name in REQ_NAMES: candidates.append(Path(base)/name)
    for path in sorted(candidates):
        try: lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
        except (FileNotFoundError,PermissionError,OSError): continue
'''
if old not in s: raise SystemExit("target block not found")
p.write_text(s.replace(old,new),encoding="utf-8")
