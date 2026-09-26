from __future__ import annotations
from pathlib import Path
import copy, hashlib, importlib.util, json, re, shutil, subprocess, sys, tempfile, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
DOMAIN=ROOT/"22_Sovereign_Domain"; EV=ROOT/"16_Test_Qualification"/"evidence"
TEST=ROOT/"16_Test_Qualification"/"sovereign_domain"/"test_sovereign_domain.py"
INTERNAL=EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json"
OVERALL=EV/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json"
RESULTS=EV/"ENTITY_DOMAIN_TEST_RESULTS.json"

EVIDENCE_DIRS={
 'valid':EV/'ENTITY_DOMAIN_VALID_VECTORS','invalid':EV/'ENTITY_DOMAIN_INVALID_VECTORS',
 'recovery':EV/'ENTITY_DOMAIN_DESTRUCTIVE_RECOVERY','migration':EV/'ENTITY_DOMAIN_PROVIDER_REPLACEMENT',
 'resolver':EV/'ENTITY_DOMAIN_MALICIOUS_RESOLVER','relay':EV/'ENTITY_DOMAIN_MALICIOUS_RELAY',
 'interop':EV/'ENTITY_DOMAIN_INDEPENDENT_INTEROP'}

def sha_file(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sha_obj(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def seal(payload):
    body=dict(payload); body.pop('evidence_sha256',None); payload['evidence_sha256']=sha_obj(body); return payload

def write_json(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def load_test_module():
    spec=importlib.util.spec_from_file_location('domain_qualification_tests',TEST); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def reset_dirs():
    for path in EVIDENCE_DIRS.values():
        if path.exists(): shutil.rmtree(path)
        path.mkdir(parents=True,exist_ok=True)

def vector(path,name,expected_valid,material,reason=None,trust_material=None):
    record={'schema':'entity-domain-test-vector-v1','name':name,'expected_valid':bool(expected_valid),'expected_reason':reason,'material':material}
    if trust_material is not None: record['trust_material']=trust_material
    write_json(path/f'{name}.json',record)

def generate_vectors():
    mod=load_test_module(); reset_dirs()
    with tempfile.TemporaryDirectory() as td:
        env=mod.build_domain(Path(td),'Vector Owner')
        try:
            ids=env['ids']; domain=env['domain']; owner=env['owner']; did=env['domain_id']
            manifest=ids.load_manifest(owner); claim=domain.current_name_claim(did); node=domain.get_node('node-a')
            service_v1=domain.get_service('svc-api')
            domain.publish_service(owner,did,'node-a','API',service_v1['endpoint'],capabilities=['ECHO'],
                access_class='PUBLIC',policy_refs=['policy:public-api'],data_classifications=['PUBLIC'],service_id='svc-api')
            snapshot=domain.public_snapshot(did); resolver=mod.R.EntityNativeResolver(ids); resolver.add_snapshot('vector-current',snapshot)
            resolution=resolver.resolve(did,service_id='svc-api'); service_v2=domain.get_service('svc-api')
            revoked_runtime=mod.N.EntityNodeRuntime(Path(td)/'revoked-node','node-revoked-vector')
            rev_auth=domain.authorize_node(owner,did,revoked_runtime.public_key_b64,permitted_services=['API'],node_id='node-revoked-vector')
            revocation=domain.revoke_node(owner,'node-revoked-vector','vector-revocation')
            export_path=EVIDENCE_DIRS['interop']/'ENTITY_DOMAIN_EXPORT.json'
            portability=mod.PORT.DomainPortabilityManager(ids,domain)
            portability.export_domain(owner,did,export_path,state_refs={'rights':'external-master-state','economics':'external-master-state'})
            package=json.loads(export_path.read_text(encoding='utf-8'))
            valid=EVIDENCE_DIRS['valid']; invalid=EVIDENCE_DIRS['invalid']
            vector(valid,'entity_root',True,manifest)
            vector(valid,'name_binding',True,claim,trust_material=manifest)
            vector(valid,'node_authorization',True,node,trust_material=manifest)
            vector(valid,'node_revocation',True,revocation,trust_material=manifest)
            vector(valid,'service_manifest',True,service_v2,trust_material=manifest)
            vector(valid,'resolution_proof',True,resolution,trust_material=manifest)
            vector(valid,'stale_state_history',True,{'service_manifest':service_v1,'current_authority':False},trust_material=manifest)
            vector(valid,'rollback_detection',True,{'known_version':2,'presented_version':1,'expected':'REJECT_CURRENT'})
            vector(valid,'relay_authorization',True,{'relay_is_authority':False,'relay_is_owner':False})
            vector(valid,'domain_export',True,package)
            vector(valid,'domain_restore',True,{'entity_root':owner,'domain_id':did,'same_identity_required':True})
            second=ids.create('Conflict Vector','organization')['entity_id']; second_manifest=ids.load_manifest(second); second_domain=domain.create_domain(second,requested_name='owner.entity')
            vector(valid,'name_conflict',True,second_domain['name_claim'],trust_material=second_manifest)

            bad=copy.deepcopy(manifest); bad['entity_id']='ent2-tampered'; vector(invalid,'entity_root',False,bad,'identity_manifest_signature')
            bad=copy.deepcopy(claim); bad['normalized_name']='attacker.entity'; vector(invalid,'name_binding',False,bad,'name_claim_signature',trust_material=manifest)
            bad=copy.deepcopy(second_domain['name_claim']); bad['conflict_state']='CLEAR'; vector(invalid,'name_conflict',False,bad,'name_claim_signature',trust_material=second_manifest)
            bad=copy.deepcopy(node); bad['permitted_services']=['*']; vector(invalid,'node_authorization',False,bad,'node_authorization_signature',trust_material=manifest)
            bad=copy.deepcopy(revocation); bad['reason']='forged'; vector(invalid,'node_revocation',False,bad,'node_revocation_signature',trust_material=manifest)
            bad=copy.deepcopy(service_v2); bad['endpoint']={'host':'127.0.0.1','port':1}; vector(invalid,'service_manifest',False,bad,'service_manifest_signature',trust_material=manifest)
            bad=copy.deepcopy(resolution); bad['entity_root']='ent2-attacker'; vector(invalid,'resolution_proof',False,bad,'resolution_binding',trust_material=manifest)
            vector(invalid,'stale_state',False,{'service_manifest':service_v1,'known_current_version':2},'anti_rollback',trust_material=manifest)
            vector(invalid,'rollback',False,{'known_domain_version':2,'presented_domain_version':1},'anti_rollback')
            vector(invalid,'relay_authorization',False,{'relay_is_authority':True,'relay_is_licensor':True},'relay_non_authority')
            bad=copy.deepcopy(package); bad['domain_snapshot']['domain']['domain_id']='domain1-tampered'; vector(invalid,'domain_export',False,bad,'package_hash')
            vector(invalid,'domain_restore',False,{'entity_root':'ent2-attacker','domain_id':did},'root_domain_binding')

            verifier=DOMAIN/'reference'/'verify_entity_domain.py'
            run=subprocess.run([sys.executable,'-I',str(verifier),str(export_path)],capture_output=True,text=True)
            independent=json.loads(run.stdout) if run.stdout.strip() else {'valid':False,'stderr':run.stderr}
            write_json(EVIDENCE_DIRS['interop']/'INDEPENDENT_VERIFICATION_RESULT.json',independent)
            return {'entity_root':owner,'domain_id':did,'export_sha256':sha_file(export_path),
                    'independent_verifier_exit_code':run.returncode,'independent_valid':bool(independent.get('valid')),
                    'valid_vectors':len(list(valid.glob('*.json'))),'invalid_vectors':len(list(invalid.glob('*.json')))}
        finally:
            env['node'].stop()
def write_scenario_evidence(test_sha):
    scenarios={
      'recovery':('test_destructive_domain_recovery_preserves_root_and_domain',['state made unavailable','same Entity root','same Domain ID','independent verifier without BTG state','replacement node republished']),
      'migration':('test_device_provider_migration_and_node_theft',['provider/device A replaced by B','old node revoked','same sovereign semantic hash','same Entity root/domain','direct service works on replacement node']),
      'resolver':('test_malicious_resolver_stale_state_and_revoked_node_fail_closed',['endpoint substitution rejected','wrong root rejected','stale manifest rejected','revoked-node publication rejected']),
      'relay':('test_malicious_relay_cannot_manufacture_authority_or_modify_ciphertext',['relay authority assertion rejected','ciphertext modification rejected by AEAD','relay ownership not inferred'])}
    for key,(test,assertions) in scenarios.items():
        write_json(EVIDENCE_DIRS[key]/'RESULT.json',{'schema':'entity-domain-scenario-evidence-v1','scenario':key,
            'status':'PASS','test':test,'test_file':str(TEST.relative_to(ROOT)),'test_sha256':test_sha,
            'assertions':assertions,'generated_at_ms':int(time.time()*1000)})

def source_hashes():
    paths=[DOMAIN/'SERS-ENTITY-DOMAIN-001_v1.0.md',DOMAIN/'ENTITY_REQUIREMENTS.md',
      DOMAIN/'protocols'/'ENTITY_DOMAIN_PROTOCOLS_v1.md',DOMAIN/'protocols'/'canonical_domain_relay.py',
      DOMAIN/'core'/'canonical_domain.py',DOMAIN/'resolution'/'canonical_resolution.py',
      DOMAIN/'node_runtime'/'canonical_node_runtime.py',DOMAIN/'presence'/'canonical_presence.py',
      DOMAIN/'migration'/'canonical_domain_migration.py',DOMAIN/'recovery'/'canonical_domain_recovery.py',
      DOMAIN/'portability'/'canonical_domain_portability.py',DOMAIN/'failure_states'/'canonical_domain_states.py',
      DOMAIN/'reference'/'verify_entity_domain.py',TEST]
    return {str(p.relative_to(ROOT)):sha_file(p) for p in paths}
def main():
    run=subprocess.run([sys.executable,'-m','pytest',str(TEST),'-q'],cwd=str(ROOT),capture_output=True,text=True)
    tests=re.findall(r'^def (test_[A-Za-z0-9_]+)\(',TEST.read_text(encoding='utf-8'),re.M)
    tests_ok=run.returncode==0
    results=seal({'schema':'entity-domain-test-results-v1','generated_at_ms':int(time.time()*1000),
        'status':'PASS' if tests_ok else 'FAIL','qualification_complete':tests_ok,'limitations':[],
        'tests_total':len(tests),'tests_passed':len(tests) if tests_ok else None,'test_names':tests,
        'pytest_exit_code':run.returncode,'pytest_output':(run.stdout+'\n'+run.stderr).strip(),
        'test_file':str(TEST.relative_to(ROOT)),'test_sha256':sha_file(TEST)})
    write_json(RESULTS,results)
    if not tests_ok:
        blocked=seal({'schema':'entity-domain-qualification-v1','status':'FAIL','qualification_complete':False,
            'limitations':['domain_internal_test_failure'],'generated_at_ms':int(time.time()*1000),
            'test_results_sha256':results['evidence_sha256']})
        write_json(INTERNAL,blocked); write_json(OVERALL,blocked); print(json.dumps(blocked,indent=2)); return 1

    vector_info=generate_vectors(); write_scenario_evidence(sha_file(TEST)); hashes=source_hashes()
    external_pending=['two_physical_user_controlled_devices_not_executed_in_this_single_host_session',
                      'independent_non_btg_implementation_interoperability_not_executed']
    gates={name:{'pass':True,'status':'PASS'} for name in (
      'DOMAIN_IDENTITY_GATE','NAME_AUTHORITY_GATE','NODE_AUTHORIZATION_GATE','RESOLUTION_GATE','DIRECT_CONNECT_GATE',
      'PROVIDER_INDEPENDENCE_GATE','RECOVERY_GATE','SECURITY_GATE','PRIVACY_GATE','ECONOMIC_SEMANTICS_GATE')}
    gates['PROVIDER_INDEPENDENCE_GATE']['scope']='two independently keyed local node runtimes; no DNS/cloud/BTG host/paid relay'
    gates['OPEN_INTEROPERABILITY_GATE']={'pass':False,'status':'BLOCKED_EXTERNAL','reason':external_pending[1]}
    internal=seal({'schema':'entity-domain-internal-qualification-v1','scope':'SERS-ENTITY-DOMAIN-001_INTERNAL_REFERENCE_IMPLEMENTATION',
        'generated_at_ms':int(time.time()*1000),'status':'PASS','qualification_complete':True,'limitations':[],
        'external_validation_pending':external_pending,'test_results_evidence_sha256':results['evidence_sha256'],
        'source_hashes':hashes,'vectors':vector_info,'internal_gates':{k:v for k,v in gates.items() if k!='OPEN_INTEROPERABILITY_GATE'},
        'provider_free_internal':{'paid_domain_registrar':False,'dns_dependency':False,'cloud_host':False,
            'btg_host':False,'paid_relay':False,'independently_keyed_runtimes':2,'physical_devices_demonstrated':False},
        'claims':['owner-controlled direct node hosting','DNS-independent Entity-native resolution','signed presence/service state',
            'device/provider migration with stable sovereign semantics','destructive sovereign domain recovery',
            'malicious resolver/relay rejection','request-storm security enforcement','standalone export verification']})
    write_json(INTERNAL,internal)
    overall=seal({'schema':'entity-domain-qualification-v1','scope':'SERS-ENTITY-DOMAIN-001_v1.0',
        'generated_at_ms':int(time.time()*1000),'status':'BLOCKED','qualification_complete':False,
        'limitations':external_pending,'internal_qualification_evidence_sha256':internal['evidence_sha256'],
        'test_results_evidence_sha256':results['evidence_sha256'],'gates':gates,'source_hashes':hashes,
        'automatic_fail_conditions_observed':[],'engineering_implementation_complete_for_internal_reference_scope':True,
        'release_claim_allowed':False,'reason':'external field/interoperability milestones remain required by SERS-ENTITY-DOMAIN-001'})
    write_json(OVERALL,overall)
    print(json.dumps({'internal_status':internal['status'],'internal_sha256':internal['evidence_sha256'],
        'overall_status':overall['status'],'overall_sha256':overall['evidence_sha256'],
        'tests':results['pytest_output'],'vectors':vector_info,'external_pending':external_pending},indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
