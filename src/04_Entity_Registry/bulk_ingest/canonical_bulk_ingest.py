from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from typing import Iterable
import hashlib, json, sqlite3, time

ZERO_HASH = "0" * 64
SCHEMA = "entity-bulk-ingest-v1"


def _now() -> int:
    return int(time.time() * 1000)


def _canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value) -> str:
    return hashlib.sha256(value if isinstance(value, (bytes, bytearray)) else _canon(value)).hexdigest()


def _merkle(leaves: list[str]) -> str:
    if not leaves:
        return ZERO_HASH
    layer = [bytes.fromhex(x) for x in leaves]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()


class CanonicalBulkIngestStore:
    """High-volume asset/event ingestion with signed batch attestations.

    This is additive to the ordinary per-record registries. A batch proves the
    integrity and controller attestation of the ingested records; it does not
    manufacture legal ownership, verified rights, or external truth.
    """

    def __init__(self, root: str | Path, identity, controller_entity_id: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "bulk_ingest.sqlite"
        self.identity = identity
        self.controller_entity_id = str(controller_entity_id)
        self.identity.load_manifest(self.controller_entity_id)
        self.sign = self.identity.open_signing_session(self.controller_entity_id)
        self._init_db()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=120)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA temp_store=MEMORY")
            db.execute("CREATE TABLE IF NOT EXISTS assets(asset_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,content_sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,media_type TEXT NOT NULL,title TEXT NOT NULL,classification TEXT NOT NULL,metadata_sha256 TEXT NOT NULL,record_sha256 TEXT NOT NULL,batch_id TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,asset_id TEXT NOT NULL,payload_sha256 TEXT NOT NULL,prior_hash TEXT NOT NULL,event_hash TEXT NOT NULL,batch_id TEXT NOT NULL,timestamp_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS batches(batch_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,asset_count INTEGER NOT NULL,event_count INTEGER NOT NULL,asset_merkle_root TEXT NOT NULL,start_prior_event_hash TEXT NOT NULL,end_event_hash TEXT NOT NULL,prior_batch_hash TEXT NOT NULL,batch_hash TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('event_head',?)", (ZERO_HASH,))
            db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('batch_head',?)", (ZERO_HASH,))
            db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('asset_total','0')")
            db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('event_total','0')")

    @staticmethod
    def _validate_digest(value: str) -> str:
        digest = str(value or "").lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("content_sha256 must be SHA-256 hex")
        return digest

    def _asset_row(self, ordinal: int, batch_id: str, item: dict, now: int):
        digest = self._validate_digest(item.get("content_sha256"))
        metadata = dict(item.get("metadata") or {})
        metadata_sha = _sha(metadata)
        asset_id = "assetb1-" + hashlib.sha256(f"{self.controller_entity_id}|{batch_id}|{ordinal}|{digest}".encode()).hexdigest()
        body = {
            "schema": "entity-bulk-asset-v1",
            "asset_id": asset_id,
            "controller_entity_id": self.controller_entity_id,
            "content_sha256": digest,
            "size_bytes": max(0, int(item.get("size_bytes") or 0)),
            "media_type": str(item.get("media_type") or "application/octet-stream")[:128],
            "title": str(item.get("title") or "")[:512],
            "classification": str(item.get("classification") or "PRIVATE").upper()[:32],
            "metadata_sha256": metadata_sha,
            "batch_id": batch_id,
            "created_at_ms": now,
            "registration_not_ownership": True,
        }
        record_sha = _sha(body)
        row = (asset_id, self.controller_entity_id, digest, body["size_bytes"], body["media_type"], body["title"], body["classification"], metadata_sha, record_sha, batch_id, now)
        return body, row, record_sha

    @staticmethod
    def _event_body(event_id: str, event_type: str, actor: str, asset_id: str, payload_sha: str, prior_hash: str, batch_id: str, now: int):
        return {"schema": "ENTITY-BULK-EVENT-v1", "event_id": event_id, "event_type": event_type, "actor_entity_id": actor, "asset_id": asset_id, "payload_sha256": payload_sha, "prior_hash": prior_hash, "batch_id": batch_id, "timestamp_ms": now}

    def ingest_assets(self, records: Iterable[dict], *, batch_id: str) -> dict:
        batch_id = str(batch_id or "").strip()
        if not batch_id:
            raise ValueError("batch_id required")
        now = _now(); asset_rows=[]; event_rows=[]; leaves=[]
        with self._connect() as db:
            if db.execute("SELECT 1 FROM batches WHERE batch_id=?", (batch_id,)).fetchone():
                raise ValueError("batch_id already exists")
            prior_event = db.execute("SELECT v FROM meta WHERE k='event_head'").fetchone()[0]
            prior_batch = db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
        start_prior = prior_event
        for ordinal, item in enumerate(records):
            body, row, record_sha = self._asset_row(ordinal, batch_id, dict(item), now)
            asset_rows.append(row); leaves.append(record_sha)
            asset_id = body["asset_id"]
            for suffix, event_type, payload in (
                ("r", "asset.registered", {"asset_id": asset_id, "content_sha256": body["content_sha256"], "registration_not_ownership": True}),
                ("p", "provenance.recorded", {"asset_id": asset_id, "content_sha256": body["content_sha256"], "truth_not_inferred": True}),
                ("c", "controller.claimed", {"asset_id": asset_id, "right_type": "DATA_CONTROLLER", "legal_truth_not_inferred": True}),
            ):
                event_id = f"evtb1-{batch_id}-{ordinal}-{suffix}"
                payload_sha = _sha(payload)
                ev_body = self._event_body(event_id,event_type,self.controller_entity_id,asset_id,payload_sha,prior_event,batch_id,now)
                event_hash = _sha(ev_body); prior_event = event_hash
                event_rows.append((event_id,event_type,self.controller_entity_id,asset_id,payload_sha,ev_body["prior_hash"],event_hash,batch_id,now))
        if not asset_rows:
            raise ValueError("batch must contain at least one asset")
        asset_root = _merkle(leaves)
        batch_body = {
            "schema": "entity-bulk-ingest-batch-v1",
            "batch_id": batch_id,
            "controller_entity_id": self.controller_entity_id,
            "asset_count": len(asset_rows),
            "event_count": len(event_rows),
            "asset_merkle_root": asset_root,
            "start_prior_event_hash": start_prior,
            "end_event_hash": prior_event,
            "prior_batch_hash": prior_batch,
            "created_at_ms": now,
            "registration_not_ownership": True,
            "batch_attestation_not_legal_truth": True,
        }
        signature = self.sign(batch_body)
        batch_hash = _sha({"body": batch_body, "signature": signature})
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current_event = db.execute("SELECT v FROM meta WHERE k='event_head'").fetchone()[0]
            current_batch = db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
            if current_event != start_prior or current_batch != prior_batch:
                raise RuntimeError("bulk ingest head changed concurrently")
            db.executemany("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)", asset_rows)
            db.executemany("INSERT INTO events(event_id,event_type,actor_entity_id,asset_id,payload_sha256,prior_hash,event_hash,batch_id,timestamp_ms) VALUES(?,?,?,?,?,?,?,?,?)", event_rows)
            db.execute("INSERT INTO batches VALUES(?,?,?,?,?,?,?,?,?,?,?)", (batch_id,self.controller_entity_id,len(asset_rows),len(event_rows),asset_root,start_prior,prior_event,prior_batch,batch_hash,json.dumps(signature,sort_keys=True),now))
            db.execute("UPDATE meta SET v=? WHERE k='event_head'", (prior_event,))
            db.execute("UPDATE meta SET v=? WHERE k='batch_head'", (batch_hash,))
            db.execute("UPDATE meta SET v=CAST(CAST(v AS INTEGER)+? AS TEXT) WHERE k='asset_total'", (len(asset_rows),))
            db.execute("UPDATE meta SET v=CAST(CAST(v AS INTEGER)+? AS TEXT) WHERE k='event_total'", (len(event_rows),))
        return {**batch_body, "batch_hash": batch_hash, "signature": signature}

    def verify_batch(self, batch_id: str, *, verify_rows: bool = True) -> dict:
        with self._connect() as db:
            batch = db.execute("SELECT * FROM batches WHERE batch_id=?", (str(batch_id),)).fetchone()
            if not batch:
                raise KeyError("batch not found")
            assets = db.execute("SELECT record_sha256 FROM assets WHERE batch_id=? ORDER BY rowid", (str(batch_id),)).fetchall() if verify_rows else []
            events = db.execute("SELECT * FROM events WHERE batch_id=? ORDER BY sequence", (str(batch_id),)).fetchall() if verify_rows else []
        body = {"schema":"entity-bulk-ingest-batch-v1","batch_id":batch["batch_id"],"controller_entity_id":batch["controller_entity_id"],"asset_count":batch["asset_count"],"event_count":batch["event_count"],"asset_merkle_root":batch["asset_merkle_root"],"start_prior_event_hash":batch["start_prior_event_hash"],"end_event_hash":batch["end_event_hash"],"prior_batch_hash":batch["prior_batch_hash"],"created_at_ms":batch["created_at_ms"],"registration_not_ownership":True,"batch_attestation_not_legal_truth":True}
        sig = json.loads(batch["signature_json"])
        manifest = self.identity.load_manifest(batch["controller_entity_id"])
        signature_ok = bool(self.identity.verify_signature(manifest, body, sig))
        batch_hash_ok = _sha({"body":body,"signature":sig}) == batch["batch_hash"]
        row_ok = True; event_ok = True
        if verify_rows:
            row_ok = len(assets) == batch["asset_count"] and _merkle([r[0] for r in assets]) == batch["asset_merkle_root"]
            prior = batch["start_prior_event_hash"]
            for row in events:
                ev_body = self._event_body(row["event_id"],row["event_type"],row["actor_entity_id"],row["asset_id"],row["payload_sha256"],row["prior_hash"],row["batch_id"],row["timestamp_ms"])
                if row["prior_hash"] != prior or _sha(ev_body) != row["event_hash"]:
                    event_ok = False; break
                prior = row["event_hash"]
            event_ok = event_ok and len(events) == batch["event_count"] and prior == batch["end_event_hash"]
        return {"pass":bool(signature_ok and batch_hash_ok and row_ok and event_ok),"batch_id":str(batch_id),"signature_ok":signature_ok,"batch_hash_ok":batch_hash_ok,"asset_rows_ok":row_ok,"event_chain_ok":event_ok,"asset_count":int(batch["asset_count"]),"event_count":int(batch["event_count"])}

    def verify_all_batches(self, *, verify_rows: bool = False) -> dict:
        with self._connect() as db:
            rows = db.execute("SELECT batch_id,prior_batch_hash,batch_hash FROM batches ORDER BY rowid").fetchall()
        prior = ZERO_HASH; checked = 0
        for row in rows:
            if row["prior_batch_hash"] != prior:
                return {"pass":False,"reason":"batch_chain_failure","batch_id":row["batch_id"],"checked":checked}
            result = self.verify_batch(row["batch_id"], verify_rows=verify_rows)
            if not result["pass"]:
                return {"pass":False,"reason":"batch_verification_failure","batch_id":row["batch_id"],"details":result,"checked":checked}
            prior = row["batch_hash"]; checked += 1
        with self._connect() as db:
            head = db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
        return {"pass":head==prior,"batches":checked,"batch_head":head,"row_level_verified":bool(verify_rows)}

    def finalize_indexes(self) -> dict:
        with self._connect() as db:
            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_assets_controller ON assets(controller_entity_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_assets_batch ON assets(batch_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_events_batch ON events(batch_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_bulk_events_asset ON events(asset_id)")
        return {"ready":True,"indexes":["idx_bulk_assets_controller","idx_bulk_assets_batch","idx_bulk_events_batch","idx_bulk_events_asset"]}

    def status(self) -> dict:
        with self._connect() as db:
            assets = int(db.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
            events = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            batches = int(db.execute("SELECT COUNT(*) FROM batches").fetchone()[0])
            event_head = db.execute("SELECT v FROM meta WHERE k='event_head'").fetchone()[0]
            batch_head = db.execute("SELECT v FROM meta WHERE k='batch_head'").fetchone()[0]
        return {"ready":True,"schema":SCHEMA,"assets":assets,"events":events,"batches":batches,"event_head":event_head,"batch_head":batch_head,"signed_batch_attestations":True,"append_only_event_hash_chain":True,"registration_is_not_ownership":True,"batch_attestation_is_not_legal_truth":True}
