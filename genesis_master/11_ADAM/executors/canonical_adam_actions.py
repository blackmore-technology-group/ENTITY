from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,sqlite3,time

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()

class AdamActionExecutor:
    """Side effects only after current ENTITY capability/policy authorization; replay safe and auditable."""
    def __init__(self,state_dir,capability_gate,policy_engine=None):
        self.root=Path(state_dir)/'adam_actions'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'actions.sqlite'
        self.gate=capability_gate; self.policy=policy_engine; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db: db.execute('CREATE TABLE IF NOT EXISTS actions(request_id TEXT PRIMARY KEY,agent_id TEXT NOT NULL,operation TEXT NOT NULL,object_ref TEXT,outcome TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,created_at_ms INTEGER NOT NULL)')
    def execute(self,proposal:dict,*,request_id:str,capability_id:str,agent_id:str,handler,policy_id:str|None=None)->dict:
        p=dict(proposal or {}); origin=str(p.get('instruction_origin') or 'UNTRUSTED_CONTENT').upper()
        if origin!='AUTHORIZED_REQUEST': raise PermissionError('untrusted content cannot become ADAM instruction')
        with self._connect() as db:
            if db.execute('SELECT 1 FROM actions WHERE request_id=?',(str(request_id),)).fetchone(): raise ValueError('duplicate/replayed ADAM request')
        decision=self.gate.authorize_proposal(p,capability_id=capability_id,agent_id=agent_id)
        if not decision.get('allowed'): raise PermissionError('ADAM capability authorization denied: '+str(decision.get('reason')))
        if policy_id and self.policy is not None:
            pd=self.policy.evaluate(policy_id,str(p.get('policy_action') or p.get('operation') or ''))
            if not pd.get('allowed'): raise PermissionError('ENTITY policy denied ADAM execution')
        result=handler(dict(p)); evidence={'request_id':str(request_id),'agent_id':str(agent_id),'capability_id':str(capability_id),'operation':str(p.get('operation') or '').upper(),'object_ref':p.get('object_ref'),'policy_id':policy_id,'authorized':True,'outcome':'SUCCESS','result_commitment':hashlib.sha256(_canon(result)).hexdigest(),'created_at_ms':_now()}
        digest=hashlib.sha256(_canon(evidence)).hexdigest()
        with self._connect() as db: db.execute('INSERT INTO actions VALUES(?,?,?,?,?,?,?)',(str(request_id),str(agent_id),evidence['operation'],p.get('object_ref'),'SUCCESS',digest,evidence['created_at_ms']))
        return {**evidence,'evidence_sha256':digest,'result':result,'historical_evidence_rewritten':False}
    def status(self):
        with self._connect() as db: count=int(db.execute('SELECT COUNT(*) FROM actions').fetchone()[0])
        return {'ready':True,'actions':count,'untrusted_content_is_instruction':False,'replay_protected':True,'unrestricted_side_effect_path':False}

def niki_accept_action_proposal_v1(*,executor:AdamActionExecutor,proposal:dict,request_id:str,capability_id:str,agent_id:str,handler,policy_id:str|None=None)->dict:
    return executor.execute(proposal,request_id=request_id,capability_id=capability_id,agent_id=agent_id,handler=handler,policy_id=policy_id)
