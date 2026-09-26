from __future__ import annotations

from typing import Any

import httpx


class NIKIBECPSession:
    """Blackmore-native NIKI client for the BECP HTTPS gateway."""

    def __init__(
        self,
        base_url: str,
        bearer_token: str,
        ca_cert: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {bearer_token}"},
            verify=ca_cert,
            timeout=timeout_seconds,
        )
        self.session_id: str | None = None
        self.selected_device_id: str | None = None

    def close_client(self) -> None:
        self.client.close()

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        return response.json()

    def bootstrap(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._json(self.client.post("/v1/session/bootstrap", json={"metadata": metadata or {}}))
        self.session_id = str(data["session_id"])
        return data

    def status(self) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("NIKI BECP session has not been bootstrapped")
        return self._json(self.client.get(f"/v1/session/{self.session_id}"))

    def devices(self) -> list[dict[str, Any]]:
        if not self.session_id:
            raise RuntimeError("NIKI BECP session has not been bootstrapped")
        data = self._json(self.client.get(f"/v1/session/{self.session_id}/devices"))
        return list(data.get("devices", []))

    def select_device(self, device_id: str) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("NIKI BECP session has not been bootstrapped")
        data = self._json(self.client.post(
            f"/v1/session/{self.session_id}/select",
            json={"device_id": device_id},
        ))
        self.selected_device_id = device_id
        return data

    def issue_approval(self, capability: str, ttl_seconds: int = 300) -> str:
        if not self.session_id or not self.selected_device_id:
            raise RuntimeError("NIKI BECP session/device selection is incomplete")
        data = self._json(self.client.post("/v1/approval", json={
            "session_id": self.session_id,
            "capability": capability,
            "target_device_id": self.selected_device_id,
            "ttl_seconds": ttl_seconds,
        }))
        return str(data["approval_token"])

    def action(
        self,
        capability: str,
        params: dict[str, Any] | None = None,
        approval_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("NIKI BECP session has not been bootstrapped")
        return self._json(self.client.post("/v1/action", json={
            "session_id": self.session_id,
            "capability": capability,
            "params": params or {},
            "approval_token": approval_token,
            "timeout_seconds": timeout_seconds,
        }))

    def privileged_action(
        self,
        capability: str,
        params: dict[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        approval = self.issue_approval(capability)
        return self.action(capability, params=params, approval_token=approval, timeout_seconds=timeout_seconds)

    def start_terminal(self, shell: str = "powershell.exe") -> dict[str, Any]:
        return self.privileged_action("engineering.terminal.start", {"shell": shell})

    def terminal_execute(self, terminal_session_id: str, command: str, timeout_seconds: float = 60.0) -> dict[str, Any]:
        return self.privileged_action(
            "engineering.terminal.execute",
            {"session_id": terminal_session_id, "command": command, "timeout_seconds": timeout_seconds},
            timeout_seconds=timeout_seconds + 5,
        )

    def terminal_close(self, terminal_session_id: str) -> dict[str, Any]:
        return self.privileged_action("engineering.terminal.close", {"session_id": terminal_session_id})

    def close_session(self) -> bool:
        if not self.session_id:
            return False
        data = self._json(self.client.delete(f"/v1/session/{self.session_id}"))
        self.session_id = None
        self.selected_device_id = None
        return bool(data.get("closed"))
