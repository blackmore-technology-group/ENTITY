"""Reference DataChip CLI.

Only packaging, inspection and integrity verification are exposed. Extraction
is an SDK operation requiring the host's independently authenticated policy.
"""
import argparse
import json
from .processor import pack_file, inspect_chip, verify_chip, DataChipError


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="entity-datachip",
        description="Experimental DataChip v0.1 transport; not a wallet or authority verifier",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", help="Copy a file into a portable, hash-checked DataChip")
    pack.add_argument("source")
    pack.add_argument("chip")
    pack.add_argument("--rights-ref", default=None,
                      help="Unverified reference only; does not grant or establish rights")
    pack.add_argument("--issuer-ref", default=None,
                      help="Unverified issuer reference only; no signing is performed")
    for name in ("inspect", "verify"):
        p = sub.add_parser(name)
        p.add_argument("chip")
    a = parser.parse_args(argv)
    try:
        if a.command == "pack":
            result = pack_file(a.source, a.chip, claimed_issuer=a.issuer_ref,
                               rights_passport_ref=a.rights_ref)
        elif a.command == "inspect":
            result = inspect_chip(a.chip)
        else:
            result = verify_chip(a.chip)
    except (ValueError, OSError) as exc:
        parser.exit(2, "DataChip failure: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
