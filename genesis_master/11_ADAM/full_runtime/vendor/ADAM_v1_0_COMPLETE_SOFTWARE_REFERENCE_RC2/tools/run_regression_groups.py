"""Cross-platform entry point for isolated file-by-file regression qualification.

On POSIX this process replaces itself with the Bash runner, so multiprocessing
resources from one pytest file cannot leak through a persistent Python parent.
Windows uses the PowerShell qualification launcher, which invokes each test file
as its own process.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if os.name == "posix":
    os.execv("/bin/bash", ["bash", str(ROOT / "tools/run_regression_files.sh")])
raise SystemExit("Use RUN_ADAM_V0501_SOURCE_AUDITED_QUALIFICATION.ps1 on Windows")
