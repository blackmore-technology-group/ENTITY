from __future__ import annotations

import os
import stat
from pathlib import Path


class MasterKeyResolutionError(RuntimeError):
    """Raised when stable software-custody master material cannot be resolved."""


def _best_effort_private_permissions(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Windows ACLs are not represented fully by chmod; the file remains a
        # development-only software-custody fallback, never an HSM claim.
        pass


def load_or_create_master_key(path: str | os.PathLike[str], *, environment_variable: str = "ADAM_V1_MASTER_KEY_HEX") -> bytes:
    """Resolve stable 256-bit software-custody material.

    Production deployments should provide key material through an HSM/KMS
    adapter.  The file-backed mode exists only for the bounded software
    reference and is restart-safe.  The raw key file is created atomically and
    must never be included in a release archive.
    """

    configured = os.environ.get(environment_variable)
    if configured:
        try:
            key = bytes.fromhex(configured.strip())
        except ValueError as exc:
            raise MasterKeyResolutionError(f"{environment_variable} is not valid hexadecimal") from exc
        if len(key) != 32:
            raise MasterKeyResolutionError(f"{environment_variable} must contain exactly 32 bytes")
        return key

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        key = target.read_bytes()
        if len(key) != 32:
            raise MasterKeyResolutionError("persisted software-custody master key has invalid length")
        _best_effort_private_permissions(target)
        return key

    key = os.urandom(32)
    temporary = target.with_suffix(target.suffix + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(key)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    os.replace(temporary, target)
    _best_effort_private_permissions(target)
    return key


def load_or_create_ed25519_private_key(path: str | os.PathLike[str]):
    """Load or atomically create a persistent Ed25519 private key.

    This is a bounded software-reference identity. Production deployments must
    replace it with a non-exportable provider-backed signing identity.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raw = target.read_bytes()
        if len(raw) != 32:
            raise MasterKeyResolutionError("persisted Ed25519 private key has invalid length")
        _best_effort_private_permissions(target)
        return Ed25519PrivateKey.from_private_bytes(raw)

    private = Ed25519PrivateKey.generate()
    raw = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    temporary = target.with_suffix(target.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    os.replace(temporary, target)
    _best_effort_private_permissions(target)
    return private
