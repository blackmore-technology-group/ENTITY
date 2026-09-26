from pathlib import Path
import asyncio, json, sys
import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
BASE = "https://127.0.0.1:8765"
MCP = "https://127.0.0.1:8767/mcp"
secret = KEY.read_text(encoding="utf-8").strip()
token = SignedTokenService(secret).issue({
    "sub": "running-service-verification",
    "subject": "running-service-verification",
    "client_type": "qualification",
    "roles": ["blackmore_admin"],
    "devices": [DEVICE],
    "capabilities": ["*"],
}, ttl_seconds=300, audience="becp-client")
HEADERS = {"Authorization": f"Bearer {token}"}


def approval(client, sid, capability):
    response = client.post("/v1/approval", json={
        "session_id": sid,
        "capability": capability,
        "target_device_id": DEVICE,
        "ttl_seconds": 120,
    })
    response.raise_for_status()
    return response.json()["approval_token"]

def verify_api_and_terminal():
    with httpx.Client(base_url=BASE, headers=HEADERS, verify=str(CA), timeout=20) as client:
        health = client.get("/health"); health.raise_for_status()
        boot = client.post("/v1/session/bootstrap", json={"metadata": {"verification": "running-service"}})
        boot.raise_for_status(); sid = boot.json()["session_id"]
        client.post(f"/v1/session/{sid}/select", json={"device_id": DEVICE}).raise_for_status()

        routed = client.post("/v1/action", json={
            "session_id": sid, "capability": "system.health", "params": {}, "timeout_seconds": 10,
        })
        routed.raise_for_status(); routed_result = routed.json()

        start = client.post("/v1/action", json={
            "session_id": sid,
            "capability": "engineering.terminal.start",
            "params": {"shell": "powershell.exe"},
            "approval_token": approval(client, sid, "engineering.terminal.start"),
            "timeout_seconds": 15,
        })
        start.raise_for_status(); terminal_id = start.json()["data"]["session_id"]
        execute = client.post("/v1/action", json={
            "session_id": sid,
            "capability": "engineering.terminal.execute",
            "params": {"session_id": terminal_id, "command": "Write-Output BECP_RUNNING_VERIFY_OK; hostname"},
            "approval_token": approval(client, sid, "engineering.terminal.execute"),
            "timeout_seconds": 15,
        })
        execute.raise_for_status(); execute_result = execute.json()

        close = client.post("/v1/action", json={
            "session_id": sid,
            "capability": "engineering.terminal.close",
            "params": {"session_id": terminal_id},
            "approval_token": approval(client, sid, "engineering.terminal.close"),
            "timeout_seconds": 15,
        })
        close.raise_for_status()
        client.delete(f"/v1/session/{sid}").raise_for_status()

    stdout = execute_result.get("data", {}).get("stdout", "")
    ok = routed_result.get("ok") is True and "BECP_RUNNING_VERIFY_OK" in stdout and "BTG" in stdout
    return {"ok": ok, "gateway_health": health.json(), "routed_health": routed_result, "terminal_stdout": stdout}

def extract_mcp(result):
    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    if structured:
        return dict(structured)
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except Exception:
                pass
    raise RuntimeError(f"MCP result had no structured JSON: {result!r}")


async def verify_mcp():
    client = httpx.AsyncClient(headers=HEADERS, verify=str(CA), timeout=20)
    try:
        async with streamable_http_client(MCP, http_client=client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                boot = extract_mcp(await session.call_tool("becp_session_bootstrap", {"metadata": {"verification": "running-mcp"}}))
                sid = boot["session_id"]
                await session.call_tool("becp_device_select", {"session_id": sid, "device_id": DEVICE})
                health = extract_mcp(await session.call_tool("becp_action", {
                    "session_id": sid,
                    "capability": "system.health",
                    "params": {},
                    "timeout_seconds": 10.0,
                }))
                closed = extract_mcp(await session.call_tool("becp_session_close", {"session_id": sid}))
                names = sorted(tool.name for tool in tools.tools)
                ok = "becp_action" in names and health.get("ok") is True and closed.get("closed") is True
                return {"ok": ok, "tool_count": len(names), "tools": names}
    finally:
        await client.aclose()


def main():
    api_result = verify_api_and_terminal()
    mcp_result = asyncio.run(verify_mcp())
    overall = bool(api_result["ok"] and mcp_result["ok"])
    result = {"status": "PASS" if overall else "FAIL", "api_terminal": api_result, "mcp": mcp_result}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if overall else 2)


if __name__ == "__main__":
    main()
