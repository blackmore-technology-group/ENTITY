from __future__ import annotations
import base64,json,os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class PeerTransportSession:
    """Authenticated-session AEAD carrier; transport success grants no ENTITY rights."""
    def __init__(self,local_peer:str,remote_peer:str,session_key:bytes,*,protocol_version:int,authenticated:bool,epoch:int=1):
        if not authenticated: raise PermissionError('authenticated peer session required')
        if len(session_key)!=32: raise ValueError('AES-256 session key required')
        self.local=str(local_peer); self.remote=str(remote_peer); self.key=bytes(session_key); self.protocol=int(protocol_version); self.epoch=int(epoch); self._sent=0; self._seen=set(); self.active=True
    def _aad(self,sender:str,receiver:str,seq:int)->bytes:
        return json.dumps({'schema':'entity-peer-transport-v1','sender':sender,'receiver':receiver,'protocol_version':self.protocol,'epoch':self.epoch,'sequence':int(seq)},sort_keys=True,separators=(',',':')).encode()
    def send(self,payload:bytes)->dict:
        if not self.active: raise ConnectionError('peer session interrupted')
        self._sent+=1; seq=self._sent; nonce=os.urandom(12); aad=self._aad(self.local,self.remote,seq); cipher=AESGCM(self.key).encrypt(nonce,bytes(payload),aad)
        return {'schema':'entity-peer-packet-v1','sender':self.local,'receiver':self.remote,'protocol_version':self.protocol,'epoch':self.epoch,'sequence':seq,'nonce_b64':base64.b64encode(nonce).decode(),'ciphertext_b64':base64.b64encode(cipher).decode(),'transport_authority_only':True}
    def receive(self,packet:dict)->bytes:
        if not self.active: raise ConnectionError('peer session interrupted')
        p=dict(packet); seq=int(p.get('sequence',0)); token=(int(p.get('epoch',0)),seq)
        if p.get('sender')!=self.remote or p.get('receiver')!=self.local: raise PermissionError('peer mismatch')
        if int(p.get('protocol_version',0))!=self.protocol or int(p.get('epoch',0))!=self.epoch: raise PermissionError('incompatible transport version/epoch')
        if token in self._seen: raise ValueError('duplicate/replayed peer packet')
        aad=self._aad(self.remote,self.local,seq); plain=AESGCM(self.key).decrypt(base64.b64decode(p['nonce_b64']),base64.b64decode(p['ciphertext_b64']),aad); self._seen.add(token); return plain
    def interrupt(self): self.active=False
    def rejoin(self,new_epoch:int): self.epoch=max(self.epoch+1,int(new_epoch)); self.active=True; self._seen.clear(); self._sent=0
    def status(self): return {'ready':True,'authenticated':True,'encrypted':True,'replay_protected':True,'rights_implied':False,'protocol_version':self.protocol,'epoch':self.epoch}
