from pathlib import Path
import hashlib,json,sqlite3
R=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network'); E=R/'16_Test_Qualification/evidence/ENTITY_MILLION_ASSET_SCALE_CURRENT.json'; D=Path(r'<LOCAL_DRIVE>/ENTITY_QUALIFICATION_SCALE\million_asset_v2\store\bulk_ingest.sqlite')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
d=json.loads(E.read_text()); b=dict(d); x=b.pop('evidence_sha256'); seal=hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()==x
with sqlite3.connect(D,timeout=120) as db: m={k:v for k,v in db.execute('select k,v from meta')}
print(json.dumps({'seal_ok':seal,'status':d['status'],'qualified':d['qualification_complete'],'asset_total':int(m['asset_total']),'event_total':int(m['event_total']),'batch_head_match':m['batch_head']==d['verification']['batch_head'],'source_match':sha(R/'04_Entity_Registry/bulk_ingest/canonical_bulk_ingest.py')==d['source_sha256']['bulk_ingest'],'runner_match':sha(R/'16_Test_Qualification/performance/run_million_asset_scale.py')==d['source_sha256']['runner'],'db_size_match':D.stat().st_size==d['database']['size_bytes']},indent=2))