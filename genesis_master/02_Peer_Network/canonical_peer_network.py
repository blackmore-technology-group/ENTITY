from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,secrets,sqlite3,time

def _now(): return int(time.time()*1000)
def _id(p): return f'{p}-'+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()

class FederationTrustStore:
    """Explicit authenticated peer trust with version/downgrade and revocation controls."""
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/'peer_network'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'federation.sqlite'; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS peers(peer_id TEXT PRIMARY KEY,identity_ref TEXT NOT NULL,protocol_version INTEGER NOT NULL,schemas_json TEXT NOT NULL,trust_level INTEGER NOT NULL,status TEXT NOT NULL,last_nonce TEXT,updated_at_ms INTEGER NOT NULL)')
    def trust_peer(self,peer_id:str,identity_ref:str,*,protocol_version:int,schemas:list[str],trust_level:int)->dict:
        now=_now(); pv=max(1,int(protocol_version)); tl=max(0,int(trust_level))
        with self._connect() as db: db.execute('INSERT OR REPLACE INTO peers VALUES(?,?,?,?,?,?,?,?)',(str(peer_id),str(identity_ref),pv,json.dumps(sorted(set(schemas))),tl,'ACTIVE',None,now))
        return {'peer_id':str(peer_id),'identity_ref':str(identity_ref),'protocol_version':pv,'trust_level':tl,'status':'ACTIVE'}
    def authenticate(self,peer_id:str,identity_ref:str,*,protocol_version:int,nonce:str,min_trust:int=0,required_schema:str|None=None)->dict:
        with self._connect() as db: row=db.execute('SELECT * FROM peers WHERE peer_id=?',(str(peer_id),)).fetchone()
        if not row or row['status']!='ACTIVE': return {'allowed':False,'reason':'peer_untrusted'}
        if row['identity_ref']!=str(identity_ref): return {'allowed':False,'reason':'identity_mismatch'}
        if int(protocol_version)<int(row['protocol_version']): return {'allowed':False,'reason':'protocol_downgrade'}
        if int(row['trust_level'])<int(min_trust): return {'allowed':False,'reason':'trust_below_minimum'}
        if required_schema and required_schema not in set(json.loads(row['schemas_json'])): return {'allowed':False,'reason':'schema_incompatible'}
        if row['last_nonce']==str(nonce): return {'allowed':False,'reason':'replay'}
        with self._connect() as db: db.execute('UPDATE peers SET protocol_version=?,last_nonce=?,updated_at_ms=? WHERE peer_id=?',(max(int(row['protocol_version']),int(protocol_version)),str(nonce),_now(),str(peer_id)))
        return {'allowed':True,'peer_id':str(peer_id),'authenticated':True,'authorized_rights_inferred':False}
    def revoke(self,peer_id:str)->dict:
        with self._connect() as db:
            if not db.execute('SELECT 1 FROM peers WHERE peer_id=?',(str(peer_id),)).fetchone(): raise KeyError('peer not found')
            db.execute("UPDATE peers SET status='REVOKED',updated_at_ms=? WHERE peer_id=?",(_now(),str(peer_id)))
        return {'peer_id':str(peer_id),'status':'REVOKED'}
    def status(self)->dict:
        with self._connect() as db: count=int(db.execute("SELECT COUNT(*) FROM peers WHERE status='ACTIVE'").fetchone()[0])
        return {'ready':True,'trusted_peers':count,'signed_downgrade_protection':True,'discovery_does_not_imply_trust':True}

class TransparencyWitness:
    """Signed witness commitments; local history is not represented as globally authoritative."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/'peer_network'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'witness.sqlite'; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db: db.execute('CREATE TABLE IF NOT EXISTS witnesses(witness_id TEXT PRIMARY KEY,event_ref TEXT NOT NULL,commitment_sha256 TEXT NOT NULL,witness_entity_id TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)')
    def witness(self,witness_entity_id:str,event_ref:str,commitment_sha256:str)->dict:
        digest=str(commitment_sha256).lower()
        if len(digest)!=64: raise ValueError('SHA-256 commitment required')
        wid=_id('wit1'); now=_now(); body={'schema':'entity-transparency-witness-v1','witness_id':wid,'event_ref':str(event_ref),'commitment_sha256':digest,'witness_entity_id':witness_entity_id,'created_at_ms':now,'global_authority_claimed':False}
        sig=self.identity.sign(witness_entity_id,body)
        with self._connect() as db: db.execute('INSERT INTO witnesses VALUES(?,?,?,?,?,?)',(wid,str(event_ref),digest,witness_entity_id,json.dumps(sig,sort_keys=True),now))
        return {**body,'signature':sig}
    def verify(self,witness_id:str)->bool:
        with self._connect() as db: row=db.execute('SELECT * FROM witnesses WHERE witness_id=?',(witness_id,)).fetchone()
        if not row: return False
        body={'schema':'entity-transparency-witness-v1','witness_id':row['witness_id'],'event_ref':row['event_ref'],'commitment_sha256':row['commitment_sha256'],'witness_entity_id':row['witness_entity_id'],'created_at_ms':row['created_at_ms'],'global_authority_claimed':False}
        return bool(self.identity.verify_signature(self.identity.load_manifest(row['witness_entity_id']),body,json.loads(row['signature_json'])))
