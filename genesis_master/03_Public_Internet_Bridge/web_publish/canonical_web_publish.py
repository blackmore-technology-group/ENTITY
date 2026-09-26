from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,secrets,sqlite3,time

def _now(): return int(time.time()*1000)
def _id(): return 'export1-'+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()
class WebPublicationLedger:
    """Publication is a separate signed ExportEvent and never rewrites source rights/provenance."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/'web_publish'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'exports.sqlite'; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db: db.execute('CREATE TABLE IF NOT EXISTS exports(export_id TEXT PRIMARY KEY,exporting_entity_id TEXT NOT NULL,asset_id TEXT NOT NULL,destination TEXT NOT NULL,terms_state TEXT NOT NULL,terms_hash TEXT,rights_impact_json TEXT NOT NULL,approval_ref TEXT,external_content_id TEXT,outcome TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)')
    def record_export(self,exporting_entity_id:str,asset_id:str,destination:str,*,terms_snapshot:dict|None,terms_state:str,rights_impact:dict,approval_ref:str|None,external_content_id:str|None,outcome:str)->dict:
        state=str(terms_state).upper()
        if state not in {'VERIFIED','REVIEW_REQUIRED'}: raise ValueError('terms state must be VERIFIED or REVIEW_REQUIRED')
        if state=='REVIEW_REQUIRED' and not approval_ref: raise PermissionError('review-required publication needs explicit approval')
        eid=_id(); now=_now(); terms_hash=hashlib.sha256(_canon(terms_snapshot)).hexdigest() if terms_snapshot is not None else None
        body={'schema':'entity-export-event-v1','export_id':eid,'exporting_entity_id':exporting_entity_id,'asset_id':str(asset_id),'destination':str(destination),'terms_state':state,'terms_hash':terms_hash,'rights_impact':dict(rights_impact or {}),'approval_ref':approval_ref,'external_content_id':external_content_id,'outcome':str(outcome).upper(),'created_at_ms':now,'source_rights_mutated':False,'source_provenance_mutated':False}
        sig=self.identity.sign(exporting_entity_id,body)
        with self._connect() as db: db.execute('INSERT INTO exports VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(eid,exporting_entity_id,str(asset_id),body['destination'],state,terms_hash,json.dumps(body['rights_impact'],sort_keys=True),approval_ref,external_content_id,body['outcome'],json.dumps(sig,sort_keys=True),now))
        return {**body,'signature':sig}
    def status(self): return {'ready':True,'publication_is_export_event':True,'source_rights_preserved':True,'uncertain_terms_review_required':True}
