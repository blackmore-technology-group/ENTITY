from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from .engineering_terminal import EngineeringTerminal
from .models import CapabilitySpec, RiskLevel

Handler = Callable[[dict[str, Any]], dict[str, Any]]


class CapabilityRegistry:
    def __init__(
        self,
        approved_commands: dict[str, list[str]],
        engineering_terminal: EngineeringTerminal | None = None,
    ) -> None:
        self.approved_commands = approved_commands
        self.engineering_terminal = engineering_terminal
        self.handlers: dict[str, Handler] = {}
        self.specs: dict[str, CapabilitySpec] = {}
        self._register_defaults()

    def register(self, spec: CapabilitySpec, handler: Handler) -> None:
        self.specs[spec.name] = spec
        self.handlers[spec.name] = handler

    def execute(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if capability not in self.handlers:
            raise KeyError(f"unknown capability: {capability}")
        return self.handlers[capability](params)

    def list_specs(self) -> list[CapabilitySpec]:
        return list(self.specs.values())

    def _register_defaults(self) -> None:
        self.register(
            CapabilitySpec(
                name="system.health",
                risk=RiskLevel.READ,
                description="Return local agent OS, Python, disk and process health.",
            ),
            self._system_health,
        )
        self.register(
            CapabilitySpec(
                name="file.hash",
                risk=RiskLevel.READ,
                description="Calculate SHA-256 for an authorized file.",
            ),
            self._file_hash,
        )
        self.register(
            CapabilitySpec(
                name="file.read_text",
                risk=RiskLevel.READ,
                description="Read bounded UTF-8 text from an authorized file.",
            ),
            self._file_read_text,
        )
        self.register(
            CapabilitySpec(
                name="diagnostic.run_approved",
                risk=RiskLevel.DIAGNOSTIC,
                description="Run a pre-registered diagnostic command without shell expansion.",
            ),
            self._run_approved,
        )
        self.register(
            CapabilitySpec(
                name="change.run_approved",
                risk=RiskLevel.CHANGE,
                description="Run a pre-registered change command with explicit approval.",
                requires_approval=True,
            ),
            self._run_approved,
        )
        if self.engineering_terminal is not None:
            self._register_engineering_terminal()

    def _register_engineering_terminal(self) -> None:
        terminal_specs = [
            ("engineering.terminal.start", "Start a privileged engineering terminal session."),
            ("engineering.terminal.execute", "Execute a command in a privileged engineering terminal session."),
            ("engineering.terminal.cwd", "Change the working directory for a privileged terminal session."),
            ("engineering.terminal.close", "Close a privileged engineering terminal session."),
            ("engineering.terminal.drives", "List drives visible to the engineering workstation account."),
        ]
        handlers = {
            "engineering.terminal.start": self._terminal_start,
            "engineering.terminal.execute": self._terminal_execute,
            "engineering.terminal.cwd": self._terminal_cwd,
            "engineering.terminal.close": self._terminal_close,
            "engineering.terminal.drives": self._terminal_drives,
        }
        for name, description in terminal_specs:
            self.register(
                CapabilitySpec(name=name, risk=RiskLevel.PRIVILEGED, description=description, requires_approval=True),
                handlers[name],
            )

    @staticmethod
    def _system_health(_: dict[str, Any]) -> dict[str, Any]:
        usage = shutil.disk_usage(Path.cwd().anchor or ".")
        return {
            "hostname": platform.node(),
            "os": platform.platform(),
            "python": platform.python_version(),
            "pid": os.getpid(),
            "disk_free_bytes": usage.free,
        }

    @staticmethod
    def _file_hash(params: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(params["path"]))
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}

    @staticmethod
    def _file_read_text(params: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(params["path"]))
        max_bytes = min(int(params.get("max_bytes", 65536)), 262144)
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]
        return {
            "path": str(path),
            "text": raw.decode("utf-8", errors="replace"),
            "truncated": truncated,
        }


    def _run_approved(self, params: dict[str, Any]) -> dict[str, Any]:
        command_id = str(params["command_id"])
        argv = self.approved_commands.get(command_id)
        if not argv:
            raise PermissionError(f"approved command not registered: {command_id}")
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=int(params.get("timeout_seconds", 120)),
            check=False,
        )
        return {
            "command_id": command_id,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _terminal(self) -> EngineeringTerminal:
        if self.engineering_terminal is None:
            raise RuntimeError("engineering terminal is not configured")
        return self.engineering_terminal

    def _terminal_start(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._terminal().start_session(
            actor=str(params.get("actor", "unknown")),
            shell=params.get("shell"),
        )

    def _terminal_execute(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._terminal().execute(
            session_id=str(params["session_id"]),
            command=str(params["command"]),
            timeout_seconds=params.get("timeout_seconds"),
        )

    def _terminal_cwd(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._terminal().set_cwd(
            session_id=str(params["session_id"]),
            path=str(params["path"]),
        )

    def _terminal_close(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._terminal().close_session(str(params["session_id"]))

    def _terminal_drives(self, _: dict[str, Any]) -> dict[str, Any]:
        return {"drives": self._terminal().list_local_drives()}
