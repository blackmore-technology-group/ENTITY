from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import hashlib, json, sqlite3, time, uuid

PROVENANCE_STATES={"RECORDED","HARD_BINDING_VERIFIED","C2PA_VERIFIED","SOFT_BINDING_MATCH"}
TRUTH_STATES={"NOT_ASSESSED","CONTESTED","EXTERNALLY_CORROBORATED"}
EVIDENCE_ORIGINS={"DIRECT_OBSERVATION","ENTITY_ASSERTION","COUNTERPARTY_ATTESTATION","EXTERNAL_AUTHORITATIVE_RECORD","DERIVED_INFERENCE","UNKNOWN"}
DERIVATIONS={"crop","resize","transcode","edit","composite","excerpt","translation","model_output","other"}

def _now(): return int(time.time()*1000)

def _sha256_hex(value: str) -> str:
    value=str(value or "").lower()
    if len(value)!=64 or any(c not in "0123456789abcdef" for c in value): raise ValueError("value must be SHA-256 hex")
    return value

class AssetProvenanceGraph:
    """Signed provenance/lineage graph; provenance validity never implies truth or legal rights."""
    def __init__(self,state_dir: str|Path,identity):
        self.root=Path(state_dir)/"asset_provenance"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"asset_provenance.sqlite"; self.identity=identity; self._lock=RLock(); self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS bindings(asset_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,content_sha256 TEXT NOT NULL,soft_binding_type TEXT,soft_binding_value TEXT,c2pa_manifest_sha256 TEXT,c2pa_reference TEXT,provenance_status TEXT NOT NULL,truth_status TEXT NOT NULL,evidence_origin TEXT NOT NULL,recorded_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS derivations(derivation_id TEXT PRIMARY KEY,parent_asset_id TEXT NOT NULL,child_asset_id TEXT NOT NULL,relation TEXT NOT NULL,metadata_json TEXT NOT NULL,evidence_origin TEXT NOT NULL,created_at_ms INTEGER NOT NULL,actor_entity_id TEXT NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_deriv_parent ON derivations(parent_asset_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_deriv_child ON derivations(child_asset_id)")
            db.execute("CREATE TABLE IF NOT EXISTS c2pa_verifications(verification_id TEXT PRIMARY KEY,asset_id TEXT NOT NULL,controller_entity_id TEXT NOT NULL,file_sha256 TEXT NOT NULL,active_manifest TEXT,report_sha256 TEXT,validation_state TEXT NOT NULL,provenance_verified INTEGER NOT NULL,signer_trust TEXT NOT NULL,truth_status TEXT NOT NULL,evidence_origin TEXT NOT NULL,result_json TEXT NOT NULL,recorded_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
    def register_binding(self,controller_entity_id: str,asset_id: str,content_sha256: str,*,soft_binding_type: str|None=None,soft_binding_value: str|None=None,c2pa_manifest_sha256: str|None=None,c2pa_reference: str|None=None,evidence_origin: str="DIRECT_OBSERVATION") -> dict:
        digest=_sha256_hex(content_sha256); origin=str(evidence_origin or "UNKNOWN").upper()
        if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
        c2pa_digest=_sha256_hex(c2pa_manifest_sha256) if c2pa_manifest_sha256 else None
        now=_now(); body={"schema":"entity-provenance-binding-v2","asset_id":str(asset_id),"controller_entity_id":controller_entity_id,"content_sha256":digest,"soft_binding_type":soft_binding_type,"soft_binding_value":soft_binding_value,"c2pa_manifest_sha256":c2pa_digest,"c2pa_reference":c2pa_reference,"provenance_status":"RECORDED","truth_status":"NOT_ASSESSED","evidence_origin":origin,"recorded_at_ms":now}
        sig=self.identity.sign(controller_entity_id,body)
        with self._lock,self._connect() as db:
            db.execute("INSERT OR REPLACE INTO bindings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(body["asset_id"],controller_entity_id,digest,soft_binding_type,soft_binding_value,c2pa_digest,c2pa_reference,"RECORDED","NOT_ASSESSED",origin,now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def register_bindings_batch(self,controller_entity_id:str,bindings:list[dict])->list[dict]:
        """Register many individually signed provenance bindings in one transaction."""
        items=list(bindings or [])
        if not items: return []
        sign=self.identity.open_signing_session(controller_entity_id)
        rows=[]; out=[]
        for item in items:
            digest=_sha256_hex(item.get("content_sha256")); origin=str(item.get("evidence_origin") or "DIRECT_OBSERVATION").upper()
            if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
            c2pa=_sha256_hex(item.get("c2pa_manifest_sha256")) if item.get("c2pa_manifest_sha256") else None
            now=_now(); body={"schema":"entity-provenance-binding-v2","asset_id":str(item["asset_id"]),"controller_entity_id":controller_entity_id,"content_sha256":digest,"soft_binding_type":item.get("soft_binding_type"),"soft_binding_value":item.get("soft_binding_value"),"c2pa_manifest_sha256":c2pa,"c2pa_reference":item.get("c2pa_reference"),"provenance_status":"RECORDED","truth_status":"NOT_ASSESSED","evidence_origin":origin,"recorded_at_ms":now}
            sig=sign(body); rows.append((body["asset_id"],controller_entity_id,digest,body["soft_binding_type"],body["soft_binding_value"],c2pa,body["c2pa_reference"],"RECORDED","NOT_ASSESSED",origin,now,json.dumps(sig,sort_keys=True))); out.append(dict(body,signature=sig))
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.executemany("INSERT OR REPLACE INTO bindings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",rows)
        return out

    def verify_hard_binding(self,asset_id: str,observed_sha256: str) -> dict:
        observed=_sha256_hex(observed_sha256)
        with self._connect() as db:
            row=db.execute("SELECT * FROM bindings WHERE asset_id=?",(str(asset_id),)).fetchone()
            if not row: raise KeyError("provenance binding not found")
            matched=observed==row["content_sha256"]
            if matched: db.execute("UPDATE bindings SET provenance_status='HARD_BINDING_VERIFIED' WHERE asset_id=?",(str(asset_id),))
        return {"asset_id":str(asset_id),"hard_binding_match":matched,"provenance_status":"HARD_BINDING_VERIFIED" if matched else row["provenance_status"],"truth_status":row["truth_status"],"rights_verified":False}
    def apply_c2pa_verification(self,asset_id: str,result: dict) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM bindings WHERE asset_id=?",(str(asset_id),)).fetchone()
        if not row: raise KeyError("provenance binding not found")
        file_sha=_sha256_hex(result.get("file_sha256"))
        if file_sha!=str(row["content_sha256"]).lower(): raise ValueError("C2PA verification file hash does not match asset hard binding")
        verified=bool(result.get("provenance_verified")); now=_now(); verification_id="c2pav1-"+uuid.uuid4().hex
        truth=str(result.get("truth_status") or "NOT_ASSESSED").upper()
        if truth not in TRUTH_STATES: raise ValueError("invalid truth_status")
        body={"schema":"entity-c2pa-verification-v2","verification_id":verification_id,"asset_id":str(asset_id),"controller_entity_id":row["controller_entity_id"],"file_sha256":file_sha,"active_manifest":result.get("active_manifest"),"report_sha256":result.get("report_sha256"),"validation_state":str(result.get("validation_state") or "UNKNOWN"),"provenance_verified":verified,"signer_trust":str(result.get("signer_trust") or "NOT_ASSESSED"),"truth_status":truth,"truth_verified":False,"rights_verified":False,"evidence_origin":"DIRECT_OBSERVATION","recorded_at_ms":now}
        sig=self.identity.sign(row["controller_entity_id"],body)
        with self._lock,self._connect() as db:
            db.execute("INSERT INTO c2pa_verifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(verification_id,str(asset_id),row["controller_entity_id"],file_sha,body["active_manifest"],body["report_sha256"],body["validation_state"],1 if verified else 0,body["signer_trust"],truth,"DIRECT_OBSERVATION",json.dumps(result,sort_keys=True),now,json.dumps(sig,sort_keys=True)))
            if verified: db.execute("UPDATE bindings SET provenance_status='C2PA_VERIFIED',c2pa_manifest_sha256=?,c2pa_reference=? WHERE asset_id=?",(body["report_sha256"],body["active_manifest"],str(asset_id)))
        return dict(body,signature=sig,provenance_status="C2PA_VERIFIED" if verified else row["provenance_status"])
    def add_derivation(self,actor_entity_id: str,parent_asset_id: str,child_asset_id: str,relation: str,metadata: dict|None=None,evidence_origin: str="ENTITY_ASSERTION") -> dict:
        rel=str(relation or "other").lower(); origin=str(evidence_origin or "UNKNOWN").upper()
        if rel not in DERIVATIONS: raise ValueError("unsupported derivation relation")
        if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
        now=_now(); derivation_id="drv1-"+uuid.uuid4().hex
        body={"schema":"entity-provenance-derivation-v2","derivation_id":derivation_id,"parent_asset_id":str(parent_asset_id),"child_asset_id":str(child_asset_id),"relation":rel,"metadata":dict(metadata or {}),"evidence_origin":origin,"created_at_ms":now,"actor_entity_id":actor_entity_id}
        sig=self.identity.sign(actor_entity_id,body)
        with self._lock,self._connect() as db:
            db.execute("INSERT INTO derivations VALUES(?,?,?,?,?,?,?,?,?)",(derivation_id,str(parent_asset_id),str(child_asset_id),rel,json.dumps(body["metadata"],sort_keys=True),origin,now,actor_entity_id,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def lineage(self,asset_id: str) -> dict:
        with self._connect() as db:
            binding=db.execute("SELECT * FROM bindings WHERE asset_id=?",(str(asset_id),)).fetchone()
            parents=db.execute("SELECT * FROM derivations WHERE child_asset_id=? ORDER BY created_at_ms",(str(asset_id),)).fetchall()
            children=db.execute("SELECT * FROM derivations WHERE parent_asset_id=? ORDER BY created_at_ms",(str(asset_id),)).fetchall()
        return {"asset_id":str(asset_id),"binding":dict(binding) if binding else None,"parents":[dict(x) for x in parents],"children":[dict(x) for x in children],"provenance_is_not_truth":True,"provenance_is_not_rights":True}
    def verify_binding_signature(self,asset_id: str) -> bool:
        with self._connect() as db: row=db.execute("SELECT * FROM bindings WHERE asset_id=?",(str(asset_id),)).fetchone()
        if not row: return False
        body={"schema":"entity-provenance-binding-v2","asset_id":row["asset_id"],"controller_entity_id":row["controller_entity_id"],"content_sha256":row["content_sha256"],"soft_binding_type":row["soft_binding_type"],"soft_binding_value":row["soft_binding_value"],"c2pa_manifest_sha256":row["c2pa_manifest_sha256"],"c2pa_reference":row["c2pa_reference"],"provenance_status":"RECORDED","truth_status":"NOT_ASSESSED","evidence_origin":row["evidence_origin"],"recorded_at_ms":row["recorded_at_ms"]}
        sig=json.loads(row["signature_json"]); manifest=self.identity.load_manifest(row["controller_entity_id"])
        return bool(self.identity.verify_signature(manifest,body,sig))

    def status(self) -> dict:
        with self._connect() as db:
            bindings=db.execute("SELECT COUNT(*) FROM bindings").fetchone()[0]
            derivations=db.execute("SELECT COUNT(*) FROM derivations").fetchone()[0]
            c2pa=db.execute("SELECT COUNT(*) FROM c2pa_verifications").fetchone()[0]
        return {"ready":True,"schema":"entity-asset-provenance-v2","bindings":int(bindings),"derivations":int(derivations),"c2pa_verifications":int(c2pa),"provenance_truth_separation":True,"provenance_rights_separation":True,"evidence_origin_preserved":True}
