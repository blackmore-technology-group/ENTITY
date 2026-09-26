from pathlib import Path
import hashlib, importlib.util, json, mimetypes, time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
BTG=Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development')
STATE=Path(r'<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE')
EVID=ROOT/'16_Test_Qualification'/'evidence'
BTG_ENTITY='ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa'
SDK_PATH=ROOT/'14_Protocols_SDK'/'btg_application_sdk'/'canonical_btg_application_sdk.py'
def loadmod(name,path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
SDK=loadmod('btg_ecosystem_sdk',SDK_PATH)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def allow(envelope,operation): return {'allowed':operation in {'INGEST_ASSET','RECORD_EVENT'}}
SYSTEMS={
 'AR_BUILDER':('AR_BUILDER','ar.builder.entity'),
 'BLACKMORE CODESEAL':('BLACKMORE CODESEAL','blackmore.codeseal.entity'),
 'BLACKMORE FABRIC':('BLACKMORE FABRIC','blackmore.fabric.entity'),
 'BLACKMORE SOFTWARE':('BLACKMORE SOFTWARE','blackmore.software.entity'),
 'BLACKMORE UNIFIED DIGITAL SYSTEM':('BLACKMORE UNIFIED DIGITAL SYSTEM','blackmore.unified.digital.system.entity'),
 'SDK':('SDK','blackmore.sdk.entity'),
 'STUDIO':('STUDIO','blackmore.studio.entity'),
}
ART_EXT={'.zip','.exe','.msi','.json','.sha256','.md'}
def candidates(root):
    out=[]
    for p in root.iterdir() if root.is_dir() else []:
        if p.is_file() and p.suffix.lower() in ART_EXT: out.append(p)
    for d in [p for p in root.iterdir() if p.is_dir()][:12] if root.is_dir() else []:
        for p in d.iterdir():
            if p.is_file() and p.suffix.lower() in {'.zip','.exe','.msi'}: out.append(p)
    out=sorted(set(out),key=lambda p:(p.stat().st_mtime,p.stat().st_size),reverse=True)
    return out[:8]
def integrate(name,rel,alias):
    root=BTG/rel
    app=SDK.BTGApplicationSDK.provision_application(STATE,BTG_ENTITY,name,alias,
        metadata={'ecosystem_role':'BTG_ENGINEERING_OR_RELEASE_TOOL','runtime_principal_binding_required':False})
    app_id=app['application_entity_id']; host=SDK.BTGApplicationSDK(STATE,app_id,BTG_ENTITY,authorizer=allow)
    regs=[]
    for p in candidates(root):
        digest=sha(p)
        env=SDK.make_asset_envelope(application_entity_id=app_id,organization_entity_id=BTG_ENTITY,
            content_sha256=digest,size_bytes=p.stat().st_size,
            media_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream',title=p.name,asset_kind='SOFTWARE',
            classification='INTERNAL',metadata={'source_path':str(p),'product':name,'automatic_ecosystem_capture':True},
            idempotency_key='ecosystem:'+name+':'+digest)
        r=host.ingest_asset(env); regs.append({'path':str(p),'sha256':digest,'bytes':p.stat().st_size,'asset_id':r['asset']['asset_id']})
    binding={'schema':'btg-product-entity-integration-binding-v1','product':name,'display_alias':alias,
      'application_entity_id':app_id,'organization_entity_id':BTG_ENTITY,'source_root':str(root),
      'registered_software_artifacts':regs,'registration_not_ownership':True,
      'runtime_principal_binding_required':False,'generated_at_ms':int(time.time()*1000)}
    binding['binding_sha256']=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return binding
def main():
    results=[]
    for name,(rel,alias) in SYSTEMS.items():
        root=BTG/rel
        if not root.exists():
            results.append({'product':name,'status':'MISSING','source_root':str(root)}); continue
        try:
            r=integrate(name,rel,alias); r['status']='PASS'; results.append(r)
        except Exception as exc:
            results.append({'product':name,'status':'FAIL','source_root':str(root),'error':str(exc)})
    passed=[x for x in results if x.get('status')=='PASS']
    failed=[x for x in results if x.get('status')!='PASS']
    record={'schema':'btg-engineering-tools-entity-integration-qualification-v1','generated_at_ms':int(time.time()*1000),
      'status':'PASS' if not failed else 'FAIL','products':results,'passed':len(passed),'total':len(results),
      'claim':'BTG engineering/release tools have stable application Entity identities and their current software release artifacts are registered through the canonical BTG Application SDK. This is provenance integration, not a claim that every tool emits runtime user-data events.',
      'ownership_not_inferred':True,'economic_value_not_inferred':True}
    record['evidence_sha256']=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    out=EVID/'BTG_ENGINEERING_TOOLS_ENTITY_INTEGRATION_CURRENT.json'; out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (EVID/(out.name+'.sha256')).write_text(sha(out)+'  '+out.name+'\n',encoding='utf-8')
    print(json.dumps({'status':record['status'],'passed':len(passed),'total':len(results),'failed':[x['product'] for x in failed],'evidence':str(out),'evidence_sha256':record['evidence_sha256']},indent=2))
    raise SystemExit(0 if record['status']=='PASS' else 2)
if __name__=='__main__': main()
