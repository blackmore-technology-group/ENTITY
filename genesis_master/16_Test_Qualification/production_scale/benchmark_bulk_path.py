from pathlib import Path
import hashlib, importlib.util, json, shutil, sys, tempfile, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
I=load('bi',ROOT/'01_Core_Runtime/identity/canonical_identity.py'); L=load('bl',ROOT/'04_Entity_Registry/event_ledger/canonical_event_ledger.py')
R=load('br',ROOT/'04_Entity_Registry/ownership_graphs/canonical_rights_claims.py'); P=load('bp',ROOT/'04_Entity_Registry/provenance/canonical_provenance.py'); A=load('ba',ROOT/'04_Entity_Registry/asset_registry/canonical_asset_registry.py')
state=ROOT/'16_Test_Qualification/evidence/_BULK_BENCH_STATE'
if state.exists(): shutil.rmtree(state)
ids=I.EntityIdentityVault(state); owner=ids.create('Bulk Benchmark','organization')['entity_id']; ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids); assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
count=10000; batch=1000; started=time.perf_counter()
for start in range(0,count,batch):
    items=[]
    for i in range(start,min(start+batch,count)):
        items.append({'content_sha256':hashlib.sha256(f'bulk-{i}'.encode()).hexdigest(),'size_bytes':i+1,'media_type':'application/octet-stream','title':f'bulk-{i}'})
    assets.register_batch(owner,items)
elapsed=time.perf_counter()-started
result={'count':count,'seconds':round(elapsed,4),'assets_per_second':round(count/elapsed,2),'ledger_blocks':ledger.verify()['blocks'],'rights':rights.status()['claims'],'provenance':prov.status()['bindings']}
print(json.dumps(result,indent=2)); shutil.rmtree(state)
