from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, time, uuid

REPO=Path(__file__).resolve().parents[2]
SRC=REPO/"src"
SDK_ROOT=REPO/"sdk"

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _now(): return int(time.time()*1000)

IDENTITY=_load("entity_principal_identity",SRC/"01_Core_Runtime"/"identity"/"canonical_identity.py")
SOVEREIGN=_load("entity_principal_sovereign",SRC/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py")
OPENSDK=_load("entity_principal_open_sdk",SDK_ROOT/"open_entity_sdk"/"canonical_open_entity_sdk.py")

SCHEMA="entity-principal-binding-v1"
def provision_bound_installation(state_dir:str|Path,*,principal_entity_id:str,application_entity_id:str,
                                 device_entity_id:str,display_name:str,alias:str,metadata=None)->dict:
    state=Path(state_dir); identity=IDENTITY.EntityIdentityVault(state)
    for entity_id in (principal_entity_id,application_entity_id,device_entity_id): identity.load_manifest(str(entity_id))
    name=OPENSDK.normalize_alias(alias)
    meta=dict(metadata or {}); meta.update({"binding_schema":SCHEMA,"principal_entity_id":str(principal_entity_id),
        "application_entity_id":str(application_entity_id),"device_entity_id":str(device_entity_id),
        "delegated_installation":True,"ownership_not_inferred":True,"authority_scope":"DATA_PROVENANCE_CAPTURE_ONLY"})
    meta["entity_subtype"]="application_installation"
    manifest=identity.create(str(display_name),"application",aliases=[name],metadata=meta)
    install_id=manifest["entity_id"]; sovereign=SOVEREIGN.SovereignAuthorityRegistry(state,identity)
    rel_device=sovereign.grant_relationship(str(device_entity_id),install_id,"POSSESSION",
        scope={"installed_instance":True,"device_possession_not_ownership":True},
        evidence_origin="ENTITY_ASSERTION",evidence={"binding_schema":SCHEMA})
    rel_app=sovereign.grant_relationship(str(application_entity_id),install_id,"PROCESSING_AUTHORITY",
        scope={"application_instance_of":str(application_entity_id),"data_rights_not_transferred":True},
        evidence_origin="ENTITY_ASSERTION",evidence={"binding_schema":SCHEMA})
    rel_principal=sovereign.grant_relationship(str(principal_entity_id),install_id,"SOVEREIGN_AUTHORITY",
        scope={"delegated_actions":["INGEST_ASSET","RECORD_EVENT"],"revocable":True,
               "data_controller_defaults_to_principal":True,"application_ownership_not_transferred":True},
        evidence_origin="ENTITY_ASSERTION",evidence={"binding_schema":SCHEMA})
    descriptor=OPENSDK.address_descriptor(name,install_id)
    pairwise_ref=identity.pairwise_id(str(principal_entity_id),f"application:{application_entity_id}:installation:{install_id}")
    body={"schema":SCHEMA,"binding_id":"pbind1-"+uuid.uuid4().hex,"principal_entity_id":str(principal_entity_id),
        "principal_pairwise_ref":pairwise_ref,"application_entity_id":str(application_entity_id),"device_entity_id":str(device_entity_id),
        "installation_entity_id":install_id,"installation_alias":name,"issued_at_ms":_now(),"status":"ACTIVE",
        "delegated_actions":["INGEST_ASSET","RECORD_EVENT"],
        "relationships":{"principal":rel_principal["relationship_id"],"application":rel_app["relationship_id"],
                         "device":rel_device["relationship_id"]},"address":descriptor}
    signature=identity.sign(str(principal_entity_id),body)
    binding=dict(body,principal_signature=signature); binding["binding_sha256"]=_sha(body)
    return binding

def validate_bound_installation(state_dir:str|Path,binding:dict)->dict:
    state=Path(state_dir); identity=IDENTITY.EntityIdentityVault(state); sovereign=SOVEREIGN.SovereignAuthorityRegistry(state,identity)
    required=("principal_entity_id","application_entity_id","device_entity_id","installation_entity_id")
    if binding.get("schema")!=SCHEMA or any(not binding.get(k) for k in required):
        return {"valid":False,"reason":"binding_schema_or_fields_invalid"}
    body={k:v for k,v in binding.items() if k not in {"principal_signature","binding_sha256"}}
    if binding.get("binding_sha256")!=_sha(body): return {"valid":False,"reason":"binding_hash_mismatch"}
    try:
        principal=str(binding["principal_entity_id"]); app=str(binding["application_entity_id"])
        device=str(binding["device_entity_id"]); install=str(binding["installation_entity_id"])
        principal_manifest=identity.load_manifest(principal); install_manifest=identity.load_manifest(install)
        identity.load_manifest(app); identity.load_manifest(device)
    except Exception as exc: return {"valid":False,"reason":"identity_missing_or_invalid","detail":str(exc)}
    if not IDENTITY.EntityIdentityVault.verify_signature(principal_manifest,body,dict(binding.get("principal_signature") or {})):
        return {"valid":False,"reason":"principal_signature_invalid"}
    meta=dict(install_manifest.get("metadata") or {})
    if meta.get("principal_entity_id")!=principal or meta.get("application_entity_id")!=app or meta.get("device_entity_id")!=device:
        return {"valid":False,"reason":"installation_manifest_binding_mismatch"}
    rels=dict(binding.get("relationships") or {})
    def active(owner,party,rtype,rid):
        return any(x.get("relationship_id")==rid and x.get("relationship_type")==rtype
                   for x in sovereign.active_relationships(owner,party))
    checks={"principal":active(principal,install,"SOVEREIGN_AUTHORITY",rels.get("principal")),
            "application":active(app,install,"PROCESSING_AUTHORITY",rels.get("application")),
            "device":active(device,install,"POSSESSION",rels.get("device"))}
    if not all(checks.values()): return {"valid":False,"reason":"binding_relationship_inactive","checks":checks}
    return {"valid":True,"schema":SCHEMA,"principal_entity_id":principal,
            "principal_pairwise_ref":binding.get("principal_pairwise_ref"),"application_entity_id":app,
            "device_entity_id":device,"installation_entity_id":install,
            "authorized_asset_controllers":[principal],"authorized_rights_claimants":[],
            "delegated_actions":list(binding.get("delegated_actions") or []),"checks":checks}
def binding_authorizer(state_dir:str|Path,binding:dict):
    def _authorize(envelope:dict,operation:str)->dict:
        verified=validate_bound_installation(state_dir,binding)
        if not verified.get("valid"): return {"allowed":False,"reason":verified.get("reason","binding_invalid")}
        if str(envelope.get("application_entity_id"))!=verified["application_entity_id"]:
            return {"allowed":False,"reason":"application_binding_mismatch"}
        if operation not in set(verified.get("delegated_actions") or []):
            return {"allowed":False,"reason":"operation_not_delegated"}
        return {"allowed":True,"principal_entity_id":verified["principal_entity_id"],
                "installation_entity_id":verified["installation_entity_id"],
                "device_entity_id":verified["device_entity_id"],
                "authorized_asset_controllers":verified["authorized_asset_controllers"],
                "authorized_rights_claimants":[]}
    return _authorize

def revoke_bound_installation(state_dir:str|Path,binding:dict,reason="principal_revocation")->dict:
    state=Path(state_dir); identity=IDENTITY.EntityIdentityVault(state)
    principal=str(binding.get("principal_entity_id") or ""); rel=(binding.get("relationships") or {}).get("principal")
    if not principal or not rel: raise ValueError("principal binding relationship required")
    sovereign=SOVEREIGN.SovereignAuthorityRegistry(state,identity)
    result=sovereign.revoke_relationship(principal,str(rel),reason=reason)
    return {"schema":"entity-principal-binding-revocation-v1","binding_id":binding.get("binding_id"),
            "principal_entity_id":principal,"installation_entity_id":binding.get("installation_entity_id"),
            "status":"REVOKED","relationship":result}
