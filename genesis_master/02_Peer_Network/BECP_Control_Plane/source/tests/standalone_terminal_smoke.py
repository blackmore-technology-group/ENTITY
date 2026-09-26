from pathlib import Path
import json, sys, httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from blackmore_ecp.security import SignedTokenService

DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
CLIENT_KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
secret = CLIENT_KEY.read_text(encoding="utf-8").strip()
token = SignedTokenService(secret).issue({
    "sub": "standalone-terminal-smoke",
    "subject": "standalone-terminal-smoke",
    "client_type": "qualification",
    "roles": ["blackmore_admin"],
    "devices": [DEVICE],
    "capabilities": ["*"],
}, ttl_seconds=300, audience="becp-client")
headers = {"Authorization": f"Bearer {token}"}
with httpx.Client(base_url="https://127.0.0.1:8975", headers=headers, verify=str(CA), timeout=20) as client:
    boot = client.post("/v1/session/bootstrap", json={"metadata": {"terminal_smoke": True}})
    boot.raise_for_status(); sid = boot.json()["session_id"]
    client.post(f"/v1/session/{sid}/select", json={"device_id": DEVICE}).raise_for_status()
    approval = client.post("/v1/approval", json={
        "session_id": sid,
        "capability": "engineering.terminal.start",
        "target_device_id": DEVICE,
        "ttl_seconds": 120,
    })
    approval.raise_for_status(); start_token = approval.json()["approval_token"]
    start = client.post("/v1/action", json={
        "session_id": sid,
        "capability": "engineering.terminal.start",
        "params": {"shell": "powershell.exe"},
        "approval_token": start_token,
        "timeout_seconds": 15,
    })
    start.raise_for_status(); start_result = start.json()
    terminal_id = start_result["data"]["session_id"]
    approval2 = client.post("/v1/approval", json={
        "session_id": sid,
        "capability": "engineering.terminal.execute",
        "target_device_id": DEVICE,
        "ttl_seconds": 120,
    })
    approval2.raise_for_status(); exec_token = approval2.json()["approval_token"]
    execute = client.post("/v1/action", json={
        "session_id": sid,
        "capability": "engineering.terminal.execute",
        "params": {"session_id": terminal_id, "command": "Write-Output BECP_STANDALONE_TERMINAL_OK; hostname"},
        "approval_token": exec_token,
        "timeout_seconds": 15,
    })
    execute.raise_for_status(); exec_result = execute.json()
    client.delete(f"/v1/session/{sid}")

stdout = str(exec_result.get("data", {}).get("stdout", ""))
ok = exec_result.get("ok") is True and "BECP_STANDALONE_TERMINAL_OK" in stdout and "BTG" in stdout
print(json.dumps({"ok": ok, "stdout": stdout, "result": exec_result}, indent=2))
raise SystemExit(0 if ok else 2)
