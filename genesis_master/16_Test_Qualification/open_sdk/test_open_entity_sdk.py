from pathlib import Path
import hashlib, importlib.util, pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
sdk=load("open_sdk",ROOT/"14_Protocols_SDK"/"open_entity_sdk"/"canonical_open_entity_sdk.py")
identity_mod=load("open_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
domain_mod=load("open_domain",ROOT/"22_Sovereign_Domain"/"core"/"canonical_domain.py")
resolver_mod=load("open_resolver",ROOT/"22_Sovereign_Domain"/"resolution"/"canonical_resolution.py")

def allow(*args,**kwargs): return {"allowed":True}
def digest(text): return hashlib.sha256(text.encode()).hexdigest()

def provision(tmp_path,alias="demo.entity",name="Demo"):
    return sdk.OpenEntityDeveloperSDK.provision_application(tmp_path,name,alias)

def add_service(state,app):
    identity=identity_mod.EntityIdentityVault(state); auth=domain_mod.EntityDomainAuthority(state,identity)
    did=app["domain"]["domain_id"]
    node=auth.authorize_node(app["entity_address"],did,"node-public-key",permitted_services=["SOFTWARE"])
    auth.publish_service(app["entity_address"],did,node["node_id"],"SOFTWARE",{"transport":"test","address":"local"})
    return auth.public_snapshot(did)
def test_duplicate_aliases_have_unique_addresses(tmp_path):
    a=provision(tmp_path,"huntar.entity","HuntAR A"); b=provision(tmp_path,"huntar.entity","HuntAR B")
    assert a["entity_address"]!=b["entity_address"]
    assert a["address"]["alias_binding_sha256"]!=b["address"]["alias_binding_sha256"]
    assert a["address"]["display_alias"]==b["address"]["display_alias"]=="huntar.entity"

def test_alias_descriptor_is_deterministic(tmp_path):
    a=provision(tmp_path,"sample.entity")
    x=sdk.address_descriptor("sample.entity",a["entity_address"]); y=sdk.address_descriptor("sample.entity",a["entity_address"])
    assert x==y and x["entity_address_is_authority"] is True and x["alias_is_authority"] is False
    assert x["collision_safe_display"].startswith("sample.entity~")

def test_resolver_rejects_ambiguous_alias_and_resolves_address(tmp_path):
    a=provision(tmp_path,"same.entity","A"); b=provision(tmp_path,"same.entity","B")
    sa=add_service(tmp_path,a); sb=add_service(tmp_path,b)
    resolver=resolver_mod.EntityNativeResolver(identity_mod.EntityIdentityVault(tmp_path))
    resolver.add_snapshot("a",sa); resolver.add_snapshot("b",sb)
    with pytest.raises(RuntimeError): resolver.resolve("same.entity")
    out=resolver.resolve(a["entity_address"],service_type="SOFTWARE")
    assert out["entity_root"]==a["entity_address"] and out["verified"] is True

def test_same_entity_multiple_artifacts_keep_identity(tmp_path):
    app=provision(tmp_path,"versioned.entity"); host=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow)
    one=host.ingest_asset(sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("v1"),size_bytes=2,media_type="application/octet-stream",title="v1",asset_kind="SOFTWARE"))
    two=host.ingest_asset(sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("v2"),size_bytes=2,media_type="application/octet-stream",title="v2",asset_kind="SOFTWARE"))
    assert one["entity_address"]==two["entity_address"]==app["entity_address"]
    assert one["asset"]["content_sha256"]!=two["asset"]["content_sha256"]
def test_data_ingest_links_origin_without_ownership(tmp_path):
    app=provision(tmp_path,"data.entity"); host=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow)
    result=host.ingest_asset(sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("observation"),size_bytes=11,media_type="application/json",title="Observation",asset_kind="DATA",source_subject_ref="user.entity"))
    stored=host.assets.get(result["asset"]["asset_id"])
    assert stored["metadata"]["producer_entity_address"]==app["entity_address"]
    assert stored["metadata"]["source_subject_ref"]=="user.entity"
    assert result["ownership_not_inferred"] is True and result["economic_value_not_inferred"] is True

def test_cross_application_lineage_preserves_parent(tmp_path):
    a=provision(tmp_path,"sensor.entity","Sensor"); b=provision(tmp_path,"model.entity","Model")
    ah=sdk.OpenEntityDeveloperSDK(tmp_path,a["entity_address"],authorizer=allow); bh=sdk.OpenEntityDeveloperSDK(tmp_path,b["entity_address"],authorizer=allow)
    parent=ah.ingest_asset(sdk.make_asset_envelope(application_entity_id=a["entity_address"],content_sha256=digest("raw"),size_bytes=3,media_type="application/json",title="Raw",asset_kind="DATA"))
    child=bh.ingest_asset(sdk.make_asset_envelope(application_entity_id=b["entity_address"],content_sha256=digest("model"),size_bytes=5,media_type="application/octet-stream",title="Model",asset_kind="MODEL",parent_asset_ids=[parent["asset"]["asset_id"]]))
    lineage=bh.provenance.lineage(child["asset"]["asset_id"])
    assert lineage["parents"][0]["parent_asset_id"]==parent["asset"]["asset_id"]
    assert lineage["parents"][0]["actor_entity_id"]==b["entity_address"]

def test_default_deny_and_raw_content_rejected(tmp_path):
    app=provision(tmp_path,"deny.entity")
    env=sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("x"),size_bytes=1,media_type="text/plain",title="x",asset_kind="DATA")
    with pytest.raises(PermissionError): sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"]).ingest_asset(env)
    env["raw_content_included"]=True
    with pytest.raises(ValueError): sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow).ingest_asset(env)
def test_forbidden_economic_event_cannot_bypass_core(tmp_path):
    app=provision(tmp_path,"economy.entity"); host=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow)
    env=sdk.make_event_envelope(application_entity_id=app["entity_address"],event_type="application.settlement_created",payload_sha256=digest("p"))
    with pytest.raises(PermissionError): host.record_event(env)

def test_explicit_rights_claim_remains_self_asserted(tmp_path):
    app=provision(tmp_path,"rights.entity"); host=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow)
    env=sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("asset"),size_bytes=5,media_type="application/octet-stream",title="Asset",asset_kind="DATA",explicit_rights_claim={"claimant_entity_id":app["entity_address"],"right_type":"DATA_CONTROLLER","legal_basis":"developer_assertion","evidence":{"reference":"test"}})
    result=host.ingest_asset(env); claim=result["explicit_rights_claims"][0]
    assert claim["verification_level"]=="SELF_ASSERTED"
    assert claim["claimant_entity_id"]==app["entity_address"]

def test_idempotency_replay_is_stable(tmp_path):
    app=provision(tmp_path,"replay.entity"); host=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow)
    env=sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("same"),size_bytes=4,media_type="text/plain",title="same",asset_kind="DATA",idempotency_key="fixed")
    first=host.ingest_asset(env); second=host.ingest_asset(env)
    assert first["asset"]["asset_id"]==second["asset"]["asset_id"] and second["idempotent_replay"] is True

def test_sdk_is_provider_neutral(tmp_path):
    app=provision(tmp_path,"neutral.entity"); status=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow).status()
    assert status["provider_neutral"] is True and status["btg_dependency_required"] is False
def test_foreign_rights_claim_requires_explicit_delegation(tmp_path):
    app=provision(tmp_path,"delegate.entity"); identity=identity_mod.EntityIdentityVault(tmp_path)
    other=identity.create("Other Controller","organization")["entity_id"]
    env=sdk.make_asset_envelope(application_entity_id=app["entity_address"],content_sha256=digest("delegated"),size_bytes=9,media_type="application/json",title="Delegated",asset_kind="DATA",explicit_rights_claim={"claimant_entity_id":other,"right_type":"DATA_CONTROLLER","legal_basis":"delegated_test","evidence":{"reference":"delegation"}})
    with pytest.raises(PermissionError): sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=allow).ingest_asset(env)
    def delegated_authorizer(*args,**kwargs): return {"allowed":True,"authorized_rights_claimants":[other]}
    result=sdk.OpenEntityDeveloperSDK(tmp_path,app["entity_address"],authorizer=delegated_authorizer).ingest_asset(env)
    assert result["explicit_rights_claims"][0]["claimant_entity_id"]==other
