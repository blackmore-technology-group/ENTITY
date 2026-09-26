from __future__ import annotations

import multiprocessing as mp
from dataclasses import asdict
from multiprocessing.connection import Connection
from typing import Callable, Any

from .physics import AtomicPhysicsKernel, ReactionIntent


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


class AuthorityServiceError(RuntimeError):
    pass


def _serve(connection: Connection, factory: Callable[[], AtomicPhysicsKernel] | None = None, kernel: AtomicPhysicsKernel | None = None) -> None:
    if kernel is None:
        if factory is None:
            raise AuthorityServiceError("authority factory or kernel is required")
        kernel = factory()
    while True:
        request = connection.recv()
        command = request.get("command")
        try:
            if command == "root":
                result: Any = {"root": kernel.root, "logical_time": kernel.logical_time}
            elif command == "simulate":
                _, proof = kernel.simulate(request["intent"])
                result = {"proof": proof.canonical(), "proof_id": proof.proof_id, "committed": False}
            elif command == "commit":
                proof = kernel.commit(request["intent"])
                result = {"proof": proof.canonical(), "proof_id": proof.proof_id, "committed": True}
            elif command == "worldline":
                entity = request["entity"]
                line = kernel.worldlines[entity]
                result = {"entity_id": line.entity_id, "genesis_root": line.genesis_root, "states": list(line.states)}
            elif command == "stop":
                connection.send({"ok": True, "result": {"root": kernel.root}})
                break
            else:
                raise AuthorityServiceError(f"unknown command {command}")
            connection.send({"ok": True, "result": result})
        except Exception as exc:
            connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    connection.close()


class IsolatedPhysicsAuthority:
    """OS-process authority boundary for the Python reference kernel.

    The production target remains the Rust kernel; this boundary prevents ordinary
    application code from holding mutable kernel objects or signing state.
    """

    def __init__(self, factory: Callable[[], AtomicPhysicsKernel]) -> None:
        context = _adam_mp_context()
        parent, child = context.Pipe(duplex=True)
        self._connection = parent
        if context.get_start_method() == "spawn":
            # Local fixture/factory functions are not necessarily importable by a
            # Windows spawn child. Materialize the pure deterministic kernel in
            # the parent and transfer only its serializable state copy.
            seed_kernel = factory()
            self._process = context.Process(target=_serve, args=(child, None, seed_kernel), daemon=True)
        else:
            self._process = context.Process(target=_serve, args=(child, factory, None), daemon=True)
        self._process.start()
        child.close()

    @property
    def pid(self) -> int | None:
        return self._process.pid

    def _call(self, command: str, **payload: Any) -> dict[str, Any]:
        if not self._process.is_alive():
            raise AuthorityServiceError("authority process is not alive")
        self._connection.send({"command": command, **payload})
        response = self._connection.recv()
        if not response.get("ok"):
            raise AuthorityServiceError(response.get("error", "authority error"))
        return dict(response["result"])

    def root(self) -> dict[str, Any]:
        return self._call("root")

    def simulate(self, intent: ReactionIntent) -> dict[str, Any]:
        return self._call("simulate", intent=intent)

    def commit(self, intent: ReactionIntent) -> dict[str, Any]:
        return self._call("commit", intent=intent)

    def worldline(self, entity: str) -> dict[str, Any]:
        return self._call("worldline", entity=entity)

    def close(self) -> None:
        process = self._process
        if process.is_alive():
            try:
                self._connection.send({"command": "stop"})
                if self._connection.poll(2.0):
                    self._connection.recv()
            except (BrokenPipeError, EOFError, OSError):
                pass
            process.join(timeout=5)
            if process.is_alive():
                process.terminate(); process.join(timeout=3)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill(); process.join(timeout=3)
        self._connection.close()
        if not process.is_alive():
            process.close()

    def __enter__(self) -> "IsolatedPhysicsAuthority":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
