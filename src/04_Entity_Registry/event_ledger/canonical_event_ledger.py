from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import hashlib, json, sqlite3, time, uuid

ZERO_HASH="0"*64

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()

def _merkle_root(leaves:list[str])->str:
    if not leaves: return ZERO_HASH
    layer=[bytes.fromhex(x) for x in leaves]
    while len(layer)>1:
        if len(layer)%2: layer.append(layer[-1])
        layer=[hashlib.sha256(layer[i]+layer[i+1]).digest() for i in range(0,len(layer),2)]
    return layer[0].hex()

class CanonicalEventLedger:
    """Signed append-only hash chain with independently verifiable checkpoints."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/"event_ledger"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"ledger.sqlite"; self.identity=identity; self._lock=RLock(); self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,subject_ids_json TEXT NOT NULL,object_ids_json TEXT NOT NULL,payload_hash TEXT NOT NULL,evidence_origin TEXT NOT NULL,confidence REAL NOT NULL,timestamp_ms INTEGER NOT NULL,prior_hash TEXT NOT NULL,event_hash TEXT NOT NULL,signature_json TEXT NOT NULL,schema_version TEXT NOT NULL)")
            cols={str(r[1]) for r in db.execute("PRAGMA table_info(events)").fetchall()}
            if "payload_sha256" not in cols:
                db.execute("ALTER TABLE events ADD COLUMN payload_sha256 TEXT")
                db.execute("UPDATE events SET payload_sha256=payload_hash WHERE payload_sha256 IS NULL")
            db.execute("CREATE TABLE IF NOT EXISTS checkpoints(checkpoint_id TEXT PRIMARY KEY,from_sequence INTEGER NOT NULL,to_sequence INTEGER NOT NULL,event_count INTEGER NOT NULL,merkle_root TEXT NOT NULL,head_hash TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signer_entity_id TEXT NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('head_hash',?)",(ZERO_HASH,))

    def append(self,actor_entity_id:str,event_type:str,*,subject_ids=None,object_ids=None,payload=None,payload_sha256=None,metadata=None,evidence_origin="DIRECT_OBSERVATION",confidence=1.0)->dict:
        body_payload=dict(payload or {})
        if payload_sha256 is not None:
            payload_hash=str(payload_sha256).lower()
            if len(payload_hash)!=64 or any(c not in "0123456789abcdef" for c in payload_hash): raise ValueError("payload_sha256 must be SHA-256 hex")
            if payload is not None and _sha(body_payload)!=payload_hash: raise ValueError("payload and payload_sha256 disagree")
        else:
            payload_hash=_sha(body_payload)
        now=_now(); event_id="evt1-"+uuid.uuid4().hex
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]
            body={"schema":"ENTITY-EVENT-v1","event_id":event_id,"event_type":str(event_type),"actor_entity_id":str(actor_entity_id),"subject_ids":list(subject_ids or []),"object_ids":list(object_ids or []),"payload_hash":payload_hash,"evidence_origin":str(evidence_origin),"confidence":float(confidence),"timestamp_ms":now,"prior_hash":prior}
            signature=self.identity.sign(actor_entity_id,body); event_hash=_sha({"body":body,"signature":signature})
            db.execute("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version,payload_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(event_id,str(event_type),str(actor_entity_id),json.dumps(body["subject_ids"]),json.dumps(body["object_ids"]),payload_hash,str(evidence_origin),float(confidence),now,prior,event_hash,json.dumps(signature,sort_keys=True),"ENTITY-EVENT-v1",payload_hash))
            db.execute("UPDATE meta SET v=? WHERE k='head_hash'",(event_hash,))
        return {"event_id":event_id,"event_hash":event_hash,"prior_hash":prior,"payload_hash":payload_hash,"payload_sha256":payload_hash,"signature":signature,"timestamp_ms":now,"raw_payload_stored":False}

    def append_batch(self,actor_entity_id:str,events:list[dict])->list[dict]:
        """Append many fully signed/hash-chained events in one durable transaction."""
        items=list(events or [])
        if not items: return []
        sign=self.identity.open_signing_session(actor_entity_id)
        out=[]; rows=[]
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]
            for item in items:
                payload=dict(item.get("payload") or {})
                supplied=item.get("payload_sha256")
                payload_hash=str(supplied).lower() if supplied is not None else _sha(payload)
                if len(payload_hash)!=64 or any(c not in "0123456789abcdef" for c in payload_hash): raise ValueError("payload_sha256 must be SHA-256 hex")
                if supplied is not None and item.get("payload") is not None and _sha(payload)!=payload_hash: raise ValueError("payload and payload_sha256 disagree")
                now=_now(); event_id="evt1-"+uuid.uuid4().hex
                body={"schema":"ENTITY-EVENT-v1","event_id":event_id,"event_type":str(item.get("event_type") or ""),"actor_entity_id":str(actor_entity_id),"subject_ids":list(item.get("subject_ids") or []),"object_ids":list(item.get("object_ids") or []),"payload_hash":payload_hash,"evidence_origin":str(item.get("evidence_origin") or "DIRECT_OBSERVATION"),"confidence":float(item.get("confidence",1.0)),"timestamp_ms":now,"prior_hash":prior}
                signature=sign(body); event_hash=_sha({"body":body,"signature":signature})
                rows.append((event_id,body["event_type"],str(actor_entity_id),json.dumps(body["subject_ids"]),json.dumps(body["object_ids"]),payload_hash,body["evidence_origin"],body["confidence"],now,prior,event_hash,json.dumps(signature,sort_keys=True),"ENTITY-EVENT-v1",payload_hash))
                out.append({"event_id":event_id,"event_hash":event_hash,"prior_hash":prior,"payload_hash":payload_hash,"payload_sha256":payload_hash,"signature":signature,"timestamp_ms":now,"raw_payload_stored":False})
                prior=event_hash
            db.executemany("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version,payload_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
            db.execute("UPDATE meta SET v=? WHERE k='head_hash'",(prior,))
        return out

    def rows(self):
        with self._connect() as db: return [dict(r) for r in db.execute("SELECT * FROM events ORDER BY sequence")]

    def verify(self)->dict:
        """Streaming full-ledger verification with bounded memory and manifest caching."""
        prior=ZERO_HASH; count=0; manifests={}
        with self._connect() as db:
            cur=db.execute("SELECT * FROM events ORDER BY sequence")
            while True:
                batch=cur.fetchmany(10000)
                if not batch: break
                for raw in batch:
                    row=dict(raw)
                    body={"schema":row["schema_version"],"event_id":row["event_id"],"event_type":row["event_type"],"actor_entity_id":row["actor_entity_id"],"subject_ids":json.loads(row["subject_ids_json"]),"object_ids":json.loads(row["object_ids_json"]),"payload_hash":row["payload_hash"],"evidence_origin":row["evidence_origin"],"confidence":row["confidence"],"timestamp_ms":row["timestamp_ms"],"prior_hash":row["prior_hash"]}
                    sig=json.loads(row["signature_json"])
                    if row.get("payload_sha256") not in {None,row["payload_hash"]}: return {"pass":False,"reason":"event_hash_failure","sequence":row["sequence"]}
                    if row["prior_hash"]!=prior: return {"pass":False,"reason":"hash_chain_failure","sequence":row["sequence"]}
                    if _sha({"body":body,"signature":sig})!=row["event_hash"]: return {"pass":False,"reason":"event_hash_failure","sequence":row["sequence"]}
                    actor=row["actor_entity_id"]; manifest=manifests.get(actor)
                    if manifest is None: manifest=self.identity.load_manifest(actor); manifests[actor]=manifest
                    if not self.identity.verify_signature(manifest,body,sig): return {"pass":False,"reason":"signature_failure","sequence":row["sequence"]}
                    prior=row["event_hash"]; count+=1
            head=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]
        return {"pass":head==prior,"blocks":count,"head_hash":head,"streaming":True}
    def checkpoint(self,signer_entity_id:str,*,from_sequence:int=1,to_sequence:int|None=None)->dict:
        rows=self.rows(); selected=[r for r in rows if int(r["sequence"])>=int(from_sequence) and (to_sequence is None or int(r["sequence"])<=int(to_sequence))]
        if not selected: raise ValueError("checkpoint range contains no events")
        root=_merkle_root([r["event_hash"] for r in selected]); now=_now(); checkpoint_id="chk1-"+uuid.uuid4().hex
        body={"schema":"entity-ledger-checkpoint-v1","checkpoint_id":checkpoint_id,"from_sequence":int(selected[0]["sequence"]),"to_sequence":int(selected[-1]["sequence"]),"event_count":len(selected),"merkle_root":root,"head_hash":selected[-1]["event_hash"],"created_at_ms":now,"signer_entity_id":str(signer_entity_id)}
        signature=self.identity.sign(signer_entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?,?,?)",(checkpoint_id,body["from_sequence"],body["to_sequence"],body["event_count"],root,body["head_hash"],now,str(signer_entity_id),json.dumps(signature,sort_keys=True)))
        return {**body,"signature":signature}

    def create_checkpoint(self,signer_entity_id:str,*,from_sequence:int=1,to_sequence:int|None=None)->dict:
        out=self.checkpoint(signer_entity_id,from_sequence=from_sequence,to_sequence=to_sequence)
        return {**out,"leaf_count":out["event_count"]}

    def verify_checkpoint(self,checkpoint_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM checkpoints WHERE checkpoint_id=?",(checkpoint_id,)).fetchone()
        if not row: raise KeyError("checkpoint not found")
        selected=[r for r in self.rows() if row["from_sequence"]<=r["sequence"]<=row["to_sequence"]]
        root=_merkle_root([r["event_hash"] for r in selected])
        body={"schema":"entity-ledger-checkpoint-v1","checkpoint_id":row["checkpoint_id"],"from_sequence":row["from_sequence"],"to_sequence":row["to_sequence"],"event_count":row["event_count"],"merkle_root":row["merkle_root"],"head_hash":row["head_hash"],"created_at_ms":row["created_at_ms"],"signer_entity_id":row["signer_entity_id"]}
        manifest=self.identity.load_manifest(row["signer_entity_id"]); sig=json.loads(row["signature_json"])
        ok=(len(selected)==row["event_count"] and root==row["merkle_root"] and selected[-1]["event_hash"]==row["head_hash"] and self.identity.verify_signature(manifest,body,sig))
        return {"pass":bool(ok),"checkpoint_id":checkpoint_id,"merkle_root":root,"event_count":len(selected)}

    def status(self):
        check=self.verify()
        with self._connect() as db: cps=db.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
        return {"ready":bool(check["pass"]),"schema":"entity-canonical-event-ledger-v1","signed_events":True,"hash_chain":True,"merkle_checkpoints":True,"blocks":check["blocks"],"checkpoints":int(cps),"head_hash":check["head_hash"]}
