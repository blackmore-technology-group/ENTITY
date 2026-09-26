from __future__ import annotations
import hashlib,time

def _now(): return int(time.time()*1000)
class OpaqueRelayCarrier:
    """Opaque authenticated-session carrier; relay cannot inspect payload or grant authority."""
    def __init__(self,max_messages_per_peer:int=128): self.max=int(max_messages_per_peer); self.queue={}; self.seen=set(); self.outage=False
    def forward(self,source_peer:str,destination_peer:str,packet:dict)->dict:
        if self.outage: raise ConnectionError('relay unavailable')
        if not packet.get('ciphertext_b64') or not packet.get('nonce_b64'): raise ValueError('relay accepts encrypted packets only')
        token=hashlib.sha256((str(source_peer)+'|'+str(destination_peer)+'|'+str(packet.get('epoch'))+'|'+str(packet.get('sequence'))+'|'+str(packet.get('ciphertext_b64'))).encode()).hexdigest()
        if token in self.seen: raise ValueError('duplicate/replayed relay packet')
        q=self.queue.setdefault(str(destination_peer),[])
        if len(q)>=self.max: raise PermissionError('relay rate/abuse limit exceeded')
        self.seen.add(token); q.append({'source_peer':str(source_peer),'packet':dict(packet),'received_at_ms':_now()})
        return {'accepted':True,'relay_token':token,'payload_decrypted':False,'authority_granted':False}
    def receive(self,destination_peer:str)->list[dict]: return self.queue.pop(str(destination_peer),[])
    def set_outage(self,value:bool): self.outage=bool(value)
    def status(self): return {'ready':True,'opaque_payloads':True,'rate_limited':True,'relay_is_authority':False,'outage_scoped_to_connectivity':True}
