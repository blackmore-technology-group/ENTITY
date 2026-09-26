from pathlib import Path
import base64, importlib.util, json, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("phase1_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
P=load("phase1_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
C=load("phase1_caps",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py")
S=load("phase1_sources",ROOT/"08_Data_Vaults"/"canonical_data_source_gateway.py")
V=load("phase1_vault",ROOT/"08_Data_Vaults"/"canonical_encrypted_vault.py")
B=load("phase1_portable",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")


def test_source_gateway_is_default_deny_and_modes_are_independent(tmp_path):
    gateway=S.DataSourceGateway(tmp_path/"state")
    root=tmp_path/"source"; root.mkdir(); f=root/"note.txt"; f.write_text("private")
    assert gateway.assess_path(f,purpose="discover")["allowed"] is False
    src=gateway.enroll_source("entity-test",root,mode="OBSERVE",discovery_allowed=True)
    assert gateway.assess_path(f,purpose="discover")["allowed"] is True
    assert gateway.assess_path(f,purpose="content")["allowed"] is False
    with pytest.raises(PermissionError): gateway.enroll_source("entity-test",root,mode="OBSERVE",content_allowed=True)
    with pytest.raises(PermissionError): gateway.enroll_source("entity-test",root,mode="INDEX",content_allowed=True,niki_content_allowed=True,economic_allowed=True)

def test_hard_source_exclusions_override_enrollment(tmp_path):
    gateway=S.DataSourceGateway(tmp_path/"state")
    root=tmp_path/"source"; secret=root/"private_keys"; secret.mkdir(parents=True)
    key=secret/"root.key"; key.write_text("secret")
    gateway.enroll_source("entity-test",root,mode="MANAGED",discovery_allowed=True,content_allowed=True,economic_allowed=True)
    decision=gateway.assess_path(key,purpose="content")
    assert decision["allowed"] is False and decision["reason"]=="excluded" and decision["exclusion"]["hard"] is True


def test_vault_encrypts_and_cryptographic_erasure_destroys_access(tmp_path):
    vault=V.EncryptedDataVault(tmp_path/"state"); raw=b"highly private payload"
    obj=vault.put_bytes("entity-a",raw,classification="RESTRICTED")
    assert vault.read_bytes("entity-a",obj["vault_object_id"])==raw
    row=vault._row(obj["vault_object_id"])
    assert raw not in vault._storage_path(row["cipher_path"],"cipher").read_bytes()
    with pytest.raises(PermissionError): vault.read_bytes("entity-b",obj["vault_object_id"])
    vault.lifecycle("entity-a",obj["vault_object_id"],"CRYPTOGRAPHICALLY_ERASED")
    with pytest.raises(PermissionError): vault.read_bytes("entity-a",obj["vault_object_id"])


def test_vault_remote_deletion_states_do_not_overclaim(tmp_path):
    vault=V.EncryptedDataVault(tmp_path/"state"); obj=vault.put_bytes("entity-a",b"x")
    requested=vault.lifecycle("entity-a",obj["vault_object_id"],"REMOTE_DELETION_REQUESTED")
    assert requested["remote_deletion_verified"] is False
    attested=vault.lifecycle("entity-a",obj["vault_object_id"],"REMOTE_DELETION_ATTESTED")
    assert attested["remote_deletion_verified"] is True

def test_encrypted_backup_restore_recovers_identity_policy_capability_and_vault(tmp_path):
    state=tmp_path/"state"; identity=I.EntityIdentityVault(state)
    entity_id=identity.create("Sovereign Recovery","organization")["entity_id"]
    payload={"event":"before-loss"}; historical=identity.sign(entity_id,payload)
    policy=P.PolicyConsentEngine(state,identity); p=policy.create_policy(entity_id,"Recovery",{"VIEW":"PERMIT"})
    caps=C.AuthorityCapabilityStore(state,identity); cap=caps.grant(entity_id,"agent-1",operations=["EXPORT"])
    vault=V.EncryptedDataVault(state); obj=vault.put_bytes(entity_id,b"recoverable private bytes")
    portable=B.PortableStateManager(state,identity); backup=portable.create_encrypted_backup(tmp_path/"state.enc")
    key=base64.urlsafe_b64decode(backup["key_b64"]); restored=tmp_path/"restored"
    portable.restore_encrypted_backup(backup["path"],key,restored)
    restored_identity=I.EntityIdentityVault(restored); manifest=restored_identity.load_manifest(entity_id)
    assert I.EntityIdentityVault.verify_signature(manifest,payload,historical)
    restored_policy=P.PolicyConsentEngine(restored,restored_identity)
    assert restored_policy.evaluate(p["policy_id"],"VIEW")["allowed"] is True
    restored_caps=C.AuthorityCapabilityStore(restored,restored_identity)
    assert restored_caps.authorize(cap["capability_id"],"agent-1","EXPORT")["allowed"] is True
    restored_vault=V.EncryptedDataVault(restored)
    assert restored_vault.read_bytes(entity_id,obj["vault_object_id"])==b"recoverable private bytes"

def test_portable_export_is_json_redacted_and_excludes_private_keys(tmp_path):
    state=tmp_path/"state"; identity=I.EntityIdentityVault(state)
    entity_id=identity.create("Portable Owner","person")["entity_id"]
    vault=V.EncryptedDataVault(state); vault.put_bytes(entity_id,b"portable secret")
    export_dir=tmp_path/"export"; evidence=B.PortableStateManager(state,identity).export_entity(entity_id,export_dir)
    assert evidence["private_keys_included"] is False and evidence["raw_vault_content_included"] is False
    assert evidence["local_paths_redacted"] is True and evidence["formats"]==["JSON"]
    assert (export_dir/"identity_manifest.json").is_file() and (export_dir/"EXPORT_MANIFEST.json").is_file()
    exported="\n".join(p.read_text(encoding="utf-8") for p in export_dir.glob("*.json"))
    assert "portable secret" not in exported
    assert "REDACTED_FROM_PORTABLE_EXPORT" in exported
