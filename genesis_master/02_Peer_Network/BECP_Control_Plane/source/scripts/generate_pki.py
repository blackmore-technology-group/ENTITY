from __future__ import annotations

import argparse
import json
import platform
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.pki import certificate_fingerprint, create_ca, issue_certificate


def _write_secret(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(secrets.token_urlsafe(64), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate BECP development PKI and signing secrets")
    parser.add_argument("--root", default=str(ROOT / "runtime" / "pki"))
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--device-name", default=platform.node() or "BTG")
    args = parser.parse_args()

    pki_root = Path(args.root)
    ca = create_ca(str(pki_root / "ca"))
    server = issue_certificate(
        ca["key"], ca["cert"], str(pki_root / "server"),
        common_name="BECP Gateway", filename_prefix="gateway", client=False,
        san_names=["localhost", "127.0.0.1", platform.node() or "BTG"],
    )
    device = issue_certificate(
        ca["key"], ca["cert"], str(pki_root / "devices" / args.device_id),
        common_name=f"BECP Device {args.device_name}", filename_prefix="device", client=True,
    )
    secrets_root = ROOT / "runtime" / "secrets"
    client_key = secrets_root / "client_signing.key"
    approval_key = secrets_root / "approval_signing.key"
    _write_secret(client_key)
    _write_secret(approval_key)

    manifest = {
        "ca_cert": ca["cert"],
        "ca_key": ca["key"],
        "server_cert": server["cert"],
        "server_key": server["key"],
        "device_cert": device["cert"],
        "device_key": device["key"],
        "device_certificate_fingerprint": certificate_fingerprint(device["cert"]),
        "client_signing_key": str(client_key),
        "approval_signing_key": str(approval_key),
    }
    manifest_path = pki_root / "PKI_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
