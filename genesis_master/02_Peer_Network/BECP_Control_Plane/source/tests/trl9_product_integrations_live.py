from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService

DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
OUT = ROOT / "runtime" / "trl9" / "BECP_0.2.1_TRL9_20260912" / "PRODUCT_INTEGRATION_LIVE_RESULTS.json"

PRODUCTS = [
    ("NIKI", Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\NIKI\Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"), "niki_privileged_engineer", True),
    ("HIKEAR", Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HIKE_AR\HikeAR_v0.1.0"), "field_app", False),
    ("HUNTAR", Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0"), "field_app", False),
    ("SEARCHAR", Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\SAR\SearchAR_v0.12.0"), "sar_operator", False),
]
BASE_CAPS = ["system.health", "file.hash", "file.read_text", "diagnostic.run_approved"]
NIKI_EXTRA = [
    "change.run_approved", "engineering.terminal.start", "engineering.terminal.execute",
    "engineering.terminal.cwd", "engineering.terminal.close", "engineering.terminal.drives",
]

CHILD = r'''
import json
from integrations.becp.orchestrator import BECPOrchestrator

o = BECPOrchestrator()
try:
    boot = o.connect()
    devices = o.devices()
    o.select_device_by_alias("BTG")
    health = o.health()
    cfg_path = str(__import__("pathlib").Path("integrations/becp/configuration.json").resolve())
    file_hash = o.hash_file(cfg_path)
    read = o.read_text(cfg_path, 8192)
    result = {"boot": bool(boot.get("session_id")), "devices": len(devices), "health": health, "hash": file_hash, "read": read}
    if __import__("os").environ.get("TRL9_PRIVILEGED") == "1":
        started = o.start_terminal()
        tid = started.get("data", {}).get("session_id")
        executed = o.terminal_execute(tid, "Write-Output NIKI_BECP_TRL9_OK; hostname", 30)
        o.terminal_close(tid)
        result["terminal"] = executed
    print(json.dumps(result))
finally:
    o.close()
'''
def main() -> int:
    signer = SignedTokenService(KEY.read_text(encoding="utf-8").strip())
    results = {}
    for name, root, role, privileged in PRODUCTS:
        caps = BASE_CAPS + (NIKI_EXTRA if privileged else [])
        token = signer.issue({
            "sub": f"trl9-{name.lower()}", "subject": f"TRL9 {name}",
            "client_type": name.lower(), "roles": ([role] + (["approval_authority"] if privileged else [])), "devices": [DEVICE],
            "capabilities": caps,
        }, ttl_seconds=300, audience="becp-client")
        env = os.environ.copy()
        env.update({
            "BECP_CLIENT_TOKEN": token,
            "BECP_BASE_URL": "https://127.0.0.1:8765",
            "BECP_CA_CERT": str(CA),
            "TRL9_PRIVILEGED": "1" if privileged else "0",
        })
        cp = subprocess.run([sys.executable, "-c", CHILD], cwd=root, env=env, capture_output=True, text=True, timeout=90)
        entry = {"returncode": cp.returncode, "stderr": cp.stderr}
        try:
            data = json.loads(cp.stdout.strip().splitlines()[-1]) if cp.stdout.strip() else {}
        except Exception:
            data = {"raw_stdout": cp.stdout}
        entry["data"] = data
        ok = cp.returncode == 0 and data.get("boot") is True and data.get("devices") == 1
        ok = ok and data.get("health", {}).get("ok") is True
        ok = ok and data.get("hash", {}).get("ok") is True and data.get("read", {}).get("ok") is True
        if privileged:
            ok = ok and data.get("terminal", {}).get("ok") is True
            ok = ok and "NIKI_BECP_TRL9_OK" in data.get("terminal", {}).get("data", {}).get("stdout", "")
        entry["ok"] = ok
        results[name] = entry

    status = "PASS" if all(item["ok"] for item in results.values()) else "FAIL"
    payload = {"status": status, "products": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

