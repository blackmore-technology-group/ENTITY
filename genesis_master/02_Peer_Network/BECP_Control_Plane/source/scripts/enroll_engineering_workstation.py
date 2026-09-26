from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp import __version__
from blackmore_ecp.device_registry import DeviceRegistry, EnrolledDevice
from blackmore_ecp.pki import certificate_fingerprint, issue_certificate


def main() -> int:
    parser = argparse.ArgumentParser(description="Enroll a BECP engineering workstation")
    parser.add_argument("--device-id", default="")
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--owner-principal", default="")
    parser.add_argument("--device-role", default="ENGINEERING_WORKSTATION")
    parser.add_argument("--default-cwd", default="<LOCAL_DRIVE>/Blackmore_Technology_Group")
    parser.add_argument("--config-output", required=True)
    parser.add_argument("--registry", default=str(ROOT / "runtime" / "registry" / "devices.json"))
    parser.add_argument("--pki-root", default=str(ROOT / "runtime" / "pki"))
    args = parser.parse_args()

    device_id = args.device_id or str(uuid4())
    ca_key = Path(args.pki_root) / "ca" / "ca.key.pem"
    ca_cert = Path(args.pki_root) / "ca" / "ca.cert.pem"
    if not ca_key.exists() or not ca_cert.exists():
        raise FileNotFoundError("BECP CA has not been generated")

    issued = issue_certificate(
        str(ca_key),
        str(ca_cert),
        str(Path(args.pki_root) / "devices" / device_id),
        common_name=f"BECP Device {args.hostname}",
        filename_prefix="device",
        client=True,
    )
    fingerprint = certificate_fingerprint(issued["cert"])
    capabilities = [
        "system.health",
        "file.hash",
        "file.read_text",
        "diagnostic.run_approved",
        "change.run_approved",
        "engineering.terminal.start",
        "engineering.terminal.execute",
        "engineering.terminal.cwd",
        "engineering.terminal.close",
        "engineering.terminal.drives",
    ]
    registry = DeviceRegistry(args.registry)
    device = EnrolledDevice(
        device_id=device_id,
        hostname=args.hostname,
        display_name=args.display_name,
        device_role=args.device_role,
        platform="Windows",
        owner_principal=args.owner_principal or None,
        agent_version=__version__,
        terminal_enabled=True,
        terminal_privilege_model="INHERIT_AGENT_PROCESS_TOKEN_AND_WINDOWS_UAC",
        certificate_path=issued["cert"],
        certificate_fingerprint=fingerprint,
        capabilities=capabilities,
        tags=["engineering", "windows"],
        online=False,
        revoked=False,
        remote_access_enabled=True,
    )
    registry.register(device)

    config = {
        "device_id": device_id,
        "device_alias": args.hostname,
        "hostname": args.hostname,
        "device_role": args.device_role,
        "owner_principal": args.owner_principal,
        "audit_path": str(ROOT / "runtime" / "audit" / f"{device_id}.jsonl"),
        "engineering_terminal": {
            "enabled": True,
            "bound_device": platform.node(),
            "default_shell": "powershell.exe",
            "allowed_shells": ["powershell.exe", "pwsh.exe", "cmd.exe"],
            "default_cwd": args.default_cwd,
            "max_timeout_seconds": 600,
            "max_output_bytes": 1048576,
            "full_filesystem_scope": True,
        },
        "required_roles": [
            "blackmore_admin",
            "chatgpt_privileged_engineer",
            "niki_privileged_engineer",
        ],
        "terminal_mode": "FULL_ENGINEERING_COMPUTER_ACCESS",
        "os_privilege_model": "INHERIT_WINDOWS_ACCOUNT_AND_UAC",
    }
    output = Path(args.config_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(json.dumps({
        "device": device.model_dump(),
        "device_cert": issued["cert"],
        "device_key": issued["key"],
        "config": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
