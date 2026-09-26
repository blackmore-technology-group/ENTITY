from pathlib import Path
import hashlib, json
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
PLATFORM=json.loads((ROOT/'10_NIKI/ENTITY_PLATFORM_BINDINGS.json').read_text(encoding='utf-8'))['bindings']
CLOSURE='16_Test_Qualification/evidence/ENTITY_RELEASE_CLOSURE_AUTHORITIES_CURRENT.json'
STANDARDS='16_Test_Qualification/evidence/ENTITY_STANDARDS_INTEROP_CURRENT.json'
CORE='16_Test_Qualification/evidence/ENTITY_CANONICAL_CORE_QUALIFICATION_CURRENT.json'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(rel):
    p=ROOT/rel; data=json.loads(p.read_text(encoding='utf-8')); return str(data.get('evidence_sha256') or sha(p))
def req_hash(owner): return sha(ROOT/Path(owner).parts[0]/'ENTITY_REQUIREMENTS.md')
def impl_hash(owner,py): return sha(ROOT/owner/py)
def q(rel): return [{'path':rel,'sha256':seal(rel)}]
NEW={
'adam_actions':('canonical_adam_actions.py',['AdamActionExecutor','niki_accept_action_proposal_v1'],CLOSURE),
'adam_capabilities':('canonical_adam_capabilities.py',['AdamCapabilityGate'],CLOSURE),
'ar_projection':('canonical_ar_projection.py',['ArProjectionAuthority','niki_accept_overlay_layer_v1'],CLOSURE),
'becp_evidence':('canonical_becp_evidence.py',['BecpObservableEvidence','niki_ingest_becp_evidence_v1'],CLOSURE),
'bsie_entity_world':('canonical_entity_world.py',['CanonicalEntityWorld','niki_project_entity_context_v1'],CLOSURE),
'c2pa':('canonical_c2pa.py',['CanonicalC2paVerifier'],CLOSURE),
'data_pools':('canonical_data_economy.py',['DataPoolManager'],CLOSURE),
'data_spaces':('canonical_data_economy.py',['DataSpaceGateway'],CLOSURE),
'data_universe':('canonical_data_universe.py',['DataUniverseProjection','niki_project_data_summary_v1'],CLOSURE),
'federation':('canonical_peer_network.py',['FederationTrustStore'],CLOSURE),
'transparency_witness':('canonical_peer_network.py',['TransparencyWitness'],CLOSURE),
}
NEW.update({
'guardian_recovery':('canonical_key_management.py',['GuardianRecoveryManager'],CLOSURE),
'knowledge_capital':('canonical_knowledge_capital.py',['KnowledgeCapitalRegistry','niki_ingest_reasoning_receipt_v1'],CLOSURE),
'nat_traversal':('canonical_nat_traversal.py',['NatTraversalCoordinator'],CLOSURE),
'peer_discovery':('canonical_peer_discovery.py',['PeerDiscoveryRegistry'],CLOSURE),
'peer_transport':('canonical_peer_transport.py',['PeerTransportSession'],CLOSURE),
'prebootstrap_evidence':('canonical_prebootstrap_evidence.py',['PrebootstrapEvidenceAdopter'],CLOSURE),
'public_gateway':('canonical_public_gateway.py',['PublicGatewayAuthority'],CLOSURE),
'purpose_keys':('canonical_key_management.py',['PurposeKeyManager'],CLOSURE),
'recovery_custody':('canonical_key_management.py',['RecoveryCustodyManager'],CLOSURE),
'relationship_identity':('canonical_relationship_identity.py',['RelationshipIdentityAuthority'],CLOSURE),
'relay':('canonical_relay.py',['OpaqueRelayCarrier'],CLOSURE),
'web_publish':('canonical_web_publish.py',['WebPublicationLedger'],CLOSURE),
'protocol_conformance':('standards_reference_client.py',['validate_did_document','validate_vc20','verify_entity_vc_extension','validate_odrl22'],STANDARDS),
})
def refresh_evidence(owner,items):
    out=[]
    for item in list(items or []):
        x=dict(item); raw=str(x.get('path') or '')
        p=Path(raw)
        if not p.is_absolute():
            cand=(ROOT/owner/p).resolve()
            if not cand.is_file(): cand=(ROOT/p).resolve()
        else: cand=p
        if cand.is_file():
            try:
                d=json.loads(cand.read_text(encoding='utf-8')); x['sha256']=str(d.get('evidence_sha256') or sha(cand))
            except Exception: x['sha256']=sha(cand)
            try: x['path']=str(cand.relative_to(ROOT)).replace('\\','/')
            except ValueError: pass
        out.append(x)
    return out

def existing_entries(owner,raw):
    if not raw: return {}
    if isinstance(raw.get('authorities'),dict): return {k:dict(v) for k,v in raw['authorities'].items()}
    auth=str(raw.get('authority') or '')
    if not auth: return {}
    entry={k:v for k,v in raw.items() if k not in {'schema','abi_version','authority','requirements_sha256','implementation_version'}}
    return {auth:entry}
groups={}
for authority,item in PLATFORM.items(): groups.setdefault(item['owner'],[]).append(authority)
written=[]
for owner,authorities in sorted(groups.items()):
    marker=ROOT/owner/'ENTITY_RUNTIME_BINDING.json'; raw=json.loads(marker.read_text(encoding='utf-8')) if marker.is_file() else {}
    entries=existing_entries(owner,raw); rh=req_hash(owner)
    for authority in authorities:
        if authority in NEW:
            py,exports,ev=NEW[authority]
            entry={'status':'READY','python_file':py,'exports':exports,'qualification_evidence':q(ev),'implementation_sha256':impl_hash(owner,py)}
        else:
            if authority not in entries: raise RuntimeError(f'no implementation binding for {authority} at {owner}')
            entry=dict(entries[authority]); entry['status']='READY'; entry['qualification_evidence']=refresh_evidence(owner,entry.get('qualification_evidence'))
            if authority=='settlement':
                entry['python_file']='canonical_economics.py'; entry['exports']=['SettlementEngine']; entry['qualification_evidence']=q('16_Test_Qualification/evidence/ENTITY_ECONOMIC_QUALIFICATION_CURRENT.json')
            if entry.get('python_file'):
                entry['implementation_sha256']=impl_hash(owner,entry['python_file'])
        entries[authority]=entry
    multi=len(entries)>1 or len(authorities)>1
    base={'schema':'entity-runtime-binding-v1','abi_version':'1','implementation_version':'2.2.0-canonical','requirements_sha256':rh,'status':'READY'}
    if multi:
        base['authorities']=entries
    else:
        authority=authorities[0]; base['authority']=authority; base.update(entries[authority])
    marker.parent.mkdir(parents=True,exist_ok=True); marker.write_text(json.dumps(base,indent=2,sort_keys=True)+'\n',encoding='utf-8'); written.append(str(marker))
print('WRITTEN',len(written))
