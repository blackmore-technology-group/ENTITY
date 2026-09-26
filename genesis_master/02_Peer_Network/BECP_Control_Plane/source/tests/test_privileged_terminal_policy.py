import json
import platform
from pathlib import Path

from blackmore_ecp.models import ActionRequest
from blackmore_ecp.runtime import BECPCore


def _write_config(tmp_path: Path) -> Path:
    config = {
        "audit_path": str(tmp_path / "audit.jsonl"),
        "engineering_terminal": {
            "enabled": True,
            "bound_device": platform.node(),
            "default_cwd": str(tmp_path),
            "default_shell": "powershell.exe",
            "allowed_shells": ["powershell.exe", "cmd.exe"],
            "max_timeout_seconds": 30,
            "max_output_bytes": 65536,
            "full_filesystem_scope": True
        }
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_normal_engineer_cannot_open_full_terminal(tmp_path: Path) -> None:
    core = BECPCore(str(_write_config(tmp_path)))
    result = core.execute(ActionRequest(
        actor="ordinary-chatgpt",
        role="chatgpt_engineer",
        capability="engineering.terminal.start",
        target="local",
        approval_id="TEST",
    ))
    assert result.ok is False
    assert "risk ceiling" in (result.error or "")


def test_privileged_engineer_requires_approval(tmp_path: Path) -> None:
    core = BECPCore(str(_write_config(tmp_path)))
    result = core.execute(ActionRequest(
        actor="privileged-chatgpt",
        role="chatgpt_privileged_engineer",
        capability="engineering.terminal.start",
        target="local",
    ))
    assert result.ok is False
    assert "approval required" in (result.error or "")
