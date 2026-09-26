from __future__ import annotations

import multiprocessing as mp
import os
import sys
import threading
from pathlib import Path

import pytest


class DeterministicSessionExit:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report) -> None:
        if report.when != "call":
            return
        if report.passed:
            self.passed += 1
        elif report.failed:
            self.failed += 1
        elif report.skipped:
            self.skipped += 1

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus) -> None:
        code = int(exitstatus)
        leaked = []
        for child in mp.active_children():
            child.join(timeout=2)
            if child.is_alive():
                leaked.append(child.pid)
                child.terminate(); child.join(timeout=2)
            if child.is_alive() and hasattr(child, "kill"):
                child.kill(); child.join(timeout=2)
        if leaked:
            print(f"LEAKED_MULTIPROCESS_WORKERS={leaked}", file=sys.stderr)
            code = code or 3

        lingering = [thread.name for thread in threading.enumerate()
                     if thread is not threading.main_thread() and not thread.daemon]
        if lingering:
            print(f"LINGERING_NON_DAEMON_THREADS={lingering}", file=sys.stderr)
            code = code or 4

        print(
            f"ADAM_PYTEST_RESULT passed={self.passed} failed={self.failed} "
            f"skipped={self.skipped} exit={code}",
            flush=True,
        )
        sys.stdout.flush(); sys.stderr.flush()
        os._exit(code)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: isolated_pytest_file.py <test-file>", file=sys.stderr)
        os._exit(2)
    test_file = Path(sys.argv[1])
    plugin = DeterministicSessionExit()
    pytest.main(["-q", str(test_file), "--disable-warnings"], plugins=[plugin])
    # The session-finish hook must always terminate the process.
    print("pytest returned without deterministic session exit", file=sys.stderr, flush=True)
    os._exit(5)


if __name__ == "__main__":
    main()
