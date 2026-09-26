from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .security import SignedTokenService


DEFAULT_CONFIG_ENV = "BECP_RDC_BRIDGE_CONFIG"
APPROVAL_PREFIXES = (
    "engineering.terminal.",
    "change.",
    "deployment.",
    "rollback.",
    "update.install",
    "model.replace",
)
@dataclass(frozen=True)
class BridgeConfig:
    gateway_url: str
    ca_cert: str
    client_signing_key_path: str
    principal: str
    subject: str
    client_type: str
    roles: list[str]
    devices: list[str]
    capabilities: list[str]
    default_device: str
    token_ttl_seconds: int = 300
    request_timeout_seconds: float = 60.0

    @classmethod
    def load(cls, path: str | Path) -> "BridgeConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**raw)


def requires_approval(capability: str) -> bool:
    return capability.startswith(APPROVAL_PREFIXES)
class RDCBECPBridge:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        secret = Path(config.client_signing_key_path).read_text(encoding="utf-8").strip()
        token = SignedTokenService(secret).issue(
            {
                "sub": config.principal,
                "subject": config.subject,
                "client_type": config.client_type,
                "roles": config.roles,
                "devices": config.devices,
                "capabilities": config.capabilities,
            },
            ttl_seconds=max(60, min(config.token_ttl_seconds, 900)),
            audience="becp-client",
        )
        self.client = httpx.Client(
            base_url=config.gateway_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            verify=config.ca_cert,
            timeout=config.request_timeout_seconds,
        )
        self.session_id: str | None = None
        self.selected_device_id: str | None = None
    def close(self) -> None:
        if self.session_id:
            try:
                self.client.delete(f"/v1/session/{self.session_id}")
            except Exception:
                pass
        self.client.close()
        self.session_id = None
        self.selected_device_id = None

    def __enter__(self) -> "RDCBECPBridge":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        return response.json()

    def bootstrap(self) -> dict[str, Any]:
        data = self._json(self.client.post("/v1/session/bootstrap", json={
            "metadata": {"transport": "remote_desktop_commander_bridge"}
        }))
        self.session_id = str(data["session_id"])
        return data
    def gateway_health(self) -> dict[str, Any]:
        return self._json(self.client.get("/health"))

    def devices(self) -> list[dict[str, Any]]:
        self._ensure_session()
        data = self._json(self.client.get(f"/v1/session/{self.session_id}/devices"))
        return list(data.get("devices", []))

    def _ensure_session(self) -> None:
        if not self.session_id:
            self.bootstrap()

    def resolve_device(self, selector: str | None = None) -> str:
        wanted = (selector or self.config.default_device).casefold()
        for device in self.devices():
            values = {
                str(device.get("device_id", "")).casefold(),
                str(device.get("hostname", "")).casefold(),
                str(device.get("display_name", "")).casefold(),
            }
            if wanted in values:
                return str(device["device_id"])
        raise KeyError(f"BECP device not found: {selector or self.config.default_device}")
    def select_device(self, selector: str | None = None) -> str:
        self._ensure_session()
        device_id = self.resolve_device(selector)
        self._json(self.client.post(
            f"/v1/session/{self.session_id}/select",
            json={"device_id": device_id},
        ))
        self.selected_device_id = device_id
        return device_id

    def _approval(self, capability: str) -> str:
        if not self.session_id or not self.selected_device_id:
            raise RuntimeError("BECP session/device selection incomplete")
        data = self._json(self.client.post("/v1/approval", json={
            "session_id": self.session_id,
            "capability": capability,
            "target_device_id": self.selected_device_id,
            "ttl_seconds": 120,
        }))
        return str(data["approval_token"])

    def action(self, capability: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_session()
        approval = self._approval(capability) if requires_approval(capability) else None
        return self._json(self.client.post("/v1/action", json={
            "session_id": self.session_id,
            "capability": capability,
            "params": params or {},
            "approval_token": approval,
            "timeout_seconds": self.config.request_timeout_seconds,
        }))
    def terminal_run(
        self,
        command: str,
        selector: str | None = None,
        shell: str = "powershell.exe",
        cwd: str | None = None,
    ) -> dict[str, Any]:
        self.select_device(selector)
        started = self.action("engineering.terminal.start", {"shell": shell})
        terminal_id = str(started.get("data", {}).get("session_id", ""))
        if not terminal_id:
            raise RuntimeError(f"BECP terminal start failed: {started}")
        try:
            if cwd:
                self.action("engineering.terminal.cwd", {"session_id": terminal_id, "path": cwd})
            return self.action(
                "engineering.terminal.execute",
                {"session_id": terminal_id, "command": command, "timeout_seconds": self.config.request_timeout_seconds},
            )
        finally:
            try:
                self.action("engineering.terminal.close", {"session_id": terminal_id})
            except Exception:
                pass


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remote Desktop Commander to BECP bridge")
    parser.add_argument("--config", default=os.getenv(DEFAULT_CONFIG_ENV, "config/RDC_BECP_BRIDGE.json"))
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("status")
    sub.add_parser("devices")

    health = sub.add_parser("health")
    health.add_argument("--device")

    action = sub.add_parser("action")
    action.add_argument("capability")
    action.add_argument("--device")
    action.add_argument("--params-json", default="{}")

    terminal = sub.add_parser("terminal-run")
    terminal.add_argument("--device")
    terminal.add_argument("--shell", default="powershell.exe")
    terminal.add_argument("--cwd")
    terminal.add_argument("--command", dest="terminal_command", required=True)
    return parser
def main() -> int:
    args = build_parser().parse_args()
    try:
        config = BridgeConfig.load(args.config)
        with RDCBECPBridge(config) as bridge:
            if args.operation == "status":
                _emit({"ok": True, "mode": "RDC_DIRECT_PLUS_BECP_BRIDGE", "gateway": bridge.gateway_health()})
            elif args.operation == "devices":
                _emit({"ok": True, "devices": bridge.devices()})
            elif args.operation == "health":
                device_id = bridge.select_device(args.device)
                _emit({"ok": True, "device_id": device_id, "result": bridge.action("system.health")})
            elif args.operation == "action":
                device_id = bridge.select_device(args.device)
                params = json.loads(args.params_json)
                _emit({"ok": True, "device_id": device_id, "result": bridge.action(args.capability, params)})
            elif args.operation == "terminal-run":
                result = bridge.terminal_run(args.terminal_command, args.device, args.shell, args.cwd)
                _emit({"ok": bool(result.get("ok")), "result": result})
        return 0
    except Exception as exc:
        _emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

