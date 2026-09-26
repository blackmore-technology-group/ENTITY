from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]
CA = ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem"
AUTH = ROOT / "runtime" / "secrets" / "openai_tunnel_becp_authorization.txt"
OUT = ROOT / "runtime" / "openai_tunnel" / "LOCAL_BINDING_VERIFICATION.json"


async def main() -> int:
    authorization = AUTH.read_text(encoding="utf-8").strip()
    client = httpx.AsyncClient(
        headers={"Authorization": authorization},
        verify=str(CA),
        timeout=20.0,
    )
    try:
        async with streamable_http_client(
            "https://127.0.0.1:8767/mcp", http_client=client
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = sorted(tool.name for tool in tools.tools)
                ok = "becp_action" in names and "becp_devices_list" in names
                result = {"status": "PASS" if ok else "FAIL", "tool_count": len(names), "tools": names}
    finally:
        await client.aclose()
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
