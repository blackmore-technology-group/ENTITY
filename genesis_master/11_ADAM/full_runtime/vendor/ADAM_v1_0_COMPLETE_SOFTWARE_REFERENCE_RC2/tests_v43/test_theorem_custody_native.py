from __future__ import annotations

import json
import multiprocessing as mp
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from adam_v43.key_custody import (
    CloudKMSProviderSpec,
    CustodyError,
    IsolatedMemorySigner,
    PKCS11ProviderSpec,
    QuorumCustody,
)
from adam_v43.theorem_proving import HornProofEngine, HornRule, SymbolicTheoremProver
from native_authority_reference import prepare_reference_command


def test_horn_and_symbolic_theorem_proofs():
    engine = HornProofEngine()
    certificate = engine.prove(
        {"authorized_actor", "valid_preconditions", "conservation_proven"},
        [
            HornRule(("authorized_actor", "valid_preconditions"), "reaction_admissible", "reaction_gate"),
            HornRule(("reaction_admissible", "conservation_proven"), "commit_allowed", "constitutional_gate"),
        ],
        "commit_allowed",
    )
    assert certificate.status == "PROVEN"
    assert certificate.proof_steps[-1].conclusion == "commit_allowed"

    identity = SymbolicTheoremProver.prove_identity("(a-b)+(c+b)", "a+c", symbols=("a", "b", "c"))
    assert identity.status == "PROVEN"

    conservation = SymbolicTheoremProver.prove_conservation(
        {"money": "cash + receivable", "assets": "equipment + inventory"},
        {"money": "receivable + cash", "assets": "inventory + equipment"},
        symbols=("cash", "receivable", "equipment", "inventory"),
    )
    assert conservation.status == "PROVEN"

    refuted = SymbolicTheoremProver.prove_by_exhaustion("before == after", {"before": (0, 1), "after": (0, 1)})
    assert refuted.status == "REFUTED" and refuted.counterexample


def test_isolated_signing_rotation_and_quorum():
    payload = b"ADAM authority root"
    signers = [IsolatedMemorySigner(f"software-hsm-{i}") for i in range(3)]
    worker_pids = {signer.pid for signer in signers}
    try:
        assert all(s.pid for s in signers)
        assert all(s.descriptor.hardware_backed is False for s in signers)
        receipt = signers[0].sign(payload)
        assert signers[0].verify(payload, receipt)
        old_key = receipt.key_id
        new_descriptor = signers[0].rotate()
        assert new_descriptor.key_id != old_key
        assert signers[0].verify(payload, receipt)

        quorum = QuorumCustody(signers, threshold=2)
        q = quorum.sign(payload)
        assert quorum.verify(payload, q)
        broken = replace(q, signatures=(replace(q.signatures[0], signature_hex="00" * 64),) + q.signatures[1:])
        assert not quorum.verify(payload, broken)  # the receipt body itself was altered
        two_provider_quorum = QuorumCustody(signers[1:], threshold=2)
        two_signature_receipt = two_provider_quorum.sign(payload)
        assert two_provider_quorum.verify(payload, two_signature_receipt)
        broken_two = replace(broken, signatures=(broken.signatures[0], replace(broken.signatures[1], signature_hex="00" * 64), broken.signatures[2]))
        assert not quorum.verify(payload, broken_two)
    finally:
        for signer in signers:
            signer.close()
    assert not worker_pids.intersection({child.pid for child in mp.active_children()})


def test_production_provider_specs_reject_unsafe_configuration():
    good = PKCS11ProviderSpec("/usr/lib/vendor-pkcs11.so", "ADAM", "authority-key", "env:ADAM_HSM_PIN")
    good.validate()
    with pytest.raises(CustodyError):
        PKCS11ProviderSpec("x", "ADAM", "key", "literal:1234").validate()
    CloudKMSProviderSpec("aws-kms", "arn:aws:kms:ca-central-1:1:key/abc", "ca-central-1").validate()
    with pytest.raises(CustodyError):
        CloudKMSProviderSpec("unknown", "key", "region").validate()


def test_compiled_native_authority_reference_and_rust_source_contract(tmp_path: Path):
    root = Path(__file__).parents[1]
    native_dir = root / "native_authority_reference"
    command, _compiled = prepare_reference_command(native_dir)
    proc = subprocess.Popen([*command, str(tmp_path / "native.log")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert proc.stdout.readline().startswith("READY")
    proc.stdin.write("HASH 616263\n"); proc.stdin.flush()
    assert proc.stdout.readline().strip().endswith("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    proc.stdin.write("APPEND 616263\nROOT\nQUIT\n"); proc.stdin.flush()
    append = proc.stdout.readline().strip(); root_line = proc.stdout.readline().strip(); bye = proc.stdout.readline().strip()
    assert append.startswith("OK 1 ")
    assert root_line == append
    assert bye == "OK BYE"
    assert proc.wait(timeout=5) == 0

    cargo = (root / "rust_authority_kernel" / "Cargo.toml").read_text()
    source = (root / "rust_authority_kernel" / "src" / "main.rs").read_text()
    assert "ed25519-dalek" in cargo and "zeroize" in cargo and "sha2" in cargo
    assert "stale root" in source and "sync_all" in source and "Integrity" in source


def test_quorum_receipt_integrity_is_bound_to_signatures():
    from dataclasses import replace
    from adam_v43.key_custody import IsolatedMemorySigner, QuorumCustody
    with IsolatedMemorySigner("a") as a, IsolatedMemorySigner("b") as b, IsolatedMemorySigner("c") as c:
        quorum = QuorumCustody([a, b, c], 2)
        receipt = quorum.sign(b"payload")
        assert quorum.verify(b"payload", receipt)
        assert not quorum.verify(b"payload", replace(receipt, quorum_id="0" * 64))
