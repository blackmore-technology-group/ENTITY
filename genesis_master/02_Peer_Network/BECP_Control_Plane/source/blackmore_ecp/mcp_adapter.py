from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from api.gateway import ActionBody, GatewayState
from blackmore_ecp import __version__


class BECPSignedTokenVerifier(TokenVerifier):
    def __init__(self, state: GatewayState) -> None:
        self.state = state

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = self.state.verify_client_token(token)
        except Exception:
            return None
        return AccessToken(
            token=token,
            client_id=str(claims.get("sub", "unknown")),
            subject=str(claims.get("subject", claims.get("sub", "unknown"))),
            scopes=list(claims.get("capabilities", ["*"])),
            expires_at=int(claims.get("exp", 0)),
            claims=claims,
        )

def _claims() -> dict[str, Any]:
    token = get_access_token()
    if token is None or not token.claims:
        raise PermissionError("authenticated BECP client token required")
    return dict(token.claims)


def create_mcp_server(state: GatewayState, resource_url: str) -> MCPServer:
    auth = AuthSettings(
        issuer_url=AnyHttpUrl("https://becp.blackmore.local"),
        resource_server_url=AnyHttpUrl(resource_url),
        required_scopes=None,
        validate_token_resource=False,
    )
    server = MCPServer(
        name="Blackmore Engineering Control Plane",
        description="Authorized Blackmore engineering device discovery, diagnostics, and workstation control.",
        version=__version__,
        auth=auth,
        token_verifier=BECPSignedTokenVerifier(state),
    )

    @server.tool(name="becp_session_bootstrap")
    async def session_bootstrap(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return state.bootstrap(_claims(), metadata or {})

    @server.tool(name="becp_session_status")
    async def session_status(session_id: str) -> dict[str, Any]:
        return state.session_for_client(session_id, _claims()).model_dump()

    @server.tool(name="becp_devices_list")
    async def devices_list(session_id: str) -> dict[str, Any]:
        state.session_for_client(session_id, _claims())
        return {"devices": state.sessions.discover_devices(session_id)}

    @server.tool(name="becp_device_describe")
    async def device_describe(session_id: str, device_id: str) -> dict[str, Any]:
        session = state.session_for_client(session_id, _claims())
        if device_id not in session.allowed_device_ids:
            raise PermissionError("device not authorized for this AI session")
        device = state.registry.get(device_id)
        return {
            **device.model_dump(),
            "router_online": state.router.online(device_id),
        }

    @server.tool(name="becp_device_select")
    async def device_select(session_id: str, device_id: str) -> dict[str, Any]:
        state.session_for_client(session_id, _claims())
        return state.sessions.select_device(session_id, device_id).model_dump()

    @server.tool(name="becp_approval_issue")
    async def approval_issue(
        session_id: str,
        capability: str,
        target_device_id: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        token = state.issue_approval(_claims(), session_id, capability, target_device_id, ttl_seconds)
        return {"approval_token": token, "expires_in_seconds": ttl_seconds}

    @server.tool(name="becp_action")
    async def action(
        session_id: str,
        capability: str,
        params: dict[str, Any] | None = None,
        approval_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        body = ActionBody(
            session_id=session_id,
            capability=capability,
            params=params or {},
            approval_token=approval_token,
            timeout_seconds=timeout_seconds,
        )
        return await state.route_action(_claims(), body)

    @server.tool(name="becp_session_close")
    async def session_close(session_id: str) -> dict[str, Any]:
        return {"closed": await state.close_ai_session(_claims(), session_id)}

    return server
