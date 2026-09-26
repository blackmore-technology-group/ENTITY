from pathlib import Path
import hashlib,json,sqlite3,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
EV=ROOT/'16_Test_Qualification'/'evidence'/'ENTITY_MILLION_ASSET_SCALE_CURRENT.json'
DB=Path(r'<LOCAL_DRIVE>/ENTITY_QUALIFICATION_SCALE\million_asset_v2\store\bulk_ingest.sqlite')
SRC=ROOT/'04_Entity_Registry'/'bulk_ingest'/'canonical_bulk_ingest.py'
RUN=ROOT/'16_Test_Qualification'/'performance'/'run_million_asset_scale.py'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(16*1024*1024),b''): h.update(c)
 return h.hexdigest()
d=json.loads(EV.read_text(encoding='utf-8')); body=dict(d); expected=body.pop('evidence_sha256')
seal=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()==expected
with sqlite3.connect(DB,timeout=120) as db:
 counts={'assets':db.execute('select count(*) from assets').fetchone()[0],'events':db.execute('select count(*) from events').fetchone()[0],'batches':db.execute('select count(*) from batches').fetchone()[0]}
 heads={k:v for k,v in db.execute("select k,v from meta where k in ('event_head','batch_head')")}
print(json.dumps({'seal_ok':seal,'status':d.get('status'),'qualification_complete':d.get('qualification_complete'),'counts':counts,'heads':heads,'source_sha_match':sha(SRC)==d['source_sha256']['bulk_ingest'],'runner_sha_match':sha(RUN)==d['source_sha256']['runner'],'db_sha256_current':sha(DB),'db_sha256_evidence':d['database']['sha256']},indent=2))
