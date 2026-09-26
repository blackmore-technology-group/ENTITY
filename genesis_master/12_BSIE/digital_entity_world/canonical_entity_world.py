from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json,secrets,sqlite3,time

EVIDENCE={'DIRECT_OBSERVATION','ENTITY_ASSERTION','COUNTERPARTY_ATTESTATION','EXTERNAL_AUTHORITATIVE_RECORD','DERIVED_INFERENCE','UNKNOWN'}
def _now(): return int(time.time()*1000)
def _id(p): return f'{p}-'+secrets.token_hex(20)

class CanonicalEntityWorld:
    """BSIE world/relationship substrate; world state never manufactures ENTITY legal authority."""
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/'bsie_entity_world'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'world.sqlite'; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS objects(world_id TEXT PRIMARY KEY,kind TEXT NOT NULL,state_json TEXT NOT NULL,evidence_origin TEXT NOT NULL,provenance_ref TEXT,classification TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS relations(relation_id TEXT PRIMARY KEY,subject_id TEXT NOT NULL,predicate TEXT NOT NULL,object_id TEXT NOT NULL,evidence_origin TEXT NOT NULL,provenance_ref TEXT,created_at_ms INTEGER NOT NULL)')
    def observe(self,kind:str,state:dict,*,evidence_origin:str,provenance_ref:str|None=None,classification:str='PRIVATE',world_id:str|None=None)->dict:
        origin=str(evidence_origin).upper()
        if origin not in EVIDENCE: raise ValueError('invalid evidence origin')
        wid=str(world_id or _id('world1')); now=_now()
        with self._connect() as db: db.execute('INSERT OR REPLACE INTO objects VALUES(?,?,?,?,?,?,COALESCE((SELECT created_at_ms FROM objects WHERE world_id=?),?),?)',(wid,str(kind).upper(),json.dumps(dict(state),sort_keys=True),origin,provenance_ref,str(classification).upper(),wid,now,now))
        return {'world_id':wid,'kind':str(kind).upper(),'state':dict(state),'evidence_origin':origin,'provenance_ref':provenance_ref,'legal_ownership_inferred':False,'consent_inferred':False}
    def relate(self,subject_id:str,predicate:str,object_id:str,*,evidence_origin:str,provenance_ref:str|None=None)->dict:
        origin=str(evidence_origin).upper()
        if origin not in EVIDENCE: raise ValueError('invalid evidence origin')
        rid=_id('relw1'); now=_now()
        with self._connect() as db:
            if not db.execute('SELECT 1 FROM objects WHERE world_id=?',(subject_id,)).fetchone() or not db.execute('SELECT 1 FROM objects WHERE world_id=?',(object_id,)).fetchone(): raise KeyError('world object missing')
            db.execute('INSERT INTO relations VALUES(?,?,?,?,?,?,?)',(rid,subject_id,str(predicate),object_id,origin,provenance_ref,now))
        return {'relation_id':rid,'subject_id':subject_id,'predicate':str(predicate),'object_id':object_id,'evidence_origin':origin,'provenance_ref':provenance_ref,'rights_inferred':False}
    def project(self,world_id:str,*,allow_sensitive:bool=False)->dict:
        with self._connect() as db: row=db.execute('SELECT * FROM objects WHERE world_id=?',(world_id,)).fetchone()
        if not row: raise KeyError('world object not found')
        state=json.loads(row['state_json'])
        if row['classification'] in {'PRIVATE','RESTRICTED'} and not allow_sensitive: state={'redacted':True}
        return {'schema':'entity-bsie-world-projection-v1','world_id':world_id,'kind':row['kind'],'state':state,'evidence_origin':row['evidence_origin'],'provenance_ref':row['provenance_ref'],'read_only':True,'entity_authority_mutable':False}
    def status(self)->dict:
        with self._connect() as db: count=int(db.execute('SELECT COUNT(*) FROM objects').fetchone()[0]); rel=int(db.execute('SELECT COUNT(*) FROM relations').fetchone()[0])
        return {'ready':True,'objects':count,'relations':rel,'bsie_authority':'WORLD_RELATIONSHIP_STATE','entity_legal_authority':False,'read_only_projection':True}

def niki_project_entity_context_v1(*,world:CanonicalEntityWorld,world_id:str,allow_sensitive:bool=False)->dict:
    return world.project(world_id,allow_sensitive=allow_sensitive)
