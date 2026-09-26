"""Clean-room implementation of ENTITY Sovereign Domain Protocol v1.
No imports from ENTITY/BTG runtime code. Built only from published JSON/crypto protocol.
"""
import base64, hashlib, json, socket, struct, os, secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey,X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes,serialization

def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def unb64(v): return base64.urlsafe_b64decode(str(v)+'='*(-len(str(v))%4))
def b64(v): return base64.urlsafe_b64encode(v).decode().rstrip('=')
def signing_method(identity,key_id):
    for m in identity.get('verification_methods') or []:
        if m.get('key_id')==key_id: return m
    return None
def verify_identity(identity):
    try:
        if identity.get('schema')!='sovereign-entity-manifest-v2': return False
        body=dict(identity); sig=dict(body.pop('signature')); method=signing_method(body,sig.get('key_id'))
        if not method or method.get('status')!='active' or method.get('algorithm')!='Ed25519': return False
        Ed25519PublicKey.from_public_bytes(unb64(method['public_key'])).verify(unb64(sig['signature']),canon(body)); return True
    except Exception: return False
def verify_entity_record(material,identity):
    try:
        body=dict(material); sig=dict(body.pop('signature')); method=signing_method(identity,sig.get('key_id'))
        if not method or method.get('algorithm')!='Ed25519': return False
        if sig.get('entity_id')!=identity.get('entity_id') or sig.get('payload_sha256')!=sha(body): return False
        signed={k:v for k,v in sig.items() if k!='signature'}
        Ed25519PublicKey.from_public_bytes(unb64(method['public_key'])).verify(unb64(sig['signature']),canon(signed)); return True
    except Exception: return False
def validate(name,material,identity,current=None):
    root=identity.get('entity_id') if identity else None
    if name=='entity_root': return verify_identity(material),'identity_manifest_signature'
    if name in {'name_binding','name_conflict'}:
        ok=material.get('schema')=='entity-name-claim-v1' and material.get('entity_root')==root and verify_entity_record(material,identity)
        return ok,'name_claim_signature'
    if name=='node_authorization':
        signed={k:v for k,v in material.items() if k not in {'effective_status','revocation'}}
        ok=material.get('schema')=='entity-node-authorization-v1' and material.get('entity_root')==root and material.get('status')=='ACTIVE' and verify_entity_record(signed,identity)
        return ok,'node_authorization_signature'
    if name=='node_revocation':
        signed={k:v for k,v in material.items() if k not in {'entity_root_unchanged','historical_evidence_preserved','status'}}
        ok=material.get('schema')=='entity-node-revocation-v1' and material.get('entity_root')==root and verify_entity_record(signed,identity)
        return ok,'node_revocation_signature'
    if name=='service_manifest':
        ok=material.get('schema')=='entity-service-manifest-v1' and material.get('entity_root')==root and material.get('provider_authority_inferred') is False and verify_entity_record(material,identity)
        return ok,'service_manifest_signature'
    if name=='relay_authorization':
        ok=material.get('relay_is_authority') is False and material.get('relay_is_owner',False) is False and material.get('relay_is_licensor',False) is False
        return ok,'relay_non_authority'
    if name in {'rollback','rollback_detection'}:
        known=int(material.get('known_domain_version',material.get('known_version',0))); shown=int(material.get('presented_domain_version',material.get('presented_version',0)))
        ok=(shown<known and material.get('expected')=='REJECT_CURRENT') if name=='rollback_detection' else shown>=known
        return ok,'anti_rollback'
    if name in {'stale_state','stale_state_history'}:
        svc=material.get('service_manifest') or {}; known=material.get('known_current_version')
        if name=='stale_state_history': return material.get('current_authority') is False,'anti_rollback'
        return int(svc.get('manifest_version',0))>=int(known or 0),'anti_rollback'
    if name=='domain_restore':
        ok=material.get('same_identity_required') is True and material.get('entity_root')==root
        return ok,'root_domain_binding'
    if name=='resolution_proof':
        ok=material.get('schema')=='entity-resolution-proof-v1' and material.get('entity_root')==root and material.get('resolver_is_authority') is False and material.get('dns_used_as_authority') is False
        for pair in material.get('services') or []:
            node=pair.get('node') or {}; service=pair.get('service') or {}
            ok=ok and node.get('entity_root')==root and service.get('entity_root')==root and node.get('domain_id')==material.get('domain_id')==service.get('domain_id') and node.get('node_id')==service.get('node_id') and node.get('effective_status',node.get('status'))=='ACTIVE'
            ok=ok and validate('node_authorization',node,identity)[0] and validate('service_manifest',service,identity)[0]
        return bool(ok),'resolution_binding'
    if name=='domain_export': return verify_export(material),'package_hash'
    return False,'unsupported_vector'
def verify_export(pkg):
    try:
        if pkg.get('schema')!='entity-domain-export-package-v1': return False
        identity=pkg['identity_manifest']; snap=pkg['domain_snapshot']; manifest=pkg['export_manifest']
        if not verify_identity(identity): return False
        root=identity['entity_id']; domain=snap['domain']; domain_id=domain['domain_id']
        if domain.get('entity_root')!=root or manifest.get('entity_root')!=root or manifest.get('domain_id')!=domain_id: return False
        if snap.get('dns_authority_required') or snap.get('btg_authority_required') or snap.get('cloud_host_required'): return False
        if manifest.get('dns_required_for_interpretation') or manifest.get('proprietary_btg_database_required'): return False
        if manifest.get('identity_manifest_sha256')!=sha(identity) or manifest.get('domain_snapshot_sha256')!=sha(snap): return False
        if not verify_entity_record(manifest,identity): return False
        nc=snap.get('name_claim');
        if nc and not validate('name_binding',nc,identity)[0]: return False
        for node in snap.get('nodes') or []:
            base={k:v for k,v in node.items() if k!='effective_status'}
            if not validate('node_authorization',base,identity)[0]: return False
            rev=node.get('revocation')
            if rev and not validate('node_revocation',rev,identity)[0]: return False
        for svc in snap.get('services') or []:
            if not validate('service_manifest',svc,identity)[0]: return False
        body=dict(pkg); expected=body.pop('package_sha256',None)
        return expected==sha(body)
    except Exception: return False

def send_frame(sock,obj):
    raw=canon(obj); sock.sendall(struct.pack('!I',len(raw))+raw)
def recv_frame(sock,max_size=4*1024*1024):
    head=b''
    while len(head)<4:
        part=sock.recv(4-len(head));
        if not part: raise ConnectionError('closed')
        head+=part
    size=struct.unpack('!I',head)[0]
    if size<1 or size>max_size: raise ValueError('frame size')
    data=b''
    while len(data)<size:
        part=sock.recv(min(65536,size-len(data))); 
        if not part: raise ConnectionError('closed')
        data+=part
    return json.loads(data.decode())
def direct_request(resolution_proof,service_id,request,timeout=5.0):
    matches=[x for x in resolution_proof.get('services') or [] if (x.get('service') or {}).get('service_id')==service_id]
    if len(matches)!=1: raise KeyError('service')
    service=matches[0]['service']; node=matches[0]['node']; endpoint=service['endpoint']
    if node.get('effective_status',node.get('status'))!='ACTIVE': raise PermissionError('node inactive')
    client=X25519PrivateKey.generate(); client_pub=b64(client.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)); nonce=secrets.token_urlsafe(24)
    hello={'schema':'entity-direct-hello-v1','node_id':node['node_id'],'service_id':service_id,'client_x25519_b64':client_pub,'nonce':nonce}
    with socket.create_connection((endpoint['host'],int(endpoint['port'])),timeout=timeout) as sock:
        send_frame(sock,hello); server=recv_frame(sock)
        if server.get('schema')!='entity-direct-server-hello-v1': raise PermissionError('handshake')
        body={k:server[k] for k in ('schema','node_id','service_id','client_x25519_b64','server_x25519_b64','nonce','created_at_ms')}
        if body['node_id']!=node['node_id'] or body['service_id']!=service_id or body['client_x25519_b64']!=client_pub or body['nonce']!=nonce: raise PermissionError('binding')
        sig=server['node_signature'];
        if sig.get('payload_sha256')!=sha(body): raise PermissionError('hash')
        Ed25519PublicKey.from_public_bytes(unb64(node['public_key_b64'])).verify(unb64(sig['signature_b64']),canon(body))
        shared=client.exchange(X25519PublicKey.from_public_bytes(unb64(body['server_x25519_b64']))); aad=canon(body); key=HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),info=b'ENTITY-DIRECT-SESSION-v1').derive(shared)
        iv=os.urandom(12); send_frame(sock,{'schema':'entity-direct-data-v1','nonce_b64':b64(iv),'ciphertext_b64':b64(AESGCM(key).encrypt(iv,canon(request),aad))}); packet=recv_frame(sock)
        plain=AESGCM(key).decrypt(unb64(packet['nonce_b64']),unb64(packet['ciphertext_b64']),aad); out=json.loads(plain.decode()); out['independent_client']=True; return out
