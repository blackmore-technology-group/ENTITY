from __future__ import annotations
import hashlib

class OpaqueDomainRelay:
    """Optional transport carrier. It can forward opaque bytes but owns no Entity authority."""
    def __init__(self,relay_id='relay-local'):
        self.relay_id=str(relay_id); self.frames=0; self.bytes=0
    def forward(self,frame:bytes)->bytes:
        raw=bytes(frame); self.frames+=1; self.bytes+=len(raw); return raw
    def transport_receipt(self,frame:bytes)->dict:
        return {'schema':'entity-domain-relay-receipt-v1','relay_id':self.relay_id,
                'frame_sha256':hashlib.sha256(bytes(frame)).hexdigest(),'bytes':len(frame),
                'relay_is_authority':False,'relay_is_licensor':False,'relay_is_owner':False}
    def authority_claim(self,*_args,**_kwargs)->dict:
        return {'accepted':False,'reason':'relay_transport_possession_is_not_sovereign_authority',
                'relay_is_authority':False}
    def status(self):
        return {'ready':True,'frames':self.frames,'bytes':self.bytes,'payload_interpretation_required':False,
                'relay_is_authority':False,'mandatory_relay':False}
