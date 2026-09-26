from __future__ import annotations

import asyncio
import json
import ssl
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import httpx2
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.niki_remote_adapter import NIKIBECPSession
from api.gateway import GatewayState, create_agent_app, create_client_app
from blackmore_ecp.device_registry import DeviceRegistry, EnrolledDevice
from blackmore_ecp.mcp_adapter import create_mcp_server
from blackmore_ecp.security import SignedTokenService

BTG_ID = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
SIM_ID = "55546079-959f-4557-a49b-84659d2ebb2e"
HOST = "127.0.0.1"
API_PORT, AGENT_PORT, MCP_PORT = 8875, 8876, 8877
QUAL = ROOT / "runtime" / "qualification"
QUAL.mkdir(parents=True, exist_ok=True)
REGISTRY = QUAL / "devices_live.json"
AUDIT = QUAL / "gateway_audit.jsonl"
RESULTS = QUAL / "LIVE_RESULTS.json"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
SERVER_CERT = ROOT / "runtime" / "pki" / "server" / "gateway.cert.pem"
SERVER_KEY = ROOT / "runtime" / "pki" / "server" / "gateway.key.pem"
CLIENT_KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
APPROVAL_KEY = ROOT / "runtime" / "secrets" / "approval_signing.key"


def device_cert(device_id: str) -> Path:
    return ROOT / "runtime" / "pki" / "devices" / device_id / "device.cert.pem"


def device_key(device_id: str) -> Path:
    return ROOT / "runtime" / "pki" / "devices" / device_id / "device.key.pem"


def prepare_registry() -> DeviceRegistry:
    if REGISTRY.exists():
        REGISTRY.unlink()
    source = DeviceRegistry(str(ROOT / "runtime" / "registry" / "devices.json"))
    target = DeviceRegistry(str(REGISTRY))
    for device_id in (BTG_ID, SIM_ID):
        original = source.get(device_id)
        cloned = EnrolledDevice.model_validate(original.model_dump())
        cloned.online = False
        cloned.connected_session_id = None
        cloned.revoked = False
        cloned.remote_access_enabled = True
        target.register(cloned)
    return target
def issue_token(subject: str, client_type: str, devices: list[str]) -> str:
    signer = SignedTokenService(CLIENT_KEY.read_text(encoding="utf-8").strip())
    return signer.issue(
        {
            "sub": subject,
            "subject": subject,
            "client_type": client_type,
            "roles": ["blackmore_admin", f"{client_type}_privileged_engineer"]
            if client_type in {"chatgpt", "niki"}
            else ["blackmore_admin"],
            "devices": devices,
            "capabilities": ["*"],
        },
        ttl_seconds=3600,
        audience="becp-client",
    )


def uvicorn_server(app: Any, port: int, require_client_cert: bool = False) -> uvicorn.Server:
    kwargs: dict[str, Any] = {
        "app": app,
        "host": HOST,
        "port": port,
        "log_level": "error",
        "ssl_certfile": str(SERVER_CERT),
        "ssl_keyfile": str(SERVER_KEY),
    }
    if require_client_cert:
        kwargs["ssl_ca_certs"] = str(CA)
        kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
    return uvicorn.Server(uvicorn.Config(**kwargs))


async def wait_started(servers: list[uvicorn.Server], timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(server.started for server in servers):
            return
        await asyncio.sleep(0.1)
    raise TimeoutError("BECP qualification servers did not start")
async def launch_agent(device_id: str, config_name: str) -> asyncio.subprocess.Process:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(ROOT / "agents" / "windows_engineering_workstation_agent.py"),
        "--config", str(ROOT / "config" / config_name),
        "--gateway", f"wss://{HOST}:{AGENT_PORT}/agent",
        "--device-cert", str(device_cert(device_id)),
        "--device-key", str(device_key(device_id)),
        "--ca-cert", str(CA),
        "--heartbeat-seconds", "2",
        "--reconnect-seconds", "1",
        cwd=str(ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    ready = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
    if b'"status": "READY"' not in ready:
        raise RuntimeError(f"agent did not report READY: {ready!r}")
    return process


async def wait_online(client: httpx.AsyncClient, count: int, timeout: float = 20.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = await client.get("/health")
        response.raise_for_status()
        last = response.json()
        if int(last.get("online_devices", 0)) == count:
            return last
        await asyncio.sleep(0.25)
    raise TimeoutError(f"expected {count} online devices; last={last}")


async def approval(client: httpx.AsyncClient, session_id: str, capability: str, device_id: str) -> str:
    response = await client.post("/v1/approval", json={
        "session_id": session_id,
        "capability": capability,
        "target_device_id": device_id,
        "ttl_seconds": 120,
    })
    response.raise_for_status()
    return str(response.json()["approval_token"])
async def action(
    client: httpx.AsyncClient,
    session_id: str,
    capability: str,
    params: dict[str, Any] | None = None,
    approval_token: str | None = None,
) -> httpx.Response:
    return await client.post("/v1/action", json={
        "session_id": session_id,
        "capability": capability,
        "params": params or {},
        "approval_token": approval_token,
        "timeout_seconds": 60,
    })


def extract_mcp(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if structured:
        return dict(structured)
    structured = getattr(result, "structured_content", None)
    if structured:
        return dict(structured)
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except Exception:
                continue
    raise RuntimeError(f"MCP result had no structured JSON: {result!r}")


async def run_mcp_qualification(token: str) -> dict[str, Any]:
    client = httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        verify=str(CA),
        timeout=30.0,
    )
    try:
        async with streamable_http_client(
            f"https://{HOST}:{MCP_PORT}/mcp", http_client=client
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                bootstrap = extract_mcp(await session.call_tool(
                    "becp_session_bootstrap", {"metadata": {"qualification": "mcp-v2"}}
                ))
                sid = str(bootstrap["session_id"])
                devices = extract_mcp(await session.call_tool(
                    "becp_devices_list", {"session_id": sid}
                ))
                extract_mcp(await session.call_tool(
                    "becp_device_select", {"session_id": sid, "device_id": SIM_ID}
                ))
                health = extract_mcp(await session.call_tool(
                    "becp_action",
                    {
                        "session_id": sid,
                        "capability": "system.health",
                        "params": {},
                        "timeout_seconds": 20.0,
                    },
                ))
                closed = extract_mcp(await session.call_tool(
                    "becp_session_close", {"session_id": sid}
                ))
                names = sorted(tool.name for tool in tools.tools)
                if "becp_action" not in names or "becp_devices_list" not in names:
                    raise AssertionError(f"required MCP tools missing: {names}")
                if len(devices.get("devices", [])) != 2:
                    raise AssertionError("MCP device discovery did not return both devices")
                if not health.get("ok") or not closed.get("closed"):
                    raise AssertionError("MCP action/session close failed")
                return {"tool_count": len(names), "health_ok": True, "session_closed": True}
    finally:
        await client.aclose()


def run_niki_qualification(token: str) -> dict[str, Any]:
    client = NIKIBECPSession(
        base_url=f"https://{HOST}:{API_PORT}",
        bearer_token=token,
        ca_cert=str(CA),
        timeout_seconds=60.0,
    )
    try:
        bootstrap = client.bootstrap({"qualification": "niki-native"})
        devices = client.devices()
        client.select_device(SIM_ID)
        health = client.action("system.health")
        terminal = client.start_terminal()
        terminal_id = str(terminal["data"]["session_id"])
        executed = client.terminal_execute(terminal_id, "Write-Output 'NIKI_BECP_E2E_OK'")
        client.terminal_close(terminal_id)
        closed = client.close_session()
        if len(devices) != 2 or not health.get("ok") or not closed:
            raise AssertionError("NIKI gateway qualification failed")
        if "NIKI_BECP_E2E_OK" not in executed.get("data", {}).get("stdout", ""):
            raise AssertionError("NIKI remote terminal output marker missing")
        return {"session_id": bootstrap["session_id"], "devices": len(devices), "terminal_ok": True}
    finally:
        client.close_client()
async def main() -> int:
    prepare_registry()
    if AUDIT.exists():
        AUDIT.unlink()
    client_secret = CLIENT_KEY.read_text(encoding="utf-8").strip()
    approval_secret = APPROVAL_KEY.read_text(encoding="utf-8").strip()
    state = GatewayState(
        registry_path=str(REGISTRY),
        audit_path=str(AUDIT),
        signing_secret=client_secret,
        approval_signing_secret=approval_secret,
        ai_session_ttl_minutes=30,
    )
    client_app = create_client_app(state)
    agent_app = create_agent_app(state)
    mcp_server = create_mcp_server(state, f"https://{HOST}:{MCP_PORT}/mcp")
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host=HOST,
    )

    servers = [
        uvicorn_server(client_app, API_PORT),
        uvicorn_server(agent_app, AGENT_PORT, require_client_cert=True),
        uvicorn_server(mcp_app, MCP_PORT),
    ]
    tasks = [asyncio.create_task(server.serve()) for server in servers]
    agents: list[asyncio.subprocess.Process] = []
    summary: dict[str, Any] = {"started_utc": time.time(), "checks": {}}
    try:
        await wait_started(servers)
        agents.append(await launch_agent(BTG_ID, "BTG_ENGINEERING_WORKSTATION.json"))
        agents.append(await launch_agent(SIM_ID, "ENG_SIM_01.json"))

        chat_token = issue_token("qualification-chat-a", "chatgpt", [BTG_ID, SIM_ID])
        headers = {"Authorization": f"Bearer {chat_token}"}
        async with httpx.AsyncClient(
            base_url=f"https://{HOST}:{API_PORT}", headers=headers,
            verify=str(CA), timeout=60.0,
        ) as client:
            online = await wait_online(client, 2)
            summary["checks"]["two_agents_online"] = online
            response = await client.post("/v1/session/bootstrap", json={"metadata": {"qualification": "new-chat"}})
            response.raise_for_status()
            session_a = response.json()
            sid_a = str(session_a["session_id"])
            devices_response = await client.get(f"/v1/session/{sid_a}/devices")
            devices_response.raise_for_status()
            discovered = devices_response.json()["devices"]
            discovered_ids = {str(item["device_id"]) for item in discovered}
            if discovered_ids != {BTG_ID, SIM_ID}:
                raise AssertionError(f"new-chat discovery mismatch: {discovered_ids}")
            summary["checks"]["new_chat_discovery"] = sorted(discovered_ids)

            selected = await client.post(
                f"/v1/session/{sid_a}/select", json={"device_id": BTG_ID}
            )
            selected.raise_for_status()
            start_approval = await approval(client, sid_a, "engineering.terminal.start", BTG_ID)
            start_result = await action(
                client, sid_a, "engineering.terminal.start",
                {"shell": "powershell.exe"}, start_approval,
            )
            start_result.raise_for_status()
            start_json = start_result.json()
            if not start_json.get("ok"):
                raise AssertionError(f"BTG terminal start failed: {start_json}")
            terminal_id = str(start_json["data"]["session_id"])

            exec_approval = await approval(client, sid_a, "engineering.terminal.execute", BTG_ID)
            exec_result = await action(
                client, sid_a, "engineering.terminal.execute",
                {"session_id": terminal_id, "command": "Write-Output 'BECP_REMOTE_E2E_OK'; hostname"},
                exec_approval,
            )
            exec_result.raise_for_status()
            exec_json = exec_result.json()
            stdout = exec_json.get("data", {}).get("stdout", "")
            if "BECP_REMOTE_E2E_OK" not in stdout:
                raise AssertionError(f"BTG remote output marker missing: {exec_json}")
            summary["checks"]["btg_remote_terminal"] = {"ok": True, "stdout": stdout.strip()}
            second = await client.post("/v1/session/bootstrap", json={"metadata": {"qualification": "ownership"}})
            second.raise_for_status()
            sid_b = str(second.json()["session_id"])
            select_b = await client.post(
                f"/v1/session/{sid_b}/select", json={"device_id": BTG_ID}
            )
            select_b.raise_for_status()
            hijack_approval = await approval(client, sid_b, "engineering.terminal.execute", BTG_ID)
            hijack = await action(
                client, sid_b, "engineering.terminal.execute",
                {"session_id": terminal_id, "command": "Write-Output 'SHOULD_NOT_RUN'"},
                hijack_approval,
            )
            if hijack.status_code != 403:
                raise AssertionError(f"terminal ownership hijack was not blocked: {hijack.status_code} {hijack.text}")
            summary["checks"]["terminal_ownership"] = {"blocked": True, "status": 403}
            close_b = await client.delete(f"/v1/session/{sid_b}")
            close_b.raise_for_status()

            close_approval = await approval(client, sid_a, "engineering.terminal.close", BTG_ID)
            close_result = await action(
                client, sid_a, "engineering.terminal.close",
                {"session_id": terminal_id}, close_approval,
            )
            close_result.raise_for_status()
            if not close_result.json().get("ok"):
                raise AssertionError("BTG terminal close failed")

            select_sim = await client.post(
                f"/v1/session/{sid_a}/select", json={"device_id": SIM_ID}
            )
            select_sim.raise_for_status()
            sim_start_token = await approval(client, sid_a, "engineering.terminal.start", SIM_ID)
            sim_start = await action(
                client, sid_a, "engineering.terminal.start",
                {"shell": "powershell.exe"}, sim_start_token,
            )
            sim_start.raise_for_status()
            sim_terminal = str(sim_start.json()["data"]["session_id"])
            sim_exec_token = await approval(client, sid_a, "engineering.terminal.execute", SIM_ID)
            sim_exec = await action(
                client, sid_a, "engineering.terminal.execute",
                {"session_id": sim_terminal, "command": "Write-Output 'ENG_SIM_E2E_OK'"}, sim_exec_token,
            )
            sim_exec.raise_for_status()
            if "ENG_SIM_E2E_OK" not in sim_exec.json().get("data", {}).get("stdout", ""):
                raise AssertionError("simulated workstation routing marker missing")
            summary["checks"]["second_workstation_routing"] = {"ok": True, "device_id": SIM_ID}
            sim_close_token = await approval(client, sid_a, "engineering.terminal.close", SIM_ID)
            sim_close = await action(
                client, sid_a, "engineering.terminal.close",
                {"session_id": sim_terminal}, sim_close_token,
            )
            sim_close.raise_for_status()

            select_btg = await client.post(
                f"/v1/session/{sid_a}/select", json={"device_id": BTG_ID}
            )
            select_btg.raise_for_status()
            disabled = await client.post(
                f"/v1/admin/device/{BTG_ID}/remote-access", json={"enabled": False}
            )
            disabled.raise_for_status()
            await wait_online(client, 1)
            denied = await action(client, sid_a, "system.health")
            if denied.status_code != 403:
                raise AssertionError(f"kill switch did not block routed action: {denied.status_code} {denied.text}")
            summary["checks"]["kill_switch"] = {"disconnect_enforced": True, "action_blocked": True}

            enabled = await client.post(
                f"/v1/admin/device/{BTG_ID}/remote-access", json={"enabled": True}
            )
            enabled.raise_for_status()
            await wait_online(client, 2, timeout=20.0)
            recovered = await action(client, sid_a, "system.health")
            recovered.raise_for_status()
            if not recovered.json().get("ok"):
                raise AssertionError("BTG did not recover after remote access re-enable")
            summary["checks"]["kill_switch_recovery"] = {"reconnected": True, "health_ok": True}

            session_close = await client.delete(f"/v1/session/{sid_a}")
            session_close.raise_for_status()
            if not session_close.json().get("closed"):
                raise AssertionError("primary qualification AI session did not close")

        mcp_token = issue_token("qualification-mcp", "chatgpt", [BTG_ID, SIM_ID])
        summary["checks"]["mcp_v2"] = await run_mcp_qualification(mcp_token)

        niki_token = issue_token("qualification-niki", "niki", [BTG_ID, SIM_ID])
        summary["checks"]["niki_adapter"] = await asyncio.to_thread(run_niki_qualification, niki_token)
        summary["completed_utc"] = time.time()
        summary["status"] = "PASS"
        RESULTS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    except Exception as exc:
        summary["completed_utc"] = time.time()
        summary["status"] = "FAIL"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        RESULTS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        raise
    finally:
        for process in agents:
            if process.returncode is None:
                process.terminate()
        for process in agents:
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        for server in servers:
            server.should_exit = True
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
