from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from adam_v41 import authority
from native_authority_reference import authority_reference


def test_authority_writer_has_no_direct_posix_fchmod_dependency(tmp_path: Path):
    source = Path(authority.__file__).read_text(encoding="utf-8")
    assert "os.fchmod(" not in source
    assert 'getattr(os, "fchmod", None)' in source
    target = tmp_path / "authority.key"
    authority._atomic_write(target, b"secret", 0o600)
    assert target.read_bytes() == b"secret"


def test_atomic_write_replaces_cleanly_without_temporary_residue(tmp_path: Path):
    target = tmp_path / "authority.key"
    authority._atomic_write(target, b"first", 0o600)
    authority._atomic_write(target, b"second", 0o600)
    assert target.read_bytes() == b"second"
    assert list(tmp_path.glob(".authority.key.*")) == []


def test_python_native_reference_is_byte_compatible_and_tamper_detecting(tmp_path: Path):
    log = tmp_path / "native.log"
    command = [sys.executable, str(Path(authority_reference.__file__).resolve()), str(log)]
    first = subprocess.run(
        command,
        input="APPEND 616263\nROOT\nQUIT\n",
        check=True,
        capture_output=True,
        text=True,
    )
    assert "READY ADAM43-NATIVE-FRAMING-REFERENCE 0" in first.stdout
    assert "OK 1 " in first.stdout
    sequence, root = authority_reference.replay(log)
    assert sequence == 1
    assert len(root) == 32

    data = bytearray(log.read_bytes())
    data[-1] ^= 1
    log.write_bytes(data)
    tampered = subprocess.run(command, capture_output=True, text=True)
    assert tampered.returncode == 65
    assert "integrity failure" in tampered.stderr


def test_spawn_context_is_forced_for_windows_qualification():
    previous = os.environ.get("ADAM_FORCE_SPAWN")
    os.environ["ADAM_FORCE_SPAWN"] = "1"
    try:
        from adam_v42.isolation import _adam_mp_context as isolation_context
        from adam_v43.key_custody import _adam_mp_context as custody_context
        from adam_v44.authority_service import _adam_mp_context as physics_context

        assert isolation_context().get_start_method() == "spawn"
        assert custody_context().get_start_method() == "spawn"
        assert physics_context().get_start_method() == "spawn"
    finally:
        if previous is None:
            os.environ.pop("ADAM_FORCE_SPAWN", None)
        else:
            os.environ["ADAM_FORCE_SPAWN"] = previous


def test_windows_powershell_launchers_are_parse_safe_and_dependency_aware():
    root = Path(__file__).resolve().parents[1]
    qualification = (root / "RUN_ADAM_V0501_SOURCE_AUDITED_QUALIFICATION.ps1").read_text(encoding="utf-8")
    launcher = (root / "START_ADAM_V0501_FINAL_WINDOWS.ps1").read_text(encoding="utf-8")

    # PowerShell parses `$Name:` as a scoped/drive-style variable reference.
    # File names followed by a colon must therefore use a subexpression.
    assert '$File:' not in qualification
    assert '$($File):' in qualification

    # Normal qualification needs pytest but must not require optional coverage.
    assert 'import cryptography, msgpack, numpy, PIL, sympy, pytest, coverage' not in launcher
    assert 'if ($Full)' in launcher and 'import coverage' in launcher

    # Dependency installation must include the package's qualification extras.
    assert '${Root}[test]' in launcher
