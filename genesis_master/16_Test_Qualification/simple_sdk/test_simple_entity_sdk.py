from pathlib import Path
import hashlib, importlib.util, json, pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
S=load("entity_simple_sdk_test",ROOT/"14_Protocols_SDK"/"simple_sdk"/"canonical_simple_entity_sdk.py")

def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def fixture(tmp_path):
    sdk=S.SimpleEntitySDK(tmp_path)
    principal=sdk.create_entity("Alice",alias="alice.entity")["entity_id"]
    app=sdk.create_application("Field App","field.entity",controller_entity_id=principal)["application_entity_id"]
    device=sdk.create_entity("Alice Phone",entity_type="system",alias="alice.phone.entity")["entity_id"]
    binding=sdk.pair_device(principal_entity_id=principal,application_entity_id=app,device_entity_id=device,
        display_name="Alice Field App",alias="alice.field.entity")
    return sdk,principal,app,device,binding

def test_public_surface_is_small(tmp_path):
    sdk=S.SimpleEntitySDK(tmp_path); status=sdk.status()
    assert status["ready"] is True
    assert status["developer_surface"]==["create_entity","create_application","pair_device","register_asset","record_event","export_entity"]
    assert status["full_move_workflow_claimed"] is False

def test_principal_bound_asset_and_event_workflow(tmp_path):
    sdk,principal,app,device,binding=fixture(tmp_path)
    assert sdk.verify_pairing(binding)["valid"] is True
    asset=sdk.register_asset(binding,content_sha256=digest("observation"),size_bytes=11,
        media_type="application/json",title="Observation",asset_kind="DATA")
    assert asset["asset_controller_entity_id"]==principal
    assert asset["producer_entity_address"]==app
    assert asset["ownership_not_inferred"] is True
    event=sdk.record_event(binding,event_type="data.observation_recorded",payload_sha256=digest("event"),
        subject_ids=[principal],object_ids=[asset["asset"]["asset_id"]])
    assert event["non_authoritative_application_event"] is True
    assert event["economic_state_mutated"] is False

def test_revocation_fails_closed(tmp_path):
    sdk,principal,app,device,binding=fixture(tmp_path)
    sdk.revoke_device(binding)
    assert sdk.verify_pairing(binding)["valid"] is False
    with pytest.raises(PermissionError):
        sdk.register_asset(binding,content_sha256=digest("x"),size_bytes=1,media_type="text/plain",
            title="x",asset_kind="DATA")

def test_forbidden_economic_transition_stays_outside_simple_sdk(tmp_path):
    sdk,principal,app,device,binding=fixture(tmp_path)
    with pytest.raises(PermissionError):
        sdk.record_event(binding,event_type="application.payment_settled",payload_sha256=digest("payment"))

def test_signed_export_verifies_and_tamper_fails(tmp_path):
    sdk,principal,app,device,binding=fixture(tmp_path)
    sdk.register_asset(binding,content_sha256=digest("portable"),size_bytes=8,
        media_type="application/json",title="Portable",asset_kind="DATA")
    dest=tmp_path/"export"
    sdk.export_entity(principal,dest)
    good=sdk.verify_export(dest)
    assert good["valid"] is True and good["entity_id"]==principal
    target=next(p for p in dest.iterdir() if p.name not in {"identity_manifest.json","EXPORT_MANIFEST.json"})
    target.write_text(target.read_text(encoding="utf-8")+"\nTAMPER",encoding="utf-8")
    bad=sdk.verify_export(dest)
    assert bad["valid"] is False and target.name in bad["file_hash_failures"]

def test_user_experience_profile_hides_internal_complexity():
    profile=json.loads((ROOT/"14_Protocols_SDK"/"simple_sdk"/"ENTITY_USER_EXPERIENCE_PROFILE_v1.json").read_text(encoding="utf-8"))
    labels={x["label"]:x for x in profile["user_actions"]}
    assert profile["internal_authority_count_exposed_to_user"]==0
    assert profile["raw_key_management_required_from_normal_user"] is False
    assert labels["Pair Device"]["sdk_operation"]=="pair_device"
    assert labels["Created by me — verified"]["must_not_mean"]=="Legal ownership or factual truth automatically proven"
    assert labels["Move My Entity"]["status"]=="RESERVED_UNTIL_END_TO_END_PROVIDER_MIGRATION_IS_QUALIFIED"
