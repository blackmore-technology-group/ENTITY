from __future__ import annotations
from pathlib import Path
import importlib.util, os
from fastapi import FastAPI, HTTPException, Request

REPO=Path(__file__).resolve().parents[2]
SRC=REPO/"src"
SDK_ROOT=REPO/"sdk"
STATE=Path(os.environ.get("ENTITY_STATE_DIR","./entity_state"))

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

PB=_load("entity_gateway_pb",SDK_ROOT/"principal_binding"/"canonical_principal_binding.py")
SDK11=_load("entity_gateway_sdk11",SDK_ROOT/"open_entity_sdk_v1_1"/"canonical_open_entity_sdk_v1_1.py")
SDK1=_load("entity_gateway_sdk1",SDK_ROOT/"open_entity_sdk"/"canonical_open_entity_sdk.py")
app=FastAPI(title="ENTITY Open SDK Gateway",version="1.1")

def _binding(envelope:dict)->dict:
    binding=dict(envelope.get("principal_binding") or {})
    q=PB.validate_bound_installation(STATE,binding)
    if not q.get("valid"): raise HTTPException(403,f"principal binding invalid: {q.get('reason')}")
    if str(envelope.get("application_entity_id"))!=q["application_entity_id"]:
        raise HTTPException(403,"application does not match principal binding")
    return binding
def _enrich(envelope:dict,binding:dict)->tuple[dict,dict]:
    q=PB.validate_bound_installation(STATE,binding)
    e=dict(envelope); meta=dict(e.get("metadata") or {})
    meta.update({"origin_principal_entity_id":q["principal_entity_id"],
                 "origin_principal_pairwise_ref":q.get("principal_pairwise_ref"),
                 "origin_installation_entity_id":q["installation_entity_id"],
                 "origin_device_entity_id":q["device_entity_id"],
                 "principal_binding_sha256":binding.get("binding_sha256")})
    e["metadata"]=meta
    e["installation_entity_id"]=q["installation_entity_id"]
    e["device_entity_id"]=q["device_entity_id"]
    return e,q

@app.get("/health")
def health():
    return {"ok":True,"schema":"entity-open-sdk-gateway-v1.1","state_dir":str(STATE),
            "principal_binding_required":True,"bare_entity_ids_accepted":False}

@app.post("/entity/principal-binding/v1/validate")
async def validate_binding(request:Request):
    body=await request.json(); return PB.validate_bound_installation(STATE,dict(body or {}))
@app.post("/entity/open-sdk/v1.1/assets")
async def ingest_asset(request:Request):
    envelope=dict(await request.json() or {}); binding=_binding(envelope); enriched,q=_enrich(envelope,binding)
    sdk=SDK11.OpenEntityDeveloperSDKv11(STATE,q["application_entity_id"],authorizer=PB.binding_authorizer(STATE,binding))
    try: result=sdk.ingest_asset(enriched)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(400,str(exc))
    result["principal_binding_verified"]=True
    result["origin_principal_entity_id"]=q["principal_entity_id"]
    result["origin_installation_entity_id"]=q["installation_entity_id"]
    result["origin_device_entity_id"]=q["device_entity_id"]
    return result

@app.post("/entity/open-sdk/v1/events")
async def record_event(request:Request):
    envelope=dict(await request.json() or {}); binding=_binding(envelope); q=PB.validate_bound_installation(STATE,binding)
    subjects=[str(x) for x in (envelope.get("subject_ids") or [])]
    for value in (q["principal_entity_id"],q["installation_entity_id"],q["device_entity_id"]):
        if value not in subjects: subjects.append(value)
    envelope["subject_ids"]=subjects
    sdk=SDK11.OpenEntityDeveloperSDKv11(STATE,q["application_entity_id"],authorizer=PB.binding_authorizer(STATE,binding))
    try: result=sdk.record_event(envelope)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(400,str(exc))
    result.update({"principal_binding_verified":True,"origin_principal_entity_id":q["principal_entity_id"],
                   "origin_installation_entity_id":q["installation_entity_id"],"origin_device_entity_id":q["device_entity_id"]})
    return result
