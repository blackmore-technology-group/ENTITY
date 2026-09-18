from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
from typing import Iterable
import hashlib, json, os, sqlite3, time

ZERO_HASH="0"*64
SCHEMA="entity-segmented-bulk-ingest-v1"

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _file_sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def _merkle(leaves:list[str])->str:
    if not leaves: return ZERO_HASH
    layer=[bytes.fromhex(x) for x in leaves]
    while len(layer)>1:
        if len(layer)%2: layer.append(layer[-1])
        layer=[hashlib.sha256(layer[i]+layer[i+1]).digest() for i in range(0,len(layer),2)]
    return layer[0].hex()

class CanonicalSegmentedBulkStore:
    """Immutable signed batch segments for production-scale ingestion.

    Each segment is created off to the side, hashed, then atomically published by a
    signed manifest-chain record. Unpublished/orphan temp segments carry no authority.
    """
    def __init__(self,root:str|Path,identity,controller_entity_id:str):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.segments=self.root/"segments"; self.segments.mkdir(exist_ok=True)
        self.manifest_path=self.root/"manifest.sqlite"
        self.identity=identity; self.controller_entity_id=str(controller_entity_id)
        self.identity.load_manifest(self.controller_entity_id)
        self.sign=self.identity.open_signing_session(self.controller_entity_id)
        self._lock=RLock(); self._init_manifest()

    @contextmanager
    def _manifest(self):
        db=sqlite3.connect(self.manifest_path,timeout=120); db.row_factory=sqlite3.Row
        try:
            yield db; db.commit()
        except Exception:
            db.rollback(); raise
        finally: db.close()

    def _init_manifest(self):
        with self._manifest() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS batches(sequence INTEGER PRIMARY KEY AUTOINCREMENT,batch_id TEXT UNIQUE NOT NULL,segment_name TEXT UNIQUE NOT NULL,segment_sha256 TEXT NOT NULL,controller_entity_id TEXT NOT NULL,asset_count INTEGER NOT NULL,event_count INTEGER NOT NULL,asset_merkle_root TEXT NOT NULL,start_prior_event_hash TEXT NOT NULL,end_event_hash TEXT NOT NULL,prior_batch_hash TEXT NOT NULL,batch_hash TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            for k,v in (("event_head",ZERO_HASH),("batch_head",ZERO_HASH),("asset_total","0"),("event_total","0")):
                db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)",(k,v))

    @staticmethod
    def _valid_digest(value:str)->str:
        digest=str(value or "").lower()
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("content_sha256 must be SHA-256 hex")
        return digest

    def _heads(self):
        with self._manifest() as db:
            event_head=db.execute("SELECT v FROM meta WHERE k='event_head'").fetchone()[0]
            batch_head=db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
            assets=int(db.execute("SELECT v FROM meta WHERE k='asset_total'").fetchone()[0])
            events=int(db.execute("SELECT v FROM meta WHERE k='event_total'").fetchone()[0])
        return event_head,batch_head,assets,events

    def _segment_path(self,batch_id:str)->Path:
        safe="".join(c for c in str(batch_id) if c.isalnum() or c in "-_")
        if not safe or safe!=str(batch_id): raise ValueError("batch_id must be filesystem safe")
        return self.segments/f"{safe}.sqlite"

    def _build_segment(self,records:Iterable[dict],batch_id:str,start_prior:str,created_at_ms:int,temp_path:Path):
        if temp_path.exists(): temp_path.unlink()
        db=sqlite3.connect(temp_path,timeout=120)
        try:
            db.execute("PRAGMA journal_mode=OFF"); db.execute("PRAGMA synchronous=OFF"); db.execute("PRAGMA temp_store=MEMORY")
            db.execute("CREATE TABLE assets(asset_ordinal INTEGER PRIMARY KEY,asset_id TEXT UNIQUE NOT NULL,controller_entity_id TEXT NOT NULL,content_sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,media_type TEXT NOT NULL,title TEXT NOT NULL,classification TEXT NOT NULL,metadata_sha256 TEXT NOT NULL,record_sha256 TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE events(local_sequence INTEGER PRIMARY KEY,event_id TEXT UNIQUE NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,asset_id TEXT NOT NULL,payload_sha256 TEXT NOT NULL,prior_hash TEXT NOT NULL,event_hash TEXT NOT NULL,timestamp_ms INTEGER NOT NULL)")
            asset_rows=[]; event_rows=[]; leaves=[]; prior=start_prior
            for ordinal,item in enumerate(records):
                digest=self._valid_digest(item.get("content_sha256")); metadata=dict(item.get("metadata") or {})
                asset_id=f"assets1-{batch_id}-{ordinal:05d}-{digest[:16]}"
                body={"schema":"entity-segmented-asset-v1","asset_id":asset_id,"controller_entity_id":self.controller_entity_id,"content_sha256":digest,"size_bytes":max(0,int(item.get("size_bytes") or 0)),"media_type":str(item.get("media_type") or "application/octet-stream")[:128],"title":str(item.get("title") or "")[:512],"classification":str(item.get("classification") or "PRIVATE").upper()[:32],"metadata_sha256":_sha(metadata),"created_at_ms":created_at_ms,"registration_not_ownership":True}
                record_sha=_sha(body); leaves.append(record_sha)
                asset_rows.append((ordinal,asset_id,self.controller_entity_id,digest,body["size_bytes"],body["media_type"],body["title"],body["classification"],body["metadata_sha256"],record_sha,created_at_ms))
                for suffix,event_type,payload in (
                    ("r","asset.registered",{"asset_id":asset_id,"content_sha256":digest,"registration_not_ownership":True}),
                    ("p","provenance.recorded",{"asset_id":asset_id,"content_sha256":digest,"truth_not_inferred":True}),
                    ("c","controller.claimed",{"asset_id":asset_id,"right_type":"DATA_CONTROLLER","legal_truth_not_inferred":True}),
                ):
                    event_id=f"evts1-{batch_id}-{ordinal:05d}-{suffix}"
                    payload_sha=_sha(payload)
                    ev_body={"schema":"ENTITY-SEGMENT-EVENT-v1","event_id":event_id,"event_type":event_type,"actor_entity_id":self.controller_entity_id,"asset_id":asset_id,"payload_sha256":payload_sha,"prior_hash":prior,"batch_id":batch_id,"timestamp_ms":created_at_ms}
                    event_hash=_sha(ev_body)
                    event_rows.append((len(event_rows)+1,event_id,event_type,self.controller_entity_id,asset_id,payload_sha,prior,event_hash,created_at_ms))
                    prior=event_hash
            if not asset_rows: raise ValueError("segment batch must contain at least one asset")
            db.execute("BEGIN")
            db.executemany("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",asset_rows)
            db.executemany("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)",event_rows)
            db.commit()
            db.execute("PRAGMA optimize")
            return {"asset_count":len(asset_rows),"event_count":len(event_rows),"asset_merkle_root":_merkle(leaves),"end_event_hash":prior}
        finally:
            db.close()

    def ingest_segment(self,records:Iterable[dict],*,batch_id:str)->dict:
        batch_id=str(batch_id or "").strip()
        if not batch_id: raise ValueError("batch_id required")
        with self._lock:
            final_path=self._segment_path(batch_id); temp_path=final_path.with_suffix(".sqlite.tmp")
            with self._manifest() as db:
                if db.execute("SELECT 1 FROM batches WHERE batch_id=?",(batch_id,)).fetchone(): raise ValueError("batch_id already exists")
            start_event,prior_batch,asset_total,event_total=self._heads(); now=_now()
            built=self._build_segment(records,batch_id,start_event,now,temp_path)
            segment_sha=_file_sha(temp_path)
            segment_name=final_path.name
            batch_body={"schema":"entity-segmented-batch-v1","batch_id":batch_id,"segment_name":segment_name,"segment_sha256":segment_sha,"controller_entity_id":self.controller_entity_id,"asset_count":built["asset_count"],"event_count":built["event_count"],"asset_merkle_root":built["asset_merkle_root"],"start_prior_event_hash":start_event,"end_event_hash":built["end_event_hash"],"prior_batch_hash":prior_batch,"created_at_ms":now,"registration_not_ownership":True,"segment_attestation_not_legal_truth":True}
            signature=self.sign(batch_body); batch_hash=_sha({"body":batch_body,"signature":signature})
            if final_path.exists(): raise FileExistsError(str(final_path))
            os.replace(temp_path,final_path)
            try:
                with self._manifest() as db:
                    db.execute("BEGIN IMMEDIATE")
                    current_event=db.execute("SELECT v FROM meta WHERE k='event_head'").fetchone()[0]
                    current_batch=db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
                    if current_event!=start_event or current_batch!=prior_batch:
                        raise RuntimeError("manifest head changed concurrently")
                    db.execute("INSERT INTO batches(batch_id,segment_name,segment_sha256,controller_entity_id,asset_count,event_count,asset_merkle_root,start_prior_event_hash,end_event_hash,prior_batch_hash,batch_hash,signature_json,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(batch_id,segment_name,segment_sha,self.controller_entity_id,built["asset_count"],built["event_count"],built["asset_merkle_root"],start_event,built["end_event_hash"],prior_batch,batch_hash,json.dumps(signature,sort_keys=True),now))
                    db.execute("UPDATE meta SET v=? WHERE k='event_head'",(built["end_event_hash"],))
                    db.execute("UPDATE meta SET v=? WHERE k='batch_head'",(batch_hash,))
                    db.execute("UPDATE meta SET v=? WHERE k='asset_total'",(str(asset_total+built["asset_count"]),))
                    db.execute("UPDATE meta SET v=? WHERE k='event_total'",(str(event_total+built["event_count"]),))
            except Exception:
                try: final_path.unlink()
                except OSError: pass
                raise
            return {**batch_body,"batch_hash":batch_hash,"signature":signature,"segment_path":str(final_path)}

    def verify_segment(self,batch_id:str,*,full_rows:bool=True)->dict:
        with self._manifest() as db:
            row=db.execute("SELECT * FROM batches WHERE batch_id=?",(str(batch_id),)).fetchone()
        if not row: raise KeyError("batch not found")
        path=self.segments/row["segment_name"]
        file_ok=path.is_file() and _file_sha(path)==row["segment_sha256"]
        body={"schema":"entity-segmented-batch-v1","batch_id":row["batch_id"],"segment_name":row["segment_name"],"segment_sha256":row["segment_sha256"],"controller_entity_id":row["controller_entity_id"],"asset_count":row["asset_count"],"event_count":row["event_count"],"asset_merkle_root":row["asset_merkle_root"],"start_prior_event_hash":row["start_prior_event_hash"],"end_event_hash":row["end_event_hash"],"prior_batch_hash":row["prior_batch_hash"],"created_at_ms":row["created_at_ms"],"registration_not_ownership":True,"segment_attestation_not_legal_truth":True}
        sig=json.loads(row["signature_json"]); manifest=self.identity.load_manifest(row["controller_entity_id"])
        sig_ok=bool(self.identity.verify_signature(manifest,body,sig))
        batch_hash_ok=_sha({"body":body,"signature":sig})==row["batch_hash"]
        asset_ok=event_ok=True
        if full_rows and file_ok:
            db=sqlite3.connect(path); db.row_factory=sqlite3.Row
            try:
                assets=db.execute("SELECT record_sha256 FROM assets ORDER BY asset_ordinal").fetchall()
                events=db.execute("SELECT * FROM events ORDER BY local_sequence").fetchall()
            finally: db.close()
            asset_ok=len(assets)==row["asset_count"] and _merkle([r[0] for r in assets])==row["asset_merkle_root"]
            prior=row["start_prior_event_hash"]
            for ev in events:
                ev_body={"schema":"ENTITY-SEGMENT-EVENT-v1","event_id":ev["event_id"],"event_type":ev["event_type"],"actor_entity_id":ev["actor_entity_id"],"asset_id":ev["asset_id"],"payload_sha256":ev["payload_sha256"],"prior_hash":ev["prior_hash"],"batch_id":row["batch_id"],"timestamp_ms":ev["timestamp_ms"]}
                if ev["prior_hash"]!=prior or _sha(ev_body)!=ev["event_hash"]: event_ok=False; break
                prior=ev["event_hash"]
            event_ok=event_ok and len(events)==row["event_count"] and prior==row["end_event_hash"]
        return {"pass":bool(file_ok and sig_ok and batch_hash_ok and asset_ok and event_ok),"batch_id":row["batch_id"],"segment_file_ok":file_ok,"signature_ok":sig_ok,"batch_hash_ok":batch_hash_ok,"asset_merkle_ok":asset_ok,"event_chain_ok":event_ok,"asset_count":int(row["asset_count"]),"event_count":int(row["event_count"])}

    def verify_all(self,*,full_rows:bool=True)->dict:
        with self._manifest() as db:
            rows=db.execute("SELECT batch_id,prior_batch_hash,batch_hash FROM batches ORDER BY sequence").fetchall()
            event_head=db.execute("SELECT v FROM meta WHERE k='event_head'").fetchone()[0]
            batch_head=db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
        prior_batch=ZERO_HASH; prior_event=ZERO_HASH; checked=0; assets=0; events=0
        for row in rows:
            if row["prior_batch_hash"]!=prior_batch:
                return {"pass":False,"reason":"batch_chain_failure","batch_id":row["batch_id"],"checked":checked}
            result=self.verify_segment(row["batch_id"],full_rows=full_rows)
            if not result["pass"]:
                return {"pass":False,"reason":"segment_verification_failure","batch_id":row["batch_id"],"details":result,"checked":checked}
            with self._manifest() as db:
                manifest_row=db.execute("SELECT start_prior_event_hash,end_event_hash FROM batches WHERE batch_id=?",(row["batch_id"],)).fetchone()
            if manifest_row["start_prior_event_hash"]!=prior_event:
                return {"pass":False,"reason":"cross_segment_event_chain_failure","batch_id":row["batch_id"],"checked":checked}
            prior_event=manifest_row["end_event_hash"]; prior_batch=row["batch_hash"]
            assets+=result["asset_count"]; events+=result["event_count"]; checked+=1
        return {"pass":batch_head==prior_batch and event_head==prior_event,"segments":checked,"assets":assets,"events":events,"batch_head":batch_head,"event_head":event_head,"full_rows_verified":bool(full_rows)}

    def status(self)->dict:
        with self._manifest() as db:
            batches=int(db.execute("SELECT COUNT(*) FROM batches").fetchone()[0])
            meta={r["k"]:r["v"] for r in db.execute("SELECT k,v FROM meta").fetchall()}
            names={r[0] for r in db.execute("SELECT segment_name FROM batches").fetchall()}
        disk={p.name for p in self.segments.glob("*.sqlite")}
        return {"ready":True,"schema":SCHEMA,"assets":int(meta.get("asset_total",0)),"events":int(meta.get("event_total",0)),"batches":batches,"event_head":meta.get("event_head",ZERO_HASH),"batch_head":meta.get("batch_head",ZERO_HASH),"orphan_segments":sorted(disk-names),"immutable_segment_publication":True,"signed_batch_chain":True,"continuous_cross_segment_event_chain":True,"registration_is_not_ownership":True}
