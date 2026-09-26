from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .runtime import ArtificialLivingUniverseV1Candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="ADAM v1.0 complete software reference RC2")
    parser.add_argument("--state-dir", type=Path, help="persistent local state directory")
    parser.add_argument("--network-reference", action="store_true", help="start the single-host socket/process authority reference")
    parser.add_argument("--status", action="store_true", help="print machine-readable candidate status")
    args = parser.parse_args()

    if args.state_dir is None:
        with tempfile.TemporaryDirectory(prefix="adam-v1-cli-") as directory:
            with ArtificialLivingUniverseV1Candidate.create(directory, enable_network_reference=args.network_reference) as runtime:
                print(json.dumps(runtime.local_status(), indent=2, default=str))
        return 0

    args.state_dir.mkdir(parents=True, exist_ok=True)
    with ArtificialLivingUniverseV1Candidate.create(args.state_dir, enable_network_reference=args.network_reference) as runtime:
        print(json.dumps(runtime.local_status(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
