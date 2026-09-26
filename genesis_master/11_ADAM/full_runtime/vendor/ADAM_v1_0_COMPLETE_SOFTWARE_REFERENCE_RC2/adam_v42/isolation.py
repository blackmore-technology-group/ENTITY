from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
from typing import Any

from adam_v41.demo_domain import install_equipment_domain
from adam_v41.kernel import UniverseKernel
from adam_v41.reactions import ReactionIntent


def _adam_mp_context():
    """Return the configured safe multiprocessing context.

    ``spawn`` is the production-reference default on every platform because it
    creates a fresh interpreter and works on Windows. POSIX-only methods may be
    selected explicitly with ``ADAM_MP_START_METHOD`` for controlled testing.
    ``ADAM_FORCE_SPAWN=1`` always overrides the configured method.
    """
    import os

    available = set(mp.get_all_start_methods())
    requested = os.environ.get("ADAM_MP_START_METHOD", "spawn").strip().lower()
    if os.environ.get("ADAM_FORCE_SPAWN") == "1":
        requested = "spawn"
    if requested not in available:
        raise RuntimeError(
            f"unsupported multiprocessing start method {requested!r}; "
            f"available methods: {sorted(available)}"
        )
    return mp.get_context(requested)


class IsolatedKernelError(RuntimeError):
    pass


def _server(root: str, conn) -> None:
    kernel = UniverseKernel(Path(root))
    install_equipment_domain(kernel.reactions)
    try:
        while True:
            request = conn.recv()
            command = request.get("command")
            if command == "stop":
                conn.send({"ok": True})
                return
            try:
                if command == "genesis":
                    result = kernel.genesis_entity(request["entity_type"], request["key"], request["facts"])
                elif command == "apply":
                    receipt = kernel.apply(ReactionIntent(**request["intent"]))
                    result = receipt.__dict__
                elif command == "simulate":
                    receipt = kernel.simulate(ReactionIntent(**request["intent"]))
                    result = receipt.__dict__
                elif command == "view":
                    result = kernel.entity_view(request["entity_id"], at_seq=request.get("at_seq"))
                elif command == "info":
                    result = {"sequence": kernel.sequence, "root_hash": kernel.root_hash, "verify": kernel.verify()}
                elif command == "raw_commit_probe":
                    # Deliberately unavailable: the client cannot obtain a substrate or capability reference.
                    raise IsolatedKernelError("raw mutation endpoint does not exist")
                else:
                    raise IsolatedKernelError(f"unknown command {command!r}")
                conn.send({"ok": True, "result": result})
            except Exception as exc:
                conn.send({"ok": False, "error_type": type(exc).__name__, "error": str(exc)})
    finally:
        conn.close()


class IsolatedKernelClient:
    """Authority kernel in an OS process with a narrow message protocol."""

    def __init__(self, root: Path | str):
        # The selected context is resolved centrally; no platform-specific method is hard-coded here.
        ctx = _adam_mp_context()
        parent, child = ctx.Pipe()
        self._conn = parent
        self._process = ctx.Process(target=_server, args=(str(root), child), daemon=True)
        self._process.start()
        child.close()

    @property
    def pid(self) -> int | None:
        return self._process.pid

    def _call(self, command: str, **payload: Any) -> Any:
        if not self._process.is_alive():
            raise IsolatedKernelError("authority process is not alive")
        self._conn.send({"command": command, **payload})
        reply = self._conn.recv()
        if not reply.get("ok"):
            raise IsolatedKernelError(f"{reply.get('error_type')}: {reply.get('error')}")
        return reply.get("result")

    def genesis_entity(self, entity_type: str, key: str, facts: dict[str, Any]):
        return self._call("genesis", entity_type=entity_type, key=key, facts=facts)

    def apply(self, intent: ReactionIntent):
        return self._call("apply", intent={"reaction": intent.reaction, "bindings": dict(intent.bindings), "args": dict(intent.args)})

    def simulate(self, intent: ReactionIntent):
        return self._call("simulate", intent={"reaction": intent.reaction, "bindings": dict(intent.bindings), "args": dict(intent.args)})

    def entity_view(self, entity_id: str, at_seq: int | None = None):
        return self._call("view", entity_id=entity_id, at_seq=at_seq)

    def info(self):
        return self._call("info")

    def raw_commit_probe(self):
        return self._call("raw_commit_probe")

    def close(self) -> None:
        process = self._process
        if process.is_alive():
            try:
                self._conn.send({"command": "stop"})
                if self._conn.poll(2.0):
                    self._conn.recv()
            except (BrokenPipeError, EOFError, OSError):
                pass
            process.join(timeout=5)
            if process.is_alive():
                process.terminate(); process.join(timeout=3)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill(); process.join(timeout=3)
        self._conn.close()
        if not process.is_alive():
            process.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
