from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\production_scale\run_million_scale.py")
s=p.read_text(encoding='utf-8')
s=s.replace('import hashlib, importlib.util, json, os, random, shutil, sys, time','import hashlib, importlib.util, json, os, random, shutil, subprocess, sys, time')
old="    shutil.rmtree(STATE,ignore_errors=True); STATE.mkdir(parents=True,exist_ok=True)\n"
new=old+"    if os.name=='nt': subprocess.run(['compact','/c','/i','/q',str(STATE)],capture_output=True,text=True)\n"
if new not in s:
    if old not in s: raise RuntimeError('scale init marker missing')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('compression enabled')
