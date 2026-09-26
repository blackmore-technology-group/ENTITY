from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

from blackmore_ecp.security import SignedTokenService


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue a BECP service token for OpenAI Secure MCP Tunnel")
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--ttl-seconds", type=int, default=2592000)
    args = parser.parse_args()

    secret = Path(args.signing_key).read_text(encoding="utf-8").strip()
    token = SignedTokenService(secret).issue(
        {
            "sub": "openai-secure-mcp-tunnel",
            "subject": "openai-secure-mcp-tunnel",
            "client_type": "chatgpt_tunnel",
            "roles": ["chatgpt_privileged_engineer"],
            "devices": [args.device_id],
            "capabilities": ["*"],
        },
        ttl_seconds=args.ttl_seconds,
        audience="becp-client",
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"Bearer {token}", encoding="utf-8")
    fingerprint = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(seconds=args.ttl_seconds)
    print(f"TOKEN_FILE={output}")
    print(f"TOKEN_SHA256={fingerprint}")
    print(f"EXPIRES_UTC={expires.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
