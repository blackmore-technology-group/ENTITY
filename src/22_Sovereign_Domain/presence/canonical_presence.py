from __future__ import annotations
import base64, hashlib, json, time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _canon(v):
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()

def _sha(v):
    return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()

def _unb64(v):
    return base64.urlsafe_b64decode(str(v)+'='*(-len(str(v))%4))

def _now():
    return int(time.time()*1000)

SCOPES={'PUBLIC','RELATIONSHIP','PRIVATE','LOCAL'}

class PresenceAdvertisementManager:
    """Node-signed scoped presence hints. Presence is discovery metadata, never authority."""
    def __init__(self):
        self.highest_sequence={}
    def create(self,runtime,node_authorization:dict,service_ids:list[str],*,scope='PUBLIC',endpoint_hints=None,
               sequence:int=1,ttl_ms:int=60000)->dict:
        scope=str(scope).upper()
        if scope not in SCOPES: raise ValueError('invalid presence scope')
        if node_authorization.get('node_id')!=runtime.node_id: raise PermissionError('node authorization mismatch')
        if node_authorization.get('public_key_b64')!=runtime.public_key_b64: raise PermissionError('node key mismatch')
        now=_now(); body={
            'schema':'entity-presence-advertisement-v1','domain_id':node_authorization['domain_id'],
            'entity_root':node_authorization['entity_root'],'node_id':runtime.node_id,
            'service_ids':sorted({str(x) for x in service_ids}),'scope':scope,
            'endpoint_hints':list(endpoint_hints or []),'sequence':int(sequence),
            'advertised_at_ms':now,'expires_at_ms':now+int(ttl_ms),
            'resolver_authority_claimed':False,'relay_authority_claimed':False}
        return {**body,'node_signature':runtime.keys.sign(body)}

    def verify(self,advertisement:dict,node_authorization:dict,*,now_ms:int|None=None)->dict:
        failures=[]; ad=dict(advertisement or {}); now=int(now_ms or _now())
        if ad.get('schema')!='entity-presence-advertisement-v1': failures.append('schema')
        for key in ('domain_id','entity_root','node_id'):
            if ad.get(key)!=node_authorization.get(key): failures.append(key+'_binding')
        if node_authorization.get('effective_status',node_authorization.get('status'))!='ACTIVE': failures.append('node_revoked')
        if int(ad.get('expires_at_ms') or 0)<=now: failures.append('expired')
        seq=int(ad.get('sequence') or 0); key=(str(ad.get('domain_id')),str(ad.get('node_id')))
        if seq<self.highest_sequence.get(key,0): failures.append('rollback')
        required=('schema','domain_id','entity_root','node_id','service_ids','scope','endpoint_hints',
                  'sequence','advertised_at_ms','expires_at_ms','resolver_authority_claimed','relay_authority_claimed')
        if any(k not in ad for k in required): failures.append('required_fields')
        body={k:ad.get(k) for k in required}
        sig=dict(ad.get('node_signature') or {})
        if sig.get('payload_sha256')!=_sha(body): failures.append('payload_hash')
        else:
            try:
                Ed25519PublicKey.from_public_bytes(_unb64(node_authorization['public_key_b64'])).verify(
                    _unb64(sig['signature_b64']),_canon(body))
            except Exception: failures.append('signature')
        if not failures: self.highest_sequence[key]=max(self.highest_sequence.get(key,0),seq)
        return {'valid':not failures,'failures':failures,'presence_is_authority':False,
                'dns_required':False,'scope':ad.get('scope'),'sequence':seq}

    def status(self):
        return {'ready':True,'schema':'entity-presence-advertisement-v1','scopes':sorted(SCOPES),
                'presence_is_authority':False,'anti_rollback':True,'dns_required':False}
