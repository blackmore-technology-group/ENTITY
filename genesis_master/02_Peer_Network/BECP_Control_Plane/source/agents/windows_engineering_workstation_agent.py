from __future__ import annotations

import argparse
import asyncio
import json
import platform
import secrets
import ssl
import sys
import time
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackmore_ecp import __version__
from blackmore_ecp.models import ActionRequest
from blackmore_ecp.pki import sign_device_hello
from blackmore_ecp.runtime import BECPCore


def _result_json(result) -> dict:
    return result.model_dump()


def run_stdio(core: BECPCore) -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            request = ActionRequest.model_validate_json(raw)
            payload = _result_json(core.execute(request))
        except Exception as exc:
            payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(payload), flush=True)
    return 0


async def _heartbeat(ws, device_id: str, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        await ws.send(json.dumps({
            "type": "heartbeat",
            "device_id": device_id,
            "timestamp": int(time.time()),
        }))


def _ssl_context(ca_cert: str, device_cert: str, device_key: str) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_cert)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=device_cert, keyfile=device_key)
    return context


async def _remote_once(core: BECPCore, args) -> None:
    device_id = str(core.config["device_id"])
    timestamp = int(time.time())
    nonce = secrets.token_urlsafe(24)
    signature = sign_device_hello(args.device_key, device_id, timestamp, nonce)
    hello = {
        "type": "hello",
        "device_id": device_id,
        "hostname": platform.node(),
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
        "agent_version": __version__,
    }
    context = _ssl_context(args.ca_cert, args.device_cert, args.device_key)
    async with websockets.connect(
        args.gateway,
        ssl=context,
        open_timeout=15,
        ping_interval=20,
        ping_timeout=20,
        max_size=2 * 1024 * 1024,
    ) as ws:
        await ws.send(json.dumps(hello))
        ack = json.loads(await ws.recv())
        if ack.get("type") != "hello_ack" or not ack.get("ok"):
            raise PermissionError(ack.get("error", "gateway rejected device authentication"))
        heartbeat = asyncio.create_task(_heartbeat(ws, device_id, args.heartbeat_seconds))
        try:
            async for raw in ws:
                message = json.loads(raw)
                if message.get("type") == "action":
                    request_id = str(message["request_id"])
                    try:
                        request = ActionRequest.model_validate(message["action"])
                        result = _result_json(core.execute(request))
                    except Exception as exc:
                        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    await ws.send(json.dumps({
                        "type": "action_result",
                        "request_id": request_id,
                        "result": result,
                    }))
                elif message.get("type") == "shutdown":
                    return
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)


async def run_remote(core: BECPCore, args) -> int:
    while True:
        try:
            await _remote_once(core, args)
            return 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"BECP agent connection error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            if args.once:
                return 2
            await asyncio.sleep(args.reconnect_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="BECP Windows Engineering Workstation Agent")
    parser.add_argument("--config", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stdio", action="store_true")
    mode.add_argument("--gateway", help="Outbound wss:// BECP gateway agent endpoint")
    parser.add_argument("--device-cert")
    parser.add_argument("--device-key")
    parser.add_argument("--ca-cert")
    parser.add_argument("--heartbeat-seconds", type=int, default=20)
    parser.add_argument("--reconnect-seconds", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    core = BECPCore(args.config)
    print(json.dumps({
        "status": "READY",
        "device_id": core.config.get("device_id"),
        "device": platform.node(),
        "terminal_enabled": core.engineering_terminal is not None,
        "transport": "stdio-local" if args.stdio else "wss-outbound",
    }), flush=True)
    if args.stdio:
        return run_stdio(core)
    required = [args.device_cert, args.device_key, args.ca_cert]
    if not all(required):
        parser.error("--device-cert, --device-key and --ca-cert are required with --gateway")
    if not str(args.gateway).startswith("wss://"):
        parser.error("remote engineering agent requires wss:// transport")
    return asyncio.run(run_remote(core, args))


if __name__ == "__main__":
    raise SystemExit(main())
