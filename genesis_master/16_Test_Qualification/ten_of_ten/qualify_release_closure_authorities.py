from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
TEST=ROOT/'16_Test_Qualification/integration/test_release_closure_authorities.py'
EVIDENCE=ROOT/'16_Test_Qualification/evidence/ENTITY_RELEASE_CLOSURE_AUTHORITIES_CURRENT.json'
FILES=[
 ROOT/'01_Core_Runtime/api/canonical_service.py', ROOT/'01_Core_Runtime/identity/canonical_identity.py', ROOT/'01_Core_Runtime/service_runtime/canonical_data_economy.py',
 ROOT/'04_Entity_Registry/canonical_knowledge_capital.py', ROOT/'04_Entity_Registry/data_universe_adapter/canonical_data_universe.py', ROOT/'04_Entity_Registry/relationships/canonical_relationship_identity.py',
 ROOT/'11_ADAM/approval_gates/canonical_adam_capabilities.py', ROOT/'11_ADAM/executors/canonical_adam_actions.py', ROOT/'12_BSIE/digital_entity_world/canonical_entity_world.py',
 ROOT/'13_Security/key_management/canonical_hardware_keys.py', ROOT/'13_Security/key_management/canonical_key_management.py', ROOT/'13_Security/key_management/tpm_cng.ps1',
]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
FILES += [
 ROOT/'02_Peer_Network/canonical_peer_network.py',
 ROOT/'02_Peer_Network/discovery/canonical_peer_discovery.py',
 ROOT/'02_Peer_Network/transport/canonical_peer_transport.py',
 ROOT/'02_Peer_Network/nat_traversal/canonical_nat_traversal.py',
 ROOT/'02_Peer_Network/relay_fallback/canonical_relay.py',
 ROOT/'02_Peer_Network/BECP_Control_Plane/canonical_becp_evidence.py',
 ROOT/'03_Public_Internet_Bridge/public_gateway/canonical_public_gateway.py',
 ROOT/'03_Public_Internet_Bridge/web_publish/canonical_web_publish.py',
 ROOT/'09_Spatial_AR_Dashboard/canonical_ar_projection.py',
 ROOT/'14_Protocols_SDK/c2pa/canonical_c2pa.py',
 ROOT/'16_Test_Qualification/evidence/canonical_prebootstrap_evidence.py',
 ROOT/'16_Test_Qualification/integration/test_release_closure_authorities.py']
AUTHORITIES=['identity','policy_consent','core_permissions','service_api','data_pools','data_spaces','data_universe','knowledge_capital','relationship_identity','adam_capabilities','adam_actions','bsie_entity_world','federation','transparency_witness','peer_discovery','peer_transport','nat_traversal','relay','becp_evidence','public_gateway','web_publish','ar_projection','purpose_keys','recovery_custody','guardian_recovery','c2pa','prebootstrap_evidence']

def tpm_status():
    p=ROOT/'13_Security/key_management/canonical_hardware_keys.py'
    s=importlib.util.spec_from_file_location('closure_hw_qual',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.commissioning_status()
def main():
    run=subprocess.run([sys.executable,'-m','pytest',str(TEST),'-q'],cwd=str(ROOT),capture_output=True,text=True)
    tpm=tpm_status(); ok=run.returncode==0 and bool(tpm.get('commissioned'))
    payload={'schema':'entity-release-closure-authorities-qualification-v1','generated_at_ms':int(time.time()*1000),'status':'PASS' if ok else 'FAIL','scope':'V2_2_CANONICAL_AUTHORITY_AND_HARDWARE_CLOSURE','pytest_exit_code':run.returncode,'pytest_output':(run.stdout+'\n'+run.stderr).strip(),'authorities':AUTHORITIES,'tpm_commissioning':tpm,'implementation_sha256':{str(p.relative_to(ROOT)):sha(p) for p in FILES},'requirements_sha256':{d.name:sha(d/'ENTITY_REQUIREMENTS.md') for d in ROOT.iterdir() if d.is_dir() and (d/'ENTITY_REQUIREMENTS.md').is_file() and d.name!='10_NIKI'},'limitations':[] if ok else ['closure qualification did not pass']}
    payload['evidence_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    EVIDENCE.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'evidence':str(EVIDENCE),'evidence_sha256':payload['evidence_sha256'],'tpm_commissioned':tpm.get('commissioned'),'pytest':run.returncode},indent=2)); return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
