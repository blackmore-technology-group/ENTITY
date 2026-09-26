from pathlib import Path
import importlib.util, json, sys
import pytest
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def test_credential_history_selective_disclosure_and_revocation(tmp_path):
    im=load("cm_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    crm=load("cm_cred",ROOT/"04_Entity_Registry"/"credentials"/"canonical_credentials.py")
    state=tmp_path/"state"; ids=im.EntityIdentityVault(state)
    issuer=ids.create("Issuer","organization")["entity_id"]; subject=ids.create("Subject","person")["entity_id"]
    store=crm.CredentialTrustStore(state,ids)
    cred=store.issue(issuer,subject,"QUALIFICATION",{"role":"tester","secret_note":"hidden"},trust_level="ORGANIZATION_VERIFIED")
    assert store.verify(cred["credential_id"])["active"] is True
    disclosed=store.selective_disclosure(cred["credential_id"],["role"])
    assert disclosed["disclosed_claims"]=={"role":"tester"} and disclosed["undisclosed_claim_count"]==1
    ids.recover_signing_key(issuer)
    assert store.verify(cred["credential_id"])["signature_valid"] is True
    store.revoke(issuer,cred["credential_id"])
    verified=store.verify(cred["credential_id"]); assert verified["signature_valid"] is True and verified["active"] is False

def test_migration_configuration_is_signed_portable_and_tamper_evident(tmp_path):
    im=load("mig_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    mm=load("mig_config",ROOT/"15_Operations"/"migration"/"canonical_migration_config.py")
    state=tmp_path/"state"; ids=im.EntityIdentityVault(state); owner=ids.create("Owner","organization")["entity_id"]
    mgr=mm.MigrationConfiguration(state,ids); record=mgr.create(owner,external_dependencies=[{"provider":"payment-provider","locally_recoverable":False}])
    check=mgr.verify(); assert check["pass"] is True and check["relative_domain_paths"] is True
    record["state_format"]="PROPRIETARY_ONLY"; mgr.path.write_text(json.dumps(record),encoding="utf-8")
    assert mgr.verify()["pass"] is False
