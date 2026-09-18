from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib, json, sqlite3, time

ZERO_HASH = "0" * 64

def _canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _sha(v):
    return hashlib.sha256(v if isinstance(v, (bytes, bytearray)) else _canon(v)).hexdigest()

def _id(prefix: str, run_id: str, index: int) -> str:
    return prefix + hashlib.sha256(f"{run_id}:{index}".encode()).hexdigest()[:32]

@contextmanager
def _db(path: Path):
    db = sqlite3.connect(path, timeout=120)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
class CanonicalBulkAssetIngestor:
    """Resumable high-throughput adapter over canonical ENTITY record schemas.

    Batches preserve per-record signatures and the canonical event-ledger hash chain.
    Cross-database completion is recovered by deterministic ids plus phase receipts.
    """
    def __init__(self, state_dir, identity, asset_registry, ledger, rights_graph, provenance):
        self.state = Path(state_dir)
        self.identity = identity
        self.assets = asset_registry
        self.ledger = ledger
        self.rights = rights_graph
        self.provenance = provenance
        self.root = self.state / "bulk_ingest"
        self.root.mkdir(parents=True, exist_ok=True)
        self.receipts = self.root / "bulk_ingest.sqlite"
        with _db(self.receipts) as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,target_assets INTEGER NOT NULL,target_extra_events INTEGER NOT NULL,base_ms INTEGER NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS batches(run_id TEXT NOT NULL,start_index INTEGER NOT NULL,item_count INTEGER NOT NULL,phase TEXT NOT NULL,first_asset_id TEXT,last_asset_id TEXT,first_event_hash TEXT,last_event_hash TEXT,updated_at_ms INTEGER NOT NULL,PRIMARY KEY(run_id,start_index))")

    def _run(self, run_id, controller, target_assets, target_extra_events):
        now = int(time.time() * 1000)
        with _db(self.receipts) as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row:
                if row["controller_entity_id"] != controller or int(row["target_assets"]) != int(target_assets) or int(row["target_extra_events"]) != int(target_extra_events):
                    raise ValueError("run_id already exists with different parameters")
                return dict(row)
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)", (run_id, controller, int(target_assets), int(target_extra_events), now, "ACTIVE", now, now))
            return dict(db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
    def _batch_phase(self, run_id, start):
        with _db(self.receipts) as db:
            row = db.execute("SELECT * FROM batches WHERE run_id=? AND start_index=?", (run_id, int(start))).fetchone()
            return dict(row) if row else None

    def _mark_batch(self, run_id, start, count, phase, first_asset_id=None, last_asset_id=None, first_event_hash=None, last_event_hash=None):
        now = int(time.time() * 1000)
        with _db(self.receipts) as db:
            db.execute("INSERT INTO batches(run_id,start_index,item_count,phase,first_asset_id,last_asset_id,first_event_hash,last_event_hash,updated_at_ms) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id,start_index) DO UPDATE SET item_count=excluded.item_count,phase=excluded.phase,first_asset_id=COALESCE(excluded.first_asset_id,batches.first_asset_id),last_asset_id=COALESCE(excluded.last_asset_id,batches.last_asset_id),first_event_hash=COALESCE(excluded.first_event_hash,batches.first_event_hash),last_event_hash=COALESCE(excluded.last_event_hash,batches.last_event_hash),updated_at_ms=excluded.updated_at_ms", (run_id,int(start),int(count),phase,first_asset_id,last_asset_id,first_event_hash,last_event_hash,now))

    def _asset_rows(self, run_id, controller, start, count, base_ms):
        rows=[]
        for idx in range(start, start+count):
            asset_id=_id("asset1-",run_id,idx)
            digest=hashlib.sha256(f"{run_id}:asset-content:{idx}".encode()).hexdigest()
            ts=base_ms+idx
            meta=json.dumps({"bulk_run_id":run_id,"bulk_index":idx},sort_keys=True)
            rows.append((asset_id,controller,digest,idx+1,"application/octet-stream",f"Scale Asset {idx}","PRIVATE","ACTIVE",meta,ts,ts))
        return rows

    def _insert_assets(self, rows):
        with _db(self.assets.path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT OR IGNORE INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",rows)
    def _append_asset_events(self, run_id, controller, rows, start, base_ms, sign):
        count=len(rows); lo=base_ms+start; hi=lo+count-1; etype="asset.bulk_registered"
        with _db(self.ledger.path) as db:
            db.execute("BEGIN IMMEDIATE")
            existing=int(db.execute("SELECT COUNT(*) FROM events WHERE event_type=? AND actor_entity_id=? AND timestamp_ms BETWEEN ? AND ?",(etype,controller,lo,hi)).fetchone()[0])
            if existing:
                if existing!=count: raise RuntimeError("partial canonical ledger batch detected")
                first=db.execute("SELECT event_hash FROM events WHERE event_type=? AND actor_entity_id=? AND timestamp_ms BETWEEN ? AND ? ORDER BY sequence LIMIT 1",(etype,controller,lo,hi)).fetchone()[0]
                last=db.execute("SELECT event_hash FROM events WHERE event_type=? AND actor_entity_id=? AND timestamp_ms BETWEEN ? AND ? ORDER BY sequence DESC LIMIT 1",(etype,controller,lo,hi)).fetchone()[0]
                return first,last
            prior=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]
            out=[]; first_hash=None
            for off,row in enumerate(rows):
                idx=start+off; asset_id=row[0]; digest=row[2]; ts=base_ms+idx
                payload={"asset_id":asset_id,"content_sha256":digest,"controller_entity_id":controller,"registration_not_ownership":True,"bulk_run_id":run_id}
                payload_hash=_sha(payload); event_id=_id("evt1-",run_id,idx)
                body={"schema":"ENTITY-EVENT-v1","event_id":event_id,"event_type":etype,"actor_entity_id":controller,"subject_ids":[controller],"object_ids":[asset_id],"payload_hash":payload_hash,"evidence_origin":"DIRECT_OBSERVATION","confidence":1.0,"timestamp_ms":ts,"prior_hash":prior}
                sig=sign(body); event_hash=_sha({"body":body,"signature":sig})
                if first_hash is None: first_hash=event_hash
                out.append((event_id,etype,controller,json.dumps([controller]),json.dumps([asset_id]),payload_hash,"DIRECT_OBSERVATION",1.0,ts,prior,event_hash,json.dumps(sig,sort_keys=True),"ENTITY-EVENT-v1",payload_hash))
                prior=event_hash
            db.executemany("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version,payload_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",out)
            db.execute("UPDATE meta SET v=? WHERE k='head_hash'",(prior,))
            return first_hash,prior
    def _insert_rights(self, run_id, controller, rows, start, base_ms, sign):
        claim_rows=[]; event_rows=[]; basis=f"bulk_scale_registration:{run_id}"
        for off,row in enumerate(rows):
            idx=start+off; asset_id=row[0]; digest=row[2]; ts=base_ms+idx
            claim_id=_id("claim1-",run_id,idx)
            scope={"control_of_entity_record":True}; evidence={"content_sha256":digest,"bulk_run_id":run_id}
            body={"schema":"entity-rights-claim-v2","claim_id":claim_id,"asset_id":asset_id,"claimant_entity_id":controller,"right_type":"DATA_CONTROLLER","share":{"numerator":1,"denominator":1},"territory":"unspecified","jurisdiction":"unspecified","legal_basis":basis,"scope":scope,"evidence":evidence,"evidence_origin":"ENTITY_ASSERTION","effective_at_ms":ts,"expires_at_ms":None,"verification_level":"SELF_ASSERTED","lifecycle_status":"ACTIVE","supersedes_claim_id":None}
            sig=sign(body)
            claim_rows.append((claim_id,asset_id,controller,"DATA_CONTROLLER",1,1,"unspecified","unspecified",basis,json.dumps(scope,sort_keys=True),json.dumps(evidence,sort_keys=True),"ENTITY_ASSERTION",ts,None,"SELF_ASSERTED","ACTIVE",None,json.dumps(sig,sort_keys=True),ts,ts))
            payload={"right_type":"DATA_CONTROLLER","verification_level":"SELF_ASSERTED","evidence_origin":"ENTITY_ASSERTION"}
            event_body={"claim_id":claim_id,"event_type":"claim.asserted","actor_entity_id":controller,"payload":payload,"timestamp_ms":ts}
            event_sig=sign(event_body); event_id=_id("evt1-claim-",run_id,idx)
            event_rows.append((event_id,claim_id,"claim.asserted",controller,json.dumps(payload,sort_keys=True),json.dumps(event_sig,sort_keys=True),ts))
        with _db(self.rights.path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",claim_rows)
            db.executemany("INSERT OR IGNORE INTO claim_events(event_id,claim_id,event_type,actor_entity_id,payload_json,signature_json,timestamp_ms) VALUES(?,?,?,?,?,?,?)",event_rows)

    def _insert_provenance(self, run_id, controller, rows, start, base_ms, sign):
        out=[]
        for off,row in enumerate(rows):
            idx=start+off; asset_id=row[0]; digest=row[2]; ts=base_ms+idx
            body={"schema":"entity-provenance-binding-v2","asset_id":asset_id,"controller_entity_id":controller,"content_sha256":digest,"soft_binding_type":None,"soft_binding_value":None,"c2pa_manifest_sha256":None,"c2pa_reference":None,"provenance_status":"RECORDED","truth_status":"NOT_ASSESSED","evidence_origin":"DIRECT_OBSERVATION","recorded_at_ms":ts}
            sig=sign(body)
            out.append((asset_id,controller,digest,None,None,None,None,"RECORDED","NOT_ASSESSED","DIRECT_OBSERVATION",ts,json.dumps(sig,sort_keys=True)))
        with _db(self.provenance.path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT OR IGNORE INTO bindings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",out)
    def ingest_generated_assets(self, controller, *, count, run_id, batch_size=5000, target_extra_events=0):
        run=self._run(run_id,controller,count,target_extra_events); base_ms=int(run["base_ms"])
        self.identity.load_manifest(controller); sign=self.identity.open_signing_session(controller)
        started=time.perf_counter(); completed=0
        for start in range(0,int(count),int(batch_size)):
            n=min(int(batch_size),int(count)-start); prior=self._batch_phase(run_id,start)
            if prior and prior.get("phase")=="COMPLETE": completed+=n; continue
            rows=self._asset_rows(run_id,controller,start,n,base_ms)
            self._insert_assets(rows); self._mark_batch(run_id,start,n,"ASSETS",rows[0][0],rows[-1][0])
            first_hash,last_hash=self._append_asset_events(run_id,controller,rows,start,base_ms,sign)
            self._mark_batch(run_id,start,n,"LEDGER",rows[0][0],rows[-1][0],first_hash,last_hash)
            self._insert_rights(run_id,controller,rows,start,base_ms,sign); self._mark_batch(run_id,start,n,"RIGHTS")
            self._insert_provenance(run_id,controller,rows,start,base_ms,sign); self._mark_batch(run_id,start,n,"COMPLETE")
            completed+=n
        elapsed=time.perf_counter()-started
        return {"run_id":run_id,"assets_completed":completed,"seconds":elapsed,"per_second":completed/elapsed if elapsed else None}

    def append_generated_events(self, controller, *, count, run_id, start_index, base_ms, batch_size=10000):
        sign=self.identity.open_signing_session(controller); started=time.perf_counter(); written=0
        for start in range(int(start_index),int(start_index)+int(count),int(batch_size)):
            n=min(int(batch_size),int(start_index)+int(count)-start)
            lo=base_ms+start; hi=lo+n-1; etype="scale.synthetic_observed"
            with _db(self.ledger.path) as db:
                db.execute("BEGIN IMMEDIATE")
                existing=int(db.execute("SELECT COUNT(*) FROM events WHERE event_type=? AND actor_entity_id=? AND timestamp_ms BETWEEN ? AND ?",(etype,controller,lo,hi)).fetchone()[0])
                if existing==n: written+=n; continue
                if existing: raise RuntimeError("partial synthetic event batch detected")
                prior=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]; out=[]
                for idx in range(start,start+n):
                    ts=base_ms+idx; payload_hash=hashlib.sha256(f"{run_id}:event-payload:{idx}".encode()).hexdigest(); event_id=_id("evt1-extra-",run_id,idx)
                    body={"schema":"ENTITY-EVENT-v1","event_id":event_id,"event_type":etype,"actor_entity_id":controller,"subject_ids":[controller],"object_ids":[],"payload_hash":payload_hash,"evidence_origin":"DIRECT_OBSERVATION","confidence":1.0,"timestamp_ms":ts,"prior_hash":prior}
                    sig=sign(body); event_hash=_sha({"body":body,"signature":sig}); out.append((event_id,etype,controller,json.dumps([controller]),"[]",payload_hash,"DIRECT_OBSERVATION",1.0,ts,prior,event_hash,json.dumps(sig,sort_keys=True),"ENTITY-EVENT-v1",payload_hash)); prior=event_hash
                db.executemany("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version,payload_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",out); db.execute("UPDATE meta SET v=? WHERE k='head_hash'",(prior,)); written+=n
        elapsed=time.perf_counter()-started
        return {"events_completed":written,"seconds":elapsed,"per_second":written/elapsed if elapsed else None}
