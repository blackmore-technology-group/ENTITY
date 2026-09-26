from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def prepare_reference_command(directory: Path | str) -> tuple[list[str], bool]:
    """Return an executable command and whether the C reference was compiled.

    The C/OpenSSL target is compiled on supported POSIX hosts. Windows uses the
    byte-compatible Python reference so qualification remains executable without
    requiring MSYS2/Make/OpenSSL development headers. The same frame format,
    replay checks, stale-root rejection, and tamper detection are exercised.
    """
    directory = Path(directory)
    binary = directory / ("authority_reference.exe" if os.name == "nt" else "authority_reference")
    make = shutil.which("make")
    if os.name != "nt" and make:
        subprocess.run([make, "-C", str(directory), "clean", "all"], check=True, capture_output=True, text=True, timeout=120)
        if binary.exists():
            return [str(binary)], True
    fallback = directory / "authority_reference.py"
    if not fallback.exists():
        raise FileNotFoundError(fallback)
    return [sys.executable, str(fallback)], False
