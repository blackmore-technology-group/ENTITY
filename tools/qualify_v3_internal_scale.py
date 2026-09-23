from __future__ import annotations
import sqlite3,hashlib,json,time,tempfile,pathlib,os,random,shutil
ASSETS=1_000_000; EVENTS=3_000_000; BATCH=10_000; SEED=3000007
REPO=pathlib.Path(__file__).resolve().parents[1]
OUT=REPO/'docs/qualification/ENTITY_V3_INTERNAL_SCALE_QUALIFICATION_2026-09-23.json'
work=pathlib.Path(tempfile.gettempdir())/'ENTITY_V3_SCALE_20260923'; shutil.rmtree(work,ignore_errors=True);work.mkdir(parents=True);db=work/'scale.db'
start=time.perf_counter(); con=sqlite3.connect(db);con.execute('PRAGMA journal_mode=WAL');con.execute('PRAGMA synchronous=NORMAL');con.execute('PRAGMA temp_store=MEMORY');con.execute('CREATE TABLE assets(asset_id INTEGER PRIMARY KEY, owner INTEGER NOT NULL, provenance TEXT NOT NULL)');con.execute('CREATE TABLE events(event_id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL, seq INTEGER NOT NULL, kind TEXT NOT NULL, amount_minor INTEGER NOT NULL)');
h_assets=hashlib.sha256();t=time.perf_counter()
for base in range(1,ASSETS+1,BATCH):
 rows=[]
 for i in range(base,min(base+BATCH,ASSETS+1)):
  prov=hashlib.sha256(f'asset:{i}:v3'.encode()).hexdigest();rows.append((i,(i%10000)+1,prov));h_assets.update(f'{i}|{(i%10000)+1}|{prov}\n'.encode())
 con.executemany('INSERT INTO assets VALUES(?,?,?)',rows);con.commit()
asset_seconds=time.perf_counter()-t
h_events=hashlib.sha256();kinds=('REGISTER','RIGHT','USE','VALUE');t=time.perf_counter()
for base in range(1,EVENTS+1,BATCH):
 rows=[]
 for i in range(base,min(base+BATCH,EVENTS+1)):
  aid=((i-1)%ASSETS)+1;seq=((i-1)//ASSETS)+1;kind=kinds[i%4];amt=(i*37)%100000
  rows.append((i,aid,seq,kind,amt));h_events.update(f'{i}|{aid}|{seq}|{kind}|{amt}\n'.encode())
 con.executemany('INSERT INTO events VALUES(?,?,?,?,?)',rows);con.commit()
event_seconds=time.perf_counter()-t
con.execute('CREATE INDEX idx_events_asset_seq ON events(asset_id,seq)');con.commit();con.close();size=db.stat().st_size
# close/reopen verification
con=sqlite3.connect(db);ac=con.execute('SELECT COUNT(*) FROM assets').fetchone()[0];ec=con.execute('SELECT COUNT(*) FROM events').fetchone()[0];samples=[]
for aid in (1,2,99991,500000,999999,1000000): samples.append(con.execute('SELECT asset_id,owner,provenance FROM assets WHERE asset_id=?',(aid,)).fetchone())
for eid in (1,2,1000000,2000000,3000000): samples.append(con.execute('SELECT event_id,asset_id,seq,kind,amount_minor FROM events WHERE event_id=?',(eid,)).fetchone())
qc=con.execute('PRAGMA quick_check').fetchone()[0];con.close();sample_hash=hashlib.sha256(json.dumps(samples,separators=(',',':')).encode()).hexdigest();elapsed=time.perf_counter()-start
payload={'schema':'entity-v3-internal-scale-qualification-v1','classification':'BTG_INTERNAL','pass':ac==ASSETS and ec==EVENTS and qc=='ok','assets':ac,'events':ec,'database_bytes':size,'asset_root_sha256':h_assets.hexdigest(),'event_root_sha256':h_events.hexdigest(),'sample_root_sha256':sample_hash,'sqlite_quick_check':qc,'asset_insert_seconds':round(asset_seconds,3),'event_insert_seconds':round(event_seconds,3),'total_seconds':round(elapsed,3),'platform':os.name,'scope':'1M persistent assets + 3M persistent events; close/reopen integrity and deterministic synthetic roots. Internal scale qualification, not third-party production certification.'};OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(json.dumps(payload,indent=2,sort_keys=True));shutil.rmtree(work,ignore_errors=True);raise SystemExit(0 if payload['pass'] else 2)
