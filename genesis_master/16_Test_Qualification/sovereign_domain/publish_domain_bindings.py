from pathlib import Path
import hashlib, json

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); DOMAIN=ROOT/'22_Sovereign_Domain'; EV=ROOT/'16_Test_Qualification'/'evidence'
REQ=DOMAIN/'ENTITY_REQUIREMENTS.md'; BIND=DOMAIN/'ENTITY_RUNTIME_BINDING.json'
PLATFORM=ROOT/'10_NIKI'/'ENTITY_PLATFORM_BINDINGS.json'; ABI=ROOT/'10_NIKI'/'CANONICAL_RUNTIME_ABI.json'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def dump(path,obj): Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')

AUTHORITIES={
 'sovereign_domain':('core/canonical_domain.py',['EntityDomainAuthority']),
 'domain_resolution':('resolution/canonical_resolution.py',['EntityNativeResolver']),
 'domain_node_runtime':('node_runtime/canonical_node_runtime.py',['EntityNodeRuntime','EntityDirectClient']),
 'domain_presence':('presence/canonical_presence.py',['PresenceAdvertisementManager']),
 'domain_portability':('portability/canonical_domain_portability.py',['DomainPortabilityManager']),
 'domain_migration':('migration/canonical_domain_migration.py',['DomainMigrationManager']),
 'domain_recovery':('recovery/canonical_domain_recovery.py',['DomainRecoveryManager']),
 'domain_failure_states':('failure_states/canonical_domain_states.py',['DomainFailureStateMachine']),
 'domain_relay':('protocols/canonical_domain_relay.py',['OpaqueDomainRelay']),
}

PRODUCTION={'sovereign_domain':['EntityDomainAuthority'],'domain_resolution':['EntityNativeResolver'],
            'domain_node_runtime':['EntityNodeRuntime','EntityDirectClient'],'domain_portability':['DomainPortabilityManager']}
def main():
    evidence=load(EV/'ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json')
    if evidence.get('status')!='PASS' or evidence.get('qualification_complete') is not True or evidence.get('limitations'):
        raise RuntimeError('internal domain qualification is not clean PASS')
    reqsha=sha(REQ); evsha=evidence['evidence_sha256']; auths={}
    for name,(rel,exports) in AUTHORITIES.items():
        path=DOMAIN/rel
        auths[name]={'status':'READY','python_file':rel.replace('/','\\'),'exports':exports,
            'implementation_sha256':sha(path),'qualification_evidence':[{
                'path':'16_Test_Qualification/evidence/ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json',
                'sha256':evsha,'status':'PASS'}]}
    binding={'schema':'entity-runtime-binding-v1','status':'READY','abi_version':'1',
        'implementation_version':'1.0.0-sers-entity-domain-001','requirements_sha256':reqsha,'authorities':auths,
        'schema_versions':['entity-domain-v1','entity-node-authorization-v1','entity-service-manifest-v1',
            'entity-presence-advertisement-v1','entity-resolution-proof-v1','entity-domain-export-package-v1']}
    dump(BIND,binding)
    platform=load(PLATFORM); bindings=platform.setdefault('bindings',{})
    for name in AUTHORITIES:
        bindings[name]={'embedded':'blackmore_ci.'+name,'owner':'22_Sovereign_Domain'}
    dump(PLATFORM,platform)
    abi=load(ABI); required=abi.setdefault('required_for_production',{})
    for name,exports in PRODUCTION.items(): required[name]=exports
    dump(ABI,abi)
    print(json.dumps({'published_authorities':len(AUTHORITIES),'requirements_sha256':reqsha,
        'qualification_evidence_sha256':evsha,'platform_authorities':len(bindings),
        'production_required':len(required)},indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
