from __future__ import annotations
from pathlib import Path
import importlib.util, uuid

REPO=Path(__file__).resolve().parents[2]
SRC=REPO/"src"
SDK_ROOT=REPO/"sdk"
BASE_PATH=SDK_ROOT/"open_entity_sdk"/"canonical_open_entity_sdk.py"
ASSET_SCHEMA="entity-open-sdk-asset-envelope-v1.1"

def _load_base():
    spec=importlib.util.spec_from_file_location("entity_open_sdk_v1_base",BASE_PATH)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

BASE=_load_base()

def make_asset_envelope(*,application_entity_id,content_sha256,size_bytes,media_type,title,asset_kind,
                        classification="PRIVATE",metadata=None,source_subject_ref=None,
                        asset_controller_entity_id=None,idempotency_key=None,explicit_rights_claim=None,
                        contributors=None,parent_asset_ids=None):
    return {"schema":ASSET_SCHEMA,"application_entity_id":str(application_entity_id),
            "asset_controller_entity_id":str(asset_controller_entity_id or application_entity_id),
            "idempotency_key":str(idempotency_key or uuid.uuid4()),"content_sha256":str(content_sha256).lower(),
            "size_bytes":int(size_bytes),"media_type":str(media_type),"title":str(title),
            "asset_kind":str(asset_kind).upper(),"classification":str(classification).upper(),
            "metadata":dict(metadata or {}),"source_subject_ref":source_subject_ref,
            "explicit_rights_claim":dict(explicit_rights_claim or {}),
            "contributors":[dict(x) for x in (contributors or [])],
            "parent_asset_ids":[str(x) for x in (parent_asset_ids or [])],"raw_content_included":False}

class OpenEntityDeveloperSDKv11(BASE.OpenEntityDeveloperSDK):
    """Open SDK v1.1: producer identity and asset controller are separate, fail-closed concepts."""
    def ingest_asset(self,envelope:dict)->dict:
        envelope=dict(envelope or {}); key,replay=self._check(envelope,ASSET_SCHEMA)
        if replay is not None: return replay
        decision=self._authorize(envelope,"INGEST_ASSET")
        if envelope.get("raw_content_included") is not False:
            raise ValueError("raw content must not be embedded")
        kind=str(envelope.get("asset_kind") or "").upper()
        if kind not in BASE.ASSET_KINDS: raise ValueError("unsupported asset_kind")
        controller=str(envelope.get("asset_controller_entity_id") or self.application_entity_id)
        allowed_controllers={self.application_entity_id}|{str(x) for x in (decision.get("authorized_asset_controllers") or [])}
        if controller not in allowed_controllers:
            raise PermissionError("asset controller is not delegated to this application operation")
        self.identity.load_manifest(controller)
        digest=self._digest(envelope.get("content_sha256"))
        manifest=self.identity.load_manifest(self.application_entity_id)
        alias=(manifest.get("aliases") or [self.application_entity_id])[0]
        addr=BASE.address_descriptor(alias,self.application_entity_id)
        meta=dict(envelope.get("metadata") or {})
        meta.update({"asset_kind":kind,"producer_entity_address":self.application_entity_id,
                     "asset_controller_entity_id":controller,"producer_alias":alias,
                     "producer_alias_binding_sha256":addr["alias_binding_sha256"],
                     "source_subject_ref":envelope.get("source_subject_ref"),"ownership_not_inferred":True,
                     "raw_content_stored_in_event_ledger":False})
        asset=self.assets.register(controller,content_sha256=digest,size_bytes=int(envelope.get("size_bytes") or 0),
            media_type=str(envelope.get("media_type") or "application/octet-stream"),title=str(envelope.get("title") or kind),
            classification=str(envelope.get("classification") or "PRIVATE"),metadata=meta)
        claims=[]; explicit=dict(envelope.get("explicit_rights_claim") or {})
        if explicit:
            claimant=str(explicit.get("claimant_entity_id") or self.application_entity_id)
            allowed_claimants={self.application_entity_id}|{str(x) for x in (decision.get("authorized_rights_claimants") or [])}
            if claimant not in allowed_claimants:
                raise PermissionError("rights claimant is not delegated to this application operation")
            self.identity.load_manifest(claimant)
            if not explicit.get("legal_basis") or not explicit.get("right_type") or not explicit.get("evidence"):
                raise ValueError("explicit rights claim requires claimant_entity_id/right_type/legal_basis/evidence")
            claims.append(self.rights.assert_claim(claimant,asset_id=asset["asset_id"],right_type=str(explicit["right_type"]),
                legal_basis=str(explicit["legal_basis"]),scope=dict(explicit.get("scope") or {}),
                evidence=dict(explicit["evidence"]),evidence_origin=str(explicit.get("evidence_origin") or "ENTITY_ASSERTION")))
        receipt=None; contributors=[dict(x) for x in (envelope.get("contributors") or [])]
        if contributors:
            receipt=self.knowledge.record(self.application_entity_id,kind=kind,title=str(envelope.get("title") or kind),
                contributors=contributors,artifact_sha256=digest,
                metadata={"asset_id":asset["asset_id"],"origin_entity":self.application_entity_id,
                          "asset_controller_entity_id":controller},evidence_origin="ENTITY_ASSERTION")
        derivations=[]; relation="model_output" if kind=="MODEL" else "other"
        for parent in envelope.get("parent_asset_ids") or []:
            derivations.append(self.provenance.add_derivation(self.application_entity_id,str(parent),asset["asset_id"],relation,
                metadata={"producer_entity_address":self.application_entity_id,"asset_controller_entity_id":controller,
                          "automatic_open_sdk_capture":True},evidence_origin="ENTITY_ASSERTION"))
        event=self.ledger.append(self.application_entity_id,"application.asset_ingested",
            subject_ids=[self.application_entity_id,controller],object_ids=[asset["asset_id"]],
            payload={"asset_id":asset["asset_id"],"asset_kind":kind,"content_sha256":digest,
                     "producer_entity_address":self.application_entity_id,"asset_controller_entity_id":controller,
                     "source_subject_ref":envelope.get("source_subject_ref"),"registration_not_ownership":True,
                     "economic_value_not_inferred":True})
        result={"schema":"entity-open-sdk-asset-result-v1.1","producer_entity_address":self.application_entity_id,
                "asset_controller_entity_id":controller,"address":addr,"asset":asset,
                "explicit_rights_claims":claims,"knowledge_receipt":receipt,"derivations":derivations,
                "ingest_event":event,"ownership_not_inferred":True,"economic_value_not_inferred":True,
                "raw_content_stored":False,"idempotent_replay":False}
        self._remember(key,envelope,result); return result

    def status(self)->dict:
        out=super().status(); out.update({"schema":"entity-open-developer-sdk-v1.1",
            "producer_controller_separation":True,"asset_controller_requires_delegation":True})
        return out
