from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\sovereign_domain\qualify_sovereign_domain.py")
s=p.read_text(encoding='utf-8')
repls={
"vector(valid,'name_binding',True,claim)":"vector(valid,'name_binding',True,claim,trust_material=manifest)",
"vector(valid,'node_authorization',True,node)":"vector(valid,'node_authorization',True,node,trust_material=manifest)",
"vector(valid,'node_revocation',True,revocation)":"vector(valid,'node_revocation',True,revocation,trust_material=manifest)",
"vector(valid,'service_manifest',True,service_v2)":"vector(valid,'service_manifest',True,service_v2,trust_material=manifest)",
"vector(valid,'resolution_proof',True,resolution)":"vector(valid,'resolution_proof',True,resolution,trust_material=manifest)",
"vector(valid,'stale_state_history',True,{'service_manifest':service_v1,'current_authority':False})":"vector(valid,'stale_state_history',True,{'service_manifest':service_v1,'current_authority':False},trust_material=manifest)",
"second=ids.create('Conflict Vector','organization')['entity_id']; second_domain=domain.create_domain(second,requested_name='owner.entity')":"second=ids.create('Conflict Vector','organization')['entity_id']; second_manifest=ids.load_manifest(second); second_domain=domain.create_domain(second,requested_name='owner.entity')",
"vector(valid,'name_conflict',True,second_domain['name_claim'])":"vector(valid,'name_conflict',True,second_domain['name_claim'],trust_material=second_manifest)",
}
for a,b in repls.items():
    if a not in s: raise RuntimeError('marker missing: '+a[:50])
    s=s.replace(a,b,1)
p.write_text(s,encoding='utf-8'); print('valid calls patched')
s=p.read_text(encoding='utf-8')
repls={
"vector(invalid,'name_binding',False,bad,'name_claim_signature')":"vector(invalid,'name_binding',False,bad,'name_claim_signature',trust_material=manifest)",
"vector(invalid,'name_conflict',False,bad,'name_claim_signature')":"vector(invalid,'name_conflict',False,bad,'name_claim_signature',trust_material=second_manifest)",
"vector(invalid,'node_authorization',False,bad,'node_authorization_signature')":"vector(invalid,'node_authorization',False,bad,'node_authorization_signature',trust_material=manifest)",
"vector(invalid,'node_revocation',False,bad,'node_revocation_signature')":"vector(invalid,'node_revocation',False,bad,'node_revocation_signature',trust_material=manifest)",
"vector(invalid,'service_manifest',False,bad,'service_manifest_signature')":"vector(invalid,'service_manifest',False,bad,'service_manifest_signature',trust_material=manifest)",
"vector(invalid,'resolution_proof',False,bad,'resolution_binding')":"vector(invalid,'resolution_proof',False,bad,'resolution_binding',trust_material=manifest)",
"vector(invalid,'stale_state',False,{'service_manifest':service_v1,'known_current_version':2},'anti_rollback')":"vector(invalid,'stale_state',False,{'service_manifest':service_v1,'known_current_version':2},'anti_rollback',trust_material=manifest)",
}
for a,b in repls.items():
    if a not in s: raise RuntimeError('marker missing: '+a[:50])
    s=s.replace(a,b,1)
p.write_text(s,encoding='utf-8'); print('invalid calls patched')
