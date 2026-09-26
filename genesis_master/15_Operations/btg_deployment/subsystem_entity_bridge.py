from __future__ import annotations
from pathlib import Path
import argparse,hashlib,importlib.util,json,sqlite3,time
ROOT=Path(__file__).resolve().parents[2]; STATE=Path(r'<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE')
def loadmod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
PB=loadmod('sub_pb',ROOT/'14_Protocols_SDK'/'principal_binding'/'canonical_principal_binding.py')
SDK11=loadmod('sub_sdk11',ROOT/'14_Protocols_SDK'/'open_entity_sdk_v1_1'/'canonical_open_entity_sdk_v1_1.py')
BASE=loadmod('sub_sdk_base',ROOT/'14_Protocols_SDK'/'open_entity_sdk'/'canonical_open_entity_sdk.py')
def fsha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def jsha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
class Bridge:
 def __init__(self,profile):
  self.profile=json.loads(Path(profile).read_text(encoding='utf-8-sig'));self.name=self.profile['subsystem'];self.app=self.profile['application_entity_id'];self.binding=json.loads(Path(self.profile['principal_binding_file']).read_text(encoding='utf-8-sig'));self.q=PB.validate_bound_installation(STATE,self.binding)
  if not self.q.get('valid'):raise PermissionError(str(self.q))
  self.sdk=SDK11.OpenEntityDeveloperSDKv11(STATE,self.app,authorizer=PB.binding_authorizer(STATE,self.binding));self.assetdb=STATE/'asset_registry'/'assets.sqlite';self.idx=STATE/'btg_integrations'/f'{self.name.lower()}_bridge.sqlite';self.idx.parent.mkdir(parents=True,exist_ok=True)
  with sqlite3.connect(self.idx) as db:db.execute('CREATE TABLE IF NOT EXISTS processed(source_key TEXT PRIMARY KEY,sha256 TEXT NOT NULL,asset_id TEXT NOT NULL,mode TEXT NOT NULL,processed_ms INTEGER NOT NULL)')
 def prior(self,key,digest):
  with sqlite3.connect(self.idx) as db:r=db.execute('SELECT asset_id,mode FROM processed WHERE source_key=? AND sha256=?',(key,digest)).fetchone()
  return r
 def remember(self,key,digest,aid,mode):
  with sqlite3.connect(self.idx) as db:db.execute('INSERT OR REPLACE INTO processed VALUES(?,?,?,?,?)',(key,digest,aid,mode,int(time.time()*1000)))
 def existing(self,digest):
  if not self.assetdb.exists():return None
  with sqlite3.connect(self.assetdb) as db:r=db.execute('SELECT asset_id,controller_entity_id FROM assets WHERE content_sha256=? ORDER BY created_at_ms LIMIT 1',(digest,)).fetchone()
  return r
 def kind(self,p):
  low=p.as_posix().lower(); ext=p.suffix.lower()
  if 'runtime_data' in low or ext in {'.db','.sqlite','.sqlite3','.geojson','.tif','.tiff','.gpkg'}:return 'DATA'
  if ext in {'.py','.ps1','.sh','.kt','.swift','.cs','.cpp','.c','.h','.hpp','.exe','.dll','.so','.aar','.jar','.json','.yaml','.yml','.toml','.md','.txt'}:return 'SOFTWARE'
  return 'EVIDENCE'
 def process(self,p,root):
  rel=p.relative_to(root).as_posix();key=f'{root}|{rel}';digest=fsha(p);old=self.prior(key,digest)
  if old:return {'path':str(p),'sha256':digest,'asset_id':old[0],'mode':old[1],'idempotent':True}
  existing=self.existing(digest); meta={'subsystem':self.name,'source_root':str(root),'source_path_relative':rel,'origin_installation_entity_id':self.q['installation_entity_id'],'origin_device_entity_id':self.q['device_entity_id'],'registration_not_ownership':True,'economic_value_not_inferred':True,'raw_content_in_entity':False}
  if existing:
   payload={'subsystem':self.name,'asset_id':existing[0],'content_sha256':digest,'source_path_relative':rel,'processing_not_ownership':True}
   env={'schema':'entity-open-sdk-event-envelope-v1','application_entity_id':self.app,'idempotency_key':'subevent:'+jsha({'key':key,'sha':digest}),'event_type':'data.asset_observed','payload_sha256':jsha(payload),'subject_ids':[self.app,self.q['installation_entity_id'],self.q['device_entity_id']],'object_ids':[existing[0]],'evidence_origin':'DIRECT_OBSERVATION','confidence':1.0,'raw_payload_included':False}
   self.sdk.record_event(env);aid=existing[0];mode='LINK_EXISTING_ASSET'
  else:
   env=SDK11.make_asset_envelope(application_entity_id=self.app,asset_controller_entity_id=self.app,content_sha256=digest,size_bytes=p.stat().st_size,media_type='application/octet-stream',title=f'{self.name} {rel}',asset_kind=self.kind(p),classification='PRIVATE',metadata=meta,idempotency_key='subasset:'+jsha({'key':key,'sha':digest}),explicit_rights_claim={},contributors=[],parent_asset_ids=[])
   res=self.sdk.ingest_asset(env);aid=res['asset']['asset_id'];mode='REGISTER_SUBSYSTEM_ASSET'
  self.remember(key,digest,aid,mode);return {'path':str(p),'sha256':digest,'asset_id':aid,'mode':mode,'idempotent':False}
 def run(self):
  rows=[];skipped=0;roots=[]
  for s in self.profile['roots']:
   root=Path(s);roots.append(str(root))
   if not root.exists():continue
   for p in root.rglob('*'):
    if not p.is_file():continue
    if any(x.lower() in {'__pycache__','.pytest_cache','.venv','.git'} for x in p.parts):skipped+=1;continue
    try:rows.append(self.process(p,root))
    except (FileNotFoundError,PermissionError,OSError) as e:skipped+=1
  modes={}
  for x in rows:modes[x['mode']]=modes.get(x['mode'],0)+1
  return {'schema':'btg-subsystem-entity-bridge-run-v1','generated_at_ms':int(time.time()*1000),'subsystem':self.name,'status':'PASS','application_entity_id':self.app,'installation_entity_id':self.q['installation_entity_id'],'principal_entity_id':self.q['principal_entity_id'],'roots':roots,'processed_files':len(rows),'modes':modes,'skipped_files':skipped,'raw_content_sent_to_entity':False,'ownership_inferred':False,'economic_value_inferred':False,'items':rows}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();rec=Bridge(a.profile).run();out=Path(a.output);out.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in rec.items() if k!='items'},indent=2));print('OUTPUT',out)
if __name__=='__main__':main()
