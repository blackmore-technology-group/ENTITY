from __future__ import annotations
from pathlib import Path
import base64, copy, importlib.util, json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load('dom_identity',ROOT/'01_Core_Runtime'/'identity'/'canonical_identity.py')
D=load('dom_core',ROOT/'22_Sovereign_Domain'/'core'/'canonical_domain.py')
R=load('dom_resolver',ROOT/'22_Sovereign_Domain'/'resolution'/'canonical_resolution.py')
N=load('dom_node',ROOT/'22_Sovereign_Domain'/'node_runtime'/'canonical_node_runtime.py')
P=load('dom_presence',ROOT/'22_Sovereign_Domain'/'presence'/'canonical_presence.py')
M=load('dom_migration',ROOT/'22_Sovereign_Domain'/'migration'/'canonical_domain_migration.py')
PORT=load('dom_portability',ROOT/'22_Sovereign_Domain'/'portability'/'canonical_domain_portability.py')
REC=load('dom_recovery',ROOT/'22_Sovereign_Domain'/'recovery'/'canonical_domain_recovery.py')
FS=load('dom_states',ROOT/'22_Sovereign_Domain'/'failure_states'/'canonical_domain_states.py')
REL=load('dom_relay',ROOT/'22_Sovereign_Domain'/'protocols'/'canonical_domain_relay.py')
B=load('dom_backup',ROOT/'15_Operations'/'backups'/'canonical_portable_state.py')
def build_domain(tmp_path,label='Owner'):
    state=tmp_path/'state'; ids=I.EntityIdentityVault(state)
    owner=ids.create(label,'organization')["entity_id"]
    domain=D.EntityDomainAuthority(state,ids)
    created=domain.create_domain(owner,requested_name='owner.entity')
    did=created['domain_id']
    node=N.EntityNodeRuntime(tmp_path/'node-a','node-a')
    node.add_api_service('svc-api',lambda req:{'echo':req.get('value'),'owner_controlled':True})
    started=node.start('127.0.0.1',0)
    auth=domain.authorize_node(owner,did,node.public_key_b64,permitted_services=['API','DATA_OFFER'],node_id='node-a')
    svc=domain.publish_service(owner,did,'node-a','API',{'host':started['host'],'port':started['port']},
        capabilities=['ECHO'],access_class='PUBLIC',policy_refs=['policy:public-api'],
        data_classifications=['PUBLIC'],economic_terms_ref=None,service_id='svc-api')
    snap=domain.public_snapshot(did); resolver=R.EntityNativeResolver(ids); resolver.add_snapshot('local-a',snap)
    proof=resolver.resolve('owner.entity',service_id='svc-api')
    return {'state':state,'ids':ids,'owner':owner,'domain':domain,'domain_id':did,'node':node,
            'node_auth':auth,'service':svc,'snapshot':snap,'resolver':resolver,'proof':proof}


def test_provider_free_internal_direct_connect_and_presence(tmp_path):
    env=build_domain(tmp_path)
    try:
        out=N.EntityDirectClient.request(env['proof'],'svc-api',{'value':'hello'})
        assert out['status']==200 and out['result']['echo']=='hello' and out['dns_used'] is False
        presence=P.PresenceAdvertisementManager()
        ad=presence.create(env['node'],env['node_auth'],['svc-api'],scope='PUBLIC',
            endpoint_hints=[env['service']['endpoint']],sequence=1,ttl_ms=60000)
        assert presence.verify(ad,env['node_auth'])['valid'] is True
        tampered=copy.deepcopy(ad); tampered['endpoint_hints']=[{'host':'127.0.0.1','port':1}]
        assert presence.verify(tampered,env['node_auth'])['valid'] is False
        assert env['proof']['dns_used_as_authority'] is False and env['proof']['resolver_is_authority'] is False
        assert env['domain'].status()['owner_controlled_hosting'] is True
    finally:
        env['node'].stop()


def test_malicious_resolver_stale_state_and_revoked_node_fail_closed(tmp_path):
    env=build_domain(tmp_path)
    try:
        malicious=copy.deepcopy(env['snapshot'])
        malicious['services'][0]['endpoint']={'host':'127.0.0.1','port':9}
        with pytest.raises(PermissionError): env['resolver'].add_snapshot('attacker',malicious)
        wrong=copy.deepcopy(env['snapshot']); wrong['domain']['entity_root']='ent1-attacker'
        assert env['resolver'].verify_snapshot(wrong)['valid'] is False
        expected=env['proof']; redirected=copy.deepcopy(expected)
        redirected['services'][0]['service']['endpoint']={'host':'127.0.0.1','port':9}
        assert R.EntityNativeResolver.reject_malicious_response(expected,redirected)['accepted'] is False
        env['domain'].publish_service(env['owner'],env['domain_id'],'node-a','API',env['service']['endpoint'],
            capabilities=['ECHO'],access_class='PUBLIC',policy_refs=['policy:public-api'],
            data_classifications=['PUBLIC'],service_id='svc-api')
        latest=env['domain'].public_snapshot(env['domain_id'])
        env['resolver'].add_snapshot('latest',latest); latest_proof=env['resolver'].resolve(env['domain_id'],service_id='svc-api')
        assert latest_proof['services'][0]['service']['manifest_version']==2
        env['resolver'].add_snapshot('stale-source',env['snapshot'])
        with pytest.raises(KeyError): env['resolver'].resolve(env['domain_id'],service_id='svc-api')
        env['domain'].revoke_node(env['owner'],'node-a','theft-test')
        revoked=env['domain'].public_snapshot(env['domain_id'])
        check=env['resolver'].verify_snapshot(revoked)
        assert check['valid'] is False and any('revoked_node' in x for x in check['failures'])
        with pytest.raises(PermissionError):
            env['domain'].publish_service(env['owner'],env['domain_id'],'node-a','API',env['service']['endpoint'])
    finally:
        env['node'].stop()


def test_device_provider_migration_and_node_theft(tmp_path):
    env=build_domain(tmp_path)
    node_b=N.EntityNodeRuntime(tmp_path/'node-b','node-b')
    node_b.add_api_service('svc-api',lambda req:{'echo':req.get('value'),'node':'b'})
    started_b=node_b.start('127.0.0.1',0)
    try:
        mgr=M.DomainMigrationManager(env['domain'])
        moved=mgr.migrate_service(env['owner'],'svc-api',new_node_public_key_b64=node_b.public_key_b64,
            new_endpoint={'host':started_b['host'],'port':started_b['port']},new_provider='provider-b',
            old_provider='provider-a',new_node_id='node-b',revoke_old=True)
        assert moved['status']=='VERIFIED' and moved['entity_root_unchanged'] and moved['domain_id_unchanged']
        assert moved['semantic_hash_before']==moved['semantic_hash_after']
        assert env['domain'].get_node('node-a')['effective_status']=='REVOKED'
        assert env['domain'].get_node('node-b')['effective_status']=='ACTIVE'
        snap=env['domain'].public_snapshot(env['domain_id']); resolver=R.EntityNativeResolver(env['ids'])
        resolver.add_snapshot('after-migration',snap); proof=resolver.resolve(env['domain_id'],service_id='svc-api')
        assert proof['services'][0]['node']['node_id']=='node-b'
        result=N.EntityDirectClient.request(proof,'svc-api',{'value':'migrated'})
        assert result['status']==200 and result['result']=={'echo':'migrated','node':'b'}
        with pytest.raises(PermissionError):
            env['domain'].publish_service(env['owner'],env['domain_id'],'node-a','API',env['service']['endpoint'])
    finally:
        env['node'].stop(); node_b.stop()


def test_destructive_domain_recovery_preserves_root_and_domain(tmp_path):
    env=build_domain(tmp_path)
    try:
        export_path=tmp_path/'ENTITY_DOMAIN_EXPORT.json'
        portability=PORT.DomainPortabilityManager(env['ids'],env['domain'])
        exported=portability.export_domain(env['owner'],env['domain_id'],export_path,
            state_refs={'rights':'external-master-state','economics':'external-master-state'},external_dependencies=[])
        assert exported['source_database_required'] is False and portability.verify_export(export_path)['valid'] is True
        verifier=ROOT/'22_Sovereign_Domain'/'reference'/'verify_entity_domain.py'
        run=subprocess.run([sys.executable,'-I',str(verifier),str(export_path)],capture_output=True,text=True)
        assert run.returncode==0,run.stdout+run.stderr
        verified=json.loads(run.stdout); assert verified['valid'] is True and verified['independent_interpretation'] is True
        backup_mgr=B.PortableStateManager(env['state'],env['ids']); backup=backup_mgr.create_encrypted_backup(tmp_path/'DOMAIN_STATE.enc')
        key=base64.urlsafe_b64decode(backup['key_b64']); env['node'].stop()
        unavailable=tmp_path/'device-a-state-unavailable'; env['state'].rename(unavailable); assert not env['state'].exists()
        without_btg=subprocess.run([sys.executable,'-I',str(verifier),str(export_path)],capture_output=True,text=True)
        assert without_btg.returncode==0 and json.loads(without_btg.stdout)['valid'] is True
        recovery=REC.DomainRecoveryManager(I.EntityIdentityVault,D.EntityDomainAuthority,PORT.DomainPortabilityManager)
        restored_state=tmp_path/'device-c-state'
        recovered=recovery.recover(backup_manager=backup_mgr,backup_path=backup['path'],key=key,
            target_state=restored_state,domain_export_path=export_path)
        assert recovered['entity_root']==env['owner'] and recovered['domain_id']==env['domain_id']
        assert recovered['entity_root_unchanged'] and recovered['domain_id_unchanged']
        node_c=N.EntityNodeRuntime(tmp_path/'node-c','node-c')
        node_c.add_api_service('svc-api',lambda req:{'echo':req.get('value'),'node':'c'})
        started_c=node_c.start('127.0.0.1',0)
        try:
            migration=M.DomainMigrationManager(recovered['domain_authority'])
            moved=migration.migrate_service(env['owner'],'svc-api',new_node_public_key_b64=node_c.public_key_b64,
                new_endpoint={'host':started_c['host'],'port':started_c['port']},new_provider='device-c',
                old_provider='device-a',new_node_id='node-c',revoke_old=True)
            assert moved['entity_root_unchanged'] and moved['domain_id_unchanged']
            resolver=R.EntityNativeResolver(recovered['identity_vault'])
            resolver.add_snapshot('restored-device',recovered['domain_authority'].public_snapshot(env['domain_id']))
            proof=resolver.resolve(env['domain_id'],service_id='svc-api')
            result=N.EntityDirectClient.request(proof,'svc-api',{'value':'restored'})
            assert result['result']=={'echo':'restored','node':'c'}
        finally:
            node_c.stop()
        tampered=json.loads(export_path.read_text(encoding='utf-8')); tampered['domain_snapshot']['domain']['domain_id']='domain1-tampered'
        bad_path=tmp_path/'DOMAIN_EXPORT_TAMPERED.json'; bad_path.write_text(json.dumps(tampered),encoding='utf-8')
        bad=subprocess.run([sys.executable,'-I',str(verifier),str(bad_path)],capture_output=True,text=True)
        assert bad.returncode==2
    finally:
        try: env['node'].stop()
        except Exception: pass
def test_request_storm_keeps_security_checks_enabled(tmp_path):
    env=build_domain(tmp_path)
    try:
        def valid(i):
            out=N.EntityDirectClient.request(env['proof'],'svc-api',{'value':i},timeout=5)
            return out['status']==200 and out['result']['echo']==i and out['direct_encrypted_session'] is True
        with ThreadPoolExecutor(max_workers=16) as pool:
            results=list(pool.map(valid,range(96)))
        assert all(results)
        bad_proof=copy.deepcopy(env['proof'])
        bad_proof['services'][0]['node']['public_key_b64']='A'*43
        def invalid(i):
            try:
                N.EntityDirectClient.request(bad_proof,'svc-api',{'value':i},timeout=5); return False
            except Exception: return True
        with ThreadPoolExecutor(max_workers=8) as pool:
            rejected=list(pool.map(invalid,range(24)))
        assert all(rejected)
        for _ in range(200):
            proof=env['resolver'].resolve(env['domain_id'],service_id='svc-api')
            assert proof['verified'] is True
    finally:
        env['node'].stop()


def test_domain_failure_states_are_explicit_and_non_reassigning(tmp_path):
    machine=FS.DomainFailureStateMachine(tmp_path/'state','domain-test')
    path=['LOCAL_ONLY','NORMAL','PROVIDER_UNAVAILABLE','RECOVERY','NORMAL','PARTIALLY_REACHABLE','DEGRADED','COMPROMISED_NODE','RECOVERY','NORMAL']
    for state in path:
        event=machine.transition(state,'qualified-test')
        assert event['entity_or_name_reassigned'] is False and event['economic_state_mutated'] is False
    status=machine.status()
    assert status['state']=='NORMAL' and status['outage_reassigns_identity'] is False
    assert status['infrastructure_failure_mutates_economic_rights'] is False
    machine.transition('RESOLUTION_CONFLICT','qualified-conflict')
    with pytest.raises(RuntimeError):
        machine.transition('RELAY_REQUIRED','illegal-direct-transition')


def test_export_privacy_and_economic_semantics(tmp_path):
    env=build_domain(tmp_path)
    try:
        env['domain'].publish_service(env['owner'],env['domain_id'],'node-a','DATA_OFFER',env['service']['endpoint'],
            capabilities=['DISCOVER_ONLY'],access_class='LICENSE_REQUIRED',policy_refs=['policy:data-offer'],
            data_classifications=['RESTRICTED'],economic_terms_ref='licence-terms:offer-1',service_id='svc-offer')
        path=tmp_path/'domain-export.json'; PORT.DomainPortabilityManager(env['ids'],env['domain']).export_domain(env['owner'],env['domain_id'],path)
        raw=path.read_text(encoding='utf-8')
        assert 'node_ed25519.key' not in raw and 'PRIVATE KEY' not in raw and 'recovery key' not in raw.lower()
        package=json.loads(raw); offer=next(x for x in package['domain_snapshot']['services'] if x['service_id']=='svc-offer')
        assert offer['access_class']=='LICENSE_REQUIRED' and offer['economic_terms_ref']=='licence-terms:offer-1'
        assert offer['source_data_custody_transferred'] is False and offer['provider_authority_inferred'] is False
    finally:
        env['node'].stop()


def test_malicious_relay_cannot_manufacture_authority_or_modify_ciphertext():
    relay=REL.OpaqueDomainRelay('relay-test')
    frame=b'opaque-encrypted-frame'; assert relay.forward(frame)==frame
    receipt=relay.transport_receipt(frame)
    assert receipt['relay_is_authority'] is False and receipt['relay_is_owner'] is False
    assert relay.authority_claim(entity_root='fake')['accepted'] is False
    key=AESGCM.generate_key(bit_length=256); nonce=os.urandom(12); aad=b'ENTITY-DIRECT-SESSION-v1'
    cipher=AESGCM(key).encrypt(nonce,b'authorized-payload',aad)
    tampered=bytearray(cipher); tampered[-1]^=1
    with pytest.raises(Exception): AESGCM(key).decrypt(nonce,bytes(tampered),aad)
    replay_guard=P.PresenceAdvertisementManager(); replay_guard.highest_sequence[('d','n')]=5
    assert replay_guard.verify({'schema':'bad'}, {'domain_id':'d','entity_root':'e','node_id':'n','status':'ACTIVE','public_key_b64':''})['valid'] is False


def test_required_protocol_specification_surface_is_published():
    text=(ROOT/'22_Sovereign_Domain'/'protocols'/'ENTITY_DOMAIN_PROTOCOLS_v1.md').read_text(encoding='utf-8')
    for title in ('Domain Identifier','Name Claim','Node Authorization','Service Manifest','Resolution Protocol',
                  'Presence Advertisement','Direct Session Protocol','Relay Protocol','Domain Export','Domain Recovery',
                  'Domain Migration','Economic Service Discovery'):
        assert title in text
    assert 'DNS != sovereign authority' in text and 'External non-BTG implementation interoperability' in text
