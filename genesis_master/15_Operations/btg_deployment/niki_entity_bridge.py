from __future__ import annotations
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, re, sqlite3, time
ROOT=Path(__file__).resolve().parents[2]
HEX64=re.compile(r'^[0-9a-fA-F]{64}$')
def loadmod(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
PB=loadmod('niki_pb',ROOT/'14_Protocols_SDK'/'principal_binding'/'canonical_principal_binding.py')
SDK11=loadmod('niki_sdk11',ROOT/'14_Protocols_SDK'/'open_entity_sdk_v1_1'/'canonical_open_entity_sdk_v1_1.py')
def sha_file(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''): h.update(c)
 return h.hexdigest()
def sha_json(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def find_sha(v,out=None):
 out=out if out is not None else set()
 if isinstance(v,dict):
  for x in v.values(): find_sha(x,out)
 elif isinstance(v,(list,tuple)):
  for x in v: find_sha(x,out)
 elif isinstance(v,str) and HEX64.fullmatch(v): out.add(v.lower())
 return out
def find_entities(v,out=None):
 out=out if out is not None else set()
 if isinstance(v,dict):
  for k,x in v.items():
   if isinstance(x,str) and x.startswith('ent2-') and any(w in k.lower() for w in ('entity','controller','principal','subject','owner','creator')): out.add(x)
   else: find_entities(x,out)
 elif isinstance(v,(list,tuple)):
  for x in v: find_entities(x,out)
 return out
class Bridge:
 def __init__(self,profile_path):
  self.profile=json.loads(Path(profile_path).read_text(encoding='utf-8-sig')); self.state=Path(r'<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE')
  self.binding=json.loads(Path(self.profile['principal_binding_file']).read_text(encoding='utf-8-sig'))
  q=PB.validate_bound_installation(self.state,self.binding)
  if not q.get('valid'): raise PermissionError('NIKI principal binding invalid: '+str(q))
  self.q=q; self.app=q['application_entity_id']; self.principal=q['principal_entity_id']
  self.sdk=SDK11.OpenEntityDeveloperSDKv11(self.state,self.app,authorizer=PB.binding_authorizer(self.state,self.binding))
  self.asset_db=self.state/'asset_registry'/'assets.sqlite'; self.runtime=Path(self.profile['runtime_state_root']); self.source=Path(self.profile['source_root'])
  self.index_db=self.state/'btg_integrations'/'niki_bridge.sqlite'; self.index_db.parent.mkdir(parents=True,exist_ok=True); self._init()
 def _init(self):
  with sqlite3.connect(self.index_db) as db:
   db.execute('CREATE TABLE IF NOT EXISTS processed(source_key TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL, entity_asset_id TEXT NOT NULL, processed_ms INTEGER NOT NULL)')
 def _prior(self,key,digest):
  with sqlite3.connect(self.index_db) as db: r=db.execute('SELECT entity_asset_id FROM processed WHERE source_key=? AND content_sha256=?',(key,digest)).fetchone()
  return r[0] if r else None
 def _remember(self,key,digest,aid):
  with sqlite3.connect(self.index_db) as db: db.execute('INSERT OR REPLACE INTO processed VALUES(?,?,?,?)',(key,digest,aid,int(time.time()*1000)))
 def parents_for_hashes(self,hashes):
  if not self.asset_db.exists() or not hashes:return []
  hs=sorted(set(hashes)); out=[]
  with sqlite3.connect(self.asset_db) as db:
   for h in hs:
    out += [r[0] for r in db.execute('SELECT asset_id FROM assets WHERE content_sha256=? ORDER BY created_at_ms',(h,)).fetchall()]
  return list(dict.fromkeys(out))
 def ingest(self,key,digest,*,title,kind='EVIDENCE',size=0,media='application/json',metadata=None,source_subject=None,parent_hashes=None):
  old=self._prior(key,digest)
  if old:return {'source_key':key,'asset_id':old,'idempotent':True}
  parents=self.parents_for_hashes(parent_hashes or [])
  md=dict(metadata or {}); md.update({'integration':'NIKI_ENTITY_BRIDGE_v1','source_key':key,'origin_installation_entity_id':self.q['installation_entity_id'],'origin_device_entity_id':self.q['device_entity_id'],'preserve_source_controller_through_derivation':True,'legacy_registration_not_ownership':True,'economic_value_not_inferred':True})
  contributors=[{'entity_id':x,'role':'UPSTREAM_SOURCE_ENTITY'} for x in sorted(find_entities(md)) if x!=self.app]
  env=SDK11.make_asset_envelope(application_entity_id=self.app,asset_controller_entity_id=self.app,content_sha256=digest,size_bytes=size,media_type=media,title=title,asset_kind=kind,classification='PRIVATE',metadata=md,source_subject_ref=source_subject,idempotency_key='niki:'+hashlib.sha256((key+'|'+digest).encode()).hexdigest(),contributors=contributors,parent_asset_ids=parents)
  result=self.sdk.ingest_asset(env); aid=result['asset']['asset_id']; self._remember(key,digest,aid)
  return {'source_key':key,'asset_id':aid,'parent_assets':len(parents),'idempotent':False}
 def scan_training_artifacts(self):
  p=self.runtime/'training_artifacts'/'registry.sqlite'; out=[]
  if not p.exists(): return out
  with sqlite3.connect(p) as db:
   db.row_factory=sqlite3.Row
   for r in db.execute('SELECT * FROM manifests ORDER BY created_ms'):
    d=dict(r); payload=json.loads(d['payload_json']); prov=json.loads(d['provenance_json']); allv={'payload':payload,'provenance':prov,'artifact_sha256':d.get('artifact_sha256')}; hs=find_sha(allv); kind='MODEL' if d['kind']=='model_artifact' else ('DATA' if d['kind']=='dataset' else 'EVIDENCE')
    out.append(self.ingest('training_manifest:'+d['manifest_id'],d['sha256'],title='NIKI '+d['kind']+' '+d['manifest_id'],kind=kind,metadata={'niki_manifest_id':d['manifest_id'],'niki_artifact_kind':d['kind'],'niki_status':d['status'],'niki_provenance':prov,'niki_payload':payload,'source_controller_status':'PRESERVED_IF_DECLARED_ELSE_UNKNOWN'},parent_hashes=hs))
  return out
 def scan_training_evidence(self):
  p=self.runtime/'sensory_training'/'training_evidence.sqlite'; out=[]
  if not p.exists(): return out
  with sqlite3.connect(p) as db:
   db.row_factory=sqlite3.Row
   for r in db.execute('SELECT * FROM candidates ORDER BY created_ms'):
    d=dict(r); payload=json.loads(d['payload_json']); digest=sha_json({'candidate_id':d['candidate_id'],'status':d['status'],'payload':payload,'evidence_sha256':d['evidence_sha256']}); hs=find_sha(payload); 
    if d['evidence_sha256'] and HEX64.fullmatch(d['evidence_sha256']): hs.add(d['evidence_sha256'].lower())
    out.append(self.ingest('training_candidate:'+d['candidate_id'],digest,title='NIKI training evidence '+d['candidate_id'],kind='EVIDENCE',metadata={'candidate_id':d['candidate_id'],'status':d['status'],'modality':d['modality'],'semantic_class':d['semantic_class'],'raw_media_in_entity':False,'source_controller_status':'PRESERVED_IF_DECLARED_ELSE_UNKNOWN','candidate_provenance':payload.get('provenance') or {}},parent_hashes=hs))
  return out
 def scan_model_lifecycle(self):
  p=self.runtime/'model_lifecycle'/'lifecycle.sqlite'; out=[]
  if not p.exists(): return out
  with sqlite3.connect(p) as db:
   db.row_factory=sqlite3.Row
   for r in db.execute('SELECT * FROM models ORDER BY created_ms'):
    d=dict(r); details=json.loads(d['details_json']); body={k:v for k,v in d.items() if k!='details_json'}|{'details':details}; digest=sha_json(body); hs=find_sha(body)
    out.append(self.ingest('model_lifecycle:'+d['model_id']+':'+d['model_version'],digest,title='NIKI model lifecycle '+d['model_id']+' '+d['model_version'],kind='MODEL',metadata={'model_id':d['model_id'],'model_version':d['model_version'],'stage':d['stage'],'approved_by':d['approved_by'],'automatic_model_promotion':False,'source_controller_status':'PRESERVED_THROUGH_PARENT_LINEAGE'},parent_hashes=hs))
  return out
 def scan_files(self,roots):
  out=[]; skipped=0
  for rel in roots:
   base=self.source/rel
   if not base.exists():continue
   for p in base.rglob('*'):
    if not p.is_file():continue
    low={x.lower() for x in p.parts}
    if '__pycache__' in low or '.pytest_cache' in low or '.venv' in low: skipped+=1;continue
    try:digest=sha_file(p)
    except (FileNotFoundError,PermissionError,OSError): skipped+=1;continue
    rp=p.relative_to(self.source).as_posix(); suffix=p.suffix.lower(); media='application/json' if suffix=='.json' else ('text/csv' if suffix=='.csv' else 'application/octet-stream')
    kind='DATA' if rel in {'corpus','runtime_data','calibration'} else ('MODEL' if 'model' in rel.lower() else 'EVIDENCE')
    out.append(self.ingest('file:'+rp,digest,title='NIKI '+rp,kind=kind,size=p.stat().st_size,media=media,metadata={'source_path_relative':rp,'source_family':rel,'source_controller_status':'LEGACY_UNKNOWN_PRESERVE_PROVENANCE','raw_content_in_entity':False},parent_hashes=[]))
  return out,skipped
 def run(self,full_files=False):
  parts={'training_artifacts':self.scan_training_artifacts(),'training_evidence':self.scan_training_evidence(),'model_lifecycle':self.scan_model_lifecycle()}; skipped=0
  if full_files:
   parts['filesystem'],skipped=self.scan_files(['corpus','runtime_data','reasoning','model_program_v081','qa_evidence','manifest','contracts','calibration','capabilities'])
  return {'schema':'btg-niki-entity-bridge-run-v1','generated_at_ms':int(time.time()*1000),'application_entity_id':self.app,'installation_entity_id':self.q['installation_entity_id'],'principal_entity_id':self.principal,'full_files':full_files,'counts':{k:len(v) for k,v in parts.items()},'skipped_files':skipped,'raw_content_sent_to_entity':False,'ownership_inferred':False,'economic_value_inferred':False,'source_controller_policy':'PRESERVE_SOURCE_CONTROLLER_THROUGH_DERIVATION','parts':parts}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',default=r'<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE\bindings\niki_entity_profile.json');ap.add_argument('--full-files',action='store_true');ap.add_argument('--output',default=r'<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\evidence\NIKI_ENTITY_BRIDGE_CURRENT.json');a=ap.parse_args(); rec=Bridge(a.profile).run(a.full_files); out=Path(a.output);out.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n'); print(json.dumps({k:v for k,v in rec.items() if k!='parts'},indent=2)); print('OUTPUT',out)
if __name__=='__main__':main()
