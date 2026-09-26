from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue a BECP client bearer token")
    parser.add_argument("--key", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--client-type", required=True)
    parser.add_argument("--roles", nargs="+", required=True)
    parser.add_argument("--devices", nargs="+", required=True)
    parser.add_argument("--capabilities", nargs="+", default=["*"])
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    args = parser.parse_args()

    secret = Path(args.key).read_text(encoding="utf-8").strip()
    signer = SignedTokenService(secret)
    token = signer.issue(
        {
            "sub": args.subject,
            "subject": args.subject,
            "client_type": args.client_type,
            "roles": args.roles,
            "devices": args.devices,
            "capabilities": args.capabilities,
        },
        ttl_seconds=args.ttl_seconds,
        audience="becp-client",
    )
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
