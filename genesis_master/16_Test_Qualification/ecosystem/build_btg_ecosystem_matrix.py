from pathlib import Path
import hashlib,json,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
BTG=Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development')
E=ROOT/'16_Test_Qualification'/'evidence'
def load(path):
    p=Path(path); return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ev(name): return load(E/name)
def state(record, qualified='NATIVE_ENTITY_QUALIFIED'):
    return qualified if record and record.get('status')=='PASS' else 'DISCOVERED_NOT_NATIVE_ENTITY_QUALIFIED'

def build():
    hunt=ev('HUNTAR_ENTITY_INTEGRATION_CURRENT.json'); hike=ev('HIKEAR_ENTITY_INTEGRATION_CURRENT.json')
    search=ev('SEARCHAR_ENTITY_INTEGRATION_CURRENT.json'); soap=ev('BOUNDARYS_BEST_ENTITY_PRINCIPAL_BINDING_CURRENT.json')
    niki=load(ROOT/'10_NIKI/tests/evidence/NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json')
    complete=load(ROOT/'10_NIKI/ENTITY_SYSTEM_COMPLETION_MATRIX.json'); simple=ev('ENTITY_SIMPLE_SDK_CURRENT.json')
    signed=ev('ENTITY_SIGNED_DISTRIBUTION_CURRENT.json')
    items=[
      {'system':'HUNTAR','path':str(BTG/'HUNT_AR/HuntAR_v4.3.0'),'state':state(hunt),'evidence':'HUNTAR_ENTITY_INTEGRATION_CURRENT.json'},
      {'system':'HIKEAR','path':str(BTG/'HIKE_AR/HikeAR_v0.1.0'),'state':state(hike),'evidence':'HIKEAR_ENTITY_INTEGRATION_CURRENT.json'},
      {'system':'SEARCHAR','path':str(BTG/'SAR/SearchAR_v0.12.0'),'state':state(search),'evidence':'SEARCHAR_ENTITY_INTEGRATION_CURRENT.json'},
      {'system':"BOUNDARY'S BEST",'path':str(BTG/'BOUNDARYS_BEST'),'state':'PRINCIPAL_BOUND_ONLY' if soap and soap.get('status')=='PASS' else 'DISCOVERED_NOT_NATIVE_ENTITY_QUALIFIED','evidence':'BOUNDARYS_BEST_ENTITY_PRINCIPAL_BINDING_CURRENT.json'},
      {'system':'NIKI','path':str(ROOT/'10_NIKI'),'state':'CANONICAL_SUBSYSTEM_INTEGRATED' if niki and niki.get('status')=='PASS' else 'DISCOVERED_NOT_NATIVE_ENTITY_QUALIFIED','evidence':'10_NIKI/tests/evidence/NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json'},
    ]
    for name in ['AR_BUILDER','BECP','BLACKMORE CODESEAL','BLACKMORE FABRIC','BLACKMORE SOFTWARE','BLACKMORE UNIFIED DIGITAL SYSTEM','BSIE','SDK','STUDIO']:
        p=BTG/name
        if p.exists():
            subsystem=name in {'BECP','BSIE'} and complete and complete.get('system_acceptance_status')=='CANONICAL_RUNTIME_READY'
            items.append({'system':name,'path':str(p),'state':'CANONICAL_SUBSYSTEM_INTEGRATED' if subsystem else 'DISCOVERED_NOT_NATIVE_ENTITY_QUALIFIED','evidence':'10_NIKI/ENTITY_SYSTEM_COMPLETION_MATRIX.json' if subsystem else None})
    counts={}
    for x in items: counts[x['state']]=counts.get(x['state'],0)+1
    native=[x['system'] for x in items if x['state']=='NATIVE_ENTITY_QUALIFIED']
    unqualified=[x['system'] for x in items if x['state']=='DISCOVERED_NOT_NATIVE_ENTITY_QUALIFIED']
    record={'schema':'btg-ecosystem-entity-integration-matrix-v1','generated_at_ms':int(time.time()*1000),
      'profile':'14_Protocols_SDK/ecosystem/BTG_ENTITY_ECOSYSTEM_INTEGRATION_PROFILE_v1.json',
      'simple_sdk':{'status':simple.get('status') if simple else 'MISSING','tests':(simple or {}).get('tests',{}).get('passed')},
      'canonical_authorities':{'ready':complete.get('canonical_ready_count') if complete else None,'total':complete.get('authority_count') if complete else None},
      'systems':items,'counts':counts,'native_entity_qualified_systems':native,'not_yet_native_entity_qualified':unqualified,
      'whole_btg_ecosystem_native_qualified':len(unqualified)==0,
      'signed_distribution_status':signed.get('status') if signed else 'PENDING',
      'external_validation':{'two_physical_devices':'PENDING','multi_host_distributed_storm':'PENDING','independent_non_btg_implementation':'PENDING'}}
    record['evidence_sha256']=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    out=E/'BTG_ECOSYSTEM_ENTITY_INTEGRATION_CURRENT.json'; out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8'); out.with_suffix('.json.sha256').write_text(sha(out)+'  '+out.name+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS_MATRIX_GENERATED','native':native,'unqualified':unqualified,'counts':counts,'output':str(out),'file_sha256':sha(out)},indent=2))
if __name__=='__main__': build()
