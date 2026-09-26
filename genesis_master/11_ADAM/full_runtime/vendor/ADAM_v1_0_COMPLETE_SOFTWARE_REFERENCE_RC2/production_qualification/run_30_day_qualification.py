#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from adam_v43.key_custody import IsolatedMemorySigner, QuorumCustody
from adam_v43.production_soak import ProductionSoakController


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ADAM v0.43 real-wall-clock production qualification")
    parser.add_argument("--root", default="./adam-v043-30-day-qualification")
    parser.add_argument("--duration-days", type=float, default=30.0)
    parser.add_argument("--cycle-seconds", type=float, default=60.0)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--one-cycle", action="store_true")
    args = parser.parse_args()

    # Software signers are intentionally used only as a runnable default. Production
    # deployment must replace these providers with the HSM/KMS adapter described in
    # HSM_KMS_DEPLOYMENT_SPEC.md.
    signers = [IsolatedMemorySigner(f"qualification-software-signer-{i}") for i in range(3)]
    try:
        custody = QuorumCustody(signers, threshold=2)
        controller = ProductionSoakController(Path(args.root), custody, duration_days=args.duration_days, cycle_interval_seconds=args.cycle_seconds)
        if args.status:
            print(controller.progress())
            return 0
        if args.one_cycle:
            print(controller.cycle())
            print(controller.progress())
            return 0
        controller.run()
        print(controller.finalize())
        return 0
    finally:
        for signer in signers:
            signer.close()


if __name__ == "__main__":
    raise SystemExit(main())
