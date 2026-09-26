from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .device_registry import DeviceRegistry


@dataclass
class AgentConnection:
    device_id: str
    connection_id: str
    socket: Any


class AgentRouter:
    def __init__(self, registry: DeviceRegistry) -> None:
        self.registry = registry
        self.connections: dict[str, AgentConnection] = {}
        self.pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def register(self, device_id: str, socket: Any) -> AgentConnection:
        async with self._lock:
            connection = AgentConnection(device_id, str(uuid4()), socket)
            old = self.connections.get(device_id)
            if old is not None:
                try:
                    await old.socket.close(code=4001)
                except Exception:
                    pass
            self.connections[device_id] = connection
            self.registry.set_connection(device_id, connection.connection_id)
            return connection

    async def unregister(self, device_id: str, connection_id: str) -> None:
        async with self._lock:
            current = self.connections.get(device_id)
            if current and current.connection_id == connection_id:
                self.connections.pop(device_id, None)
                try:
                    self.registry.set_connection(device_id, None)
                except PermissionError:
                    pass

    async def request(self, device_id: str, action: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
        device = self.registry.get(device_id)
        if device.revoked:
            raise PermissionError("device is revoked")
        connection = self.connections.get(device_id)
        if connection is None:
            raise ConnectionError("device is offline")
        request_id = str(uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self.pending[request_id] = future
        message = {"type": "action", "request_id": request_id, "action": action}
        try:
            await connection.socket.send_json(message)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self.pending.pop(request_id, None)

    def resolve(self, request_id: str, result: dict[str, Any]) -> bool:
        future = self.pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(result)
        return True

    async def disconnect(self, device_id: str, code: int = 4003) -> bool:
        async with self._lock:
            connection = self.connections.pop(device_id, None)
            if connection is None:
                return False
            try:
                await connection.socket.close(code=code)
            finally:
                try:
                    self.registry.set_connection(device_id, None)
                except Exception:
                    pass
            return True

    def online(self, device_id: str) -> bool:
        device = self.registry.get(device_id)
        return (
            device_id in self.connections
            and not device.revoked
            and device.remote_access_enabled
        )
