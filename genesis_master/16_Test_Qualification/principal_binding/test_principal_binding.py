from pathlib import Path
import importlib.util, json, tempfile

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
PB=load("pb",ROOT/"14_Protocols_SDK"/"principal_binding"/"canonical_principal_binding.py")
ID=load("idv",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
SDK11=load("sdk11",ROOT/"14_Protocols_SDK"/"open_entity_sdk_v1_1"/"canonical_open_entity_sdk_v1_1.py")

def fixture():
    td=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); state=Path(td.name); v=ID.EntityIdentityVault(state)
    principal=v.create("Alice","person",aliases=["alice.entity"])["entity_id"]
    app=v.create("Example App","application",aliases=["example.entity"])["entity_id"]
    device=v.create("Alice Phone","system",aliases=["alice.phone.entity"])["entity_id"]
    binding=PB.provision_bound_installation(state,principal_entity_id=principal,application_entity_id=app,
        device_entity_id=device,display_name="Alice Example",alias="alice.example.entity")
    return td,state,v,principal,app,device,binding
def test_valid_binding_and_alias_chain():
    td,state,v,p,a,d,b=fixture()
    try:
        q=PB.validate_bound_installation(state,b)
        assert q["valid"] and q["principal_entity_id"]==p and q["application_entity_id"]==a
        assert b["installation_alias"]=="alice.example.entity"
        assert b["address"]["entity_address"]==b["installation_entity_id"]
        assert b["address"]["alias_is_authority"] is False
    finally: td.cleanup()

def test_tampered_principal_fails():
    td,state,v,p,a,d,b=fixture()
    try:
        other=v.create("Mallory","person",aliases=["mallory.entity"])["entity_id"]
        x=json.loads(json.dumps(b)); x["principal_entity_id"]=other
        assert PB.validate_bound_installation(state,x)["valid"] is False
    finally: td.cleanup()
def test_wrong_application_fails_even_if_hash_rewritten():
    td,state,v,p,a,d,b=fixture()
    try:
        other=v.create("Other App","application",aliases=["other.entity"])["entity_id"]
        x=json.loads(json.dumps(b)); x["application_entity_id"]=other
        body={k:v for k,v in x.items() if k not in {"principal_signature","binding_sha256"}}
        x["binding_sha256"]=PB._sha(body)
        assert PB.validate_bound_installation(state,x)["valid"] is False
    finally: td.cleanup()

def test_principal_revocation_invalidates_future_use():
    td,state,v,p,a,d,b=fixture()
    try:
        assert PB.validate_bound_installation(state,b)["valid"]
        PB.revoke_bound_installation(state,b)
        q=PB.validate_bound_installation(state,b)
        assert q["valid"] is False and q["reason"]=="binding_relationship_inactive"
    finally: td.cleanup()
def test_bound_sdk_records_user_as_controller_not_app():
    td,state,v,p,a,d,b=fixture()
    try:
        sdk=SDK11.OpenEntityDeveloperSDKv11(state,a,authorizer=PB.binding_authorizer(state,b))
        e=SDK11.make_asset_envelope(application_entity_id=a,asset_controller_entity_id=p,
            content_sha256="1"*64,size_bytes=10,media_type="application/json",title="Observation",asset_kind="DATA",
            source_subject_ref=p,contributors=[{"entity_id":p,"role":"DATA_CREATOR"}])
        r=sdk.ingest_asset(e)
        assert r["asset_controller_entity_id"]==p and r["producer_entity_address"]==a
        assert r["ownership_not_inferred"] is True and r["asset"]["controller_entity_id"]==p
    finally: td.cleanup()

def test_cross_user_controller_substitution_denied():
    td,state,v,p,a,d,b=fixture()
    try:
        other=v.create("Bob","person",aliases=["bob.entity"])["entity_id"]
        sdk=SDK11.OpenEntityDeveloperSDKv11(state,a,authorizer=PB.binding_authorizer(state,b))
        e=SDK11.make_asset_envelope(application_entity_id=a,asset_controller_entity_id=other,
            content_sha256="2"*64,size_bytes=1,media_type="application/json",title="Wrong user",asset_kind="DATA")
        try: sdk.ingest_asset(e); assert False,"cross-user substitution accepted"
        except PermissionError: pass
    finally: td.cleanup()
def test_app_cannot_claim_user_rights_without_separate_delegation():
    td,state,v,p,a,d,b=fixture()
    try:
        sdk=SDK11.OpenEntityDeveloperSDKv11(state,a,authorizer=PB.binding_authorizer(state,b))
        e=SDK11.make_asset_envelope(application_entity_id=a,asset_controller_entity_id=p,
            content_sha256="3"*64,size_bytes=1,media_type="application/json",title="Rights",asset_kind="DATA",
            explicit_rights_claim={"claimant_entity_id":p,"right_type":"CONTROL","legal_basis":"USER_CREATION",
                                   "evidence":{"binding_id":b["binding_id"]}})
        try: sdk.ingest_asset(e); assert False,"application asserted principal rights without rights delegation"
        except PermissionError: pass
    finally: td.cleanup()

def test_binding_allows_events_but_not_undelegated_operations():
    td,state,v,p,a,d,b=fixture()
    try:
        auth=PB.binding_authorizer(state,b)
        assert auth({"application_entity_id":a},"RECORD_EVENT")["allowed"] is True
        assert auth({"application_entity_id":a},"SET_POLICY")["allowed"] is False
    finally: td.cleanup()
