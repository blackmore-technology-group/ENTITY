from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "bind_host": "127.0.0.1",
    "bind_port": 8765,
    "allowed_roots": [],
    "approved_commands": {},
    "audit_path": "./runtime/audit/becp_audit.jsonl",
    "roles": {
        "field_app": 20,
        "sar_operator": 20,
        "qa_engineer": 30,
        "chatgpt_engineer": 30,
        "niki_engineer": 30,
        "chatgpt_privileged_engineer": 40,
        "niki_privileged_engineer": 40,
        "blackmore_admin": 40
    },
    "engineering_terminal": {
        "enabled": False,
        "bound_device": "",
        "default_shell": "powershell.exe",
        "allowed_shells": ["powershell.exe", "pwsh.exe", "cmd.exe"],
        "default_cwd": "<LOCAL_DRIVE>/Blackmore_Technology_Group",
        "max_timeout_seconds": 600,
        "max_output_bytes": 1048576,
        "full_filesystem_scope": True
    },
}


def load_config(path: str | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config["roles"] = dict(DEFAULT_CONFIG["roles"])
    config["engineering_terminal"] = dict(DEFAULT_CONFIG["engineering_terminal"])
    selected = path or os.getenv("BECP_CONFIG")
    if selected:
        loaded = json.loads(Path(selected).read_text(encoding="utf-8"))
        config.update(loaded)
        if "roles" in loaded:
            config["roles"] = loaded["roles"]
        if "engineering_terminal" in loaded:
            terminal = dict(DEFAULT_CONFIG["engineering_terminal"])
            terminal.update(loaded["engineering_terminal"])
            config["engineering_terminal"] = terminal
    return config
