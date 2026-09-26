import hashlib,hmac,json,sys
from pathlib import Path
out=Path(__file__).resolve().parent
key=Path(sys.argv[1]).read_bytes()
m=(out/'TRL9_MANIFEST.json').read_bytes(); man=json.loads(m.decode('utf-8'))
seal=json.loads((out/'TRL9_SEAL.json').read_text(encoding='utf-8'))
errs=[]
if hashlib.sha256(m).hexdigest()!=seal['manifest_sha256']: errs.append('manifest sha256')
if not hmac.compare_digest(hmac.new(key,m,hashlib.sha256).hexdigest(),seal['manifest_hmac_sha256']): errs.append('manifest hmac')
for f in man['files']:
 p=out/f['name']
 if not p.exists(): errs.append('missing '+f['name']); continue
 if p.stat().st_size!=f['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']: errs.append('hash '+f['name'])
print(json.dumps({'ok':not errs,'errors':errs},indent=2)); raise SystemExit(0 if not errs else 2)
