from pathlib import Path
import importlib.util,sys,shutil,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
STATE=Path(r'<LOCAL_DRIVE>/ENTITY_RIGHTS_INIT_PROBE')
shutil.rmtree(STATE,ignore_errors=True); STATE.mkdir(parents=True,exist_ok=True)
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); sys.modules[n]=m; s.loader.exec_module(m); return m
I=load('probe_i',ROOT/'01_Core_Runtime/identity/canonical_identity.py')
R=load('probe_r',ROOT/'04_Entity_Registry/ownership_graphs/canonical_rights_claims.py')
t=time.perf_counter(); ids=I.EntityIdentityVault(STATE); print('vault',time.perf_counter()-t,flush=True)
t=time.perf_counter(); owner=ids.create('Probe','organization')['entity_id']; print('entity',time.perf_counter()-t,flush=True)
t=time.perf_counter(); rights=R.RightsClaimsGraph(STATE,ids); print('rights',time.perf_counter()-t,rights.status(),flush=True)
shutil.rmtree(STATE,ignore_errors=True)
