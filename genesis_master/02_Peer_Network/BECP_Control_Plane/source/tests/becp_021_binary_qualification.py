from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService

Q = ROOT / "runtime" / "qualification" / "becp_0.2.1"
BRIDGE = ROOT / "build" / "BECP_0.2.1" / "bridge" / "BECP_RDC_Bridge_v0.2.1.exe"
BRIDGE_CONFIG = Q / "bridge.json"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
SIGNING_KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
API_URL = "https://127.0.0.1:9175"
MCP_URL = "https://127.0.0.1:9177/mcp"


def bridge_json(*args: str) -> dict:
    completed = subprocess.run(
        [str(BRIDGE), "--config", str(BRIDGE_CONFIG), *args],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"bridge failed: {completed.stderr or completed.stdout}")
    return json.loads(completed.stdout)


def file_record(path: Path) -> dict:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> int:
    with httpx.Client(verify=str(CA), timeout=15.0) as client:
        response = client.get(f"{API_URL}/health")
        response.raise_for_status()
        gateway_health = response.json()
    status = bridge_json("status")
    devices = bridge_json("devices")
    health = bridge_json("health", "--device", "BTG")
    terminal = bridge_json(
        "terminal-run",
        "--device", "BTG",
        "--cwd", r"<LOCAL_DRIVE>/Blackmore_Technology_Group",
        "--command", "Write-Output BECP_021_BINARY_QUALIFIED; hostname",
    )
    stdout = str(terminal.get("result", {}).get("data", {}).get("stdout", ""))
    audit_path = Q / "btg_agent_audit.jsonl"
    audit_text = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""
    artifacts = [
        ROOT / "build" / "BECP_0.2.1" / "server" / "BECP_Gateway_v0.2.1.exe",
        ROOT / "build" / "BECP_0.2.1" / "agent" / "BECP_Workstation_Agent_v0.2.1.exe",
        BRIDGE,
        ROOT / "build" / "BECP_0.2.1" / "packages" / "blackmore_ecp-0.2.1-py3-none-any.whl",
    ]
    checks = {
        "gateway_health": gateway_health.get("ok") is True,
        "agent_online": gateway_health.get("online_devices", 0) >= 1,
        "bridge_status": status.get("ok") is True,
        "device_discovery": len(devices.get("devices", [])) == 1 and devices["devices"][0].get("device_id") == DEVICE,
        "routed_health": health.get("result", {}).get("ok") is True,
        "privileged_terminal": terminal.get("ok") is True and "BECP_021_BINARY_QUALIFIED" in stdout,
        "bridge_audited": "Remote Desktop Commander via BECP" in audit_text,
        "artifacts_present": all(path.exists() for path in artifacts),
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "gateway_health": gateway_health,
        "terminal_stdout": stdout,
        "artifacts": [file_record(path) for path in artifacts],
    }
    output = Q / "BINARY_QUALIFICATION_RESULTS.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
