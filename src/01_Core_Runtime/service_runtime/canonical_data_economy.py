from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json,secrets,sqlite3,time

def _now(): return int(time.time()*1000)
def _id(p): return f"{p}-"+secrets.token_hex(20)

class DataPoolManager:
    """Governed contributor pool with versioned deterministic revenue allocation."""
    def __init__(self,state_dir: str|Path,identity):
        self.root=Path(state_dir)/"data_economy"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"data_pools.sqlite"; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS pools(pool_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,name TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,rules_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS contributions(contribution_id TEXT PRIMARY KEY,pool_id TEXT NOT NULL,contributor_entity_id TEXT NOT NULL,asset_id TEXT NOT NULL,weight_bps INTEGER NOT NULL,evidence_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,UNIQUE(pool_id,asset_id))")
    def create_pool(self,controller_entity_id:str,name:str,*,rules:dict|None=None)->dict:
        pid=_id("pool1"); now=_now(); body={"schema":"entity-data-pool-v1","pool_id":pid,"controller_entity_id":controller_entity_id,"name":str(name)[:256],"version":1,"status":"ACTIVE","rules":dict(rules or {}),"created_at_ms":now}
        sig=self.identity.sign(controller_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO pools VALUES(?,?,?,?,?,?,?,?)",(pid,controller_entity_id,body["name"],1,"ACTIVE",json.dumps(body["rules"],sort_keys=True),json.dumps(sig,sort_keys=True),now))
        return {**body,"signature":sig}
    def contribute(self,pool_id:str,contributor_entity_id:str,asset_id:str,*,weight_bps:int,evidence:dict)->dict:
        weight=int(weight_bps)
        if weight<1 or weight>10000: raise ValueError("weight_bps must be 1..10000")
        self.identity.load_manifest(contributor_entity_id); cid=_id("contrib1"); now=_now()
        body={"schema":"entity-pool-contribution-v1","contribution_id":cid,"pool_id":pool_id,"contributor_entity_id":contributor_entity_id,"asset_id":str(asset_id),"weight_bps":weight,"evidence":dict(evidence or {}),"created_at_ms":now}
        sig=self.identity.sign(contributor_entity_id,body)
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM pools WHERE pool_id=? AND status='ACTIVE'",(pool_id,)).fetchone(): raise KeyError("active pool not found")
            db.execute("INSERT INTO contributions VALUES(?,?,?,?,?,?,?,?)",(cid,pool_id,contributor_entity_id,str(asset_id),weight,json.dumps(body["evidence"],sort_keys=True),json.dumps(sig,sort_keys=True),now))
        return {**body,"signature":sig}
    def allocation(self,pool_id:str,amount_units:int,currency:str)->dict:
        with self._connect() as db: rows=db.execute("SELECT contributor_entity_id,weight_bps FROM contributions WHERE pool_id=? ORDER BY contribution_id",(pool_id,)).fetchall()
        if not rows: raise ValueError("pool has no contributions")
        weights={}
        for r in rows: weights[r["contributor_entity_id"]]=weights.get(r["contributor_entity_id"],0)+int(r["weight_bps"])
        total=sum(weights.values()); amount=max(0,int(amount_units)); ordered=sorted(weights)
        dist={k:(amount*weights[k])//total for k in ordered}; remainder=amount-sum(dist.values())
        for k in ordered[:remainder]: dist[k]+=1
        return {"schema":"entity-data-pool-allocation-v1","pool_id":pool_id,"amount_units":amount,"currency":str(currency).upper(),"distribution":dist,"allocated_total":sum(dist.values()),"deterministic":True,"weight_total":total}
    def status(self)->dict:
        with self._connect() as db: pools=int(db.execute("SELECT COUNT(*) FROM pools").fetchone()[0]); contributions=int(db.execute("SELECT COUNT(*) FROM contributions").fetchone()[0])
        return {"ready":True,"pools":pools,"contributions":contributions,"deterministic_allocation":True,"contributor_rights_preserved":True}

class DataSpaceGateway:
    """Metered compute-to-data authority; raw-file transfer is not implied by access."""
    def __init__(self,state_dir: str|Path,identity):
        self.root=Path(state_dir)/"data_economy"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"data_spaces.sqlite"; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS spaces(space_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,assets_json TEXT NOT NULL,operations_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY,space_id TEXT NOT NULL,counterparty_entity_id TEXT NOT NULL,operation TEXT NOT NULL,nonce TEXT UNIQUE NOT NULL,status TEXT NOT NULL,quantity INTEGER NOT NULL,created_at_ms INTEGER NOT NULL,consumed_at_ms INTEGER)")
    def create_space(self,controller_entity_id:str,assets:list[str],operations:list[str])->dict:
        aid=sorted({str(x) for x in assets if str(x)}); ops=sorted({str(x).upper() for x in operations if str(x)})
        if not aid or not ops: raise ValueError("assets and operations required")
        sid=_id("space1"); now=_now()
        with self._connect() as db: db.execute("INSERT INTO spaces VALUES(?,?,?,?,?,?)",(sid,controller_entity_id,json.dumps(aid),json.dumps(ops),"ACTIVE",now))
        return {"space_id":sid,"controller_entity_id":controller_entity_id,"assets":aid,"operations":ops,"raw_file_transfer_authorized":False}
    def issue_session(self,controller_entity_id:str,space_id:str,counterparty_entity_id:str,operation:str,*,quantity:int=1,nonce:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM spaces WHERE space_id=?",(space_id,)).fetchone()
        if not row or row["status"]!="ACTIVE": raise KeyError("active data space not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("data space controller mismatch")
        op=str(operation).upper()
        if op not in set(json.loads(row["operations_json"])): raise PermissionError("operation outside data-space scope")
        session=_id("dss1"); now=_now()
        with self._connect() as db:
            try: db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",(session,space_id,counterparty_entity_id,op,str(nonce),"ISSUED",max(1,int(quantity)),now,None))
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed data-space nonce") from exc
        return {"session_id":session,"space_id":space_id,"counterparty_entity_id":counterparty_entity_id,"operation":op,"status":"ISSUED","raw_file_transfer_authorized":False}
    def consume(self,counterparty_entity_id:str,session_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM sessions WHERE session_id=?",(session_id,)).fetchone()
        if not row: raise KeyError("data-space session not found")
        if row["counterparty_entity_id"]!=counterparty_entity_id: raise PermissionError("data-space counterparty mismatch")
        if row["status"]!="ISSUED": raise PermissionError("data-space session already consumed")
        now=_now()
        with self._connect() as db: db.execute("UPDATE sessions SET status='CONSUMED',consumed_at_ms=? WHERE session_id=?",(now,session_id))
        return {"session_id":session_id,"status":"CONSUMED","metered_quantity":int(row["quantity"]),"raw_file_transfer_observed":False,"consumed_at_ms":now}
    def status(self)->dict:
        with self._connect() as db: spaces=int(db.execute("SELECT COUNT(*) FROM spaces").fetchone()[0]); sessions=int(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
        return {"ready":True,"spaces":spaces,"sessions":sessions,"compute_to_data":True,"raw_transfer_not_implied":True,"replay_protected":True}
