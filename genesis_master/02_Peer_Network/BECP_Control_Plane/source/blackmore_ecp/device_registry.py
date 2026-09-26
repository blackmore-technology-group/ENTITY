from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EnrolledDevice(BaseModel):
    device_id: str = Field(default_factory=lambda: str(uuid4()))
    hostname: str
    display_name: str
    device_role: str = "ENGINEERING_WORKSTATION"
    platform: str
    owner_principal: str | None = None
    agent_version: str | None = None
    terminal_enabled: bool = False
    terminal_privilege_model: str = "INHERIT_OS_ACCOUNT"
    certificate_path: str | None = None
    certificate_fingerprint: str | None = None
    connected_session_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    online: bool = False
    last_seen_utc: str | None = None
    revoked: bool = False
    remote_access_enabled: bool = True


class DeviceRegistry:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.devices: dict[str, EnrolledDevice] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw.get("devices", []):
            device = EnrolledDevice.model_validate(item)
            self.devices[device.device_id] = device

    def _save(self) -> None:
        body: dict[str, Any] = {
            "schema_version": 2,
            "devices": [d.model_dump() for d in self.devices.values()],
        }
        self.path.write_text(json.dumps(body, indent=2), encoding="utf-8")

    def register(self, device: EnrolledDevice) -> EnrolledDevice:
        if device.device_id in self.devices and self.devices[device.device_id].revoked:
            raise PermissionError("revoked device cannot be silently re-enrolled")
        self.devices[device.device_id] = device
        self._save()
        return device
    def heartbeat(self, device_id: str, online: bool = True) -> EnrolledDevice:
        device = self.get(device_id)
        if device.revoked:
            raise PermissionError("revoked device")
        if not device.remote_access_enabled:
            raise PermissionError("remote access disabled")
        device.online = online
        device.last_seen_utc = datetime.now(timezone.utc).isoformat()
        self._save()
        return device

    def set_connection(self, device_id: str, connection_id: str | None) -> EnrolledDevice:
        device = self.get(device_id)
        if device.revoked:
            raise PermissionError("revoked device")
        if connection_id is not None and not device.remote_access_enabled:
            raise PermissionError("remote access disabled")
        device.connected_session_id = connection_id
        device.online = connection_id is not None
        device.last_seen_utc = datetime.now(timezone.utc).isoformat()
        self._save()
        return device

    def revoke(self, device_id: str) -> EnrolledDevice:
        device = self.get(device_id)
        device.revoked = True
        device.online = False
        device.connected_session_id = None
        self._save()
        return device

    def set_remote_access(self, device_id: str, enabled: bool) -> EnrolledDevice:
        device = self.get(device_id)
        if device.revoked and enabled:
            raise PermissionError("revoked device cannot be re-enabled")
        device.remote_access_enabled = bool(enabled)
        if not enabled:
            device.online = False
            device.connected_session_id = None
        self._save()
        return device

    def get(self, device_id: str) -> EnrolledDevice:
        try:
            return self.devices[device_id]
        except KeyError as exc:
            raise KeyError(f"unknown BECP device: {device_id}") from exc

    def discover(self, allowed_device_ids: set[str] | None = None) -> list[EnrolledDevice]:
        devices = [d for d in self.devices.values() if not d.revoked]
        if allowed_device_ids is not None:
            devices = [d for d in devices if d.device_id in allowed_device_ids]
        return sorted(devices, key=lambda d: (not d.online, d.display_name.casefold()))

    def by_alias(self, alias: str) -> EnrolledDevice:
        matches = [
            d for d in self.devices.values()
            if d.display_name.casefold() == alias.casefold()
            or d.hostname.casefold() == alias.casefold()
        ]
        if len(matches) != 1:
            raise KeyError(f"device alias is missing or ambiguous: {alias}")
        return matches[0]
