from pathlib import Path

from blackmore_ecp.ai_session import AISessionManager
from blackmore_ecp.device_registry import DeviceRegistry, EnrolledDevice


def test_device_discovery_and_session_binding(tmp_path: Path) -> None:
    registry = DeviceRegistry(str(tmp_path / "devices.json"))
    first = registry.register(
        EnrolledDevice(
            hostname="ENG-01",
            display_name="Engineer One Laptop",
            platform="Windows",
            owner_principal="BTG\\engineer1",
            terminal_enabled=True,
            online=True,
        )
    )
    second = registry.register(
        EnrolledDevice(
            hostname="ENG-02",
            display_name="Engineer Two Laptop",
            platform="Windows",
            owner_principal="BTG\\engineer2",
            terminal_enabled=True,
            online=True,
        )
    )
    sessions = AISessionManager(registry, ttl_minutes=15)
    session = sessions.bootstrap(
        client_type="chatgpt",
        client_principal="workspace-user-123",
        authenticated_subject="engineer1@blackmore",
        allowed_device_ids=[first.device_id],
    )

    visible = sessions.discover_devices(session.session_id)
    assert [d["device_id"] for d in visible] == [first.device_id]
    assert second.device_id not in {d["device_id"] for d in visible}

    selected = sessions.select_device(session.session_id, first.device_id)
    assert selected.selected_device_id == first.device_id

    try:
        sessions.select_device(session.session_id, second.device_id)
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized device selection was allowed")
