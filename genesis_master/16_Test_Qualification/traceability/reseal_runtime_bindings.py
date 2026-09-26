from pathlib import Path
import hashlib,json,os
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
EXCLUDED={'10_NIKI','.pytest_cache','__pycache__','node_modules','build','dist','target'}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve_evidence(binding_path:Path,text:str):
    raw=Path(str(text)); candidates=[]
    if raw.is_absolute(): candidates.append(raw)
    candidates.extend([ROOT/raw,binding_path.parent/raw])
    for p in candidates:
        try:
            if p.is_file(): return p.resolve()
        except OSError: pass
    return None
def normalize_entry(binding_path:Path,entry:dict):
    changed=0
    for ev in list(entry.get('qualification_evidence') or []):
        p=resolve_evidence(binding_path,str(ev.get('path') or ''))
        if not p: continue
        try: rel=str(p.relative_to(ROOT)).replace('\\','/')
        except ValueError: rel=str(p)
        actual=sha(p)
        if ev.get('path')!=rel: ev['path']=rel; changed+=1
        if str(ev.get('sha256') or '').lower()!=actual: ev['sha256']=actual; changed+=1
    source=binding_path.parent/str(entry.get('python_file') or '')
    if source.is_file():
        actual=sha(source)
        if str(entry.get('implementation_sha256') or '').lower()!=actual: entry['implementation_sha256']=actual; changed+=1
    return changed
def main():
    files=[]; updated=changes=0
    for base,dirs,names in os.walk(ROOT,topdown=True,onerror=lambda _:None):
        rel=Path(base).relative_to(ROOT)
        dirs[:]=[d for d in dirs if d not in EXCLUDED]
        if 'ENTITY_RUNTIME_BINDING.json' not in names: continue
        p=Path(base)/'ENTITY_RUNTIME_BINDING.json'; files.append(p)
        try: data=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        local=0
        if isinstance(data.get('authorities'),dict):
            for entry in data['authorities'].values(): local+=normalize_entry(p,entry)
            for ev in list(data.get('qualification_evidence') or []):
                ep=resolve_evidence(p,str(ev.get('path') or ''))
                if ep:
                    relp=str(ep.relative_to(ROOT)).replace('\\','/'); actual=sha(ep)
                    if ev.get('path')!=relp: ev['path']=relp; local+=1
                    if str(ev.get('sha256') or '').lower()!=actual: ev['sha256']=actual; local+=1
        else: local+=normalize_entry(p,data)
        if local:
            p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8'); updated+=1; changes+=local
    print(json.dumps({'binding_files_scanned':len(files),'binding_files_updated':updated,'fields_resealed':changes},indent=2))
if __name__=='__main__': main()
