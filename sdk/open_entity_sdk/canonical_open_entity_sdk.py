from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import hashlib, importlib.util, json, sqlite3, time, uuid

ROOT=Path(__file__).resolve().parents[2] / "src"
ASSET_SCHEMA="entity-open-sdk-asset-envelope-v1"
EVENT_SCHEMA="entity-open-sdk-event-envelope-v1"
ASSET_KINDS={"SOFTWARE","DATA","MODEL","KNOWLEDGE","EVIDENCE"}
ALLOWED_EVENT_PREFIXES=("application.","data.","model.","knowledge.","software.","evidence.")
FORBIDDEN_EVENT_TOKENS=("ownership","licence","license","settlement","payment","capital","authority","consent","rights.verify","commodity")

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def normalize_alias(alias:str)->str:
    value=".".join(p.strip().lower() for p in str(alias or "").strip().split(".") if p.strip())
    if not value or len(value)>253: raise ValueError("invalid Entity alias")
    if any(not all(c.isalnum() or c in "-_" for c in part) for part in value.split(".")):
        raise ValueError("unsupported Entity alias characters")
    return value

def address_descriptor(alias:str,entity_id:str,namespace:str="entity",domain_id:str|None=None)->dict:
    name=normalize_alias(alias); root=str(entity_id); ns=str(namespace or "entity").lower()
    binding=_sha({"namespace":ns,"normalized_name":name,"entity_root":root})
    addr_hash=hashlib.sha256(root.encode("utf-8")).hexdigest()
    return {"schema":"entity-address-descriptor-v1","display_alias":name,"namespace":ns,
            "entity_address":root,"entity_address_sha256":addr_hash,"alias_binding_sha256":binding,
            "collision_safe_display":f"{name}~{binding[:12]}","domain_id":domain_id,
            "alias_is_authority":False,"entity_address_is_authority":True}

def make_asset_envelope(*,application_entity_id,content_sha256,size_bytes,media_type,title,asset_kind,
                        classification="PRIVATE",metadata=None,source_subject_ref=None,idempotency_key=None,
                        explicit_rights_claim=None,contributors=None,parent_asset_ids=None):
    return {"schema":ASSET_SCHEMA,"application_entity_id":str(application_entity_id),
            "idempotency_key":str(idempotency_key or uuid.uuid4()),"content_sha256":str(content_sha256).lower(),
            "size_bytes":int(size_bytes),"media_type":str(media_type),"title":str(title),
            "asset_kind":str(asset_kind).upper(),"classification":str(classification).upper(),
            "metadata":dict(metadata or {}),"source_subject_ref":source_subject_ref,
            "explicit_rights_claim":dict(explicit_rights_claim or {}),"contributors":[dict(x) for x in (contributors or [])],
            "parent_asset_ids":[str(x) for x in (parent_asset_ids or [])],"raw_content_included":False}
def make_event_envelope(*,application_entity_id,event_type,payload_sha256,subject_ids=None,object_ids=None,
                        idempotency_key=None,evidence_origin="DIRECT_OBSERVATION",confidence=1.0):
    return {"schema":EVENT_SCHEMA,"application_entity_id":str(application_entity_id),
            "idempotency_key":str(idempotency_key or uuid.uuid4()),"event_type":str(event_type),
            "payload_sha256":str(payload_sha256).lower(),"subject_ids":[str(x) for x in (subject_ids or [])],
            "object_ids":[str(x) for x in (object_ids or [])],"evidence_origin":str(evidence_origin),
            "confidence":float(confidence),"raw_payload_included":False}

class OpenEntityDeveloperSDK:
    """Open, provider-neutral application/data integration adapter for ENTITY."""
    def __init__(self,state_dir:str|Path,application_entity_id:str,*,authorizer=None):
        self.state=Path(state_dir); self.application_entity_id=str(application_entity_id); self.authorizer=authorizer
        im=_load("open_sdk_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
        lm=_load("open_sdk_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
        rm=_load("open_sdk_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
        pm=_load("open_sdk_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
        am=_load("open_sdk_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
        km=_load("open_sdk_knowledge",ROOT/"04_Entity_Registry"/"canonical_knowledge_capital.py")
        self.identity=im.EntityIdentityVault(self.state); self.identity.load_manifest(self.application_entity_id)
        self.ledger=lm.CanonicalEventLedger(self.state,self.identity); self.rights=rm.RightsClaimsGraph(self.state,self.identity)
        self.provenance=pm.AssetProvenanceGraph(self.state,self.identity)
        self.assets=am.CanonicalAssetRegistry(self.state,self.identity,self.ledger,self.rights,self.provenance)
        self.knowledge=km.KnowledgeCapitalRegistry(self.state,self.identity)
        self.root=self.state/"open_entity_sdk"; self.root.mkdir(parents=True,exist_ok=True); self.db_path=self.root/"ingest.sqlite"; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.db_path,timeout=30); db.row_factory=sqlite3.Row
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
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS idempotency(idempotency_key TEXT PRIMARY KEY,envelope_sha256 TEXT NOT NULL,result_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")

    @classmethod
    def provision_application(cls,state_dir:str|Path,display_name:str,alias:str,*,controller_entity_id:str|None=None,metadata=None)->dict:
        state=Path(state_dir); name=normalize_alias(alias)
        im=_load("open_sdk_provision_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
        dm=_load("open_sdk_provision_domain",ROOT/"22_Sovereign_Domain"/"core"/"canonical_domain.py")
        sm=_load("open_sdk_provision_sovereign",ROOT/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py")
        identity=im.EntityIdentityVault(state)
        if controller_entity_id: identity.load_manifest(str(controller_entity_id))
        meta=dict(metadata or {}); meta.update({"entity_sdk_profile":"ENTITY_OPEN_SDK_v1","application_alias":name,
                                                "alias_is_not_authority":True,"asset_ownership_not_inferred":True})
        manifest=identity.create(str(display_name),"application",aliases=[name],metadata=meta); app_id=manifest["entity_id"]
        domain=dm.EntityDomainAuthority(state,identity).create_domain(app_id,namespace="entity",requested_name=name)
        descriptor=address_descriptor(name,app_id,"entity",domain["domain_id"])
        control=None
        if controller_entity_id:
            control=sm.SovereignAuthorityRegistry(state,identity).grant_relationship(app_id,str(controller_entity_id),"SOVEREIGN_AUTHORITY",
                scope={"application_control":True,"asset_ownership_not_implied":True,"user_data_ownership_not_implied":True},
                evidence_origin="ENTITY_ASSERTION",evidence={"profile":"ENTITY_OPEN_SDK_v1"})
        return {"application_entity_id":app_id,"entity_address":app_id,"alias":name,"manifest":manifest,
                "domain":domain,"address":descriptor,"controller_relationship":control}

    def _authorize(self,envelope:dict,operation:str):
        if self.authorizer is None: raise PermissionError("open SDK ingest requires explicit authorization")
        decision=self.authorizer(dict(envelope),str(operation)); allowed=decision.get("allowed") if isinstance(decision,dict) else bool(decision)
        if not allowed: raise PermissionError("open SDK ingest authorization denied")
        return decision if isinstance(decision,dict) else {"allowed":True}
    @staticmethod
    def _digest(value:str):
        d=str(value or "").lower()
        if len(d)!=64 or any(c not in "0123456789abcdef" for c in d): raise ValueError("SHA-256 hex required")
        return d

    def _check(self,envelope:dict,schema:str):
        if envelope.get("schema")!=schema: raise ValueError("unsupported open SDK envelope schema")
        if envelope.get("application_entity_id")!=self.application_entity_id: raise PermissionError("application entity mismatch")
        key=str(envelope.get("idempotency_key") or "").strip()
        if not key or len(key)>256: raise ValueError("idempotency_key required")
        digest=_sha(envelope)
        with self._connect() as db:
            row=db.execute("SELECT * FROM idempotency WHERE idempotency_key=?",(key,)).fetchone()
        if row:
            if row["envelope_sha256"]!=digest: raise ValueError("idempotency key reused with different envelope")
            out=json.loads(row["result_json"]); out["idempotent_replay"]=True; return key,out
        return key,None

    def _remember(self,key,envelope,result):
        with self._connect() as db:
            db.execute("INSERT INTO idempotency VALUES(?,?,?,?)",(key,_sha(envelope),json.dumps(result,sort_keys=True,default=str),_now()))

    def ingest_asset(self,envelope:dict)->dict:
        envelope=dict(envelope or {}); key,replay=self._check(envelope,ASSET_SCHEMA)
        if replay is not None: return replay
        decision=self._authorize(envelope,"INGEST_ASSET")
        if envelope.get("raw_content_included") is not False: raise ValueError("raw content must not be embedded")
        kind=str(envelope.get("asset_kind") or "").upper()
        if kind not in ASSET_KINDS: raise ValueError("unsupported asset_kind")
        digest=self._digest(envelope.get("content_sha256")); manifest=self.identity.load_manifest(self.application_entity_id)
        alias=(manifest.get("aliases") or [self.application_entity_id])[0]
        addr=address_descriptor(alias,self.application_entity_id)
        meta=dict(envelope.get("metadata") or {}); meta.update({"asset_kind":kind,"producer_entity_address":self.application_entity_id,
            "producer_alias":alias,"producer_alias_binding_sha256":addr["alias_binding_sha256"],"source_subject_ref":envelope.get("source_subject_ref"),
            "ownership_not_inferred":True,"raw_content_stored_in_event_ledger":False})
        asset=self.assets.register(self.application_entity_id,content_sha256=digest,size_bytes=int(envelope.get("size_bytes") or 0),
            media_type=str(envelope.get("media_type") or "application/octet-stream"),title=str(envelope.get("title") or kind),
            classification=str(envelope.get("classification") or "PRIVATE"),metadata=meta)
        claims=[]; explicit=dict(envelope.get("explicit_rights_claim") or {})
        if explicit:
            claimant=str(explicit.get("claimant_entity_id") or self.application_entity_id)
            allowed_claimants={self.application_entity_id}|{str(x) for x in (decision.get("authorized_rights_claimants") or [])}
            if claimant not in allowed_claimants: raise PermissionError("rights claimant is not delegated to this application operation")
            self.identity.load_manifest(claimant)
            if not explicit.get("legal_basis") or not explicit.get("right_type") or not explicit.get("evidence"):
                raise ValueError("explicit rights claim requires claimant_entity_id/right_type/legal_basis/evidence")
            claims.append(self.rights.assert_claim(claimant,asset_id=asset["asset_id"],right_type=str(explicit["right_type"]),
                legal_basis=str(explicit["legal_basis"]),scope=dict(explicit.get("scope") or {}),evidence=dict(explicit["evidence"]),
                evidence_origin=str(explicit.get("evidence_origin") or "ENTITY_ASSERTION")))
        receipt=None; contributors=[dict(x) for x in (envelope.get("contributors") or [])]
        if contributors:
            receipt=self.knowledge.record(self.application_entity_id,kind=kind,title=str(envelope.get("title") or kind),
                contributors=contributors,artifact_sha256=digest,metadata={"asset_id":asset["asset_id"],"origin_entity":self.application_entity_id},
                evidence_origin="ENTITY_ASSERTION")
        derivations=[]; relation="model_output" if kind=="MODEL" else "other"
        for parent in envelope.get("parent_asset_ids") or []:
            derivations.append(self.provenance.add_derivation(self.application_entity_id,str(parent),asset["asset_id"],relation,
                metadata={"producer_entity_address":self.application_entity_id,"automatic_open_sdk_capture":True},evidence_origin="ENTITY_ASSERTION"))
        event=self.ledger.append(self.application_entity_id,"application.asset_ingested",subject_ids=[self.application_entity_id],
            object_ids=[asset["asset_id"]],payload={"asset_id":asset["asset_id"],"asset_kind":kind,"content_sha256":digest,
            "source_subject_ref":envelope.get("source_subject_ref"),"registration_not_ownership":True,"economic_value_not_inferred":True})
        result={"schema":"entity-open-sdk-asset-result-v1","entity_address":self.application_entity_id,"address":addr,"asset":asset,
                "explicit_rights_claims":claims,"knowledge_receipt":receipt,"derivations":derivations,"ingest_event":event,
                "ownership_not_inferred":True,"economic_value_not_inferred":True,"raw_content_stored":False,"idempotent_replay":False}
        self._remember(key,envelope,result); return result

    def record_event(self,envelope:dict)->dict:
        envelope=dict(envelope or {}); key,replay=self._check(envelope,EVENT_SCHEMA)
        if replay is not None: return replay
        self._authorize(envelope,"RECORD_EVENT")
        if envelope.get("raw_payload_included") is not False: raise ValueError("raw event payload must not be embedded")
        event_type=str(envelope.get("event_type") or "").lower()
        if not event_type.startswith(ALLOWED_EVENT_PREFIXES) or any(x in event_type for x in FORBIDDEN_EVENT_TOKENS):
            raise PermissionError("event type would bypass canonical authority/economic subsystem")
        digest=self._digest(envelope.get("payload_sha256"))
        event=self.ledger.append(self.application_entity_id,event_type,subject_ids=envelope.get("subject_ids") or [],
            object_ids=envelope.get("object_ids") or [],payload_sha256=digest,evidence_origin=str(envelope.get("evidence_origin") or "DIRECT_OBSERVATION"),
            confidence=float(envelope.get("confidence",1.0)))
        result={"schema":"entity-open-sdk-event-result-v1","entity_address":self.application_entity_id,"event":event,
                "non_authoritative_application_event":True,"economic_state_mutated":False,"rights_state_mutated":False,"idempotent_replay":False}
        self._remember(key,envelope,result); return result

    def status(self)->dict:
        return {"ready":True,"schema":"entity-open-developer-sdk-v1","entity_address":self.application_entity_id,
                "default_deny_authorization":True,"raw_content_not_required":True,"registration_not_ownership":True,
                "alias_is_not_authority":True,"economic_mutation_not_exposed":True,"provider_neutral":True,"btg_dependency_required":False}
