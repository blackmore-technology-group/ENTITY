from pathlib import Path
import hashlib, importlib.util, json, os, random, shutil, subprocess, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
STATE=Path(r"<LOCAL_DRIVE>/ENTITY_PRODUCTION_SCALE_STATE")
EVID=ROOT/"16_Test_Qualification"/"evidence"
OUT=EVID/"ENTITY_PRODUCTION_SCALE_CURRENT.json"
PROGRESS=EVID/"ENTITY_PRODUCTION_SCALE_PROGRESS.json"
ASSET_TARGET=1_000_000
LEDGER_TARGET=3_000_000
ASSET_BATCH=10_000
EVENT_BATCH=25_000
MIN_FREE=10*1024*1024*1024

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
I=load('ps_i',ROOT/'01_Core_Runtime/identity/canonical_identity.py')
L=load('ps_l',ROOT/'04_Entity_Registry/event_ledger/canonical_event_ledger.py')
R=load('ps_r',ROOT/'04_Entity_Registry/ownership_graphs/canonical_rights_claims.py')
P=load('ps_p',ROOT/'04_Entity_Registry/provenance/canonical_provenance.py')
A=load('ps_a',ROOT/'04_Entity_Registry/asset_registry/canonical_asset_registry.py')

def free_bytes(): return shutil.disk_usage(str(STATE.anchor)).free
def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8'); tmp.replace(path)
def checkpoint(phase,assets,events,started,extra=None):
    atomic_json(PROGRESS,{"schema":"entity-production-scale-progress-v1","phase":phase,"assets":assets,"ledger_events":events,"elapsed_seconds":round(time.perf_counter()-started,2),"free_gb":round(free_bytes()/1024**3,3),"extra":extra or {}})
def main():
    shutil.rmtree(STATE,ignore_errors=True); STATE.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter(); checkpoint('initializing',0,0,started)
    print('INIT identity vault',flush=True); ids=I.EntityIdentityVault(STATE)
    print('INIT entity',flush=True); owner=ids.create('Production Scale Entity','organization')['entity_id']
    print('INIT ledger',flush=True); ledger=L.CanonicalEventLedger(STATE,ids)
    print('INIT rights',flush=True); rights=R.RightsClaimsGraph(STATE,ids)
    print('INIT provenance',flush=True); prov=P.AssetProvenanceGraph(STATE,ids)
    print('INIT asset registry',flush=True); assets=A.CanonicalAssetRegistry(STATE,ids,ledger,rights,prov)
    checkpoint('runtime_initialized',0,0,started)
    print('INIT complete',flush=True)
    sample_ids={}; asset_count=0
    for start in range(0,ASSET_TARGET,ASSET_BATCH):
        if free_bytes()<MIN_FREE: raise RuntimeError('disk safety floor reached during asset phase')
        stop=min(start+ASSET_BATCH,ASSET_TARGET)
        batch=[{'content_sha256':hashlib.sha256(f'production-asset-{i}'.encode()).hexdigest(),'size_bytes':i+1,'media_type':'application/octet-stream','title':f'production-asset-{i}'} for i in range(start,stop)]
        out=assets.register_batch(owner,batch); asset_count+=len(out)
        for idx in (0,len(out)-1):
            if out: sample_ids[start+idx]=out[idx]['asset_id']
        if asset_count%100_000==0: checkpoint('assets',asset_count,asset_count,started)
    event_count=asset_count
    checkpoint('assets_complete',asset_count,event_count,started)
    remaining=LEDGER_TARGET-event_count
    for start in range(0,remaining,EVENT_BATCH):
        if free_bytes()<MIN_FREE: raise RuntimeError('disk safety floor reached during event phase')
        stop=min(start+EVENT_BATCH,remaining)
        batch=[{'event_type':'scale.synthetic','subject_ids':[owner],'object_ids':[f'scale-object-{i}'],'payload':{'sequence':i,'purpose':'production-scale-qualification'},'evidence_origin':'DIRECT_OBSERVATION'} for i in range(start,stop)]
        ledger.append_batch(owner,batch); event_count+=len(batch)
        if event_count%250_000==0: checkpoint('events',asset_count,event_count,started)
    checkpoint('verifying',asset_count,event_count,started)
    verify_started=time.perf_counter(); ledger_check=ledger.verify(); verify_seconds=time.perf_counter()-verify_started
    checks={"asset_count_exact":assets.status()['assets']==ASSET_TARGET,"rights_count_exact":rights.status()['claims']==ASSET_TARGET,"provenance_count_exact":prov.status()['bindings']==ASSET_TARGET,"ledger_count_exact":ledger_check.get('blocks')==LEDGER_TARGET,"ledger_full_verify":ledger_check.get('pass') is True}
    sampled=[]
    for index,asset_id in sorted(sample_ids.items())[::max(1,len(sample_ids)//50)]:
        rec=assets.get(asset_id); claims=rights.claims_for_asset(asset_id)
        ok=bool(rec and claims and rights.verify_record_signature(claims[0]['claim_id']) and prov.verify_binding_signature(asset_id))
        sampled.append({"index":index,"asset_id":asset_id,"verified":ok}); checks[f'sample_{index}']=ok
    def file_sha(path):
        h=hashlib.sha256()
        with open(path,'rb') as f:
            for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
        return h.hexdigest()
    dbs={}
    for p in sorted(STATE.rglob('*.sqlite')):
        dbs[str(p.relative_to(STATE))]={"bytes":p.stat().st_size,"sha256":file_sha(p)}
    elapsed=time.perf_counter()-started
    result={"schema":"entity-production-scale-qualification-v1","status":"PASS" if all(checks.values()) else "FAIL","qualification_complete":all(checks.values()),"targets":{"assets":ASSET_TARGET,"ledger_events":LEDGER_TARGET},"observed":{"assets":assets.status()['assets'],"rights_claims":rights.status()['claims'],"provenance_bindings":prov.status()['bindings'],"ledger_events":ledger_check.get('blocks'),"ledger_head_hash":ledger_check.get('head_hash')},"elapsed_seconds":round(elapsed,3),"ledger_verify_seconds":round(verify_seconds,3),"checks":checks,"samples":sampled,"state_database_files":dbs,"limitations":["single-workstation production-scale qualification; distributed multi-host storm is a separate gate"],"free_gb_before_cleanup":round(free_bytes()/1024**3,3)}
    shutil.rmtree(STATE,ignore_errors=True); result['ephemeral_scale_state_deleted_after_hashing']=not STATE.exists(); result['free_gb_after_cleanup']=round(free_bytes()/1024**3,3)
    body=dict(result); raw=json.dumps(body,sort_keys=True,separators=(',',':'),default=str).encode(); result['evidence_sha256']=hashlib.sha256(raw).hexdigest(); atomic_json(OUT,result); checkpoint('complete',ASSET_TARGET,LEDGER_TARGET,started,{"status":result['status'],"evidence_sha256":result['evidence_sha256']})
    print(json.dumps({"status":result['status'],"assets":result['observed']['assets'],"ledger_events":result['observed']['ledger_events'],"elapsed_seconds":result['elapsed_seconds'],"verify_seconds":result['ledger_verify_seconds'],"evidence_sha256":result['evidence_sha256'],"output":str(OUT)},indent=2)); return 0 if result['status']=='PASS' else 2

if __name__=='__main__':
    raise SystemExit(main())
