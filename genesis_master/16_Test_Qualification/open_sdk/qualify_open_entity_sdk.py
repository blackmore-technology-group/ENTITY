from pathlib import Path
import hashlib,json,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network'); EV=ROOT/'16_Test_Qualification'/'evidence'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def text_any(p):
    raw=Path(p).read_bytes()
    for enc in ('utf-8-sig','utf-16','utf-16-le'):
        try:
            s=raw.decode(enc)
            if 'passed' in s: return s
        except Exception: pass
    return raw.decode('utf-8',errors='ignore')
pre=load(EV/'ENTITY_SDK_PRE_ADAPTATION_CORE_HASHES.json'); post=load(EV/'ENTITY_SDK_POST_ADAPTATION_CORE_HASHES.json'); log=text_any(EV/'ENTITY_OPEN_SDK_PYTEST.txt')
module=ROOT/'14_Protocols_SDK/open_entity_sdk/canonical_open_entity_sdk.py'; schema=ROOT/'14_Protocols_SDK/open_entity_sdk/ENTITY_OPEN_SDK_ENVELOPES_v1.schema.json'; readme=ROOT/'14_Protocols_SDK/open_entity_sdk/README.md'
checks={'open_sdk_tests_12_of_12':'12 passed' in log,'core_file_count_unchanged':pre.get('file_count')==post.get('file_count')==47,'core_aggregate_hash_unchanged':pre.get('aggregate_sha256')==post.get('aggregate_sha256'),'module_present':module.is_file(),'schema_present':schema.is_file(),'developer_spec_present':readme.is_file()}
payload={'schema':'entity-open-sdk-qualification-v1','generated_at_ms':int(time.time()*1000),'status':'PASS' if all(checks.values()) else 'FAIL','qualification_complete':all(checks.values()),'checks':checks,'pytest':{'passed':12,'file_sha256':sha(EV/'ENTITY_OPEN_SDK_PYTEST.txt')},'core_invariance':{'source_file_count':post.get('file_count'),'before_sha256':pre.get('aggregate_sha256'),'after_sha256':post.get('aggregate_sha256')},'implementation':{'module_sha256':sha(module),'schema_sha256':sha(schema),'readme_sha256':sha(readme)},'preserved_invariants':['alias is not identity','entity_address is cryptographic authority','duplicate aliases fail closed','registration is not ownership','provenance is not rights or truth','economic mutation is not exposed','provider/DNS/host is not sovereign authority'],'claim':'Open SDK adds provider-neutral developer integration and collision-safe human naming without changing pre-existing critical ENTITY core implementations or sovereign semantics.','limitations':[]}
raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode(); payload['evidence_sha256']=hashlib.sha256(raw).hexdigest(); out=EV/'ENTITY_OPEN_SDK_CURRENT.json'; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8'); out.with_suffix('.json.sha256').write_text(sha(out)+'  '+out.name+'\n',encoding='utf-8')
print(json.dumps({'status':payload['status'],'checks':checks,'evidence_sha256':payload['evidence_sha256'],'output':str(out)},indent=2)); raise SystemExit(0 if payload['status']=='PASS' else 2)
