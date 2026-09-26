from __future__ import annotations
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
def _load():
    p=ROOT/'01_Core_Runtime'/'permissions'/'canonical_permissions.py'; s=importlib.util.spec_from_file_location('adam_core_perm',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class AdamCapabilityGate:
    """ADAM authorization facade; proposal metadata never grants authority by itself."""
    def __init__(self,state_dir,identity):
        mod=_load(); self.store=mod.AuthorityCapabilityStore(state_dir,identity); self.threshold=mod.ThresholdAuthorityStore(state_dir,identity)
    def grant(self,*args,**kwargs): return self.store.grant(*args,**kwargs)
    def revoke(self,*args,**kwargs): return self.store.revoke(*args,**kwargs)
    def approve(self,*args,**kwargs): return self.store.approve(*args,**kwargs)
    def authorize_proposal(self,proposal:dict,*,capability_id:str,agent_id:str)->dict:
        p=dict(proposal or {}); op=str(p.get('operation') or '').upper()
        decision=self.store.authorize(capability_id,agent_id,op,asset_id=p.get('asset_id'),counterparty_id=p.get('counterparty_id'),amount=p.get('amount'),object_ref=p.get('object_ref'))
        return {**decision,'proposal_state':'AUTHORIZED_FOR_EXECUTION' if decision.get('allowed') else 'PROPOSED_NOT_EXECUTED','proposal_claimed_authorization_ignored':bool(p.get('authorized'))}
    def status(self): return {'ready':True,'proposal_is_not_authority':True,'capability_store':self.store.status()}
