import platform
from pathlib import Path

from blackmore_ecp.audit import AuditLog
from blackmore_ecp.engineering_terminal import EngineeringTerminal


def _config(tmp_path: Path) -> dict:
    return {
        "enabled": True,
        "bound_device": platform.node(),
        "default_shell": "powershell.exe",
        "allowed_shells": ["powershell.exe", "cmd.exe"],
        "default_cwd": str(tmp_path),
        "max_timeout_seconds": 30,
        "max_output_bytes": 65536,
        "full_filesystem_scope": True,
    }


def test_terminal_session_and_execution(tmp_path: Path) -> None:
    audit = AuditLog(str(tmp_path / "audit.jsonl"))
    terminal = EngineeringTerminal(_config(tmp_path), audit)
    session = terminal.start_session("pytest")
    result = terminal.execute(session["session_id"], "Write-Output 'BECP_TERMINAL_OK'")
    assert result["returncode"] == 0
    assert "BECP_TERMINAL_OK" in result["stdout"]
    assert terminal.list_local_drives()
    changed = terminal.set_cwd(session["session_id"], str(tmp_path))
    assert Path(changed["cwd"]).resolve() == tmp_path.resolve()
    closed = terminal.close_session(session["session_id"])
    assert closed["closed"] is True
    audit_text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "engineering_terminal.command_completed" in audit_text


def test_wrong_device_is_rejected(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config["bound_device"] = "NOT_THIS_DEVICE"
    audit = AuditLog(str(tmp_path / "audit.jsonl"))
    try:
        EngineeringTerminal(config, audit)
    except PermissionError:
        return
    raise AssertionError("terminal must reject a non-bound device")
