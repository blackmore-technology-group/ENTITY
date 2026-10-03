from pathlib import Path
import importlib.util
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_clean_install_creates_user_lineage_device_binding_and_crypto_login():
    mod = load("wallet_onboarding_test", "src/42_ENTITY_Wallet/onboarding.py")
    with tempfile.TemporaryDirectory() as td:
        state = Path(td)
        onboarding = mod.EntityWalletOnboarding(state)

        device = onboarding.ensure_device_identity()
        device_manifest = onboarding.identity.load_manifest(device["device_entity_id"])
        assert device_manifest["entity_type"] == "system"
        assert device_manifest["metadata"]["device_information_is_not_user_identity"] is True
        assert onboarding.status()["profile_count"] == 0

        profile = onboarding.create_profile(
            principal_display_name="Jane Smith",
            principal_public_name="jane.smith.entity",
            principal_entity_type="person",
            organization_display_name="Acme Corp",
            organization_public_name="acme.entity",
            organization_entity_type="business",
            operate_as_organization=True,
        )

        assert profile["display_path"] == "jane.smith.entity → acme.entity"
        assert profile["principal_entity_id"] != profile["active_entity_id"]
        assert profile["device_entity_id"] == device["device_entity_id"]
        assert profile["public_name_is_alias_not_authority"] is True
        assert profile["device_identity_is_not_user_identity"] is True
        assert profile["protocol_origin_is_separate_from_user_lineage"] is True

        principal = onboarding.identity.load_manifest(profile["principal_entity_id"])
        active = onboarding.identity.load_manifest(profile["active_entity_id"])
        assert principal["display_name"] == "Jane Smith"
        assert principal["aliases"] == ["jane.smith.entity"]
        assert active["display_name"] == "Acme Corp"
        assert active["aliases"] == ["acme.entity"]

        auth = onboarding.authenticate(profile)
        assert auth["authenticated"] is True
        assert auth["active_entity_id"] == profile["active_entity_id"]
        assert auth["mode"] == "DEVICE_BOUND_SIGNING_KEY"
        assert auth["password_used"] is False

        rels = onboarding.authority.active_relationships(profile["active_entity_id"], profile["principal_entity_id"])
        assert any(
            r["relationship_type"] == "SOVEREIGN_AUTHORITY"
            and r["scope"].get("wallet_lineage_parent") is True
            for r in rels
        )
        device_rels = onboarding.authority.active_relationships(profile["principal_entity_id"], profile["device_entity_id"])
        assert any(
            r["relationship_type"] == "POSSESSION"
            and r["scope"].get("device_possession_not_identity") is True
            for r in device_rels
        )

        loaded = onboarding.active_profile()
        assert loaded["profile_id"] == profile["profile_id"]
        assert onboarding.status()["first_run_required"] is False


def test_adopt_existing_preserves_existing_entity_ids_and_aliases():
    mod = load("wallet_onboarding_test_existing", "src/42_ENTITY_Wallet/onboarding.py")
    with tempfile.TemporaryDirectory() as td:
        state = Path(td)
        onboarding = mod.EntityWalletOnboarding(state)
        principal = onboarding.identity.create("Existing Person", "person", aliases=["existing.person.entity"])
        org = onboarding.identity.create("Existing Org", "business", aliases=["existing.org.entity"])
        device = onboarding.identity.create(
            "Existing Device",
            "system",
            aliases=["existing.device.entity"],
            metadata={"software_device_identity": True, "device_information_is_not_user_identity": True},
        )

        profile = onboarding.adopt_existing(
            principal_entity_id=principal["entity_id"],
            active_entity_id=org["entity_id"],
            device_entity_id=device["entity_id"],
        )

        assert profile["migrated_existing"] is True
        assert profile["principal_entity_id"] == principal["entity_id"]
        assert profile["active_entity_id"] == org["entity_id"]
        assert profile["device_entity_id"] == device["entity_id"]
        assert profile["display_path"] == "existing.person.entity → existing.org.entity"
        assert onboarding.authenticate(profile)["authenticated"] is True


def test_public_names_are_aliases_and_local_conflicts_do_not_replace_entity_authority():
    mod = load("wallet_onboarding_test_alias", "src/42_ENTITY_Wallet/onboarding.py")
    with tempfile.TemporaryDirectory() as td:
        state = Path(td)
        onboarding = mod.EntityWalletOnboarding(state)
        a = onboarding.identity.create("A", "person", aliases=["shared.entity"])
        b = onboarding.identity.create("B", "person", aliases=["shared.entity"])

        ca = onboarding.ensure_public_name(a["entity_id"], "shared.entity")
        cb = onboarding.ensure_public_name(b["entity_id"], "shared.entity")

        assert ca["public_name"] == "shared.entity"
        assert cb["public_name"] == "shared.entity"
        assert ca["entity_id"] != cb["entity_id"]
        assert cb["name_claim"]["conflict_state"] == "CONFLICT"
        assert ca["entity_id_is_authority"] is True
        assert cb["entity_id_is_authority"] is True
