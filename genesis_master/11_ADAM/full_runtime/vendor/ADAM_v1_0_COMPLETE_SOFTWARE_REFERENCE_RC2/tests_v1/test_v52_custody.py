from __future__ import annotations

from dataclasses import replace

import pytest

from adam_v52 import AuthorityKeyHierarchy, CustodyError, EncryptedSoftwareCustodyProvider


def test_encrypted_custody_sign_rotate_disable_destroy(tmp_path):
    provider = EncryptedSoftwareCustodyProvider(tmp_path, b"m" * 32)
    handle = provider.create_key(key_id="reaction", purpose="REACTION_SIGNING", jurisdiction="CA-BC")
    payload = b"authoritative reaction"
    receipt = provider.sign(handle, payload, purpose="REACTION_SIGNING", context={"root": "abc"})
    assert provider.verify_receipt(receipt, payload)
    assert not provider.verify_receipt(receipt, payload + b"x")
    assert provider.verify_attestation(provider.attest(handle))
    assert provider.attest(handle).non_exportable is False

    rotated = provider.rotate(handle)
    with pytest.raises(CustodyError):
        provider.sign(handle, payload, purpose="REACTION_SIGNING", context={})
    new_receipt = provider.sign(rotated, payload, purpose="REACTION_SIGNING", context={})
    assert provider.verify_receipt(new_receipt, payload)

    provider.disable(rotated)
    with pytest.raises(CustodyError):
        provider.sign(rotated, payload, purpose="REACTION_SIGNING", context={})
    provider.destroy(rotated)
    assert provider.attest(rotated).state == "DESTROYED"
    provider.close()


def test_receipt_context_and_provider_are_bound(tmp_path):
    provider = EncryptedSoftwareCustodyProvider(tmp_path, b"k" * 32)
    handle = provider.create_key(key_id="witness", purpose="WITNESS", jurisdiction="CA-BC")
    receipt = provider.sign(handle, b"root", purpose="WITNESS", context={"epoch": 1})
    assert provider.verify_receipt(receipt, b"root")
    assert not provider.verify_receipt(replace(receipt, context={"epoch": 2}), b"root")
    assert not provider.verify_receipt(replace(receipt, provider_instance="other"), b"root")


def test_custody_persists_encrypted_keys(tmp_path):
    provider = EncryptedSoftwareCustodyProvider(tmp_path, b"p" * 32, instance_id="persist")
    handle = provider.create_key(key_id="checkpoint", purpose="CHECKPOINT", jurisdiction="CA-BC")
    public = provider.get_public_key(handle)
    provider.close()

    reopened = EncryptedSoftwareCustodyProvider(tmp_path, b"p" * 32, instance_id="persist")
    assert reopened.get_public_key(handle) == public
    receipt = reopened.sign(handle, b"checkpoint", purpose="CHECKPOINT", context={})
    assert reopened.verify_receipt(receipt, b"checkpoint")
    raw = (tmp_path / "custody.json").read_bytes()
    assert public not in raw


def test_authority_key_hierarchy_separates_purposes(tmp_path):
    provider = EncryptedSoftwareCustodyProvider(tmp_path, b"h" * 32)
    hierarchy = AuthorityKeyHierarchy(provider)
    created = hierarchy.provision(jurisdiction="CA-BC", purposes=("ROOT_GOVERNANCE", "REACTION_SIGNING", "WITNESS"))
    assert len({handle.key_id for handle in created.values()}) == 3
    assert hierarchy.require("CA-BC", "REACTION_SIGNING").purpose == "REACTION_SIGNING"
    with pytest.raises(CustodyError):
        hierarchy.require("CA-BC", "SESSION")
