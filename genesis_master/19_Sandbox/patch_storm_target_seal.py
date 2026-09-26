from pathlib import Path
p=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\distributed_storm\storm_target.py')
s=p.read_text(encoding='utf-8')
s=s.replace('import argparse, importlib.util, json, os, signal, sys, time','import argparse, hashlib, importlib.util, json, os, signal, sys, time')
old="out=Path(args.out); out.write_text(json.dumps({'endpoint':ep,'resolution_proof':proof},indent=2,sort_keys=True)+'\\n',encoding='utf-8'); print(json.dumps({'ready':True,'target':str(out),'endpoint':ep}),flush=True)"
new="payload={'endpoint':ep,'resolution_proof':proof}; payload['evidence_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(); out=Path(args.out); out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\\n',encoding='utf-8'); out.with_suffix('.json.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\\n',encoding='utf-8'); print(json.dumps({'ready':True,'target':str(out),'endpoint':ep,'evidence_sha256':payload['evidence_sha256']}),flush=True)"
if old not in s: raise SystemExit('storm target write block not found')
s=s.replace(old,new,1); p.write_text(s,encoding='utf-8')
cur=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\evidence\ENTITY_STORM_TARGET_CURRENT.json')
import json,hashlib
d=json.loads(cur.read_text(encoding='utf-8')); d.pop('evidence_sha256',None); d['evidence_sha256']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(); cur.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n',encoding='utf-8'); cur.with_suffix('.json.sha256').write_text(hashlib.sha256(cur.read_bytes()).hexdigest()+'  '+cur.name+'\n',encoding='utf-8')
print('patched and resealed')
