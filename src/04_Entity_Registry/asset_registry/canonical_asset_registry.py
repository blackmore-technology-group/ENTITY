from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import hashlib, json, sqlite3, time, uuid

def _now(): return int(time.time()*1000)
def _id(): return "asset1-"+uuid.uuid4().hex

class CanonicalAssetRegistry:
    """Controller-owned asset records. Registration never establishes legal ownership."""
    def __init__(self,state_dir:str|Path,identity,ledger=None,rights_graph=None,provenance=None):
        # Preserve the pre-v2 positional ABI: (state, identity, rights_graph, provenance, ledger).
        if ledger is not None and not hasattr(ledger,"append") and rights_graph is not None and hasattr(rights_graph,"register_binding") and provenance is not None and hasattr(provenance,"append"):
            ledger,rights_graph,provenance=provenance,ledger,rights_graph
        self.root=Path(state_dir)/"asset_registry"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"assets.sqlite"; self.identity=identity; self.ledger=ledger
        self.rights_graph=rights_graph; self.provenance=provenance; self._lock=RLock(); self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS assets(asset_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,content_sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,media_type TEXT NOT NULL,title TEXT NOT NULL,classification TEXT NOT NULL,status TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS locators(asset_id TEXT PRIMARY KEY,local_locator TEXT NOT NULL)")
    def register(self,controller_entity_id:str,*,content_sha256:str,size_bytes:int,media_type:str,title:str,classification="PRIVATE",metadata=None,local_locator=None)->dict:
        digest=str(content_sha256).lower()
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): raise ValueError("content_sha256 must be SHA-256 hex")
        self.identity.load_manifest(controller_entity_id)
        asset_id=_id(); now=_now(); meta=dict(metadata or {})
        with self._lock,self._connect() as db:
            db.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",(asset_id,controller_entity_id,digest,max(0,int(size_bytes)),str(media_type)[:128],str(title)[:512],str(classification).upper()[:32],"ACTIVE",json.dumps(meta,sort_keys=True),now,now))
            if local_locator: db.execute("INSERT INTO locators VALUES(?,?)",(asset_id,str(local_locator)))
        event=self.ledger.append(controller_entity_id,"asset.registered",subject_ids=[controller_entity_id],object_ids=[asset_id],payload={"asset_id":asset_id,"content_sha256":digest,"controller_entity_id":controller_entity_id,"registration_not_ownership":True},evidence_origin="DIRECT_OBSERVATION") if self.ledger else None
        control_claim=self.rights_graph.assert_claim(controller_entity_id,asset_id=asset_id,right_type="DATA_CONTROLLER",legal_basis="entity_asset_registration",scope={"control_of_entity_record":True},evidence={"content_sha256":digest}) if self.rights_graph else None
        prov=self.provenance.register_binding(controller_entity_id,asset_id,digest) if self.provenance else None
        return {"asset_id":asset_id,"controller_entity_id":controller_entity_id,"content_sha256":digest,"status":"ACTIVE","state":"ACTIVE","ownership_claimed_not_proven":True,"ownership_not_inferred":True,"rights_control_claim":control_claim,"provenance":prov,"event":event}

    def register_batch(self,controller_entity_id:str,assets:list[dict])->list[dict]:
        """Register many assets with full ledger/rights/provenance semantics using batch-capable canonical stores."""
        items=list(assets or [])
        if not items: return []
        self.identity.load_manifest(controller_entity_id)
        now=_now(); rows=[]; loc_rows=[]; base=[]
        for item in items:
            digest=str(item.get("content_sha256") or "").lower()
            if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): raise ValueError("content_sha256 must be SHA-256 hex")
            asset_id=_id(); meta=dict(item.get("metadata") or {}); classification=str(item.get("classification") or "PRIVATE").upper()[:32]
            rows.append((asset_id,controller_entity_id,digest,max(0,int(item.get("size_bytes") or 0)),str(item.get("media_type") or "application/octet-stream")[:128],str(item.get("title") or asset_id)[:512],classification,"ACTIVE",json.dumps(meta,sort_keys=True),now,now))
            if item.get("local_locator"): loc_rows.append((asset_id,str(item["local_locator"])))
            base.append({"asset_id":asset_id,"controller_entity_id":controller_entity_id,"content_sha256":digest,"status":"ACTIVE","state":"ACTIVE","ownership_claimed_not_proven":True,"ownership_not_inferred":True})
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.executemany("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",rows)
            if loc_rows: db.executemany("INSERT INTO locators VALUES(?,?)",loc_rows)
        events=self.ledger.append_batch(controller_entity_id,[{"event_type":"asset.registered","subject_ids":[controller_entity_id],"object_ids":[x["asset_id"]],"payload":{"asset_id":x["asset_id"],"content_sha256":x["content_sha256"],"controller_entity_id":controller_entity_id,"registration_not_ownership":True},"evidence_origin":"DIRECT_OBSERVATION"} for x in base]) if self.ledger else [None]*len(base)
        claims=self.rights_graph.assert_claims_batch(controller_entity_id,[{"asset_id":x["asset_id"],"right_type":"DATA_CONTROLLER","legal_basis":"entity_asset_registration","scope":{"control_of_entity_record":True},"evidence":{"content_sha256":x["content_sha256"]}} for x in base]) if self.rights_graph else [None]*len(base)
        provs=self.provenance.register_bindings_batch(controller_entity_id,[{"asset_id":x["asset_id"],"content_sha256":x["content_sha256"],"evidence_origin":"DIRECT_OBSERVATION"} for x in base]) if self.provenance else [None]*len(base)
        return [dict(x,event=events[i],rights_control_claim=claims[i],provenance=provs[i]) for i,x in enumerate(base)]

    def get(self,asset_id:str,*,include_private_locator=False)->dict|None:
        with self._connect() as db:
            row=db.execute("SELECT * FROM assets WHERE asset_id=?",(asset_id,)).fetchone()
            if not row: return None
            out=dict(row); out["metadata"]=json.loads(out.pop("metadata_json")); out["owner_semantics"]="controller record only; not legal ownership proof"; out["state"]=out["status"]
            if include_private_locator:
                loc=db.execute("SELECT local_locator FROM locators WHERE asset_id=?",(asset_id,)).fetchone(); out["local_locator"]=loc[0] if loc else None
            return out

    def list_for_controller(self,entity_id:str)->list[dict]:
        with self._connect() as db: rows=db.execute("SELECT asset_id FROM assets WHERE controller_entity_id=? ORDER BY created_at_ms",(entity_id,)).fetchall()
        return [self.get(r[0]) for r in rows]
    def set_state(self,controller_entity_id:str,asset_id:str,state:str,reason:str="owner_action")->dict:
        row=self.get(asset_id)
        if not row: raise KeyError("asset not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("asset controller mismatch")
        target=str(state or "").strip().upper()
        if not target or len(target)>64: raise ValueError("asset state required")
        with self._connect() as db: db.execute("UPDATE assets SET status=?,updated_at_ms=? WHERE asset_id=?",(target,_now(),asset_id))
        event=self.ledger.append(controller_entity_id,"asset.state_changed",subject_ids=[controller_entity_id],object_ids=[asset_id],payload={"asset_id":asset_id,"from_state":row["status"],"to_state":target,"reason":str(reason)[:256],"historical_provenance_preserved":True}) if self.ledger else None
        return {"asset_id":asset_id,"status":target,"state":target,"historical_provenance_preserved":True,"event":event}

    def deactivate(self,controller_entity_id:str,asset_id:str,reason:str="owner_action")->dict:
        row=self.get(asset_id)
        if not row: raise KeyError("asset not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("asset controller mismatch")
        with self._connect() as db: db.execute("UPDATE assets SET status='INACTIVE',updated_at_ms=? WHERE asset_id=?",(_now(),asset_id))
        event=self.ledger.append(controller_entity_id,"asset.deactivated",subject_ids=[controller_entity_id],object_ids=[asset_id],payload={"asset_id":asset_id,"reason":str(reason)[:256],"historical_provenance_preserved":True}) if self.ledger else None
        return {"asset_id":asset_id,"status":"INACTIVE","historical_provenance_preserved":True,"event":event}

    def summary(self,entity_id:str)->dict:
        assets=self.list_for_controller(entity_id)
        active=sum(1 for a in assets if a["status"]=="ACTIVE")
        return {"schema":"entity-asset-summary-v1","entity_id":entity_id,"active_assets":active,"total_assets":len(assets),"ownership_not_inferred":True,"private_locators_exposed":False}

    def status(self)->dict:
        with self._connect() as db: count=db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        return {"ready":True,"schema":"entity-canonical-asset-registry-v1","assets":int(count),"registration_is_not_ownership":True,"private_locators_separated":True}

def niki_project_data_summary_v1(*,entity_id:str)->dict:
    import importlib.util, os
    here=Path(__file__).resolve(); network=here.parents[2]; core=network/"01_Core_Runtime"; state=Path(os.environ.get("ENTITY_CANONICAL_CORE_STATE",str(core/"runtime_state")))
    ipath=core/"identity"/"canonical_identity.py"; spec=importlib.util.spec_from_file_location("entity_asset_identity",ipath); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    registry=CanonicalAssetRegistry(state,mod.EntityIdentityVault(state))
    return registry.summary(str(entity_id))
