from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\production_scale\run_million_scale.py")
s=p.read_text(encoding='utf-8')
old="""    ids=I.EntityIdentityVault(STATE); owner=ids.create('Production Scale Entity','organization')['entity_id']
    ledger=L.CanonicalEventLedger(STATE,ids); rights=R.RightsClaimsGraph(STATE,ids); prov=P.AssetProvenanceGraph(STATE,ids)
    assets=A.CanonicalAssetRegistry(STATE,ids,ledger,rights,prov)
    sample_ids={}; asset_count=0"""
new="""    print('INIT identity vault',flush=True); ids=I.EntityIdentityVault(STATE)
    print('INIT entity',flush=True); owner=ids.create('Production Scale Entity','organization')['entity_id']
    print('INIT ledger',flush=True); ledger=L.CanonicalEventLedger(STATE,ids)
    print('INIT rights',flush=True); rights=R.RightsClaimsGraph(STATE,ids)
    print('INIT provenance',flush=True); prov=P.AssetProvenanceGraph(STATE,ids)
    print('INIT asset registry',flush=True); assets=A.CanonicalAssetRegistry(STATE,ids,ledger,rights,prov)
    checkpoint('runtime_initialized',0,0,started)
    print('INIT complete',flush=True)
    sample_ids={}; asset_count=0"""
if old not in s: raise SystemExit('init block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('instrumented',p)
