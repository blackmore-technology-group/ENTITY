from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.gateway import GatewayState, create_agent_app, create_client_app
from blackmore_ecp.mcp_adapter import create_mcp_server


def _read_secret(path: str) -> str:
    value = Path(path).read_text(encoding="utf-8").strip()
    if len(value.encode("utf-8")) < 32:
        raise RuntimeError(f"BECP secret is too short: {path}")
    return value


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


async def serve(config_path: str) -> None:
    cfg = _load(config_path)
    state = GatewayState(
        registry_path=cfg["registry_path"],
        audit_path=cfg["audit_path"],
        signing_secret=_read_secret(cfg["client_signing_key_path"]),
        approval_signing_secret=_read_secret(cfg["approval_signing_key_path"]),
        ai_session_ttl_minutes=int(cfg.get("ai_session_ttl_minutes", 60)),
    )

    client_app = create_client_app(state)
    agent_app = create_agent_app(state)

    mcp_listener = cfg.get("mcp_listener", {"host": "127.0.0.1", "port": 8767})
    mcp_resource = str(cfg.get(
        "mcp_resource_url",
        f"https://{mcp_listener.get('host', '127.0.0.1')}:{mcp_listener.get('port', 8767)}/mcp",
    ))
    mcp_server = create_mcp_server(state, mcp_resource)
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host=str(mcp_listener.get("host", "127.0.0.1")),
    )

    tls = cfg["tls"]
    client_server = uvicorn.Server(uvicorn.Config(
        client_app,
        host=str(cfg["client_listener"].get("host", "127.0.0.1")),
        port=int(cfg["client_listener"].get("port", 8765)),
        log_level=str(cfg.get("log_level", "info")),
        ssl_certfile=tls["server_cert"],
        ssl_keyfile=tls["server_key"],
    ))

    agent_server = uvicorn.Server(uvicorn.Config(
        agent_app,
        host=str(cfg["agent_listener"].get("host", "127.0.0.1")),
        port=int(cfg["agent_listener"].get("port", 8766)),
        log_level=str(cfg.get("log_level", "info")),
        ssl_certfile=tls["server_cert"],
        ssl_keyfile=tls["server_key"],
        ssl_ca_certs=tls["ca_cert"],
        ssl_cert_reqs=ssl.CERT_REQUIRED,
    ))

    mcp_uvicorn = uvicorn.Server(uvicorn.Config(
        mcp_app,
        host=str(mcp_listener.get("host", "127.0.0.1")),
        port=int(mcp_listener.get("port", 8767)),
        log_level=str(cfg.get("log_level", "info")),
        ssl_certfile=tls["server_cert"],
        ssl_keyfile=tls["server_key"],
    ))

    await asyncio.gather(
        client_server.serve(),
        agent_server.serve(),
        mcp_uvicorn.serve(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BECP HTTPS, mTLS agent, and MCP gateways")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    asyncio.run(serve(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
