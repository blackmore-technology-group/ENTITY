from __future__ import annotations
import hashlib,secrets,time

def _now(): return int(time.time()*1000)
class PublicGatewayAuthority:
    """Scoped public exposure authorization; local readiness never implies public exposure."""
    def __init__(self,max_requests_per_token:int=64): self.tokens={}; self.counts={}; self.max=int(max_requests_per_token)
    def issue_token(self,controller_entity_id:str,subject_ref:str,scopes:list[str],*,ttl_ms:int=300000)->dict:
        token=secrets.token_urlsafe(32); digest=hashlib.sha256(token.encode()).hexdigest(); now=_now()
        self.tokens[digest]={'controller':str(controller_entity_id),'subject':str(subject_ref),'scopes':sorted({str(x).upper() for x in scopes}),'expires':now+max(1000,int(ttl_ms)),'status':'ACTIVE'}
        return {'token':token,'token_sha256':digest,'expires_at_ms':self.tokens[digest]['expires'],'scopes':self.tokens[digest]['scopes']}
    def revoke(self,token:str):
        digest=hashlib.sha256(str(token).encode()).hexdigest()
        if digest in self.tokens: self.tokens[digest]['status']='REVOKED'
    def authorize(self,token:str,scope:str,*,secure_transport:bool)->dict:
        if not secure_transport: return {'allowed':False,'reason':'secure_transport_required'}
        digest=hashlib.sha256(str(token).encode()).hexdigest(); row=self.tokens.get(digest)
        if not row or row['status']!='ACTIVE': return {'allowed':False,'reason':'token_not_active'}
        if row['expires']<=_now(): return {'allowed':False,'reason':'token_expired'}
        if str(scope).upper() not in set(row['scopes']): return {'allowed':False,'reason':'scope_denied'}
        used=self.counts.get(digest,0)
        if used>=self.max: return {'allowed':False,'reason':'rate_limited'}
        self.counts[digest]=used+1
        return {'allowed':True,'subject_ref':row['subject'],'controller_entity_id':row['controller'],'root_identifier_publication_authorized':False}
    @staticmethod
    def minimum_disclosure(metadata:dict)->dict:
        blocked={'root_entity_id','private_key','vault_content','raw_private_content','recovery_secret'}
        return {k:v for k,v in dict(metadata or {}).items() if str(k).lower() not in blocked}
    def status(self): return {'ready':True,'secure_transport_required':True,'scoped_auth':True,'rate_limited':True,'default_public_exposure':False}
