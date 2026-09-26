from pathlib import Path
import hashlib, importlib.util, json, sqlite3, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def sealed(path:Path)->bool:
    data=json.loads(path.read_text(encoding="utf-8")); expected=str(data.get("evidence_sha256") or "")
    body=dict(data); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return bool(expected and expected==actual)

ID=load("genesis_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
EC=load("genesis_controls",ROOT/"01_Core_Runtime"/"engineering_controls"/"canonical_engineering_controls.py")

def test_genesis_identity_rotation_device_revocation_migration_and_tamper(tmp_path):
    ids=ID.EntityIdentityVault(tmp_path)
    entity=ids.create("Genesis Entity","organization")["entity_id"]
    payload={"event":"historical-authority","value":1}
    old_sig=ids.sign(entity,payload)
    ids.rotate_signing_key(entity)
    manifest=ids.load_manifest(entity)
    assert manifest["entity_id"]==entity
    assert ID.EntityIdentityVault.verify_signature(manifest,payload,old_sig) is True
    new_sig=ids.sign(entity,{"event":"post-rotation"})
    assert ID.EntityIdentityVault.verify_signature(manifest,{"event":"post-rotation"},new_sig) is True

    cp=EC.CanonicalEngineeringControlPlane(tmp_path)
    cp.authorize_node(entity,"device-a","pub-a",["READ","WRITE"],protocol_version="1",schema_version="1",crypto_suite="ED25519")
    first=cp.reconcile_node_event("device-a","nonce-1",payload={"op":"sync"})
    second=cp.reconcile_node_event("device-a","nonce-1",payload={"op":"sync"})
    assert first==second
    cp.revoke_node("device-a")
    with pytest.raises(PermissionError):
        cp.reconcile_node_event("device-a","nonce-2",payload={"op":"write"})

    semantic=hashlib.sha256(b"genesis-semantic-root").hexdigest()
    mig=cp.record_migration("mig-1",entity_root_before=entity,entity_root_after=entity,
        semantic_root_before=semantic,semantic_root_after=semantic,source_provider="provider-a",
        destination_provider="provider-b",source_schema="v1",target_schema="v2",tool_version="genesis-1")
    assert mig["payload"]["former_provider_authority_retained"] is False
    assert mig["payload"]["historical_meaning_preserved"] is True
    with pytest.raises(ValueError):
        cp.record_migration("mig-bad",entity_root_before=entity,entity_root_after=entity,
            semantic_root_before=semantic,semantic_root_after="0"*64,source_provider="a",
            destination_provider="b",source_schema="v1",target_schema="v2",tool_version="bad")
    cp.register_sdk("WINDOWS","1.0",schema_version="1",crypto_suite="ED25519",scopes=["ASSET_WRITE"])
    a=cp.sdk_mutation("WINDOWS","sdk-nonce",scope="ASSET_WRITE",policy_allowed=True)
    b=cp.sdk_mutation("WINDOWS","sdk-nonce",scope="ASSET_WRITE",policy_allowed=True)
    assert a==b and a["replay_safe"] is True
    assert cp.verify_audit()["pass"] is True

    with sqlite3.connect(cp.path) as db:
        db.execute("UPDATE audit SET payload_json=? WHERE seq=(SELECT MIN(seq) FROM audit)",('{"tampered":true}',))
        db.commit()
    assert cp.verify_audit()["pass"] is False


def test_genesis_requires_closed_rtm_scale_and_destructive_evidence():
    rtm=json.loads((ROOT/"16_Test_Qualification"/"traceability"/"MASTER_RTM.json").read_text(encoding="utf-8"))
    assert rtm["full_internal_requirements_closed"] is True
    assert rtm["traceability_complete_count"]==rtm["requirement_count"]==1997
    assert rtm["state_counts"]["QUALIFIED"]==1997 and rtm["active_internal_unclosed_count"]==0
    assert rtm["master_source_mirrored"] is True

    ev=ROOT/"16_Test_Qualification"/"evidence"
    million=json.loads((ev/"ENTITY_MILLION_ASSET_SCALE_CURRENT.json").read_text(encoding="utf-8"))
    live=json.loads((ev/"ENTITY_MILLION_SCALE_REVALIDATION_CURRENT.json").read_text(encoding="utf-8"))
    loss=json.loads((ev/"ENTITY_BLOCK_DEVICE_LOSS_CURRENT.json").read_text(encoding="utf-8"))
    domain=json.loads((ev/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json").read_text(encoding="utf-8"))
    for p in (ev/"ENTITY_MILLION_ASSET_SCALE_CURRENT.json",ev/"ENTITY_MILLION_SCALE_REVALIDATION_CURRENT.json",ev/"ENTITY_BLOCK_DEVICE_LOSS_CURRENT.json",ev/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json"):
        assert sealed(p)
    assert million["status"]=="PASS" and million["verification"]["row_level_verified"] is True
    assert million["observed"]["assets"]==1_000_000 and million["observed"]["events"]==3_000_000
    db=Path(live["database_path"]); assert db.is_file() and db.stat().st_size==million["database"]["size_bytes"]
    assert live["status"]=="PASS" and all(live["checks"].values())
    assert loss["status"]=="PASS" and loss["whole_block_device_removed"] is True and loss["backing_media_deleted"] is True
    assert domain["status"]=="PASS" and domain["internal_gates"]["PROVIDER_INDEPENDENCE_GATE"]["pass"] is True


def test_genesis_release_control_fails_closed(tmp_path):
    cp=EC.CanonicalEngineeringControlPlane(tmp_path)
    minimal={"source_revision":"abc","build_hashes":{"x":"1"},"sbom":"s","rbom":"r","pbom":"p",
        "test_results":"t","qualification_result":"q","schema_versions":"1","crypto_versions":"1",
        "migration_versions":"1","artifact_hashes":{"a":"b"},"release_signer":"test","timestamp":"now",
        "rtm_snapshot":"rtm","release_gates":"gates"}
    denied=cp.evaluate_release([{"class":"ROOT_TAKEOVER","status":"OPEN"}],minimal)
    assert denied["pass"] is False and denied["blocking_critical_defects"]
    missing=cp.evaluate_release([],{})
    assert missing["pass"] is False and missing["missing_evidence"]
    passed=cp.evaluate_release([],minimal)
    assert passed["pass"] is True and passed["claims_bounded_to_evidence"] is True
