from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import run_audit
from .exact import ExactCodec
from .universe import AtomicUniverse


def main() -> int:
    ap = argparse.ArgumentParser(prog="adam-v40")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_audit = sub.add_parser("audit")
    p_audit.add_argument("root", type=Path)
    p_audit.add_argument("--records", type=int, default=1500)
    p_ingest = sub.add_parser("ingest-file")
    p_ingest.add_argument("universe", type=Path)
    p_ingest.add_argument("file", type=Path)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("universe", type=Path)
    args = ap.parse_args()
    if args.cmd == "audit":
        result = run_audit(args.root, records=args.records)
        print(json.dumps(result, indent=2))
        return 0 if result["overall_pass"] else 2
    if args.cmd == "ingest-file":
        universe = AtomicUniverse(args.universe)
        obj = ExactCodec(universe).ingest(args.file.read_bytes(), name=args.file.name)
        print(json.dumps(obj.__dict__, indent=2))
        return 0
    if args.cmd == "verify":
        print(json.dumps(AtomicUniverse(args.universe).verify(), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
