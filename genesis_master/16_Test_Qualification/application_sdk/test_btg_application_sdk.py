from pathlib import Path
import hashlib, importlib.util, json, pytest
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
SDK=load("test_btg_sdk",ROOT/"14_Protocols_SDK"/"btg_application_sdk"/"canonical_btg_application_sdk.py")
ID=load("test_btg_sdk_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")

def setup_sdk(tmp_path,allow=True):
    ids=ID.EntityIdentityVault(tmp_path); org=ids.create("Blackmore Technology Group Limited","organization")
    provision=SDK.BTGApplicationSDK.provision_application(tmp_path,org["entity_id"],"HUNTAR","huntar.entity")
    auth=(lambda envelope,op:{"allowed":True,"operation":op}) if allow else None
    sdk=SDK.BTGApplicationSDK(tmp_path,provision["application_entity_id"],org["entity_id"],authorizer=auth)
    return ids,org,provision,sdk

def digest(text): return hashlib.sha256(text.encode()).hexdigest()

def basic_envelope(sdk,**kw):
    data=dict(application_entity_id=sdk.application_entity_id,organization_entity_id=sdk.organization_entity_id,content_sha256=digest("observation-1"),size_bytes=128,media_type="application/json",title="Field observation",asset_kind="DATA",classification="PRIVATE",metadata={"species":"elk"},source_subject_ref="hunter:user-1",idempotency_key="obs-1")
    data.update(kw); return SDK.make_asset_envelope(**data)

def test_application_entity_is_separate_and_btg_control_is_explicit(tmp_path):
    ids,org,provision,sdk=setup_sdk(tmp_path); app=ids.load_manifest(provision["application_entity_id"])
    assert app["entity_id"]!=org["entity_id"] and "huntar.entity" in app["aliases"]
    rel=sdk.sovereign.active_relationships(app["entity_id"],org["entity_id"])
    assert any(x["relationship_type"]=="SOVEREIGN_AUTHORITY" for x in rel)
    assert all((x["scope"].get("asset_ownership_not_implied") is True) for x in rel if x["relationship_type"]=="SOVEREIGN_AUTHORITY")

def test_data_ingest_preserves_subject_and_does_not_infer_btg_ownership(tmp_path):
    ids,org,provision,sdk=setup_sdk(tmp_path); result=sdk.ingest_asset(basic_envelope(sdk))
    asset=sdk.assets.get(result["asset"]["asset_id"])
    assert asset["metadata"]["source_subject_ref"]=="hunter:user-1"
    assert result["ownership_not_inferred"] is True and result["economic_value_not_inferred"] is True
    claims=sdk.rights.claims_for_asset(asset["asset_id"])
    assert not any(x["claimant_entity_id"]==org["entity_id"] for x in claims)
    assert sdk.ledger.verify()["pass"] is True

def test_explicit_btg_rights_claim_requires_basis_and_remains_self_asserted(tmp_path):
    ids,org,provision,sdk=setup_sdk(tmp_path)
    claim={"right_type":"DATA_CONTROLLER","legal_basis":"signed contributor terms ref BTG-001","evidence":{"terms_sha256":digest("terms")},"scope":{"research_use":True}}
    result=sdk.ingest_asset(basic_envelope(sdk,idempotency_key="obs-rights",explicit_rights_claim=claim))
    recorded=result["explicit_organization_rights_claims"][0]
    assert recorded["claimant_entity_id"]==org["entity_id"]
    assert recorded["verification_level"]=="SELF_ASSERTED" and recorded["evidence_origin"]=="ENTITY_ASSERTION"

def test_missing_rights_evidence_fails_closed(tmp_path):
    _,_,_,sdk=setup_sdk(tmp_path)
    claim={"right_type":"DATA_CONTROLLER","legal_basis":"terms","evidence":{}}
    with pytest.raises(ValueError): sdk.ingest_asset(basic_envelope(sdk,idempotency_key="bad-rights",explicit_rights_claim=claim))

def test_default_deny_authorization(tmp_path):
    ids,org,provision,_=setup_sdk(tmp_path)
    sdk=SDK.BTGApplicationSDK(tmp_path,provision["application_entity_id"],org["entity_id"])
    with pytest.raises(PermissionError): sdk.ingest_asset(basic_envelope(sdk,idempotency_key="deny"))

def test_idempotency_replays_same_result_and_rejects_key_reuse(tmp_path):
    _,_,_,sdk=setup_sdk(tmp_path); env=basic_envelope(sdk,idempotency_key="idem-1")
    first=sdk.ingest_asset(env); second=sdk.ingest_asset(env)
    assert first["asset"]["asset_id"]==second["asset"]["asset_id"] and second["idempotent_replay"] is True
    changed=dict(env); changed["content_sha256"]=digest("changed")
    with pytest.raises(ValueError): sdk.ingest_asset(changed)

def test_raw_content_is_rejected(tmp_path):
    _,_,_,sdk=setup_sdk(tmp_path); env=basic_envelope(sdk,idempotency_key="raw")
    env["raw_content_included"]=True
    with pytest.raises(ValueError): sdk.ingest_asset(env)

def test_model_derivation_preserves_lineage(tmp_path):
    _,_,_,sdk=setup_sdk(tmp_path)
    parent=sdk.ingest_asset(basic_envelope(sdk,idempotency_key="parent"))["asset"]["asset_id"]
    env=basic_envelope(sdk,idempotency_key="model",content_sha256=digest("model-v2"),title="Habitat model",asset_kind="MODEL",parent_asset_ids=[parent],contributors=[{"type":"application","ref":"huntar.entity"}])
    child=sdk.ingest_asset(env); lineage=sdk.provenance.lineage(child["asset"]["asset_id"])
    assert any(x["parent_asset_id"]==parent and x["relation"]=="model_output" for x in lineage["parents"])
    assert child["knowledge_receipt"]["ownership_not_inferred"] is True

def test_application_event_cannot_bypass_economic_or_authority_subsystems(tmp_path):
    _,_,_,sdk=setup_sdk(tmp_path)
    bad=SDK.make_event_envelope(application_entity_id=sdk.application_entity_id,organization_entity_id=sdk.organization_entity_id,event_type="application.settlement.created",payload_sha256=digest("x"),idempotency_key="bad-event")
    with pytest.raises(PermissionError): sdk.record_event(bad)
    good=SDK.make_event_envelope(application_entity_id=sdk.application_entity_id,organization_entity_id=sdk.organization_entity_id,event_type="data.observation.created",payload_sha256=digest("obs"),idempotency_key="good-event")
    result=sdk.record_event(good)
    assert result["economic_state_mutated"] is False and result["rights_state_mutated"] is False
