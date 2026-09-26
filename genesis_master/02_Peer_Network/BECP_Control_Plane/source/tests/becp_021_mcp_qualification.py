from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp.security import SignedTokenService

DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
KEY = ROOT / "runtime" / "secrets" / "client_signing.key"
OUT = ROOT / "runtime" / "qualification" / "becp_0.2.1" / "MCP_QUALIFICATION_RESULTS.json"
URL = "https://127.0.0.1:9177/mcp"

def extract(result):
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
    raise RuntimeError(f"No structured MCP result: {result!r}")


def issue_token() -> str:
    secret = KEY.read_text(encoding="utf-8").strip()
    return SignedTokenService(secret).issue({
        "sub": "becp-0.2.1-mcp-qualification",
        "subject": "BECP 0.2.1 MCP Qualification",
        "client_type": "qualification",
        "roles": ["blackmore_admin"],
        "devices": [DEVICE],
        "capabilities": ["*"],
    }, ttl_seconds=300, audience="becp-client")

async def main() -> int:
    token = issue_token()
    client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        verify=str(CA),
        timeout=30.0,
    )
    try:
        async with streamable_http_client(URL, http_client=client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = sorted(tool.name for tool in tools.tools)
                boot = extract(await session.call_tool("becp_session_bootstrap", {"metadata": {"qualification": "0.2.1-mcp"}}))
                sid = str(boot["session_id"])
                devices = extract(await session.call_tool("becp_devices_list", {"session_id": sid}))
                extract(await session.call_tool("becp_device_select", {"session_id": sid, "device_id": DEVICE}))
                health = extract(await session.call_tool("becp_action", {"session_id": sid, "capability": "system.health", "params": {}, "timeout_seconds": 20.0}))
                closed = extract(await session.call_tool("becp_session_close", {"session_id": sid}))
    finally:
        await client.aclose()

    result = {
        "status": "PASS" if len(names) >= 8 and health.get("ok") is True and closed.get("closed") is True else "FAIL",
        "tool_count": len(names),
        "tools": names,
        "authorized_devices": len(devices.get("devices", [])),
        "health_ok": health.get("ok") is True,
        "session_closed": closed.get("closed") is True,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
