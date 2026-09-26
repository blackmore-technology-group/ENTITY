from __future__ import annotations
from pathlib import Path
import importlib.util, sys

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def test_section172_provider_replacement_preserves_sovereign_authority(tmp_path):
    I=load("s172_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    S=load("s172_authority",ROOT/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py")
    state=tmp_path/"state"; ids=I.EntityIdentityVault(state); entity=ids.create("Section 172 Owner","organization")["entity_id"]
    reg=S.SovereignAuthorityRegistry(state,ids); provider_a="storage-provider-a"; provider_b="storage-provider-b"
    sovereign=reg.grant_relationship(entity,entity,"SOVEREIGN_AUTHORITY",scope={"domain":"entity-root"},evidence_origin="DIRECT_OBSERVATION")
    storage_a=reg.bind_storage(entity,provider_a,"provider-a://vault/entity",evidence={"contract_ref":"storage-a-1"})
    reg.grant_relationship(entity,provider_a,"PROCESSING_AUTHORITY",scope={"purpose":"encrypted-backup"},evidence_origin="COUNTERPARTY_ATTESTATION")
    denied=reg.authorize_relationship_action(entity,provider_a,"GRANT_LICENCE")
    assert denied["allowed"] is False and denied["required_relationship"]=="LICENSING_AUTHORITY"
    assert "STORAGE_CONTROL" in denied["observed_relationships"] and "PROCESSING_AUTHORITY" in denied["observed_relationships"]
    licence_auth=reg.grant_relationship(entity,provider_a,"LICENSING_AUTHORITY",scope={"asset_scope":["asset-demo"],"purpose":"limited-licensing"},evidence_origin="ENTITY_ASSERTION")
    assert reg.authorize_relationship_action(entity,provider_a,"GRANT_LICENCE")["allowed"] is True
    reg.revoke_relationship(entity,licence_auth["relationship_id"],"provider replacement")
    assert reg.authorize_relationship_action(entity,provider_a,"GRANT_LICENCE")["allowed"] is False
    assert reg.authorize_relationship_action(entity,provider_a,"GRANT_CONSENT")["allowed"] is False

    before=reg.authority_semantic_hash(entity)
    participation=reg.record_economic_participation(entity,"contributor-1",basis_ref="contract-royalty-1",participation_type="ROYALTY",terms={"basis_points":750})
    with_participation=reg.authority_semantic_hash(entity); assert with_participation!=before
    migration=reg.migrate_storage_provider(entity,storage_a["binding_id"],provider_b,"provider-b://vault/entity",export_sha256="ab"*32,evidence={"contract_ref":"storage-b-1"})
    assert migration["status"]=="VERIFIED" and migration["entity_root_unchanged"] is True
    assert migration["pre_semantic_sha256"]==migration["post_semantic_sha256"]==with_participation
    assert reg.authorize_relationship_action(entity,provider_b,"GRANT_LICENCE")["allowed"] is False
    assert reg.authorize_relationship_action(entity,provider_a,"GRANT_LICENCE")["allowed"] is False

    active_a={x["relationship_type"] for x in reg.active_relationships(entity,provider_a)}
    active_b={x["relationship_type"] for x in reg.active_relationships(entity,provider_b)}
    assert "STORAGE_CONTROL" not in active_a and "STORAGE_CONTROL" in active_b
    assert "SOVEREIGN_AUTHORITY" not in active_a and "SOVEREIGN_AUTHORITY" not in active_b

    manifest=reg.export_manifest(entity); signed_body={k:v for k,v in manifest.items() if k not in {"signature","snapshot","provider_independent"}}
    assert manifest["provider_independent"] is True
    assert ids.verify_signature(ids.load_manifest(entity),signed_body,manifest["signature"]) is True
    assert manifest["snapshot"]["semantic_sha256"]==reg.semantic_snapshot(entity)["semantic_sha256"]
    assert reg.status()["custody_is_not_authority"] is True and participation["basis_ref"]=="contract-royalty-1"
