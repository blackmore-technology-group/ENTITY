from __future__ import annotations

import hashlib
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .audit import AuditLog


@dataclass
class TerminalSession:
    session_id: str
    actor: str
    shell: str
    cwd: str
    created_monotonic: float


_SECRET_RE = re.compile(
    r"(?i)(password|passwd|token|secret|api[_-]?key)\s*([=:])\s*([^\s;]+)"
)


def _redact(command: str) -> str:
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***REDACTED***", command)


class EngineeringTerminal:
    def __init__(self, config: dict, audit: AuditLog) -> None:
        self.config = config
        self.audit = audit
        self.sessions: dict[str, TerminalSession] = {}
        self._assert_enabled_and_bound()

    def _assert_enabled_and_bound(self) -> None:
        if not bool(self.config.get("enabled", False)):
            raise PermissionError("engineering terminal is disabled")
        bound = str(self.config.get("bound_device", "")).strip()
        actual = platform.node().strip()
        if bound and bound.casefold() != actual.casefold():
            raise PermissionError(
                f"engineering terminal bound to {bound!r}, current device is {actual!r}"
            )

    def _allowed_shells(self) -> list[str]:
        return [str(x) for x in self.config.get("allowed_shells", ["powershell.exe"])]

    def start_session(self, actor: str, shell: str | None = None) -> dict:
        chosen = shell or str(self.config.get("default_shell", "powershell.exe"))
        if chosen not in self._allowed_shells():
            raise PermissionError(f"shell not enabled: {chosen}")
        cwd = str(self.config.get("default_cwd", Path.cwd()))
        if not Path(cwd).exists():
            raise FileNotFoundError(cwd)
        session = TerminalSession(
            session_id=str(uuid4()),
            actor=actor,
            shell=chosen,
            cwd=str(Path(cwd).resolve()),
            created_monotonic=time.monotonic(),
        )
        self.sessions[session.session_id] = session
        self.audit.append({
            "event": "engineering_terminal.session_started",
            "actor": actor,
            "session_id": session.session_id,
            "shell": chosen,
            "cwd": session.cwd,
            "device": platform.node(),
        })
        return self._session_view(session)

    def set_cwd(self, session_id: str, path: str) -> dict:
        session = self._session(session_id)
        resolved = Path(path).resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(str(resolved))
        session.cwd = str(resolved)
        self.audit.append({
            "event": "engineering_terminal.cwd_changed",
            "actor": session.actor,
            "session_id": session_id,
            "cwd": session.cwd,
            "device": platform.node(),
        })
        return self._session_view(session)

    def close_session(self, session_id: str) -> dict:
        session = self._session(session_id)
        self.sessions.pop(session_id, None)
        self.audit.append({
            "event": "engineering_terminal.session_closed",
            "actor": session.actor,
            "session_id": session_id,
            "device": platform.node(),
        })
        return {"closed": True, "session_id": session_id}

    def execute(self, session_id: str, command: str, timeout_seconds: int | None = None) -> dict:
        session = self._session(session_id)
        timeout = int(timeout_seconds or self.config.get("max_timeout_seconds", 600))
        timeout = max(1, min(timeout, int(self.config.get("max_timeout_seconds", 600))))
        argv = self._command_argv(session.shell, command)
        safe_preview = _redact(command)[:512]
        command_hash = hashlib.sha256(command.encode("utf-8")).hexdigest()
        started = time.monotonic()
        self.audit.append({
            "event": "engineering_terminal.command_started",
            "actor": session.actor,
            "session_id": session_id,
            "shell": session.shell,
            "cwd": session.cwd,
            "command_preview": safe_preview,
            "command_sha256": command_hash,
            "device": platform.node(),
        })
        completed = subprocess.run(
            argv,
            cwd=session.cwd,
            capture_output=True,
            text=False,
            timeout=timeout,
            check=False,
        )
        max_output = int(self.config.get("max_output_bytes", 1048576))
        stdout = completed.stdout[:max_output]
        stderr = completed.stderr[:max_output]
        result = {
            "session_id": session_id,
            "returncode": completed.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "stdout_truncated": len(completed.stdout) > max_output,
            "stderr_truncated": len(completed.stderr) > max_output,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
        self.audit.append({
            "event": "engineering_terminal.command_completed",
            "actor": session.actor,
            "session_id": session_id,
            "command_sha256": command_hash,
            "returncode": completed.returncode,
            "duration_seconds": result["duration_seconds"],
            "device": platform.node(),
        })
        return result

    def list_local_drives(self) -> list[str]:
        if os.name != "nt":
            return ["/"]
        return [f"{chr(letter)}:\\" for letter in range(65, 91) if Path(f"{chr(letter)}:\\").exists()]

    def _session(self, session_id: str) -> TerminalSession:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"unknown terminal session: {session_id}") from exc

    @staticmethod
    def _session_view(session: TerminalSession) -> dict:
        return {
            "session_id": session.session_id,
            "actor": session.actor,
            "shell": session.shell,
            "cwd": session.cwd,
        }

    @staticmethod
    def _command_argv(shell: str, command: str) -> list[str]:
        lowered = shell.casefold()
        if lowered.endswith("powershell.exe") or lowered.endswith("pwsh.exe"):
            return [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
        if lowered.endswith("cmd.exe"):
            return [shell, "/d", "/s", "/c", command]
        raise PermissionError(f"unsupported shell: {shell}")
