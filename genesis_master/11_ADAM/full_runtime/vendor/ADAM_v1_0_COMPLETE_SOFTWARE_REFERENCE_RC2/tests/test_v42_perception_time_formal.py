from __future__ import annotations

import io
import math
import wave
from pathlib import Path

import numpy as np
from PIL import Image

from adam_v41.universe import AtomicUniverse
from adam_v42.formal import BoundedProofChecker, Law
from adam_v42.perception import MultimodalPerception
from adam_v42.time_model import HybridLogicalClock, UncertainInstant, ValidInterval


def wav_bytes() -> bytes:
    rate = 8000
    samples = (np.sin(2 * math.pi * 440 * np.arange(rate) / rate) * 20000).astype(np.int16)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(samples.tobytes())
    return out.getvalue()


def png_bytes() -> bytes:
    image = Image.new("RGB", (32, 24), (20, 80, 140))
    out = io.BytesIO(); image.save(out, format="PNG"); return out.getvalue()


def test_multimodal_codecs_create_exact_aligned_claims(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    cap = u.enable_commit_guard()
    perception = MultimodalPerception(u, capability=cap)
    payloads = [
        (b"The river bank is 12 metres wide. Alice Example inspected it.", perception.text),
        (png_bytes(), perception.image),
        (wav_bytes(), perception.audio),
        (b"import math\ndef area(r):\n    return math.pi*r*r\n", perception.program),
        (b"id,value\nA,10\nB,20\n", perception.tabular_csv),
    ]
    for payload, method in payloads:
        result = method(payload)
        assert perception.alignment.exact.reconstruct(result.evidence_object_id) == payload
        assert perception.alignment.verify_claim(result.claims[0].claim_id)["pass"]
    assert perception.text(payloads[0][0]).ambiguity


def test_hybrid_logical_clock_and_interval_reasoning():
    clock_a = HybridLogicalClock("a", now_ns=lambda: 100)
    clock_b = HybridLogicalClock("b", now_ns=lambda: 90)
    a1 = clock_a.tick(); b1 = clock_b.merge(a1); a2 = clock_a.merge(b1)
    assert a1 < b1 < a2
    assert ValidInterval(0, 10).relation(ValidInterval(10, 20)) == "MEETS"
    assert ValidInterval(0, 20).relation(ValidInterval(5, 10)) == "CONTAINS"
    assert ValidInterval(10, 20).intersects_uncertainty(UncertainInstant(19, 25))


def test_bounded_machine_checked_conservation_law():
    law = Law(
        "balanced_transfer",
        "before_a + before_b == after_a + after_b",
        {"before_a": (0, 1, 2), "before_b": (0, 1, 2), "after_a": (0, 1, 2), "after_b": (0, 1, 2)},
    )
    # This universal statement is false because after values are independent.
    refuted = BoundedProofChecker.prove(law)
    assert refuted.status == "REFUTED" and refuted.counterexample

    states = [(a, b) for a in range(4) for b in range(4)]
    actions = [0, 1, 2, 3]
    def transition(state, amount):
        a, b = state
        return None if amount > a else (a - amount, b + amount)
    proof = BoundedProofChecker.prove_transition(
        "transfer_conserves_total", states, actions, transition,
        lambda before, action, after: sum(before) == sum(after),
    )
    assert proof.status == "PROVEN_BOUNDED" and proof.cases_checked > 0
