from __future__ import annotations

import json
from pathlib import Path

from blackmore_ecp import __version__

PRODUCTS = {
    "niki": {
        "root": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\NIKI\Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"),
        "product_id": "NIKI",
        "client_type": "niki",
        "expected_roles": ["niki_engineer", "niki_privileged_engineer"],
        "privileged_terminal": True,
    },
    "hikear": {
        "root": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HIKE_AR\HikeAR_v0.1.0"),
        "product_id": "HIKEAR",
        "client_type": "hikear",
        "expected_roles": ["field_app"],
        "privileged_terminal": False,
    },
    "huntar": {
        "root": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0"),
        "product_id": "HUNTAR",
        "client_type": "huntar",
        "expected_roles": ["field_app"],
        "privileged_terminal": False,
    },
    "searchar": {
        "root": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\SAR\SearchAR_v0.12.0"),
        "product_id": "SEARCHAR",
        "client_type": "searchar",
        "expected_roles": ["sar_operator"],
        "privileged_terminal": False,
    },
}

CLIENT = r'''from __future__ import annotations

from typing import Any

import httpx


class BECPClient:
    """Authenticated HTTPS client for the Blackmore Engineering Control Plane."""

    def __init__(self, base_url: str, bearer_token: str, ca_cert: str, timeout_seconds: float = 60.0) -> None:
        if not bearer_token:
            raise ValueError("BECP bearer token is required")
        self.client = httpx.Client(base_url=base_url.rstrip("/"), headers={"Authorization": f"Bearer {bearer_token}"}, verify=ca_cert, timeout=timeout_seconds)
        self.session_id: str | None = None
        self.selected_device_id: str | None = None
'''
CLIENT += r'''
    def close_client(self) -> None:
        self.client.close()

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        return response.json()

    def bootstrap(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._json(self.client.post("/v1/session/bootstrap", json={"metadata": metadata or {}}))
        self.session_id = str(data["session_id"])
        return data

    def status(self) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("BECP session has not been bootstrapped")
        return self._json(self.client.get(f"/v1/session/{self.session_id}"))

    def devices(self) -> list[dict[str, Any]]:
        if not self.session_id:
            raise RuntimeError("BECP session has not been bootstrapped")
        data = self._json(self.client.get(f"/v1/session/{self.session_id}/devices"))
        return list(data.get("devices", []))

    def select_device(self, device_id: str) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("BECP session has not been bootstrapped")
        data = self._json(self.client.post(f"/v1/session/{self.session_id}/select", json={"device_id": device_id}))
        self.selected_device_id = device_id
        return data

    def action(self, capability: str, params: dict[str, Any] | None = None, approval_token: str | None = None, timeout_seconds: float = 30.0) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("BECP session has not been bootstrapped")
        return self._json(self.client.post("/v1/action", json={"session_id": self.session_id, "capability": capability, "params": params or {}, "approval_token": approval_token, "timeout_seconds": timeout_seconds}))
'''
CLIENT += r'''
    def issue_approval(self, capability: str, ttl_seconds: int = 300) -> str:
        if not self.session_id or not self.selected_device_id:
            raise RuntimeError("BECP session/device selection is incomplete")
        data = self._json(self.client.post("/v1/approval", json={"session_id": self.session_id, "capability": capability, "target_device_id": self.selected_device_id, "ttl_seconds": ttl_seconds}))
        return str(data["approval_token"])

    def privileged_action(self, capability: str, params: dict[str, Any] | None = None, timeout_seconds: float = 30.0) -> dict[str, Any]:
        approval = self.issue_approval(capability)
        return self.action(capability, params=params, approval_token=approval, timeout_seconds=timeout_seconds)

    def close_session(self) -> bool:
        if not self.session_id:
            return False
        data = self._json(self.client.delete(f"/v1/session/{self.session_id}"))
        self.session_id = None
        self.selected_device_id = None
        return bool(data.get("closed"))

    def __enter__(self) -> "BECPClient":
        return self

    def __exit__(self, *_: object) -> None:
        try:
            self.close_session()
        finally:
            self.close_client()
'''

BASE_MAPPING = {
    "health": "system.health",
    "file_hash": "file.hash",
    "read_text": "file.read_text",
    "diagnostic": "diagnostic.run_approved",
}

NIKI_EXTRA = {
    "approved_change": "change.run_approved",
    "terminal_start": "engineering.terminal.start",
    "terminal_execute": "engineering.terminal.execute",
    "terminal_cwd": "engineering.terminal.cwd",
    "terminal_close": "engineering.terminal.close",
    "terminal_drives": "engineering.terminal.drives",
}
ORCHESTRATOR = r'''from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .capability_mapping import CAPABILITIES, PRIVILEGED_TERMINAL_ALLOWED
from .client import BECPClient


class BECPOrchestrator:
    """Product-facing BECP orchestration wrapper. Server policy remains authoritative."""

    def __init__(self, config_path: str | None = None, bearer_token: str | None = None) -> None:
        path = Path(config_path) if config_path else Path(__file__).with_name("configuration.json")
        self.config = json.loads(path.read_text(encoding="utf-8"))
        token_env = str(self.config.get("bearer_token_env", "BECP_CLIENT_TOKEN"))
        token = bearer_token or os.getenv(token_env, "")
        base_url = os.getenv("BECP_BASE_URL", str(self.config["gateway_url"]))
        ca_cert = os.getenv("BECP_CA_CERT", str(self.config["ca_cert"]))
        self.client = BECPClient(base_url, token, ca_cert, float(self.config.get("timeout_seconds", 60)))

    def connect(self) -> dict[str, Any]:
        return self.client.bootstrap({"product_id": self.config["product_id"], "integration_version": self.config["integration_version"]})

    def devices(self) -> list[dict[str, Any]]:
        return self.client.devices()

    def select_device(self, device_id: str) -> dict[str, Any]:
        return self.client.select_device(device_id)

    def select_device_by_alias(self, alias: str) -> dict[str, Any]:
        matches = [d for d in self.devices() if alias.casefold() in {str(d.get("hostname", "")).casefold(), str(d.get("display_name", "")).casefold()}]
        if len(matches) != 1:
            raise KeyError(f"BECP device alias missing or ambiguous: {alias}")
        return self.select_device(str(matches[0]["device_id"]))
'''
ORCHESTRATOR += r'''
    def run(self, operation: str, params: dict[str, Any] | None = None, timeout_seconds: float = 30.0) -> dict[str, Any]:
        try:
            capability = CAPABILITIES[operation]
        except KeyError as exc:
            raise KeyError(f"unsupported BECP operation for this product: {operation}") from exc
        if capability.startswith("engineering.terminal.") and not PRIVILEGED_TERMINAL_ALLOWED:
            raise PermissionError("privileged engineering terminal is not enabled for this product integration")
        privileged = capability.startswith("engineering.terminal.") or capability == "change.run_approved"
        if privileged:
            return self.client.privileged_action(capability, params=params, timeout_seconds=timeout_seconds)
        return self.client.action(capability, params=params, timeout_seconds=timeout_seconds)

    def health(self) -> dict[str, Any]:
        return self.run("health")

    def hash_file(self, path: str) -> dict[str, Any]:
        return self.run("file_hash", {"path": path})

    def read_text(self, path: str, max_bytes: int = 65536) -> dict[str, Any]:
        return self.run("read_text", {"path": path, "max_bytes": max_bytes})

    def diagnostic(self, command_id: str, timeout_seconds: float = 120.0) -> dict[str, Any]:
        return self.run("diagnostic", {"command_id": command_id, "timeout_seconds": timeout_seconds}, timeout_seconds + 5)

    def start_terminal(self, shell: str = "powershell.exe") -> dict[str, Any]:
        return self.run("terminal_start", {"shell": shell})

    def terminal_execute(self, terminal_session_id: str, command: str, timeout_seconds: float = 60.0) -> dict[str, Any]:
        return self.run("terminal_execute", {"session_id": terminal_session_id, "command": command, "timeout_seconds": timeout_seconds}, timeout_seconds + 5)

    def terminal_close(self, terminal_session_id: str) -> dict[str, Any]:
        return self.run("terminal_close", {"session_id": terminal_session_id})

    def close(self) -> None:
        try:
            self.client.close_session()
        finally:
            self.client.close_client()
'''

INIT = '''from .client import BECPClient\nfrom .orchestrator import BECPOrchestrator\n\n__all__ = ["BECPClient", "BECPOrchestrator"]\n'''
MAPPING_TEMPLATE = '''from __future__ import annotations\n\nCAPABILITIES = {mapping}\nPRIVILEGED_TERMINAL_ALLOWED = {privileged}\n\n\ndef capability_for(operation: str) -> str:\n    try:\n        return CAPABILITIES[operation]\n    except KeyError as exc:\n        raise KeyError(f"Unsupported BECP operation: {{operation}}") from exc\n'''

TEST_TEMPLATE = r'''from __future__ import annotations

import json
from pathlib import Path

from integrations.becp.capability_mapping import CAPABILITIES, PRIVILEGED_TERMINAL_ALLOWED


def test_becp_integration_configuration() -> None:
    config = json.loads((Path(__file__).parents[1] / "configuration.json").read_text(encoding="utf-8"))
    assert config["integration_version"] == "__BECP_VERSION__"
    assert config["gateway_url"].startswith("https://")
    assert config["bearer_token_env"] == "BECP_CLIENT_TOKEN"
    assert CAPABILITIES["health"] == "system.health"
    assert config["privileged_terminal_allowed"] is PRIVILEGED_TERMINAL_ALLOWED
    if not PRIVILEGED_TERMINAL_ALLOWED:
        assert not any(value.startswith("engineering.terminal.") for value in CAPABILITIES.values())
'''

README_TEMPLATE = '''# BECP Integration\n\nThis package connects {product_id} to the independently deployed Blackmore Engineering Control Plane (BECP) v{version}.\n\nBECP itself remains in `<LOCAL_DRIVE>/Blackmore_Technology_Group\\Software Development\\BECP`. This directory contains only the product client/orchestration contract. Credentials are never stored here; use `BECP_CLIENT_TOKEN`, `BECP_BASE_URL`, and `BECP_CA_CERT` environment variables. Server-side BECP policy, device identity, approval, and role enforcement remain authoritative.\n'''
def install_product(name: str, spec: dict) -> dict:
    root: Path = spec["root"]
    target = root / "integrations" / "becp"
    tests = target / "tests"
    target.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)

    mapping = dict(BASE_MAPPING)
    if spec["privileged_terminal"]:
        mapping.update(NIKI_EXTRA)

    config = {
        "schema_version": 1,
        "integration_version": __version__,
        "becp_product_id": "BTG-PLAT-010",
        "product_id": spec["product_id"],
        "client_type": spec["client_type"],
        "gateway_url": "https://127.0.0.1:8765",
        "ca_cert": r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP\runtime\pki\ca\ca.cert.pem",
        "bearer_token_env": "BECP_CLIENT_TOKEN",
        "expected_roles": spec["expected_roles"],
        "privileged_terminal_allowed": spec["privileged_terminal"],
        "timeout_seconds": 60,
        "server_policy_authoritative": True,
    }
    (target / "client.py").write_text(CLIENT, encoding="utf-8")
    (target / "orchestrator.py").write_text(ORCHESTRATOR, encoding="utf-8")
    (target / "capability_mapping.py").write_text(
        MAPPING_TEMPLATE.format(mapping=repr(mapping), privileged=repr(spec["privileged_terminal"])),
        encoding="utf-8",
    )
    (target / "configuration.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (target / "__init__.py").write_text(INIT, encoding="utf-8")
    (target / "README.md").write_text(README_TEMPLATE.format(product_id=spec["product_id"], version=__version__), encoding="utf-8")
    (tests / "test_becp_integration.py").write_text(TEST_TEMPLATE.replace("__BECP_VERSION__", __version__), encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    integrations = root / "integrations"
    init = integrations / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")
    return {"product": name, "root": str(root), "integration": str(target), "files": 8}


def main() -> int:
    results = []
    for name, spec in PRODUCTS.items():
        if not spec["root"].exists():
            raise FileNotFoundError(spec["root"])
        results.append(install_product(name, spec))
    print(json.dumps({"status": "INSTALLED", "integrations": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
