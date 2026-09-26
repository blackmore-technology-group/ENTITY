from __future__ import annotations

from pathlib import Path

import pytest

from adam_v41.authority import Authority
from adam_v41.reactions import ReactionIntent
from adam_v41.universe import AtomicUniverse
from adam_v42.evidence import EvidenceAlignmentEngine, EvidenceError
from adam_v42.isolation import IsolatedKernelClient, IsolatedKernelError
from adam_v42.key_management import CryptoErasureStore, EncryptedSigningKeyStore, KeyStoreError
from adam_v42.security import AuthorizationError, ClosureAuthorization, SecurityLabel


def test_inference_closure_blocks_restricted_combination(tmp_path: Path):
    auth = Authority(tmp_path / "auth")
    policy = ClosureAuthorization(auth)
    policy.label("name", SecurityLabel.INTERNAL)
    policy.label("medical_code", SecurityLabel.CONFIDENTIAL)
    policy.protect_combination({"name", "medical_code"}, SecurityLabel.RESTRICTED)
    grant = policy.issue("analyst", ["care"], SecurityLabel.CONFIDENTIAL)
    assert policy.authorize(grant, "care", ["name"]) == {"name"}
    with pytest.raises(AuthorizationError):
        policy.authorize(grant, "care", ["name", "medical_code"])


def test_mandatory_evidence_alignment(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    cap = u.enable_commit_guard()
    align = EvidenceAlignmentEngine(u, capability=cap)
    with pytest.raises(EvidenceError):
        align.assert_claim("fact", {"x": 1}, evidence_object_id="missing", extractor="x", confidence=1.0)
    evidence = align.ingest_evidence(b"source fact", media_type="text/plain", name="source.txt")
    claim = align.assert_claim("fact", {"x": 1}, evidence_object_id=evidence.object_id, extractor="test", confidence=1.0)
    assert align.verify_claim(claim.claim_id)["pass"]


def test_encrypted_keys_rotate_and_old_signatures_verify(tmp_path: Path):
    store = EncryptedSigningKeyStore(tmp_path / "keys", "correct horse battery staple")
    plaintext = store.path.read_bytes()
    assert b"authority_private" not in plaintext and len(plaintext) > 100
    old = store.descriptor
    sig = store.sign(b"message")
    new = store.rotate()
    assert new.generation == old.generation + 1 and new.key_id != old.key_id
    assert store.verify(b"message", sig, old.key_id)
    with pytest.raises(KeyStoreError):
        EncryptedSigningKeyStore(tmp_path / "keys", "wrong passphrase").sign(b"x")


def test_crypto_erasure_destroys_readability_but_retains_tombstone(tmp_path: Path):
    store = CryptoErasureStore(tmp_path / "erase", b"master-secret")
    object_id = store.put(b"sensitive payload", {"retention": "test"})
    assert store.get(object_id) == b"sensitive payload"
    tombstone = store.erase(object_id, "retention expired", "records-officer")
    assert tombstone["ciphertext_retained"]
    with pytest.raises(KeyStoreError):
        store.get(object_id)


def test_os_process_authority_boundary(tmp_path: Path):
    with IsolatedKernelClient(tmp_path / "isolated") as client:
        assert client.pid is not None
        equipment, _ = client.genesis_entity("equipment", "EQ", {"status": "AVAILABLE", "location": "YARD"})
        project, _ = client.genesis_entity("project", "P", {"status": "ACTIVE"})
        actor, _ = client.genesis_entity("person", "A", {"name": "A", "grant::ASSIGN_EQUIPMENT": True, "grant::RELEASE_EQUIPMENT": True})
        client.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": actor}))
        assert client.entity_view(equipment)["status"] == "ASSIGNED"
        with pytest.raises(IsolatedKernelError):
            client.raw_commit_probe()
