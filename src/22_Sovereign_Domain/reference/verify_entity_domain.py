from __future__ import annotations
import base64,hashlib,json,sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def unb64(v): return base64.urlsafe_b64decode(str(v)+'='*(-len(str(v))%4))
def method(manifest,key_id):
    return next((x for x in manifest.get('verification_methods') or [] if x.get('key_id')==key_id),None)

def verify_manifest(manifest):
    try:
        if manifest.get('schema')!='sovereign-entity-manifest-v2': return False
        data=dict(manifest); sig=dict(data.pop('signature')); m=method(data,sig.get('key_id'))
        if not m or m.get('status')!='active': return False
        Ed25519PublicKey.from_public_bytes(unb64(m['public_key'])).verify(unb64(sig['signature']),canon(data)); return True
    except Exception: return False

def verify_sig(manifest,payload,record):
    try:
        if record.get('signature_schema')!='entity-signature-record-v2' or record.get('entity_id')!=manifest.get('entity_id'): return False
        if record.get('payload_sha256')!=sha(payload): return False
        m=method(manifest,record.get('key_id'))
        if not m or m.get('suite')!=record.get('suite'): return False
        signed={k:record.get(k) for k in ('signature_schema','entity_id','key_id','suite','signed_at_ms','payload_sha256')}
        Ed25519PublicKey.from_public_bytes(unb64(m['public_key'])).verify(unb64(record['signature']),canon(signed)); return True
    except Exception: return False
def verify_package(package):
    failures=[]; pkg=dict(package or {})
    if pkg.get('schema')!='entity-domain-export-package-v1': failures.append('package_schema')
    expected=pkg.get('package_sha256'); material={k:v for k,v in pkg.items() if k!='package_sha256'}
    if expected!=sha(material): failures.append('package_hash')
    identity=dict(pkg.get('identity_manifest') or {}); snap=dict(pkg.get('domain_snapshot') or {}); export=dict(pkg.get('export_manifest') or {})
    export_sig=export.pop('signature',None); domain=dict(snap.get('domain') or {}); root=domain.get('entity_root'); did=domain.get('domain_id')
    if not verify_manifest(identity): failures.append('identity_manifest')
    if root!=identity.get('entity_id') or export.get('entity_root')!=root or export.get('domain_id')!=did: failures.append('root_domain_binding')
    if export.get('domain_snapshot_sha256')!=sha(snap) or export.get('identity_manifest_sha256')!=sha(identity): failures.append('export_commitment')
    if identity and export_sig and not verify_sig(identity,export,export_sig): failures.append('export_signature')
    claim=snap.get('name_claim')
    if claim:
        body={k:claim[k] for k in ('schema','claim_id','domain_id','entity_root','normalized_name','namespace','status','conflict_state','evidence','created_at_ms','first_seen_is_not_ownership','dns_possession_is_not_authority')}
        if claim.get('domain_id')!=did or claim.get('entity_root')!=root or not verify_sig(identity,body,claim.get('signature') or {}): failures.append('name_claim')
    nodes={}
    for node in snap.get('nodes') or []:
        nid=node.get('node_id'); body={k:node[k] for k in ('schema','domain_id','entity_root','node_id','public_key_b64','permitted_services','network_scopes','publication_scopes','data_scopes','not_before_ms','expires_at_ms','delegation','status','auth_version','created_at_ms')}
        if node.get('domain_id')!=did or node.get('entity_root')!=root or not verify_sig(identity,body,node.get('signature') or {}): failures.append('node:'+str(nid))
        rev=node.get('revocation')
        if rev:
            rb={k:rev[k] for k in ('schema','revocation_id','domain_id','node_id','entity_root','reason','effective_at_ms','created_at_ms')}
            if rev.get('domain_id')!=did or rev.get('node_id')!=nid or not verify_sig(identity,rb,rev.get('signature') or {}): failures.append('revocation:'+str(nid))
        nodes[nid]=node
    for svc in snap.get('services') or []:
        sid=svc.get('service_id'); body={k:svc[k] for k in ('schema','entity_root','domain_id','domain_name','service_id','service_type','node_id','endpoint','protocol_version','capabilities','access_class','required_credentials','policy_refs','data_classifications','economic_terms_ref','availability','manifest_version','expires_at_ms','status','created_at_ms','source_data_custody_transferred','provider_authority_inferred')}
        if svc.get('domain_id')!=did or svc.get('entity_root')!=root or svc.get('node_id') not in nodes or not verify_sig(identity,body,svc.get('signature') or {}): failures.append('service:'+str(sid))
        node=nodes.get(svc.get('node_id')) or {}
        if svc.get('status')=='ACTIVE' and node.get('effective_status',node.get('status'))!='ACTIVE': failures.append('active_service_on_revoked_node:'+str(sid))
        if svc.get('service_type') not in set(node.get('permitted_services') or []) and '*' not in set(node.get('permitted_services') or []): failures.append('service_scope:'+str(sid))
    for mig in snap.get('migrations') or []:
        mb={k:mig[k] for k in ('schema','migration_id','domain_id','entity_root','from_node','to_node','from_provider','to_provider','semantic_hash_before','semantic_hash_after','created_at_ms','provider_replacement_is_not_entity_replacement')}
        if mig.get('domain_id')!=did or mig.get('entity_root')!=root or mig.get('semantic_hash_before')!=mig.get('semantic_hash_after') or not verify_sig(identity,mb,mig.get('signature') or {}): failures.append('migration:'+str(mig.get('migration_id')))
    if snap.get('dns_authority_required') is not False or snap.get('btg_authority_required') is not False or snap.get('cloud_host_required') is not False: failures.append('mandatory_provider_dependency')
    result={'valid':not failures,'failures':sorted(failures),'entity_root':root,'domain_id':did,'package_sha256':expected,
            'dns_required':False,'btg_required':False,'proprietary_database_required':False,'independent_interpretation':True}
    result['result_sha256']=sha(result); return result

def main(argv=None):
    args=list(argv or sys.argv[1:])
    if len(args)!=1: print(json.dumps({'valid':False,'failures':['usage']})); return 2
    pkg=json.loads(Path(args[0]).read_text(encoding='utf-8')); result=verify_package(pkg); print(json.dumps(result,sort_keys=True))
    return 0 if result['valid'] else 2

if __name__=='__main__': raise SystemExit(main())
