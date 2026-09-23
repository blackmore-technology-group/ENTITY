from __future__ import annotations
import hashlib,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1]
P=R/'ENTITY_V3_0_1_RELEASE_MANIFEST.json'
m=json.loads(P.read_text(encoding='utf-8-sig')); errors=[]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if m.get('version')!='3.0.1': errors.append('version')
if m.get('status')!='BTG_INTERNAL_QUALIFIED_MAINTENANCE_RELEASE': errors.append('status')
for item in m.get('files',[]):
    p=R/item['path']
    if not p.is_file(): errors.append('missing:'+item['path']); continue
    actual=sha(p)
    if actual!=item['sha256']: errors.append('hash:'+item['path']+':'+actual)
items=sorted(m.get('files',[]),key=lambda x:x['path'])
material='\n'.join(f"{x['path']}|{x['sha256']}" for x in items).encode()
root=hashlib.sha256(material).hexdigest()
if root!=m.get('release_snapshot_sha256'): errors.append('snapshot:'+root)
print(json.dumps({'valid':not errors,'version':m.get('version'),'files':len(items),'release_snapshot_sha256':root,'errors':errors},indent=2,sort_keys=True))
sys.exit(0 if not errors else 2)
