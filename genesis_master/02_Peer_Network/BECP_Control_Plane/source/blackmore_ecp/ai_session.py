from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .device_registry import DeviceRegistry


class AISession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    client_type: str
    client_principal: str
    authenticated_subject: str
    created_utc: str
    expires_utc: str
    allowed_device_ids: list[str] = Field(default_factory=list)
    selected_device_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AISessionManager:
    def __init__(self, registry: DeviceRegistry, ttl_minutes: int = 60) -> None:
        self.registry = registry
        self.ttl_minutes = ttl_minutes
        self.sessions: dict[str, AISession] = {}

    def bootstrap(
        self,
        client_type: str,
        client_principal: str,
        authenticated_subject: str,
        allowed_device_ids: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> AISession:
        now = datetime.now(timezone.utc)
        session = AISession(
            client_type=client_type,
            client_principal=client_principal,
            authenticated_subject=authenticated_subject,
            created_utc=now.isoformat(),
            expires_utc=(now + timedelta(minutes=self.ttl_minutes)).isoformat(),
            allowed_device_ids=allowed_device_ids,
            metadata=metadata or {},
        )
        self.sessions[session.session_id] = session
        return session

    def discover_devices(self, session_id: str) -> list[dict[str, Any]]:
        session = self._session(session_id)
        allowed = set(session.allowed_device_ids)
        return [d.model_dump() for d in self.registry.discover(allowed)]
    def select_device(self, session_id: str, device_id: str) -> AISession:
        session = self._session(session_id)
        if device_id not in session.allowed_device_ids:
            raise PermissionError("device not authorized for this AI session")
        device = self.registry.get(device_id)
        if device.revoked:
            raise PermissionError("device is revoked")
        session.selected_device_id = device_id
        return session

    def status(self, session_id: str) -> AISession:
        return self._session(session_id)

    def close(self, session_id: str) -> bool:
        return self.sessions.pop(session_id, None) is not None

    def _session(self, session_id: str) -> AISession:
        try:
            session = self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"unknown AI session: {session_id}") from exc
        if datetime.fromisoformat(session.expires_utc) <= datetime.now(timezone.utc):
            self.sessions.pop(session_id, None)
            raise PermissionError("AI session expired")
        return session
