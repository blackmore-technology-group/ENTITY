from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,sqlite3,time

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()
class PrebootstrapEvidenceAdopter:
    """Adopts historical evidence without upgrading how/when it was originally observed."""
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/'prebootstrap_evidence'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'adopted.sqlite'; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db: db.execute('CREATE TABLE IF NOT EXISTS adopted(evidence_id TEXT PRIMARY KEY,content_sha256 TEXT NOT NULL,evidence_origin TEXT NOT NULL,assurance TEXT NOT NULL,payload_json TEXT NOT NULL,adopted_at_ms INTEGER NOT NULL)')
    def adopt(self,evidence_id:str,payload:dict,*,content_sha256:str,evidence_origin:str,assurance:str)->dict:
        digest=hashlib.sha256(_canon(payload)).hexdigest()
        if digest!=str(content_sha256).lower(): raise ValueError('prebootstrap evidence commitment mismatch')
        origin=str(evidence_origin).upper(); level=str(assurance).upper(); now=_now()
        with self._connect() as db:
            prior=db.execute('SELECT * FROM adopted WHERE evidence_id=?',(str(evidence_id),)).fetchone()
            if prior:
                if prior['content_sha256']!=digest: raise ValueError('conflicting evidence id')
                return {'evidence_id':str(evidence_id),'deduplicated':True,'evidence_origin':prior['evidence_origin'],'assurance':prior['assurance'],'retroactively_upgraded':False}
            db.execute('INSERT INTO adopted VALUES(?,?,?,?,?,?)',(str(evidence_id),digest,origin,level,json.dumps(dict(payload),sort_keys=True),now))
        return {'evidence_id':str(evidence_id),'deduplicated':False,'evidence_origin':origin,'assurance':level,'retroactively_upgraded':False,'direct_observation_claimed':origin=='DIRECT_OBSERVATION'}
    def status(self): return {'ready':True,'integrity_checked':True,'idempotent':True,'retroactive_upgrade':False}
