from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from blackmore_ecp import __version__
from blackmore_ecp.ai_session import AISessionManager
from blackmore_ecp.audit import AuditLog
from blackmore_ecp.device_registry import DeviceRegistry
from blackmore_ecp.models import ActionRequest
from blackmore_ecp.pki import certificate_fingerprint, verify_device_hello
from blackmore_ecp.policy import DEFAULT_ROLE_LIMITS
from blackmore_ecp.router import AgentRouter
from blackmore_ecp.security import ApprovalService, SecurityError, SignedTokenService


class BootstrapRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class SelectDeviceRequest(BaseModel):
    device_id: str


class ApprovalRequest(BaseModel):
    session_id: str
    capability: str
    target_device_id: str
    ttl_seconds: int = 300


class ActionBody(BaseModel):
    session_id: str
    capability: str
    params: dict[str, Any] = Field(default_factory=dict)
    approval_token: str | None = None
    timeout_seconds: float = 30.0


class RemoteAccessRequest(BaseModel):
    enabled: bool


class GatewayState:
    def __init__(
        self,
        registry_path: str,
        audit_path: str,
        signing_secret: str,
        approval_signing_secret: str,
        ai_session_ttl_minutes: int = 60,
    ) -> None:
        self.registry = DeviceRegistry(registry_path)
        self.router = AgentRouter(self.registry)
        self.audit = AuditLog(audit_path)
        self.signer = SignedTokenService(signing_secret)
        self.approval_signer = SignedTokenService(approval_signing_secret, issuer="becp-approval-authority")
        self.approvals = ApprovalService.create(self.approval_signer)
        self.sessions = AISessionManager(self.registry, ttl_minutes=ai_session_ttl_minutes)
        self.terminal_owners: dict[tuple[str, str], str] = {}
        self.used_nonces: dict[tuple[str, str], int] = {}

    def verify_client_token(self, token: str) -> dict[str, Any]:
        return self.signer.verify(token, "becp-client")

    def bootstrap(self, claims: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        allowed = list(claims.get("devices", []))
        if allowed == ["*"] or "*" in allowed:
            allowed = [d.device_id for d in self.registry.discover()]
        session = self.sessions.bootstrap(
            client_type=str(claims.get("client_type", "unknown")),
            client_principal=str(claims.get("sub", "unknown")),
            authenticated_subject=str(claims.get("subject", claims.get("sub", "unknown"))),
            allowed_device_ids=allowed,
            metadata={
                **metadata,
                "roles": list(claims.get("roles", [])),
                "capabilities": list(claims.get("capabilities", ["*"])),
                "client_jti": claims.get("jti"),
            },
        )
        return session.model_dump()

    def session_for_client(self, session_id: str, claims: dict[str, Any]):
        session = self.sessions.status(session_id)
        if session.client_principal != str(claims.get("sub", "")):
            raise SecurityError("AI session principal mismatch")
        return session

    def _selected_role(self, session) -> str:
        roles = [r for r in session.metadata.get("roles", []) if r in DEFAULT_ROLE_LIMITS]
        if not roles:
            raise SecurityError("no authorized BECP role in AI session")
        return max(roles, key=lambda r: DEFAULT_ROLE_LIMITS[r])

    def _capability_allowed(self, session, capability: str) -> bool:
        allowed = list(session.metadata.get("capabilities", ["*"]))
        return "*" in allowed or capability in allowed

    @staticmethod
    def requires_approval(capability: str) -> bool:
        return (
            capability.startswith("engineering.terminal.")
            or capability.startswith("change.")
            or capability.startswith("deployment.")
            or capability.startswith("rollback.")
            or capability.startswith("update.install")
            or capability.startswith("model.replace")
        )

    def issue_approval(
        self,
        claims: dict[str, Any],
        session_id: str,
        capability: str,
        target_device_id: str,
        ttl_seconds: int,
    ) -> str:
        roles = set(claims.get("roles", []))
        if not roles.intersection({"blackmore_admin", "security_admin", "approval_authority"}):
            raise SecurityError("client is not an approval authority")
        self.session_for_client(session_id, claims)
        return self.approvals.issue(
            subject=session_id,
            capability=capability,
            target=target_device_id,
            ttl_seconds=max(30, min(int(ttl_seconds), 900)),
        )

    def _verify_terminal_ownership(self, ai_session_id: str, device_id: str, capability: str, params: dict[str, Any]) -> None:
        if capability in {
            "engineering.terminal.execute",
            "engineering.terminal.cwd",
            "engineering.terminal.close",
        }:
            terminal_session_id = str(params.get("session_id", ""))
            owner = self.terminal_owners.get((device_id, terminal_session_id))
            if owner != ai_session_id:
                raise SecurityError("terminal session is not owned by this AI session")

    async def route_action(
        self,
        claims: dict[str, Any],
        body: ActionBody,
    ) -> dict[str, Any]:
        session = self.session_for_client(body.session_id, claims)
        if not session.selected_device_id:
            raise SecurityError("no BECP device selected")
        device_id = session.selected_device_id
        device = self.registry.get(device_id)
        if device.revoked or not device.remote_access_enabled:
            raise SecurityError("selected device is unavailable for remote access")
        if not self._capability_allowed(session, body.capability):
            raise SecurityError("capability not authorized for this AI session")
        self._verify_terminal_ownership(body.session_id, device_id, body.capability, body.params)

        approval_id = None
        if self.requires_approval(body.capability):
            if not body.approval_token:
                raise SecurityError("scoped approval token required")
            approval = self.approvals.consume(
                body.approval_token,
                subject=body.session_id,
                capability=body.capability,
                target=device_id,
            )
            approval_id = str(approval["jti"])
        role = self._selected_role(session)
        request = ActionRequest(
            actor=session.authenticated_subject,
            role=role,
            capability=body.capability,
            target=device_id,
            params=dict(body.params),
            approval_id=approval_id,
        )
        result = await self.router.request(
            device_id,
            request.model_dump(),
            timeout=max(1.0, min(float(body.timeout_seconds), 600.0)),
        )
        if body.capability == "engineering.terminal.start" and result.get("ok"):
            terminal_id = str(result.get("data", {}).get("session_id", ""))
            if terminal_id:
                self.terminal_owners[(device_id, terminal_id)] = body.session_id
        elif body.capability == "engineering.terminal.close" and result.get("ok"):
            terminal_id = str(body.params.get("session_id", ""))
            self.terminal_owners.pop((device_id, terminal_id), None)
        self.audit.append({
            "event": "gateway.remote_action",
            "ai_session_id": body.session_id,
            "device_id": device_id,
            "capability": body.capability,
            "ok": bool(result.get("ok")),
        })
        return result

    async def close_ai_session(self, claims: dict[str, Any], session_id: str) -> bool:
        session = self.session_for_client(session_id, claims)
        owned = [
            (device_id, terminal_id)
            for (device_id, terminal_id), owner in self.terminal_owners.items()
            if owner == session_id
        ]
        for device_id, terminal_id in owned:
            try:
                request = ActionRequest(
                    actor=session.authenticated_subject,
                    role="blackmore_admin",
                    capability="engineering.terminal.close",
                    target=device_id,
                    params={"session_id": terminal_id},
                    approval_id="internal-session-cleanup",
                )
                await self.router.request(device_id, request.model_dump(), timeout=10.0)
            except Exception:
                pass
            self.terminal_owners.pop((device_id, terminal_id), None)
        return self.sessions.close(session_id)

    def accept_nonce(self, device_id: str, nonce: str, timestamp: int) -> None:
        now = int(time.time())
        self.used_nonces = {
            key: ts for key, ts in self.used_nonces.items()
            if now - ts <= 300
        }
        key = (device_id, nonce)
        if key in self.used_nonces:
            raise SecurityError("replayed device authentication nonce")
        self.used_nonces[key] = int(timestamp)

def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    return authorization.split(" ", 1)[1].strip()


def _claims_dependency(state: GatewayState):
    async def dependency(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        try:
            return state.verify_client_token(_bearer_token(authorization))
        except (SecurityError, ValueError) as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    return dependency


def _to_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (SecurityError, PermissionError)):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConnectionError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")


def create_client_app(state: GatewayState) -> FastAPI:
    app = FastAPI(title="Blackmore Engineering Control Plane", version=__version__)
    claims_dep = _claims_dependency(state)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "BECP client gateway",
            "registered_devices": len(state.registry.devices),
            "online_devices": sum(1 for d in state.registry.devices if state.router.online(d)),
        }

    @app.post("/v1/session/bootstrap")
    async def bootstrap(body: BootstrapRequest, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            return state.bootstrap(claims, body.metadata)
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.get("/v1/session/{session_id}")
    async def session_status(session_id: str, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            return state.session_for_client(session_id, claims).model_dump()
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.delete("/v1/session/{session_id}")
    async def session_close(session_id: str, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            return {"closed": await state.close_ai_session(claims, session_id)}
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.get("/v1/session/{session_id}/devices")
    async def list_devices(session_id: str, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            state.session_for_client(session_id, claims)
            return {"devices": state.sessions.discover_devices(session_id)}
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.post("/v1/session/{session_id}/select")
    async def select_device(session_id: str, body: SelectDeviceRequest, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            state.session_for_client(session_id, claims)
            return state.sessions.select_device(session_id, body.device_id).model_dump()
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.post("/v1/approval")
    async def issue_approval(body: ApprovalRequest, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            token = state.issue_approval(
                claims,
                body.session_id,
                body.capability,
                body.target_device_id,
                body.ttl_seconds,
            )
            return {"approval_token": token, "expires_in_seconds": body.ttl_seconds}
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.post("/v1/action")
    async def action(body: ActionBody, claims: dict[str, Any] = Depends(claims_dep)):
        try:
            return await state.route_action(claims, body)
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.post("/v1/admin/device/{device_id}/remote-access")
    async def remote_access(device_id: str, body: RemoteAccessRequest, claims: dict[str, Any] = Depends(claims_dep)):
        roles = set(claims.get("roles", []))
        if not roles.intersection({"blackmore_admin", "security_admin"}):
            raise HTTPException(status_code=403, detail="administrator role required")
        try:
            device = state.registry.set_remote_access(device_id, body.enabled)
            if not body.enabled:
                await state.router.disconnect(device_id, code=4004)
            return device.model_dump()
        except Exception as exc:
            raise _to_http_error(exc) from exc

    @app.post("/v1/admin/device/{device_id}/revoke")
    async def revoke(device_id: str, claims: dict[str, Any] = Depends(claims_dep)):
        roles = set(claims.get("roles", []))
        if not roles.intersection({"blackmore_admin", "security_admin"}):
            raise HTTPException(status_code=403, detail="administrator role required")
        try:
            device = state.registry.revoke(device_id)
            await state.router.disconnect(device_id, code=4005)
            return device.model_dump()
        except Exception as exc:
            raise _to_http_error(exc) from exc

    return app

def create_agent_app(state: GatewayState) -> FastAPI:
    app = FastAPI(title="BECP Agent Gateway", version=__version__)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "BECP agent gateway",
            "online_devices": [
                device_id for device_id in state.registry.devices
                if state.router.online(device_id)
            ],
        }

    @app.websocket("/agent")
    async def agent_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        connection = None
        device_id = None
        try:
            hello = await asyncio.wait_for(websocket.receive_json(), timeout=15.0)
            if hello.get("type") != "hello":
                raise SecurityError("device hello required")
            device_id = str(hello.get("device_id", ""))
            device = state.registry.get(device_id)
            if device.revoked or not device.remote_access_enabled:
                raise SecurityError("device remote access is disabled")
            if not device.certificate_path:
                raise SecurityError("device certificate is not registered")
            if device.certificate_fingerprint:
                actual_fp = certificate_fingerprint(device.certificate_path)
                if actual_fp != device.certificate_fingerprint:
                    raise SecurityError("registered device certificate fingerprint mismatch")
            timestamp = int(hello.get("timestamp", 0))
            nonce = str(hello.get("nonce", ""))
            state.accept_nonce(device_id, nonce, timestamp)
            verify_device_hello(
                certificate_path=device.certificate_path,
                device_id=device_id,
                timestamp=timestamp,
                nonce=nonce,
                signature_b64=str(hello.get("signature", "")),
            )
            device.agent_version = str(hello.get("agent_version", device.agent_version or "unknown"))
            state.registry.register(device)
            connection = await state.router.register(device_id, websocket)
            await websocket.send_json({
                "type": "hello_ack",
                "ok": True,
                "device_id": device_id,
                "connection_id": connection.connection_id,
            })
            state.audit.append({
                "event": "gateway.agent_connected",
                "device_id": device_id,
                "connection_id": connection.connection_id,
            })
            while True:
                message = await websocket.receive_json()
                kind = message.get("type")
                if kind == "heartbeat":
                    state.registry.heartbeat(device_id, online=True)
                    await websocket.send_json({"type": "heartbeat_ack", "timestamp": int(time.time())})
                elif kind == "action_result":
                    state.router.resolve(
                        str(message.get("request_id", "")),
                        dict(message.get("result", {})),
                    )
                else:
                    await websocket.send_json({"type": "error", "error": "unsupported agent message"})
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as exc:
            try:
                await websocket.send_json({"type": "hello_ack", "ok": False, "error": str(exc)})
            except Exception:
                pass
            try:
                await websocket.close(code=4403)
            except Exception:
                pass
        finally:
            if connection is not None and device_id is not None:
                await state.router.unregister(device_id, connection.connection_id)
                state.audit.append({
                    "event": "gateway.agent_disconnected",
                    "device_id": device_id,
                    "connection_id": connection.connection_id,
                })

    return app
