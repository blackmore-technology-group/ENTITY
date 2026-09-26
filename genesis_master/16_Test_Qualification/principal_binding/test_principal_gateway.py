from pathlib import Path
import importlib.util, json, os, sqlite3, tempfile
from fastapi.testclient import TestClient

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
PB=load("pbgw",ROOT/"14_Protocols_SDK"/"principal_binding"/"canonical_principal_binding.py")
ID=load("idgw",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
SDK11=load("sdk11gw",ROOT/"14_Protocols_SDK"/"open_entity_sdk_v1_1"/"canonical_open_entity_sdk_v1_1.py")

def setup():
    td=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); state=Path(td.name); v=ID.EntityIdentityVault(state)
    p=v.create("Alice","person",aliases=["alice.entity"])["entity_id"]
    a=v.create("App","application",aliases=["app.entity"])["entity_id"]
    d=v.create("Phone","system",aliases=["alice.phone.entity"])["entity_id"]
    b=PB.provision_bound_installation(state,principal_entity_id=p,application_entity_id=a,device_entity_id=d,
        display_name="Alice App",alias="alice.app.entity")
    os.environ["ENTITY_STATE_DIR"]=str(state)
    gw=load("gw_"+p[-8:],ROOT/"14_Protocols_SDK"/"open_entity_sdk"/"entity_open_sdk_gateway.py")
    return td,state,v,p,a,d,b,TestClient(gw.app)
def test_gateway_accepts_bound_user_asset_and_preserves_origin():
    td,state,v,p,a,d,b,client=setup()
    try:
        e=SDK11.make_asset_envelope(application_entity_id=a,asset_controller_entity_id=p,
            content_sha256="4"*64,size_bytes=12,media_type="application/json",title="Observation",asset_kind="DATA",
            source_subject_ref=p,contributors=[{"entity_id":p,"role":"DATA_CREATOR"}])
        e["principal_binding"]=b
        r=client.post("/entity/open-sdk/v1.1/assets",json=e)
        assert r.status_code==200, r.text
        j=r.json(); assert j["principal_binding_verified"] is True
        assert j["asset_controller_entity_id"]==p and j["origin_principal_entity_id"]==p
        with sqlite3.connect(state/"asset_registry"/"assets.sqlite") as db:
            raw=db.execute("select metadata_json from assets where asset_id=?",(j["asset"]["asset_id"],)).fetchone()[0]
        meta=json.loads(raw)
        assert meta["origin_installation_entity_id"]==b["installation_entity_id"]
        assert meta["origin_principal_entity_id"]==p and meta["origin_device_entity_id"]==d
    finally: td.cleanup()

def test_gateway_rejects_unbound_or_wrong_controller():
    td,state,v,p,a,d,b,client=setup()
    try:
        other=v.create("Bob","person",aliases=["bob.entity"])["entity_id"]
        e=SDK11.make_asset_envelope(application_entity_id=a,asset_controller_entity_id=other,
            content_sha256="5"*64,size_bytes=1,media_type="application/json",title="Wrong",asset_kind="DATA")
        e["principal_binding"]=b
        assert client.post("/entity/open-sdk/v1.1/assets",json=e).status_code==403
    finally: td.cleanup()
def test_gateway_rejects_revoked_binding():
    td,state,v,p,a,d,b,client=setup()
    try:
        PB.revoke_bound_installation(state,b)
        e=SDK11.make_asset_envelope(application_entity_id=a,asset_controller_entity_id=p,
            content_sha256="6"*64,size_bytes=1,media_type="application/json",title="Revoked",asset_kind="DATA")
        e["principal_binding"]=b
        r=client.post("/entity/open-sdk/v1.1/assets",json=e)
        assert r.status_code==403 and "binding" in r.text.lower()
    finally: td.cleanup()

def test_event_gateway_injects_principal_installation_device_subjects():
    td,state,v,p,a,d,b,client=setup()
    try:
        e={"schema":"entity-open-sdk-event-envelope-v1","application_entity_id":a,"idempotency_key":"evt-test-1",
           "event_type":"data.observation_created","payload_sha256":"7"*64,"subject_ids":[],"object_ids":[],
           "evidence_origin":"DIRECT_OBSERVATION","confidence":1.0,"raw_payload_included":False,"principal_binding":b}
        r=client.post("/entity/open-sdk/v1/events",json=e); assert r.status_code==200,r.text
        j=r.json(); assert j["principal_binding_verified"] is True and j["origin_principal_entity_id"]==p
    finally: td.cleanup()
