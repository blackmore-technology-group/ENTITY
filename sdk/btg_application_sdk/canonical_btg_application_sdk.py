from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib, importlib.util, json, sqlite3, time, uuid

ROOT=Path(__file__).resolve().parents[2] / "src"
SCHEMA="entity-btg-app-ingest-envelope-v1"
EVENT_SCHEMA="entity-btg-app-event-envelope-v1"
ASSET_KINDS={"SOFTWARE","DATA","MODEL","KNOWLEDGE","EVIDENCE"}
ALLOWED_EVENT_PREFIXES=("application.","data.","model.","knowledge.","software.","evidence.")
FORBIDDEN_EVENT_TOKENS=("ownership","licence","license","settlement","payment","capital","authority","consent","rights.verify","commodity")

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod); return mod

def make_asset_envelope(*,application_entity_id,organization_entity_id,content_sha256,size_bytes,media_type,title,asset_kind,classification="PRIVATE",metadata=None,source_subject_ref=None,idempotency_key=None,explicit_rights_claim=None,contributors=None,parent_asset_ids=None):
    return {"schema":SCHEMA,"application_entity_id":str(application_entity_id),"organization_entity_id":str(organization_entity_id),"idempotency_key":str(idempotency_key or uuid.uuid4()),"content_sha256":str(content_sha256).lower(),"size_bytes":int(size_bytes),"media_type":str(media_type),"title":str(title),"asset_kind":str(asset_kind).upper(),"classification":str(classification).upper(),"metadata":dict(metadata or {}),"source_subject_ref":source_subject_ref,"explicit_rights_claim":dict(explicit_rights_claim or {}),"contributors":[dict(x) for x in (contributors or [])],"parent_asset_ids":[str(x) for x in (parent_asset_ids or [])],"raw_content_included":False}

def make_event_envelope(*,application_entity_id,organization_entity_id,event_type,payload_sha256,subject_ids=None,object_ids=None,idempotency_key=None,evidence_origin="DIRECT_OBSERVATION",confidence=1.0):
    return {"schema":EVENT_SCHEMA,"application_entity_id":str(application_entity_id),"organization_entity_id":str(organization_entity_id),"idempotency_key":str(idempotency_key or uuid.uuid4()),"event_type":str(event_type),"payload_sha256":str(payload_sha256).lower(),"subject_ids":[str(x) for x in (subject_ids or [])],"object_ids":[str(x) for x in (object_ids or [])],"evidence_origin":str(evidence_origin),"confidence":float(confidence),"raw_payload_included":False}

class BTGApplicationSDK:
    """Additive application ingestion adapter. It never grants legal truth, ownership, consent or economic authority."""
    def __init__(self,state_dir:str|Path,application_entity_id:str,organization_entity_id:str,*,authorizer=None):
        self.state=Path(state_dir); self.application_entity_id=str(application_entity_id); self.organization_entity_id=str(organization_entity_id)
        self.authorizer=authorizer
        im=_load("btg_sdk_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
        lm=_load("btg_sdk_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
        rm=_load("btg_sdk_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
        pm=_load("btg_sdk_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
        am=_load("btg_sdk_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
        km=_load("btg_sdk_knowledge",ROOT/"04_Entity_Registry"/"canonical_knowledge_capital.py")
        sm=_load("btg_sdk_sovereign",ROOT/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py")
        self.identity=im.EntityIdentityVault(self.state); self.identity.load_manifest(self.application_entity_id); self.identity.load_manifest(self.organization_entity_id)
        self.ledger=lm.CanonicalEventLedger(self.state,self.identity); self.rights=rm.RightsClaimsGraph(self.state,self.identity)
        self.provenance=pm.AssetProvenanceGraph(self.state,self.identity); self.assets=am.CanonicalAssetRegistry(self.state,self.identity,self.ledger,self.rights,self.provenance)
        self.knowledge=km.KnowledgeCapitalRegistry(self.state,self.identity); self.sovereign=sm.SovereignAuthorityRegistry(self.state,self.identity)
        self.root=self.state/"btg_application_sdk"; self.root.mkdir(parents=True,exist_ok=True); self.db_path=self.root/"ingest.sqlite"; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.db_path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS idempotency(idempotency_key TEXT PRIMARY KEY,envelope_sha256 TEXT NOT NULL,result_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")

    @classmethod
    def provision_application(cls,state_dir:str|Path,organization_entity_id:str,display_name:str,alias:str,metadata=None)->dict:
        state=Path(state_dir); alias=str(alias or "").strip().lower()
        if not alias.endswith(".entity") or len(alias)>128: raise ValueError("application alias must end in .entity")
        im=_load("btg_sdk_provision_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
        sm=_load("btg_sdk_provision_sovereign",ROOT/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py")
        identity=im.EntityIdentityVault(state); identity.load_manifest(str(organization_entity_id))
        for item in identity.list_local():
            if alias in {str(x).lower() for x in (item.get("aliases") or [])}:
                if (item.get("metadata") or {}).get("btg_controller_entity_id")!=str(organization_entity_id): raise PermissionError("alias already bound to another controller")
                return {"application_entity_id":item["entity_id"],"alias":alias,"existing":True,"manifest":item}
        meta=dict(metadata or {}); meta.update({"btg_controller_entity_id":str(organization_entity_id),"application_alias":alias,"entity_sdk_profile":"BTG_APPLICATION_SDK_v1","asset_ownership_not_inferred":True})
        manifest=identity.create(str(display_name),"application",aliases=[alias],metadata=meta); app_id=manifest["entity_id"]
        sovereign=sm.SovereignAuthorityRegistry(state,identity)
        relationship=sovereign.grant_relationship(app_id,str(organization_entity_id),"SOVEREIGN_AUTHORITY",scope={"application_control":True,"asset_ownership_not_implied":True,"user_data_ownership_not_implied":True},evidence_origin="ENTITY_ASSERTION",evidence={"profile":"BTG_APPLICATION_SDK_v1"})
        return {"application_entity_id":app_id,"alias":alias,"existing":False,"manifest":manifest,"organization_control_relationship":relationship}

    def _authorize(self,envelope:dict,operation:str):
        if self.authorizer is None: raise PermissionError("application ingest requires explicit authorization")
        decision=self.authorizer(dict(envelope),str(operation))
        allowed=decision.get("allowed") if isinstance(decision,dict) else bool(decision)
        if not allowed: raise PermissionError("application ingest authorization denied")
        return decision if isinstance(decision,dict) else {"allowed":True}

    def _validate_common(self,envelope:dict,schema:str):
        if envelope.get("schema")!=schema: raise ValueError("unsupported application envelope schema")
        if envelope.get("application_entity_id")!=self.application_entity_id: raise PermissionError("application entity mismatch")
        if envelope.get("organization_entity_id")!=self.organization_entity_id: raise PermissionError("organization entity mismatch")
        key=str(envelope.get("idempotency_key") or "").strip()
        if not key or len(key)>256: raise ValueError("idempotency_key required")
        return key

    def _replay_or_none(self,key:str,envelope:dict):
        digest=_sha(envelope)
        with self._connect() as db: row=db.execute("SELECT * FROM idempotency WHERE idempotency_key=?",(key,)).fetchone()
        if not row: return None
        if row["envelope_sha256"]!=digest: raise ValueError("idempotency key reused with different envelope")
        out=json.loads(row["result_json"]); out["idempotent_replay"]=True; return out

    def _remember(self,key:str,envelope:dict,result:dict):
        digest=_sha(envelope)
        with self._connect() as db: db.execute("INSERT INTO idempotency VALUES(?,?,?,?)",(key,digest,json.dumps(result,sort_keys=True,default=str),_now()))

    @staticmethod
    def _validate_digest(value:str):
        digest=str(value or "").lower()
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): raise ValueError("SHA-256 hex required")
        return digest

    def ingest_asset(self,envelope:dict)->dict:
        envelope=dict(envelope or {}); key=self._validate_common(envelope,SCHEMA); replay=self._replay_or_none(key,envelope)
        if replay is not None: return replay
        self._authorize(envelope,"INGEST_ASSET")
        if envelope.get("raw_content_included") is not False: raise ValueError("raw content must not be embedded in ENTITY ingest envelope")
        kind=str(envelope.get("asset_kind") or "").upper()
        if kind not in ASSET_KINDS: raise ValueError("unsupported asset_kind")
        digest=self._validate_digest(envelope.get("content_sha256")); meta=dict(envelope.get("metadata") or {})
        meta.update({"asset_kind":kind,"producer_application_entity_id":self.application_entity_id,"btg_organization_entity_id":self.organization_entity_id,"source_subject_ref":envelope.get("source_subject_ref"),"ownership_not_inferred":True,"raw_content_stored_in_event_ledger":False})
        asset=self.assets.register(self.application_entity_id,content_sha256=digest,size_bytes=int(envelope.get("size_bytes") or 0),media_type=str(envelope.get("media_type") or "application/octet-stream"),title=str(envelope.get("title") or kind),classification=str(envelope.get("classification") or "PRIVATE"),metadata=meta)
        claims=[]; explicit=dict(envelope.get("explicit_rights_claim") or {})
        if explicit:
            if not explicit.get("legal_basis") or not explicit.get("right_type") or not explicit.get("evidence"): raise ValueError("explicit rights claim requires right_type, legal_basis and evidence")
            claims.append(self.rights.assert_claim(self.organization_entity_id,asset_id=asset["asset_id"],right_type=str(explicit["right_type"]),legal_basis=str(explicit["legal_basis"]),scope=dict(explicit.get("scope") or {}),evidence=dict(explicit["evidence"]),evidence_origin=str(explicit.get("evidence_origin") or "ENTITY_ASSERTION")))

        receipt=None
        contributors=[dict(x) for x in (envelope.get("contributors") or [])]
        if contributors:
            receipt=self.knowledge.record(self.application_entity_id,kind=kind,title=str(envelope.get("title") or kind),contributors=contributors,artifact_sha256=digest,metadata={"asset_id":asset["asset_id"],"organization_entity_id":self.organization_entity_id,"ownership_not_inferred":True},evidence_origin="ENTITY_ASSERTION")
        derivations=[]
        relation="model_output" if kind=="MODEL" else "other"
        for parent in envelope.get("parent_asset_ids") or []:
            derivations.append(self.provenance.add_derivation(self.application_entity_id,str(parent),asset["asset_id"],relation,metadata={"producer_application_entity_id":self.application_entity_id,"automatic_sdk_capture":True},evidence_origin="ENTITY_ASSERTION"))
        accepted=self.ledger.append(self.application_entity_id,"application.asset_ingested",subject_ids=[self.application_entity_id,self.organization_entity_id],object_ids=[asset["asset_id"]],payload={"asset_id":asset["asset_id"],"asset_kind":kind,"content_sha256":digest,"source_subject_ref":envelope.get("source_subject_ref"),"explicit_organization_rights_claim_count":len(claims),"registration_not_ownership":True,"economic_value_not_inferred":True},evidence_origin="DIRECT_OBSERVATION")
        result={"schema":"entity-btg-app-ingest-result-v1","application_entity_id":self.application_entity_id,"organization_entity_id":self.organization_entity_id,"asset":asset,"explicit_organization_rights_claims":claims,"knowledge_receipt":receipt,"derivations":derivations,"ingest_event":accepted,"ownership_not_inferred":True,"economic_value_not_inferred":True,"raw_content_stored":False,"idempotent_replay":False}
        self._remember(key,envelope,result); return result

    def record_event(self,envelope:dict)->dict:
        envelope=dict(envelope or {}); key=self._validate_common(envelope,EVENT_SCHEMA); replay=self._replay_or_none(key,envelope)
        if replay is not None: return replay
        self._authorize(envelope,"RECORD_EVENT")
        if envelope.get("raw_payload_included") is not False: raise ValueError("raw event payload must not be embedded")
        event_type=str(envelope.get("event_type") or "").lower()
        if not event_type.startswith(ALLOWED_EVENT_PREFIXES) or any(x in event_type for x in FORBIDDEN_EVENT_TOKENS): raise PermissionError("event type would bypass canonical authority/economic subsystem")
        digest=self._validate_digest(envelope.get("payload_sha256"))
        event=self.ledger.append(self.application_entity_id,event_type,subject_ids=envelope.get("subject_ids") or [],object_ids=envelope.get("object_ids") or [],payload_sha256=digest,evidence_origin=str(envelope.get("evidence_origin") or "DIRECT_OBSERVATION"),confidence=float(envelope.get("confidence",1.0)))
        result={"schema":"entity-btg-app-event-result-v1","event":event,"non_authoritative_application_event":True,"economic_state_mutated":False,"rights_state_mutated":False,"idempotent_replay":False}
        self._remember(key,envelope,result); return result

    def status(self)->dict:
        return {"ready":True,"schema":"entity-btg-application-sdk-v1","application_entity_id":self.application_entity_id,"organization_entity_id":self.organization_entity_id,"default_deny_authorization":True,"raw_content_not_required":True,"registration_not_ownership":True,"rights_require_explicit_basis":True,"economic_mutation_not_exposed":True,"core_registries_reused":True}
