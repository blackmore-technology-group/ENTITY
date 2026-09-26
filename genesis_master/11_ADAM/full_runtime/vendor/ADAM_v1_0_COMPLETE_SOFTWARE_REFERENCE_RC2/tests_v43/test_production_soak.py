from __future__ import annotations

import time
from pathlib import Path

import pytest

from adam_v43.key_custody import IsolatedMemorySigner, QuorumCustody
from adam_v43.production_soak import ProductionSoakController, QualificationError


def make_custody():
    signers = [IsolatedMemorySigner(f"soak-{i}") for i in range(3)]
    return signers, QuorumCustody(signers, 2)


def test_test_clock_cannot_issue_production_certificate(tmp_path: Path):
    current = [1_000_000_000]
    signers, custody = make_custody()
    try:
        controller = ProductionSoakController(
            tmp_path / "test-clock", custody, duration_days=1 / 86400,
            cycle_interval_seconds=0.1, now_ns=lambda: current[0], test_only=True,
        )
        for _ in range(12):
            current[0] += 100_000_000
            controller.cycle()
        assert controller.progress()["progress"] == 1.0
        report, receipt = controller.signed_report()
        assert custody.verify(__import__('adam_v41.canonical', fromlist=['canonical_json_bytes']).canonical_json_bytes(report), receipt)
        with pytest.raises(QualificationError):
            controller.finalize(minimum_availability=0.0, maximum_p99_ms=10_000)
    finally:
        for signer in signers:
            signer.close()


def test_real_wall_clock_smoke_can_finalize_only_after_elapsed_duration(tmp_path: Path):
    signers, custody = make_custody()
    try:
        # Use a long independent qualification for the pre-duration rejection. This
        # remains valid regardless of host speed, antivirus scanning, or CI load.
        early = ProductionSoakController(
            tmp_path / "real-clock-early", custody,
            duration_days=1.0,
            cycle_interval_seconds=60.0,
            test_only=False,
        )
        with pytest.raises(QualificationError):
            early.finalize(minimum_availability=0.0, maximum_p99_ms=10_000)

        # Use a separate short qualification for the positive wall-clock gate and
        # wait only for the measured remainder rather than assuming cycle speed.
        duration_seconds = 0.25
        controller = ProductionSoakController(
            tmp_path / "real-clock-complete", custody,
            duration_days=duration_seconds / 86400,
            cycle_interval_seconds=5.0,
            test_only=False,
        )
        controller.cycle()
        remaining = max(0.0, duration_seconds - controller.elapsed_ns() / 1_000_000_000)
        time.sleep(remaining + 0.20)
        result = controller.finalize(minimum_availability=0.0, maximum_p99_ms=10_000)
        assert result["passed"]
        assert result["gates"]["duration"]
        assert result["gates"]["minimum_cycles"]
        assert (tmp_path / "real-clock-complete" / "FINAL_PRODUCTION_QUALIFICATION.json").exists()
    finally:
        for signer in signers:
            signer.close()
