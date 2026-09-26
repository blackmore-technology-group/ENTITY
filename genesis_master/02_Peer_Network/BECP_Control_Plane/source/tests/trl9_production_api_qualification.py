from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService

BASE = "https://127.0.0.1:8765"
DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
OUT = ROOT / "runtime" / "trl9" / "BECP_0.2.1_TRL9_20260912" / "PRODUCTION_API_SECURITY_RESULTS.json"
README = ROOT / "build" / "BECP_0.2.1" / "release" / "BECP_0.2.1" / "README_RELEASE.md"

checks: dict[str, dict] = {}
def record(name: str, ok: bool, evidence=None) -> None:
    checks[name] = {"ok": bool(ok), "evidence": evidence}
    if not ok:
        raise AssertionError(f"{name} failed: {evidence}")


def issue(subject: str, roles: list[str], capabilities: list[str], ttl: int = 300, devices=None) -> str:
    signer = SignedTokenService(KEY.read_text(encoding="utf-8").strip())
    return signer.issue({
        "sub": subject,
        "subject": subject,
        "client_type": "trl9_operational_qualification",
        "roles": roles,
        "devices": devices or [DEVICE],
        "capabilities": capabilities,
    }, ttl_seconds=ttl, audience="becp-client")


def client(token: str | None = None) -> httpx.Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=BASE, headers=headers, verify=str(CA), timeout=30.0)


def wait_online(c: httpx.Client, count: int, timeout: float = 25.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = c.get("/health").json()
        if last.get("online_devices") == count:
            return last
        time.sleep(0.5)
    raise AssertionError(f"online device count did not become {count}: {last}")
def action(c: httpx.Client, sid: str, capability: str, params=None, approval=None, timeout=30.0):
    return c.post("/v1/action", json={
        "session_id": sid,
        "capability": capability,
        "params": params or {},
        "approval_token": approval,
        "timeout_seconds": timeout,
    })


def approval(c: httpx.Client, sid: str, capability: str) -> str:
    r = c.post("/v1/approval", json={
        "session_id": sid,
        "capability": capability,
        "target_device_id": DEVICE,
        "ttl_seconds": 120,
    })
    r.raise_for_status()
    return str(r.json()["approval_token"])


def bootstrap(c: httpx.Client, label: str) -> str:
    r = c.post("/v1/session/bootstrap", json={"metadata": {"trl9": label}})
    r.raise_for_status()
    return str(r.json()["session_id"])


def select(c: httpx.Client, sid: str) -> None:
    r = c.post(f"/v1/session/{sid}/select", json={"device_id": DEVICE})
    r.raise_for_status()
def main() -> int:
    admin_token = issue("trl9-admin", ["blackmore_admin"], ["*"])
    field_token = issue("trl9-field", ["field_app"], ["*"])
    scoped_token = issue("trl9-scoped", ["blackmore_admin"], ["system.health"])
    expired_token = issue("trl9-expired", ["blackmore_admin"], ["*"], ttl=-1)

    with client() as anon:
        health = anon.get("/health")
        record("gateway_health", health.status_code == 200 and health.json().get("ok") is True, health.json())
        openapi = anon.get("/openapi.json")
        record("gateway_version_0_2_1", openapi.status_code == 200 and openapi.json().get("info", {}).get("version") == "0.2.1", openapi.json().get("info"))
        unauth = anon.post("/v1/session/bootstrap", json={"metadata": {}})
        record("unauthenticated_rejected", unauth.status_code == 401, unauth.status_code)

    with client("bad.bad") as bad:
        r = bad.post("/v1/session/bootstrap", json={"metadata": {}})
        record("invalid_signature_rejected", r.status_code == 401, r.status_code)
    with client(expired_token) as expired:
        r = expired.post("/v1/session/bootstrap", json={"metadata": {}})
        record("expired_token_rejected", r.status_code == 401, r.status_code)
    with client(scoped_token) as scoped:
        sid = bootstrap(scoped, "scoped")
        select(scoped, sid)
        r = action(scoped, sid, "file.hash", {"path": str(README)})
        record("capability_scope_enforced", r.status_code == 403, r.status_code)
        scoped.delete(f"/v1/session/{sid}")

    with client(field_token) as field:
        sid_field = bootstrap(field, "field")
        select(field, sid_field)
        r = field.post("/v1/approval", json={
            "session_id": sid_field,
            "capability": "engineering.terminal.start",
            "target_device_id": DEVICE,
            "ttl_seconds": 120,
        })
        record("field_role_cannot_issue_approval", r.status_code == 403, r.status_code)
        r = action(field, sid_field, "engineering.terminal.start", {"shell": "powershell.exe"})
        record("privileged_action_requires_approval", r.status_code == 403, r.status_code)
        field.delete(f"/v1/session/{sid_field}")
    with client(admin_token) as admin:
        sid_a = bootstrap(admin, "admin-a")
        select(admin, sid_a)
        devices = admin.get(f"/v1/session/{sid_a}/devices")
        devices.raise_for_status()
        authorized = devices.json().get("devices", [])
        record("device_discovery", len(authorized) == 1 and authorized[0].get("device_id") == DEVICE, authorized)

        h = action(admin, sid_a, "system.health")
        h.raise_for_status()
        record("routed_system_health", h.json().get("ok") is True and h.json().get("data", {}).get("hostname") == "BTG", h.json())

        fh = action(admin, sid_a, "file.hash", {"path": str(README)})
        fh.raise_for_status()
        expected = hashlib.sha256(README.read_bytes()).hexdigest()
        record("file_hash", fh.json().get("data", {}).get("sha256") == expected, fh.json())

        fr = action(admin, sid_a, "file.read_text", {"path": str(README), "max_bytes": 8192})
        fr.raise_for_status()
        record("file_read_text", "BECP 0.2.1 Release" in fr.json().get("data", {}).get("text", ""), fr.json())

        outside = action(admin, sid_a, "file.read_text", {"path": r"<LOCAL_DRIVE>/Windows\win.ini"})
        record(
            "file_root_boundary",
            outside.status_code == 200
            and outside.json().get("ok") is False
            and "outside authorized roots" in str(outside.json().get("error", "")),
            outside.json(),
        )
        diag = action(admin, sid_a, "diagnostic.run_approved", {"command_id": "system_python_version", "timeout_seconds": 30})
        diag.raise_for_status()
        record("approved_diagnostic", diag.json().get("ok") is True and "Python" in diag.json().get("data", {}).get("stdout", ""), diag.json())

        change_approval = approval(admin, sid_a, "change.run_approved")
        change = action(admin, sid_a, "change.run_approved", {"command_id": "system_windows_version", "timeout_seconds": 30}, change_approval)
        change.raise_for_status()
        record("approved_change_path", change.json().get("ok") is True and change.json().get("data", {}).get("returncode") == 0, change.json())
        replay = action(admin, sid_a, "change.run_approved", {"command_id": "system_windows_version"}, change_approval)
        record("approval_replay_rejected", replay.status_code == 403, replay.status_code)

        start_token = approval(admin, sid_a, "engineering.terminal.start")
        started = action(admin, sid_a, "engineering.terminal.start", {"shell": "powershell.exe"}, start_token)
        started.raise_for_status()
        terminal_id = str(started.json().get("data", {}).get("session_id", ""))
        record("terminal_start", bool(terminal_id), terminal_id)
        drives_token = approval(admin, sid_a, "engineering.terminal.drives")
        drives = action(admin, sid_a, "engineering.terminal.drives", {}, drives_token)
        drives.raise_for_status()
        record("terminal_drives", bool(drives.json().get("data", {}).get("drives")), drives.json())

        cwd_token = approval(admin, sid_a, "engineering.terminal.cwd")
        cwd = action(admin, sid_a, "engineering.terminal.cwd", {"session_id": terminal_id, "path": str(ROOT)}, cwd_token)
        cwd.raise_for_status()
        record("terminal_cwd", cwd.json().get("ok") is True, cwd.json())

        exec_token = approval(admin, sid_a, "engineering.terminal.execute")
        executed = action(admin, sid_a, "engineering.terminal.execute", {
            "session_id": terminal_id,
            "command": "Write-Output BECP_TRL9_OPERATIONAL_OK; hostname",
            "timeout_seconds": 30,
        }, exec_token, timeout=40)
        executed.raise_for_status()
        stdout = executed.json().get("data", {}).get("stdout", "")
        record("terminal_execute", "BECP_TRL9_OPERATIONAL_OK" in stdout and "BTG" in stdout, executed.json())

        sid_b = bootstrap(admin, "admin-b")
        select(admin, sid_b)
        owner_token = approval(admin, sid_b, "engineering.terminal.execute")
        ownership = action(admin, sid_b, "engineering.terminal.execute", {"session_id": terminal_id, "command": "hostname"}, owner_token)
        record("terminal_ownership_isolation", ownership.status_code == 403, ownership.status_code)
        close_token = approval(admin, sid_a, "engineering.terminal.close")
        closed = action(admin, sid_a, "engineering.terminal.close", {"session_id": terminal_id}, close_token)
        closed.raise_for_status()
        record("terminal_close", closed.json().get("ok") is True, closed.json())

        try:
            disabled = admin.post(f"/v1/admin/device/{DEVICE}/remote-access", json={"enabled": False})
            disabled.raise_for_status()
            offline = wait_online(admin, 0)
            record("kill_switch_disconnect", offline.get("online_devices") == 0, offline)
            denied = action(admin, sid_a, "system.health")
            record("kill_switch_blocks_action", denied.status_code == 403, denied.status_code)
        finally:
            enabled = admin.post(f"/v1/admin/device/{DEVICE}/remote-access", json={"enabled": True})
            enabled.raise_for_status()

        recovered = wait_online(admin, 1)
        health_after = action(admin, sid_a, "system.health")
        health_after.raise_for_status()
        record("kill_switch_recovery", recovered.get("online_devices") == 1 and health_after.json().get("ok") is True, health_after.json())

        closed_b = admin.delete(f"/v1/session/{sid_b}")
        closed_a = admin.delete(f"/v1/session/{sid_a}")
        record("session_cleanup", closed_a.status_code == 200 and closed_b.status_code == 200, [closed_a.status_code, closed_b.status_code])
    result = {
        "status": "PASS",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": checks,
        "check_count": len(checks),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "checks": checks,
            "check_count": len(checks),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(failure, indent=2), encoding="utf-8")
        print(json.dumps(failure, indent=2))
        raise
