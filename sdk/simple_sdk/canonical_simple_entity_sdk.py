from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json

REPO=Path(__file__).resolve().parents[2]
SRC=REPO/"src"
SDK_ROOT=REPO/"sdk"

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

ID=_load("simple_entity_identity",SRC/"01_Core_Runtime"/"identity"/"canonical_identity.py")
PB=_load("simple_entity_principal",SDK_ROOT/"principal_binding"/"canonical_principal_binding.py")
SDK11=_load("simple_entity_sdk11",SDK_ROOT/"open_entity_sdk_v1_1"/"canonical_open_entity_sdk_v1_1.py")
PORT=_load("simple_entity_portability",SRC/"15_Operations"/"backups"/"canonical_portable_state.py")

class SimpleEntitySDK:
    """Small developer facade. It delegates authority to canonical ENTITY subsystems."""
    VERSION="1.0"
    def __init__(self,state_dir:str|Path):
        self.state=Path(state_dir)
        self.identity=ID.EntityIdentityVault(self.state)

    def create_entity(self,display_name:str,*,entity_type="person",alias:str|None=None,metadata=None)->dict:
        aliases=[alias] if alias else []
        manifest=self.identity.create(display_name,entity_type,aliases=aliases,metadata=dict(metadata or {}))
        return {"entity_id":manifest["entity_id"],"display_name":manifest["display_name"],"entity_type":manifest["entity_type"],"verified":ID.EntityIdentityVault.verify_manifest(manifest)}

    def create_application(self,display_name:str,alias:str,*,controller_entity_id:str|None=None,metadata=None)->dict:
        return SDK11.OpenEntityDeveloperSDKv11.provision_application(
            self.state,display_name,alias,controller_entity_id=controller_entity_id,metadata=metadata)

    def pair_device(self,*,principal_entity_id:str,application_entity_id:str,device_entity_id:str,
                    display_name:str,alias:str,metadata=None)->dict:
        return PB.provision_bound_installation(self.state,principal_entity_id=principal_entity_id,
            application_entity_id=application_entity_id,device_entity_id=device_entity_id,
            display_name=display_name,alias=alias,metadata=metadata)

    def verify_pairing(self,binding:dict)->dict:
        return PB.validate_bound_installation(self.state,binding)

    def register_asset(self,binding:dict,*,content_sha256:str,size_bytes:int,media_type:str,title:str,
                       asset_kind:str,classification="PRIVATE",source_subject_ref=None,metadata=None,
                       contributors=None,parent_asset_ids=None,idempotency_key=None)->dict:
        verified=self.verify_pairing(binding)
        if not verified.get("valid"): raise PermissionError("device pairing is not valid")
        app=verified["application_entity_id"]; principal=verified["principal_entity_id"]
        host=SDK11.OpenEntityDeveloperSDKv11(self.state,app,authorizer=PB.binding_authorizer(self.state,binding))
        envelope=SDK11.make_asset_envelope(application_entity_id=app,asset_controller_entity_id=principal,
            content_sha256=content_sha256,size_bytes=size_bytes,media_type=media_type,title=title,asset_kind=asset_kind,
            classification=classification,metadata=metadata,source_subject_ref=source_subject_ref or principal,
            contributors=contributors,parent_asset_ids=parent_asset_ids,idempotency_key=idempotency_key)
        return host.ingest_asset(envelope)

    def record_event(self,binding:dict,*,event_type:str,payload_sha256:str,subject_ids=None,object_ids=None,
                     evidence_origin="DIRECT_OBSERVATION",confidence=1.0,idempotency_key=None)->dict:
        verified=self.verify_pairing(binding)
        if not verified.get("valid"): raise PermissionError("device pairing is not valid")
        app=verified["application_entity_id"]
        host=SDK11.OpenEntityDeveloperSDKv11(self.state,app,authorizer=PB.binding_authorizer(self.state,binding))
        envelope=SDK11.BASE.make_event_envelope(application_entity_id=app,event_type=event_type,
            payload_sha256=payload_sha256,subject_ids=subject_ids,object_ids=object_ids,
            idempotency_key=idempotency_key,evidence_origin=evidence_origin,confidence=confidence)
        return host.record_event(envelope)

    def export_entity(self,entity_id:str,destination:str|Path)->dict:
        manager=PORT.PortableStateManager(self.state,self.identity)
        return manager.export_entity(entity_id,destination)

    def verify_export(self,destination:str|Path)->dict:
        dest=Path(destination); manifest_path=dest/"identity_manifest.json"; export_path=dest/"EXPORT_MANIFEST.json"
        if not manifest_path.is_file() or not export_path.is_file(): return {"valid":False,"reason":"export_files_missing"}
        manifest=json.loads(manifest_path.read_text(encoding="utf-8")); export=json.loads(export_path.read_text(encoding="utf-8"))
        if not ID.EntityIdentityVault.verify_manifest(manifest): return {"valid":False,"reason":"identity_manifest_invalid"}
        body={k:v for k,v in export.items() if k!="signature"}
        if not ID.EntityIdentityVault.verify_signature(manifest,body,dict(export.get("signature") or {})):
            return {"valid":False,"reason":"export_signature_invalid"}
        failures=[]
        for item in export.get("files") or []:
            p=dest/str(item.get("name") or "")
            actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
            if actual!=item.get("sha256"): failures.append(str(item.get("name")))
        return {"valid":not failures,"entity_id":export.get("entity_id"),"file_hash_failures":failures,
                "private_keys_included":export.get("private_keys_included"),"provider_independent":True}

    def revoke_device(self,binding:dict,reason="principal_revocation")->dict:
        return PB.revoke_bound_installation(self.state,binding,reason=reason)

    def status(self)->dict:
        return {"ready":True,"schema":"entity-simple-sdk-v1","version":self.VERSION,
                "developer_surface":["create_entity","create_application","pair_device","register_asset","record_event","export_entity"],
                "verification":["verify_pairing","verify_export"],"revocation":["revoke_device"],
                "authority_implementation":"delegated_to_canonical_ENTITY","provider_neutral":True,
                "registration_not_ownership":True,"economic_mutation_not_exposed":True,
                "full_move_workflow_claimed":False}
