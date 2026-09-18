from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,secrets,sqlite3,time

def _now(): return int(time.time()*1000)
def _id(): return 'kc1-'+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

class KnowledgeCapitalRegistry:
    """Signed knowledge/engineering receipts; contribution evidence is not automatic ownership or value."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/'knowledge_capital'; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'knowledge.sqlite'; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts(receipt_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,contributors_json TEXT NOT NULL,artifact_sha256 TEXT NOT NULL,evidence_origin TEXT NOT NULL,metadata_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)')
    def record(self,controller_entity_id:str,*,kind:str,title:str,contributors:list[dict],artifact_sha256:str,metadata:dict|None=None,evidence_origin:str='ENTITY_ASSERTION')->dict:
        digest=str(artifact_sha256).lower()
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): raise ValueError('artifact_sha256 required')
        rid=_id(); now=_now(); people=[dict(x) for x in contributors]
        body={'schema':'entity-knowledge-capital-receipt-v1','receipt_id':rid,'controller_entity_id':controller_entity_id,'kind':str(kind).upper(),'title':str(title)[:512],'contributors':people,'artifact_sha256':digest,'evidence_origin':str(evidence_origin).upper(),'metadata':dict(metadata or {}),'created_at_ms':now,'ownership_not_inferred':True,'economic_value_not_inferred':True}
        sig=self.identity.sign(controller_entity_id,body)
        with self._connect() as db: db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,controller_entity_id,body['kind'],body['title'],json.dumps(people,sort_keys=True),digest,body['evidence_origin'],json.dumps(body['metadata'],sort_keys=True),json.dumps(sig,sort_keys=True),now))
        return {**body,'signature':sig}
    def get(self,receipt_id:str)->dict:
        with self._connect() as db: row=db.execute('SELECT * FROM receipts WHERE receipt_id=?',(receipt_id,)).fetchone()
        if not row: raise KeyError('knowledge receipt not found')
        out=dict(row); out['contributors']=json.loads(out.pop('contributors_json')); out['metadata']=json.loads(out.pop('metadata_json')); out['signature']=json.loads(out.pop('signature_json')); out['schema']='entity-knowledge-capital-receipt-v1'; out['ownership_not_inferred']=True; out['economic_value_not_inferred']=True
        return out
    def verify(self,receipt_id:str)->bool:
        item=self.get(receipt_id); sig=item.pop('signature'); body={k:v for k,v in item.items() if k not in {'ownership_not_inferred','economic_value_not_inferred'}}
        body['ownership_not_inferred']=True; body['economic_value_not_inferred']=True
        manifest=self.identity.load_manifest(body['controller_entity_id']); return bool(self.identity.verify_signature(manifest,body,sig))
    def status(self)->dict:
        with self._connect() as db: count=int(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0])
        return {'ready':True,'receipts':count,'human_and_ai_contributors_supported':True,'ownership_not_inferred':True,'value_not_inferred':True}

def niki_ingest_reasoning_receipt_v1(*,registry:KnowledgeCapitalRegistry,controller_entity_id:str,title:str,artifact_sha256:str,contributors:list[dict],metadata:dict|None=None)->dict:
    return registry.record(controller_entity_id,kind='AI_REASONING_RECEIPT',title=title,contributors=contributors,artifact_sha256=artifact_sha256,metadata=metadata,evidence_origin='ENTITY_ASSERTION')
