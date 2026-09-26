from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,sqlite3,time

def _now(): return int(time.time()*1000)
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
class BecpObservableEvidence:
    """Externally observable BECP commitments only; hidden provider activity remains UNKNOWN."""
    def __init__(self,state_dir:str|Path,identity=None):
        self.root=Path(state_dir)/'becp_evidence'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'becp.sqlite'; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db: db.execute('CREATE TABLE IF NOT EXISTS evidence(event_nonce TEXT PRIMARY KEY,controller_entity_id TEXT,destination TEXT NOT NULL,purpose TEXT NOT NULL,request_sha256 TEXT NOT NULL,response_sha256 TEXT,provider_metadata_json TEXT NOT NULL,transport_outcome TEXT NOT NULL,evidence_origin TEXT NOT NULL,assurance TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT)')
    def record(self,*,event_nonce:str,destination:str,purpose:str,request_visible:bytes|dict,response_visible:bytes|dict|None,provider_metadata:dict|None,transport_outcome:str,controller_entity_id:str|None=None)->dict:
        req=_sha(request_visible); resp=_sha(response_visible) if response_visible is not None else None; now=_now()
        body={'schema':'entity-becp-observable-evidence-v1','event_nonce':str(event_nonce),'controller_entity_id':controller_entity_id,'destination':str(destination),'purpose':str(purpose),'request_sha256':req,'response_sha256':resp,'provider_metadata':dict(provider_metadata or {}),'transport_outcome':str(transport_outcome),'evidence_origin':'DIRECT_OBSERVATION','assurance':'EXTERNALLY_OBSERVABLE_BOUNDARY','hidden_provider_activity':'UNKNOWN','created_at_ms':now}
        sig=self.identity.sign(controller_entity_id,body) if self.identity is not None and controller_entity_id else None
        try:
            with self._connect() as db: db.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(str(event_nonce),controller_entity_id,body['destination'],body['purpose'],req,resp,json.dumps(body['provider_metadata'],sort_keys=True),body['transport_outcome'],body['evidence_origin'],body['assurance'],now,json.dumps(sig,sort_keys=True) if sig else None))
        except sqlite3.IntegrityError:
            with self._connect() as db: row=db.execute('SELECT request_sha256,response_sha256 FROM evidence WHERE event_nonce=?',(str(event_nonce),)).fetchone()
            if row and row['request_sha256']==req and row['response_sha256']==resp: return {**body,'signature':sig,'deduplicated':True}
            raise ValueError('duplicate BECP nonce with conflicting evidence')
        return {**body,'signature':sig,'deduplicated':False}
    def status(self): return {'ready':True,'hidden_provider_activity_claimed':False,'idempotent':True,'visible_commitments_only':True}

def niki_ingest_becp_evidence_v1(*,store:BecpObservableEvidence,**kwargs): return store.record(**kwargs)
