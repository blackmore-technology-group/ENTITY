from pathlib import Path
import hashlib, importlib.util, json, os, shutil, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
I=load('fi',ROOT/'01_Core_Runtime/identity/canonical_identity.py'); L=load('fl',ROOT/'04_Entity_Registry/event_ledger/canonical_event_ledger.py'); R=load('fr',ROOT/'04_Entity_Registry/ownership_graphs/canonical_rights_claims.py'); P=load('fp',ROOT/'04_Entity_Registry/provenance/canonical_provenance.py'); A=load('fa',ROOT/'04_Entity_Registry/asset_registry/canonical_asset_registry.py')
state=ROOT/'16_Test_Qualification/evidence/_FOOTPRINT_10K'; shutil.rmtree(state,ignore_errors=True)
ids=I.EntityIdentityVault(state); owner=ids.create('Footprint','organization')['entity_id']; ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids); assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
for start in range(0,10000,1000):
 items=[{'content_sha256':hashlib.sha256(f'f-{i}'.encode()).hexdigest(),'size_bytes':i+1,'media_type':'application/octet-stream','title':f'f-{i}'} for i in range(start,start+1000)]; assets.register_batch(owner,items)
files=[]; total=0
for p in state.rglob('*'):
 if p.is_file(): files.append((str(p.relative_to(state)),p.stat().st_size)); total+=p.stat().st_size
print(json.dumps({'total_bytes':total,'total_mb':round(total/1024**2,2),'files':sorted(files,key=lambda x:x[1],reverse=True)[:12]},indent=2)); shutil.rmtree(state)
