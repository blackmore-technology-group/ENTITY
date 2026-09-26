from pathlib import Path
import importlib.util, os
import pytest

NETWORK = Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
CORE = NETWORK / "01_Core_Runtime"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.setenv("ENTITY_CANONICAL_CORE_STATE", str(tmp_path / "state"))
    identity_mod = load_module("canonical_identity_test", CORE / "identity" / "canonical_identity.py")
    policy_mod = load_module("canonical_policy_test", CORE / "policy_engine" / "canonical_policy.py")
    permissions_mod = load_module("canonical_permissions_test", CORE / "permissions" / "canonical_permissions.py")
    service_mod = load_module("canonical_service_test", CORE / "api" / "canonical_service.py")
    identity = identity_mod.EntityIdentityVault(tmp_path / "state")
    return identity_mod, policy_mod, permissions_mod, service_mod, identity


def test_identity_root_survives_rotation_and_recovery(core):
    identity_mod, _, _, _, identity = core
    created = identity.create("Qualification Entity", "person")
    entity_id = created["entity_id"]
    payload = {"purpose":"historical-proof"}
    original_sig = identity.sign(entity_id, payload)
    rotated = identity.rotate_signing_key(entity_id)
    assert rotated["entity_id"] == entity_id
    assert identity_mod.EntityIdentityVault.verify_signature(rotated, payload, original_sig)
    recovered = identity.recover_signing_key(entity_id)
    assert recovered["entity_id"] == entity_id
    assert recovered["active_signing_key_id"] != rotated["active_signing_key_id"]
    assert identity_mod.EntityIdentityVault.verify_manifest(recovered)


def test_pairwise_identifiers_are_relationship_specific(core):
    _, _, _, _, identity = core
    entity_id = identity.create("Pairwise Entity", "person")["entity_id"]
    a = identity.pairwise_id(entity_id, "service-a")
    b = identity.pairwise_id(entity_id, "service-b")
    assert a != b and a == identity.pairwise_id(entity_id, "service-a")


def test_policy_is_versioned_purpose_bound_and_fail_closed(core):
    _, policy_mod, _, _, identity = core
    entity_id = identity.create("Policy Entity", "person")["entity_id"]
    policy = policy_mod.PolicyConsentEngine(Path(os.environ["ENTITY_CANONICAL_CORE_STATE"]), identity)
    p = policy.create_policy(entity_id, "Controlled", {"VIEW":"PERMIT", "AI_TRAINING":"PROHIBIT"})
    assert policy.evaluate(p["policy_id"], "UNKNOWN")["allowed"] is False
    assert policy.evaluate(p["policy_id"], "AI_TRAINING")["allowed"] is False
    consent = policy.grant_consent(entity_id, p["policy_id"], purpose="research", asset_scope=["asset-1"], counterparty_entity_id="peer-1")
    ok = policy.authorize_consent(consent["consent_id"], counterparty_entity_id="peer-1", purpose="research", asset_scope=["asset-1"], action="VIEW")
    bad = policy.authorize_consent(consent["consent_id"], counterparty_entity_id="peer-1", purpose="advertising", asset_scope=["asset-1"], action="VIEW")
    assert ok["allowed"] is True and bad["allowed"] is False
    revised = policy.revise_policy(entity_id, p["policy_id"], {"VIEW":"PROHIBIT"})
    assert revised["version"] == 2
    historical = policy.authorize_consent(consent["consent_id"], counterparty_entity_id="peer-1", purpose="research", asset_scope=["asset-1"], action="VIEW")
    assert historical["allowed"] is True and historical["policy"]["policy_version"] == 1


def test_capability_scope_expiry_approval_and_revocation_fail_closed(core):
    _, _, permissions_mod, _, identity = core
    entity_id = identity.create("Authority Entity", "person")["entity_id"]
    store = permissions_mod.AuthorityCapabilityStore(Path(os.environ["ENTITY_CANONICAL_CORE_STATE"]), identity)
    cap = store.grant(entity_id, "agent-1", operations=["EXPORT"], asset_scope=["asset-1"], counterparty_scope=["peer-1"], financial_limit=100, approval_required=True)
    denied = store.authorize(cap["capability_id"], "agent-1", "EXPORT", asset_id="asset-1", counterparty_id="peer-1", amount=50, object_ref="job-1")
    assert denied["allowed"] is False and denied["reason"] == "approval_required"
    store.approve(entity_id, cap["capability_id"], "EXPORT", "job-1")
    assert store.authorize(cap["capability_id"], "agent-1", "EXPORT", asset_id="asset-1", counterparty_id="peer-1", amount=50, object_ref="job-1")["allowed"] is True
    assert store.authorize(cap["capability_id"], "agent-1", "EXPORT", asset_id="asset-2", counterparty_id="peer-1", amount=50, object_ref="job-1")["allowed"] is False
    assert store.authorize(cap["capability_id"], "agent-1", "EXPORT", asset_id="asset-1", counterparty_id="peer-1", amount=500, object_ref="job-1")["allowed"] is False
    store.revoke(entity_id, cap["capability_id"])
    assert store.authorize(cap["capability_id"], "agent-1", "EXPORT", asset_id="asset-1", counterparty_id="peer-1")["allowed"] is False


def test_canonical_bootstrap_requires_root_authorization_and_is_single_use(core):
    _, _, _, service, _ = core
    info = service.ensure_bootstrap_secret_v1()
    token = Path(info["path"]).read_text(encoding="utf-8").strip()
    with pytest.raises(PermissionError): service.entity_bootstrap_v1(request={"display_name":"Root"})
    result = service.entity_bootstrap_v1(request={"display_name":"Root","entity_type":"organization","bootstrap_token":token})
    assert result["manifest"]["entity_id"].startswith("ent2-")
    assert "10_NIKI" not in result["state_root"]
    with pytest.raises(RuntimeError): service.entity_bootstrap_v1(request={"display_name":"Second","bootstrap_token":token})


def test_sers_acceptance_cannot_self_declare_success(core):
    _, _, _, service, _ = core
    with pytest.raises(RuntimeError, match="qualification evidence"):
        service.sers_acceptance_v1(request={}, required_steps=["bootstrap_entity_a"])


def test_threshold_authority_requires_distinct_m_of_n_approvers(core):
    _, _, permissions_mod, _, identity = core
    controller = identity.create("Threshold Controller", "organization")["entity_id"]
    a = identity.create("Approver A", "person")["entity_id"]
    b = identity.create("Approver B", "person")["entity_id"]
    c = identity.create("Approver C", "person")["entity_id"]
    store = permissions_mod.ThresholdAuthorityStore(Path(os.environ["ENTITY_CANONICAL_CORE_STATE"]), identity)
    policy = store.create_policy(controller, "ROOT_AUTHORITY_CHANGE", [a,b,c], 2)
    assert store.authorize(policy["policy_id"], "req-1", "ROOT_AUTHORITY_CHANGE", "root-key")["allowed"] is False
    store.approve(policy["policy_id"], "req-1", a, "root-key")
    assert store.authorize(policy["policy_id"], "req-1", "ROOT_AUTHORITY_CHANGE", "root-key")["allowed"] is False
    with pytest.raises(ValueError, match="duplicate"):
        store.approve(policy["policy_id"], "req-1", a, "root-key")
    store.approve(policy["policy_id"], "req-1", b, "root-key")
    result = store.authorize(policy["policy_id"], "req-1", "ROOT_AUTHORITY_CHANGE", "root-key")
    assert result["allowed"] is True and result["approvals"] == 2 and result["threshold"] == 2

def test_destructive_encrypted_backup_restore_preserves_core_authority(core, tmp_path):
    identity_mod, policy_mod, permissions_mod, _, identity = core
    state = Path(os.environ["ENTITY_CANONICAL_CORE_STATE"])
    entity_id = identity.create("Recovery Entity", "organization")["entity_id"]
    policy = policy_mod.PolicyConsentEngine(state, identity)
    p = policy.create_policy(entity_id, "Recovery Policy", {"VIEW":"PERMIT"})
    perms = permissions_mod.AuthorityCapabilityStore(state, identity)
    cap = perms.grant(entity_id, "recovery-agent", operations=["VIEW"])
    payload = {"proof":"survives-restore"}; sig = identity.sign(entity_id, payload)
    portable_mod = load_module("canonical_portable_state_test", NETWORK / "15_Operations" / "backups" / "canonical_portable_state.py")
    manager = portable_mod.PortableStateManager(state, identity)
    backup = manager.create_encrypted_backup(tmp_path / "core.backup.enc")
    import base64, shutil
    key = base64.urlsafe_b64decode(backup["key_b64"])
    shutil.rmtree(state)
    restored = tmp_path / "restored_state"
    manager.restore_encrypted_backup(backup["path"], key, restored)
    restored_identity = identity_mod.EntityIdentityVault(restored)
    manifest = restored_identity.load_manifest(entity_id)
    assert identity_mod.EntityIdentityVault.verify_signature(manifest, payload, sig)
    restored_policy = policy_mod.PolicyConsentEngine(restored, restored_identity)
    assert restored_policy.evaluate(p["policy_id"], "VIEW")["allowed"] is True
    restored_perms = permissions_mod.AuthorityCapabilityStore(restored, restored_identity)
    assert restored_perms.authorize(cap["capability_id"], "recovery-agent", "VIEW")["allowed"] is True
