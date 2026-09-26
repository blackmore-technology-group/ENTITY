from pathlib import Path
import hashlib, importlib.util, os, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load('closure_identity',ROOT/'01_Core_Runtime/identity/canonical_identity.py')
S=load('closure_service',ROOT/'01_Core_Runtime/api/canonical_service.py')
K=load('closure_keys',ROOT/'13_Security/key_management/canonical_key_management.py')
H=load('closure_hw',ROOT/'13_Security/key_management/canonical_hardware_keys.py')
A=load('closure_adamcap',ROOT/'11_ADAM/approval_gates/canonical_adam_capabilities.py')
X=load('closure_adamact',ROOT/'11_ADAM/executors/canonical_adam_actions.py')
B=load('closure_bsie',ROOT/'12_BSIE/digital_entity_world/canonical_entity_world.py')
AR=load('closure_ar',ROOT/'09_Spatial_AR_Dashboard/canonical_ar_projection.py')
F=load('closure_fed',ROOT/'02_Peer_Network/canonical_peer_network.py')
D=load('closure_discovery',ROOT/'02_Peer_Network/discovery/canonical_peer_discovery.py')
T=load('closure_transport',ROOT/'02_Peer_Network/transport/canonical_peer_transport.py')
N=load('closure_nat',ROOT/'02_Peer_Network/nat_traversal/canonical_nat_traversal.py')
R=load('closure_relay',ROOT/'02_Peer_Network/relay_fallback/canonical_relay.py')
BE=load('closure_becp',ROOT/'02_Peer_Network/BECP_Control_Plane/canonical_becp_evidence.py')
PG=load('closure_gateway',ROOT/'03_Public_Internet_Bridge/public_gateway/canonical_public_gateway.py')
WP=load('closure_publish',ROOT/'03_Public_Internet_Bridge/web_publish/canonical_web_publish.py')
KC=load('closure_kc',ROOT/'04_Entity_Registry/canonical_knowledge_capital.py')
DU=load('closure_du',ROOT/'04_Entity_Registry/data_universe_adapter/canonical_data_universe.py')
RI=load('closure_relid',ROOT/'04_Entity_Registry/relationships/canonical_relationship_identity.py')
PB=load('closure_preboot',ROOT/'16_Test_Qualification/evidence/canonical_prebootstrap_evidence.py')
C2=load('closure_c2pa',ROOT/'14_Protocols_SDK/c2pa/canonical_c2pa.py')
def test_tpm_hardware_custody_and_portable_recovery(tmp_path):
    name='ENTITY-QUALIFY-'+os.urandom(6).hex(); protector=H.WindowsTpmProtector(name)
    try:
        probe=protector.probe(); assert probe['ready'] and probe['private_export_blocked'] and probe['provider']==H.PROVIDER
        ids=I.EntityIdentityVault(tmp_path/'state',key_protector=protector); ent=ids.create('TPM Entity','organization')['entity_id']
        secret=os.urandom(32); custody=K.RecoveryCustodyManager(tmp_path/'state',ids,protector)
        result=custody.commission_entity(ent,secret); assert result['hardware_protected'] and result['raw_recovery_keys_removed']
        manifest=ids.load_manifest(ent); rec=manifest['recovery_policy']['authorities'][0]
        assert not (ids._entity_key_dir(ent)/f'{rec}.key').exists() and (ids._entity_key_dir(ent)/f'{rec}.key.tpm').exists()
        assert ids.sign(ent,{'probe':'operational'})
        restored=I.EntityIdentityVault(tmp_path/'restored'); restored._manifest_path(ent).write_text(ids._manifest_path(ent).read_text(),encoding='utf-8')
        custody2=K.RecoveryCustodyManager(tmp_path/'state',ids,protector); assert custody2.restore_portable(ent,rec,secret,target_identity=restored)['portable_recovery_restored']
    finally: protector.delete()

def test_guardian_and_purpose_keys(tmp_path):
    protector=H.WindowsTpmProtector('ENTITY-QUALIFY-'+os.urandom(6).hex())
    try:
        ids=I.EntityIdentityVault(tmp_path/'state'); a=ids.create('A','organization')['entity_id']; g1=ids.create('G1','person')['entity_id']; g2=ids.create('G2','person')['entity_id']
        pm=K.PurposeKeyManager(tmp_path/'state',protector); key=pm.create(a,'PAYMENT'); sig=pm.sign(key['key_id'],'PAYMENT',b'abc')
        assert pm.verify(key['key_id'],'PAYMENT',b'abc',sig['signature_b64']) and not pm.verify(key['key_id'],'CONTRACT',b'abc',sig['signature_b64'])
        gm=K.GuardianRecoveryManager(tmp_path/'state',ids); pol=gm.create_policy(a,[g1,g2],2); gm.request(pol['policy_id'],'recover-1'); gm.approve('recover-1',g1)
        assert not gm.authorize('recover-1')['allowed']; gm.approve('recover-1',g2); assert gm.authorize('recover-1')['allowed']
        with pytest.raises(ValueError): gm.approve('recover-1',g2)
    finally: protector.delete()
def test_canonical_service_full_domain_surface(tmp_path):
    api=S.CanonicalServiceAPI(tmp_path/'state'); a=api.identity.create('Controller','organization')['entity_id']; b=api.identity.create('Counterparty','organization')['entity_id']
    ops=['IDENTITY_ADMIN','SOURCE_ADMIN','VAULT_WRITE','ASSET_REGISTER','RIGHTS_ASSERT','RIGHTS_DISPUTE','POLICY_ADMIN','CONSENT_GRANT','LICENCE_CREATE','LICENCE_OFFER','LICENCE_ACTIVATE','USAGE_AUTHORIZE','USAGE_RECORD','LEDGER_APPEND','LEDGER_CHECKPOINT','SETTLEMENT_CREATE','SETTLEMENT_AUTHORIZE','SETTLEMENT_EXECUTE','SETTLEMENT_EVIDENCE','SETTLEMENT_CONFIRM','EXPORT','BACKUP_CREATE','CAPABILITY_ADMIN','DATA_POOL_ADMIN','DATA_POOL_CONTRIBUTE','DATA_SPACE_ADMIN','DATA_SPACE_AUTHORIZE','DATA_SPACE_USE']
    ac=api.capabilities.grant(a,'agent-a',operations=ops); bc=api.capabilities.grant(b,'agent-b',operations=['LICENCE_ACCEPT','USAGE_RECORD','DATA_POOL_CONTRIBUTE','DATA_SPACE_USE'])
    c=api.identity_create(ac['capability_id'],'agent-a',display_name='Created Through API',entity_type='person'); assert c['entity_id']!=a
    src=tmp_path/'source'; src.mkdir(); f=src/'asset.bin'; f.write_bytes(b'asset-data')
    enrolled=api.source_enroll(ac['capability_id'],'agent-a',a,src,mode='PROVENANCE',discovery_allowed=True,content_allowed=True); assert enrolled['mode']=='PROVENANCE'
    vault=api.vault_put(ac['capability_id'],'agent-a',a,b'private',classification='PRIVATE'); assert vault['state']=='ACTIVE'
    asset=api.asset_register(ac['capability_id'],'agent-a',a,content_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),size_bytes=f.stat().st_size,media_type='application/octet-stream',title='Qualified Asset'); aid=asset['asset_id']
    pol=api.policy_create(ac['capability_id'],'agent-a',a,'Use Policy',{'VIEW':'PERMIT'}); con=api.consent_grant(ac['capability_id'],'agent-a',a,pol['policy_id'],purpose='research',asset_scope=[aid],counterparty_entity_id=b); assert con['status']=='ACTIVE'
    terms={'assets':[aid],'rights':['VIEW'],'purpose':'research','scope':{},'territory':'CA','duration':'1y','consideration':{'amount':100},'usage_requirements':{'max_quantity_per_event':5},'reporting_requirements':{},'retention_requirements':{},'derivative_rules':{},'revocation_rules':{},'termination_rules':{}}
    lic=api.licence_draft(ac['capability_id'],'agent-a',a,b,terms); lid=lic['licence_id']; api.licence_offer(ac['capability_id'],'agent-a',a,lid); api.licence_accept(bc['capability_id'],'agent-b',b,lid); api.licence_activate(ac['capability_id'],'agent-a',a,lid)
    ticket=api.usage_gateway_ticket(ac['capability_id'],'agent-a',a,licence_id=lid,asset_id=aid,use_type='VIEW',quantity=1,nonce='ticket-1'); receipt=api.usage_consume(bc['capability_id'],'agent-b',b,ticket['ticket_id'],purpose='research',nonce='receipt-1'); assert receipt['assurance']=='ENTITY_GATEWAY_OBSERVED'
    st=api.settlement_create(ac['capability_id'],'agent-a',a,b,amount_units=100,currency='CAD',obligation_ref=lid,transaction_nonce='settle-1',settlement_kind='INTERNAL_ACCOUNTING'); api.settlement_authorize(ac['capability_id'],'agent-a',a,st['settlement_id']); final=api.settlement_confirm(ac['capability_id'],'agent-a',a,st['settlement_id']); assert final['double_entry_balanced']
    pool=api.data_pool_create(ac['capability_id'],'agent-a',a,name='Pool'); api.data_pool_contribute(bc['capability_id'],'agent-b',b,pool['pool_id'],asset_id=aid,weight_bps=10000,evidence={'receipt':receipt['receipt_id']})
    space=api.data_space_create(ac['capability_id'],'agent-a',a,[aid],['INFERENCE']); sess=api.data_space_issue(ac['capability_id'],'agent-a',a,space['space_id'],b,'INFERENCE',quantity=1,nonce='space-1'); used=api.data_space_consume(bc['capability_id'],'agent-b',b,sess['session_id']); assert used['raw_file_transfer_observed'] is False
    chk=api.ledger_checkpoint(ac['capability_id'],'agent-a',a); assert api.ledger.verify_checkpoint(chk['checkpoint_id'])['pass']
    out=api.export_entity(ac['capability_id'],'agent-a',a,tmp_path/'export'); assert out['private_keys_included'] is False
    with pytest.raises(PermissionError): api.capability_grant(ac['capability_id'],'agent-a',b,'evil',operations=['ENTITY_ADMIN'])
    status=api.status(); assert status['ready'] and all(v.get('ready',True) for v in status['domains'].values())
def test_adam_bsie_and_ar_authority_boundaries(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/'state'); a=ids.create('Owner','organization')['entity_id']
    gate=A.AdamCapabilityGate(tmp_path/'state',ids); cap=gate.grant(a,'adam-1',operations=['EXPORT'],asset_scope=['asset-x'])
    executor=X.AdamActionExecutor(tmp_path/'state',gate); proposal={'operation':'EXPORT','asset_id':'asset-x','object_ref':'obj','instruction_origin':'AUTHORIZED_REQUEST'}
    result=executor.execute(proposal,request_id='req-1',capability_id=cap['capability_id'],agent_id='adam-1',handler=lambda p:{'ok':True}); assert result['authorized']
    with pytest.raises(PermissionError): executor.execute(dict(proposal,instruction_origin='WEB_CONTENT'),request_id='req-2',capability_id=cap['capability_id'],agent_id='adam-1',handler=lambda p:{})
    with pytest.raises(ValueError): executor.execute(proposal,request_id='req-1',capability_id=cap['capability_id'],agent_id='adam-1',handler=lambda p:{})
    gate.revoke(a,cap['capability_id']); assert not gate.authorize_proposal(proposal,capability_id=cap['capability_id'],agent_id='adam-1')['allowed']
    world=B.CanonicalEntityWorld(tmp_path/'state'); w1=world.observe('PLACE',{'secret':'x'},evidence_origin='DIRECT_OBSERVATION',classification='PRIVATE'); w2=world.observe('OBJECT',{'kind':'tree'},evidence_origin='DERIVED_INFERENCE'); rel=world.relate(w1['world_id'],'NEAR',w2['world_id'],evidence_origin='DERIVED_INFERENCE')
    assert rel['rights_inferred'] is False and world.project(w1['world_id'])['state']=={'redacted':True}
    overlay=AR.ArProjectionAuthority.project(world.project(w2['world_id']),classification='PUBLIC'); assert overlay['read_only'] and not overlay['authoritative_mutation_allowed']
    assert AR.ArProjectionAuthority.classify_ai('trail',.8)['evidence_origin']=='DERIVED_INFERENCE'

def test_peer_network_connectivity_is_not_authority(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/'state'); witness_id=ids.create('Witness','organization')['entity_id']
    fed=F.FederationTrustStore(tmp_path/'state'); fed.trust_peer('p2','did:peer:p2',protocol_version=2,schemas=['v1'],trust_level=5)
    assert fed.authenticate('p2','did:peer:p2',protocol_version=2,nonce='n1',min_trust=4,required_schema='v1')['allowed']
    assert not fed.authenticate('p2','did:peer:p2',protocol_version=1,nonce='n2')['allowed']; assert not fed.authenticate('p2','did:peer:p2',protocol_version=2,nonce='n1')['allowed']
    wit=F.TransparencyWitness(tmp_path/'state',ids).witness(witness_id,'evt',hashlib.sha256(b'e').hexdigest()); assert F.TransparencyWitness(tmp_path/'state',ids).verify(wit['witness_id'])
    discovery=D.PeerDiscoveryRegistry(tmp_path/'state'); one=discovery.announce('p2','pair-p2','hint',nonce='d1'); assert one['trust_state']=='UNTRUSTED_DISCOVERED'
    key=os.urandom(32); ab=T.PeerTransportSession('a','b',key,protocol_version=1,authenticated=True); ba=T.PeerTransportSession('b','a',key,protocol_version=1,authenticated=True); packet=ab.send(b'hello'); assert ba.receive(packet)==b'hello'
    with pytest.raises(ValueError): ba.receive(packet)
    nat=N.NatTraversalCoordinator(); ns=nat.negotiate('a','b',authenticated=True,direct_candidates=[],relay_candidates=['relay']); assert ns['connected'] and not ns['relay_or_nat_is_authority']
    relay=R.OpaqueRelayCarrier(); p2=ab.send(b'opaque'); accepted=relay.forward('a','b',p2); assert accepted['accepted'] and not accepted['payload_decrypted']
def test_public_becp_knowledge_relationship_and_prebootstrap(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/'state'); a=ids.create('Publisher','organization')['entity_id']
    becp=BE.BecpObservableEvidence(tmp_path/'state',ids); ev=becp.record(event_nonce='be1',destination='provider',purpose='inference',request_visible={'q':1},response_visible={'a':2},provider_metadata={'model':'x'},transport_outcome='SUCCESS',controller_entity_id=a)
    dup=becp.record(event_nonce='be1',destination='provider',purpose='inference',request_visible={'q':1},response_visible={'a':2},provider_metadata={'model':'x'},transport_outcome='SUCCESS',controller_entity_id=a); assert dup['deduplicated'] and ev['hidden_provider_activity']=='UNKNOWN'
    gate=PG.PublicGatewayAuthority(max_requests_per_token=2); tok=gate.issue_token(a,'asset-x',['READ']); assert not gate.authorize(tok['token'],'READ',secure_transport=False)['allowed']; assert gate.authorize(tok['token'],'READ',secure_transport=True)['allowed']
    pub=WP.WebPublicationLedger(tmp_path/'state',ids); out=pub.record_export(a,'asset-x','https://example.test',terms_snapshot=None,terms_state='REVIEW_REQUIRED',rights_impact={'none':True},approval_ref='approval-1',external_content_id='x1',outcome='SUCCESS'); assert not out['source_rights_mutated']
    kc=KC.KnowledgeCapitalRegistry(tmp_path/'state',ids); rec=kc.record(a,kind='ARCHITECTURE',title='Design',contributors=[{'kind':'HUMAN','id':a},{'kind':'AI','id':'model'}],artifact_sha256=hashlib.sha256(b'design').hexdigest()); assert kc.verify(rec['receipt_id'])
    rel=RI.RelationshipIdentityAuthority(ids); pw=rel.pairwise(a,'partner-x'); assert pw['entity_id_not_disclosed'];
    with pytest.raises(PermissionError): rel.correlate(pw['relationship_id'])
    adopter=PB.PrebootstrapEvidenceAdopter(tmp_path/'state'); payload={'legacy':'evidence'}; digest=hashlib.sha256(__import__('json').dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(); adopted=adopter.adopt('old-1',payload,content_sha256=digest,evidence_origin='EXTERNAL_AUTHORITATIVE_RECORD',assurance='IMPORTED'); assert not adopted['retroactively_upgraded']

def test_real_c2pa_and_data_universe_projection(tmp_path):
    sample=ROOT/'14_Protocols_SDK/c2pa/c2patool-v0.27.22/c2patool/sample/C.jpg'; c=C2.CanonicalC2paVerifier().verify(sample); assert c['provenance_valid'] and not c['factual_truth_established'] and not c['ownership_established']
    api=S.CanonicalServiceAPI(tmp_path/'state'); a=api.identity.create('Owner','organization')['entity_id']; cap=api.capabilities.grant(a,'agent',operations=['ASSET_REGISTER'])
    data=b'data'; asset=api.asset_register(cap['capability_id'],'agent',a,content_sha256=hashlib.sha256(data).hexdigest(),size_bytes=len(data),media_type='application/octet-stream',title='Asset')
    projection=DU.DataUniverseProjection(tmp_path/'state',api.identity).project(a); row=next(x for x in projection['assets'] if x['asset_id']==asset['asset_id']); assert row['ownership_not_inferred'] and projection['raw_vault_content_exposed'] is False
