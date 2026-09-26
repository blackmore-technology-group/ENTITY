from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\traceability\build_rtm.py")
s=p.read_text(encoding="utf-8")
old='''        for name in files:
            if name in REQ_NAMES: candidates.append(Path(base)/name)
'''
new='''        for name in files:
            if name not in REQ_NAMES: continue
            path=Path(base)/name
            try: rel=path.relative_to(ROOT)
            except ValueError: continue
            if not rel.parts or not re.fullmatch(r"\\d{2}_.+",rel.parts[0]): continue
            if len(rel.parts)>3: continue
            candidates.append(path)
'''
if old not in s: raise SystemExit("target block not found")
p.write_text(s.replace(old,new),encoding="utf-8")
