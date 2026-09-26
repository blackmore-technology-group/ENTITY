from pathlib import Path
import importlib.util, sys
import pytest

ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

EC=load('closure_controls',ROOT/'01_Core_Runtime'/'engineering_controls'/'canonical_engineering_controls.py')
ID=load('closure_identity',ROOT/'01_Core_Runtime'/'identity'/'canonical_identity.py')
PG=load('closure_public_gateway',ROOT/'03_Public_Internet_Bridge'/'public_gateway'/'canonical_public_gateway.py')
WP=load('closure_web_publish',ROOT/'03_Public_Internet_Bridge'/'web_publish'/'canonical_web_publish.py')
ADAM=load('closure_adam',ROOT/'11_ADAM'/'approval_gates'/'canonical_adam_capabilities.py')
BSIE=load('closure_bsie',ROOT/'12_BSIE'/'digital_entity_world'/'canonical_entity_world.py')

def cp(tmp_path): return EC.CanonicalEngineeringControlPlane(tmp_path)

def test_governance_authority_and_claim_evidence(tmp_path):
    c=cp(tmp_path); c.register_jurisdiction_profile('CA-BC',1,{'regulated_execution':'DISABLED'})
    denied=c.authorize({'actor':'a','capability':'x','action':'VIEW','purpose':'test','policy':'DENY','jurisdiction':'CA-BC','time_ms':1,'capability_active':True}); assert denied['allowed'] is False
    high=c.authorize({'actor':'a','capability':'x','action':'IP_ASSIGNMENT','purpose':'test','policy':'ALLOW','jurisdiction':'CA-BC','time_ms':1,'capability_active':True}); assert high['allowed'] is False
    allowed=c.authorize({'actor':'a','capability':'x','action':'IP_ASSIGNMENT','purpose':'test','policy':'ALLOW','jurisdiction':'CA-BC','time_ms':1,'capability_active':True,'approval_ref':'board:1'}); assert allowed['allowed'] is True
    with pytest.raises(PermissionError): c.transition_claim('claim-1','UNKNOWN','VERIFIED')
    assert c.transition_claim('claim-1','UNKNOWN','VERIFIED',evidence={'record':'authority:1'})['payload']['status']=='VERIFIED'

def test_node_authority_offline_replay_conflict_and_recovery(tmp_path):
    c=cp(tmp_path); root='ent-root-1'
    c.authorize_node(root,'node-a','pk-a',['PRESENCE','SIGN_EVENT'],protocol_version='1.0',schema_version='1',crypto_suite='Ed25519+X25519')
    first=c.reconcile_node_event('node-a','n1',exclusive=False,payload={'x':1}); second=c.reconcile_node_event('node-a','n1',exclusive=False,payload={'x':999})
    assert first==second and first['signed_locally'] and first['reconciled']
    with pytest.raises(PermissionError): c.reconcile_node_event('node-a','n2',exclusive=True,conflicting_state=True)
    exported=c.export_node_state('node-a'); assert exported['entity_root']==root and exported['historical_evidence_preserved']
    c.revoke_node('node-a')
    with pytest.raises(PermissionError): c.reconcile_node_event('node-a','n3')
    c.authorize_node(root,'node-b','pk-b',['PRESENCE'],protocol_version='1.0',schema_version='1',crypto_suite='Ed25519+X25519')
    assert c.export_node_state('node-b')['entity_root']==root

def test_hosted_site_publication_is_explicit_and_rights_safe(tmp_path):
    c=cp(tmp_path)
    c.register_site('entity-a','private-site','asset-1',classification='PRIVATE',rights_state='VERIFIED',policy_ref='p1',provenance_ref='prov1')
    with pytest.raises(PermissionError): c.publish_site('private-site','public-web',terms_state='VERIFIED',approval_ref='a1')
    c.register_site('entity-a','public-site','asset-2',classification='PUBLIC',rights_state='UNKNOWN',policy_ref='p2',provenance_ref='prov2')
    with pytest.raises(PermissionError): c.publish_site('public-site','public-web',terms_state='VERIFIED',approval_ref='a1')
    c.register_site('entity-a','ok-site','asset-3',classification='PUBLIC',rights_state='VERIFIED',policy_ref='p3',provenance_ref='prov3')
    with pytest.raises(PermissionError): c.publish_site('ok-site','platform-x',terms_state='REVIEW_REQUIRED',approval_ref=None)
    ev=c.publish_site('ok-site','platform-x',terms_state='REVIEW_REQUIRED',approval_ref='human-approval')
    assert ev['source_rights_mutated'] is False and ev['source_provenance_mutated'] is False

def test_hosted_app_scope_update_idempotency_and_untrusted_content(tmp_path):
    c=cp(tmp_path); h='a'*64
    c.install_app('entity-a','app-1','1.0',['READ','WRITE'],package_sha256=h,sbom_sha256=h,rbom_sha256=h)
    c.update_app('app-1','1.1',['READ'])
    with pytest.raises(PermissionError): c.update_app('app-1','1.2',['READ','ADMIN'])
    c.update_app('app-1','1.2',['READ','ADMIN'],approved_scope_expansion=True)
    with pytest.raises(PermissionError): c.authorize_app_action('app-1','ADMIN',policy_allowed=True,instruction_origin='DOCUMENT',nonce='r1')
    first=c.authorize_app_action('app-1','ADMIN',policy_allowed=True,instruction_origin='AUTHORIZED_REQUEST',nonce='r2')
    second=c.authorize_app_action('app-1','ADMIN',policy_allowed=True,instruction_origin='AUTHORIZED_REQUEST',nonce='r2')
    assert first==second and first['commercialization_rights_inferred'] is False

def test_security_projection_crypto_sessions_and_public_gateway(tmp_path):
    c=cp(tmp_path); profile=c.register_crypto_profile('default',signing='Ed25519',hashing='SHA-256',key_agreement='X25519+HKDF-SHA256')
    assert profile['payload']['schema_crypto_agile'] is True
    data={'name':'safe','private_key':'never','api_key':'never2','summary':'ok'}
    out=c.minimum_projection(data,['name','private_key','api_key','summary'],classification='INTERNAL',permission=True,provider='OPENAI',purpose='analysis')
    assert out['projection']=={'name':'safe','summary':'ok'}
    with pytest.raises(PermissionError): c.minimum_projection(data,['name'],classification='RESTRICTED',permission=True,provider='OPENAI',purpose='analysis')
    assert c.device_session('dev1',authorized=True,secure_transport=True,expires_at_ms=10**15,high_impact=True,step_up=False)['allowed'] is False
    assert c.device_session('dev1',authorized=True,secure_transport=True,expires_at_ms=10**15,high_impact=True,step_up=True)['allowed'] is True
    g=PG.PublicGatewayAuthority(max_requests_per_token=1); tok=g.issue_token('entity-a','site-1',['READ'])['token']
    assert g.authorize(tok,'READ',secure_transport=False)['allowed'] is False
    assert g.authorize(tok,'READ',secure_transport=True)['allowed'] is True
    assert g.authorize(tok,'READ',secure_transport=True)['allowed'] is False

def test_operations_slo_telemetry_incident_and_provider_migration(tmp_path):
    c=cp(tmp_path)
    slo=c.register_slo('entity-api',availability_target=.999,latency_target_ms=250,error_budget=.001,rpo_seconds=300,rto_seconds=900,max_sync_lag_seconds=120,alert_thresholds={'latency_ms':500},owner='operations',runbook='runbooks/entity-api.md')
    assert slo['payload']['rto_seconds']==900
    tel=c.telemetry('latency_ms',123,tags={'region':'ca-bc','entity_id':'private','path':'secret'})
    assert tel['tags']=={'region':'ca-bc'} and tel['sensitive_content_stored'] is False
    inc=c.record_incident('inc-1',category='KEY_COMPROMISE',containment='revoke-key',evidence_ref='ev:1',recovery='rotate',root_cause='test',remediation='patched')
    assert inc['state']=='CLOSED'
    mig=c.record_migration('mig-1',entity_root_before='root1',entity_root_after='root1',semantic_root_before='sem1',semantic_root_after='sem1',source_provider='A',destination_provider='B',source_schema='1',target_schema='2',tool_version='migrator-1')
    assert mig['payload']['former_provider_authority_retained'] is False and mig['payload']['historical_meaning_preserved'] is True
    with pytest.raises(ValueError): c.record_migration('bad',entity_root_before='root1',entity_root_after='root2',semantic_root_before='sem1',semantic_root_after='sem1',source_provider='A',destination_provider='B',source_schema='1',target_schema='2',tool_version='migrator-1')

def test_all_sdk_profiles_are_versioned_scoped_and_replay_safe(tmp_path):
    c=cp(tmp_path)
    for platform in ('ANDROID','APPLE','WEB','WINDOWS'):
        row=c.register_sdk(platform,'1.0',schema_version='entity-api-v1',crypto_suite='Ed25519+SHA256',scopes=['READ','MUTATE'],extensions=['btg:entity:v1'])
        assert row['payload']['ambient_authority'] is False and 'DUPLICATE_REPLAY' in row['payload']['error_taxonomy']
        first=c.sdk_mutation(platform,'nonce-1',scope='MUTATE',policy_allowed=True)
        second=c.sdk_mutation(platform,'nonce-1',scope='MUTATE',policy_allowed=True)
        assert first==second and first['replay_safe'] is True
        with pytest.raises(PermissionError): c.sdk_mutation(platform,'nonce-2',scope='ADMIN',policy_allowed=True)

def test_adam_and_bsie_authority_boundaries(tmp_path):
    c=cp(tmp_path)
    cap={'agent_id':'adam-1','active':True,'operations':['EXPORT'],'financial_limit':100}
    assert c.authorize_adam(cap,{'operation':'EXPORT','instruction_origin':'AUTHORIZED_REQUEST','amount':0})['entity_root_authority_inherited'] is False
    with pytest.raises(PermissionError): c.authorize_adam(cap,{'operation':'EXPORT','instruction_origin':'WEB_PAGE','amount':0})
    with pytest.raises(PermissionError): c.authorize_adam(cap,{'operation':'PAY','instruction_origin':'AUTHORIZED_REQUEST','amount':1})
    world={'world_id':'w1','evidence_origin':'DERIVED_INFERENCE','state':{'label':'trail','private_owner_guess':'x'}}
    projection=c.bsie_projection(world,['label'])
    assert projection['state']=={'label':'trail'} and projection['legal_ownership_inferred'] is False and projection['verified_truth_inferred'] is False
    bsie=BSIE.CanonicalEntityWorld(tmp_path); obj=bsie.observe('TRAIL',{'name':'T1'},evidence_origin='DERIVED_INFERENCE',classification='PRIVATE')
    assert bsie.project(obj['world_id'])['state']=={'redacted':True}

def test_web_publication_uses_separate_signed_export_event(tmp_path):
    ids=ID.EntityIdentityVault(tmp_path); entity=ids.create('Publisher','organization')['entity_id']
    ledger=WP.WebPublicationLedger(tmp_path,ids)
    with pytest.raises(PermissionError): ledger.record_export(entity,'asset-1','platform-x',terms_snapshot=None,terms_state='REVIEW_REQUIRED',rights_impact={'licence':'unknown'},approval_ref=None,external_content_id=None,outcome='PENDING')
    event=ledger.record_export(entity,'asset-1','platform-x',terms_snapshot={'version':'1'},terms_state='VERIFIED',rights_impact={'ownership_retained':True},approval_ref='approval-1',external_content_id='ext-1',outcome='SUCCESS')
    assert event['source_rights_mutated'] is False and event['source_provenance_mutated'] is False and ID.EntityIdentityVault.verify_signature(ids.load_manifest(entity),{k:v for k,v in event.items() if k!='signature'},event['signature'])

def test_release_gate_fails_closed_and_claims_are_precise(tmp_path):
    c=cp(tmp_path)
    package={k:'x' for k in ['source_revision','build_hashes','sbom','rbom','pbom','test_results','qualification_result','schema_versions','crypto_versions','migration_versions','artifact_hashes','release_signer','timestamp','rtm_snapshot','release_gates']}; package['representative_operational_evidence']='field:1'
    assert c.evaluate_release([],package)['pass'] is True
    bad=c.evaluate_release([{'class':'ROOT_TAKEOVER','status':'OPEN'}],package); assert bad['pass'] is False
    assert c.classify_public_claim('RIGHTS_VERIFIED')['ownership_implied'] is False
    assert c.verify_audit()['pass'] is True and c.status()['ready'] is True


def test_research_sandbox_promotion_and_archive_integrity(tmp_path):
    c=cp(tmp_path)
    sandbox=c.classify_artifact('prototype-1',environment='SANDBOX',maturity='EXPERIMENTAL',evidence_origin='DERIVED_INFERENCE',synthetic=True)
    assert sandbox['payload']['production_authority'] is False
    with pytest.raises(PermissionError): c.promote_artifact('prototype-1',tests_passed=True,review_ref=None,release_evidence_ref='ev:1')
    prod=c.promote_artifact('prototype-1',tests_passed=True,review_ref='review:1',release_evidence_ref='ev:1')
    assert prod['payload']['environment']=='PRODUCTION' and prod['payload']['production_authority'] is True
    archive=c.archive_state('old-release-1',schema_version='1',verification_ref='hash:1',retention_basis='historical evidence',active_authority=False)
    assert archive['payload']['historical_verifiable'] is True and archive['payload']['active_authority'] is False
    with pytest.raises(PermissionError): c.archive_state('bad-archive',schema_version='1',verification_ref='hash:2',retention_basis='test',active_authority=True)
