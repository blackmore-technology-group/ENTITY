from __future__ import annotations
import secrets,time

def _now(): return int(time.time()*1000)
class NatTraversalCoordinator:
    """Connectivity-path selection only; it never creates peer trust or ENTITY authority."""
    def __init__(self): self.sessions={}
    def negotiate(self,local_peer:str,remote_peer:str,*,authenticated:bool,direct_candidates:list[str],relay_candidates:list[str])->dict:
        if not authenticated: raise PermissionError('peer authentication required before traversal')
        direct=[str(x) for x in direct_candidates if str(x)]; relay=[str(x) for x in relay_candidates if str(x)]
        path=('DIRECT',direct[0]) if direct else ('RELAY',relay[0]) if relay else (None,None)
        if path[0] is None: return {'connected':False,'reason':'no_connectivity_path','security_policy_weakened':False}
        sid='nat1-'+secrets.token_hex(16); self.sessions[sid]={'local':str(local_peer),'remote':str(remote_peer),'mode':path[0],'endpoint':path[1],'status':'ACTIVE','created_at_ms':_now()}
        return {'session_id':sid,'connected':True,'mode':path[0],'endpoint':path[1],'peer_authenticated':True,'relay_or_nat_is_authority':False}
    def revoke(self,session_id:str)->dict:
        row=self.sessions.get(str(session_id))
        if not row: raise KeyError('traversal session not found')
        row['status']='REVOKED'; return {'session_id':str(session_id),'status':'REVOKED'}
    def validate(self,session_id:str,local_peer:str,remote_peer:str)->dict:
        row=self.sessions.get(str(session_id))
        if not row or row['status']!='ACTIVE': return {'allowed':False,'reason':'session_not_active'}
        if row['local']!=str(local_peer) or row['remote']!=str(remote_peer): return {'allowed':False,'reason':'peer_mismatch'}
        return {'allowed':True,'mode':row['mode'],'authority_granted':False}
    def status(self): return {'ready':True,'direct_and_relay_paths':True,'traversal_is_authority':False,'failure_weakens_security':False}
