from __future__ import annotations

import json
from pathlib import Path

from blackmore_ecp.desktop_commander_bridge import BridgeConfig, requires_approval


def test_requires_approval_for_privileged_capabilities() -> None:
    assert requires_approval("engineering.terminal.execute")
    assert requires_approval("change.run_approved")
    assert not requires_approval("system.health")


def test_bridge_config_loads_scoped_identity(tmp_path: Path) -> None:
    path = tmp_path / "bridge.json"
    payload = {
        "gateway_url": "https://127.0.0.1:8765",
        "ca_cert": "ca.pem",
        "client_signing_key_path": "client.key",
        "principal": "rdc-bridge",
        "subject": "Remote Desktop Commander via BECP",
        "client_type": "desktop_commander_bridge",
        "roles": ["blackmore_admin"],
        "devices": ["device-1"],
        "capabilities": ["system.health"],
        "default_device": "BTG",
        "token_ttl_seconds": 300,
        "request_timeout_seconds": 60.0,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    config = BridgeConfig.load(path)
    assert config.client_type == "desktop_commander_bridge"
    assert config.devices == ["device-1"]
    assert config.capabilities == ["system.health"]


def test_bridge_config_does_not_require_rdc_direct_mode_changes(tmp_path: Path) -> None:
    # Bridge configuration is additive; it does not configure or disable Desktop Commander.
    path = tmp_path / "bridge.json"
    path.write_text(json.dumps({
        "gateway_url": "https://127.0.0.1:8765",
        "ca_cert": "ca.pem",
        "client_signing_key_path": "client.key",
        "principal": "rdc-bridge",
        "subject": "RDC via BECP",
        "client_type": "desktop_commander_bridge",
        "roles": ["blackmore_admin"],
        "devices": ["device-1"],
        "capabilities": ["system.health"],
        "default_device": "BTG",
    }), encoding="utf-8")
    config = BridgeConfig.load(path)
    assert config.default_device == "BTG"
    assert not hasattr(config, "disable_desktop_commander")
