from pathlib import Path
import json
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService

DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
KEY = ROOT / "runtime" / "secrets" / "client_signing.key"

secret = KEY.read_text(encoding="utf-8").strip()
token = SignedTokenService(secret).issue({
    "sub": "standalone-build-smoke",
    "subject": "standalone-build-smoke",
    "client_type": "qualification",
    "roles": ["chatgpt_engineer"],
    "devices": [DEVICE],
    "capabilities": ["*"],
}, ttl_seconds=300, audience="becp-client")
headers = {"Authorization": f"Bearer {token}"}
with httpx.Client(base_url="https://127.0.0.1:8975", headers=headers, verify=str(CA), timeout=15) as client:
    boot = client.post("/v1/session/bootstrap", json={"metadata": {"build_smoke": True}})
    boot.raise_for_status()
    sid = boot.json()["session_id"]
    select = client.post(f"/v1/session/{sid}/select", json={"device_id": DEVICE})
    select.raise_for_status()
    action = client.post("/v1/action", json={
        "session_id": sid,
        "capability": "system.health",
        "params": {},
        "timeout_seconds": 10,
    })
    action.raise_for_status()
    result = action.json()
    client.delete(f"/v1/session/{sid}")

print(json.dumps({"ok": bool(result.get("ok")), "result": result}, indent=2))
raise SystemExit(0 if result.get("ok") else 2)
