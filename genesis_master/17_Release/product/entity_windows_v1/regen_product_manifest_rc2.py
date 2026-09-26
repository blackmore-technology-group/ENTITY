from pathlib import Path
import json,hashlib,time
root=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\17_Release\product\entity_windows_v1\build\payload')
mp=root/'PRODUCT_MANIFEST.json'
data=json.loads(mp.read_text(encoding='utf-8-sig'))
data['version']='1.0.0-rc2.1'
data['generated_at_ms']=int(time.time()*1000)
for item in data['files']:
    p=root/item['path']
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    item['sha256']=h.hexdigest(); item['bytes']=p.stat().st_size
mp.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(hashlib.sha256(mp.read_bytes()).hexdigest(),len(data['files']))
