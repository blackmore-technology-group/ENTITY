from pathlib import Path
import hashlib,json
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
platform=json.loads((ROOT/"10_NIKI"/"ENTITY_PLATFORM_BINDINGS.json").read_text())
missing=[]; not_ready=[]; stale=[]; bad=[]
for authority,item in sorted(platform['bindings'].items()):
    owner=ROOT/item['owner']; marker=owner/'ENTITY_RUNTIME_BINDING.json'; contract=ROOT/Path(item['owner']).parts[0]/'ENTITY_REQUIREMENTS.md'
    expected=hashlib.sha256(contract.read_bytes()).hexdigest()
    if not marker.is_file(): missing.append(authority); continue
    raw=json.loads(marker.read_text()); multi=raw.get('authorities'); payload=dict(raw)
    if isinstance(multi,dict):
        if authority not in multi: not_ready.append((authority,'missing selected authority')); continue
        payload.pop('authorities',None); payload.update(multi[authority])
    elif str(raw.get('authority') or '')!=authority: not_ready.append((authority,'authority mismatch')); continue
    status=payload.get('status'); actual=payload.get('requirements_sha256') or raw.get('requirements_sha256')
    if status!='READY': not_ready.append((authority,status))
    elif str(actual).lower()!=expected: stale.append((authority,actual,expected))
    for ev in payload.get('qualification_evidence') or raw.get('qualification_evidence') or []:
        if not isinstance(ev,dict) or not ev.get('path'): continue
        p=Path(ev['path']); ep=p if p.is_absolute() else (ROOT/p).resolve()
        exists=ep.is_file(); actual_ev=hashlib.sha256(ep.read_bytes()).hexdigest() if exists else None
        if not exists or actual_ev!=ev.get('sha256'): bad.append((authority,ev['path'],exists,ev.get('sha256'),actual_ev))
print('TOTAL',len(platform['bindings']))
print('MISSING',missing)
print('NOT_READY',not_ready)
print('STALE_REQ',[x[0] for x in stale])
print('BAD_EVIDENCE',bad)
