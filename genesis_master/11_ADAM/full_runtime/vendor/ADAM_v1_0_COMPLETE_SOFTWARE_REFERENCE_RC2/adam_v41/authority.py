from __future__ import annotations

import base64
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .canonical import canonical_json_bytes, sha256_bytes


class AuthorityError(RuntimeError):
    """Raised when signing authority state is missing, corrupt, or inconsistent."""


def _best_effort_fd_mode(fd: int, mode: int) -> None:
    """Apply POSIX descriptor permissions when the platform exposes fchmod.

    Windows CPython does not provide ``os.fchmod``. File confidentiality on
    Windows is handled by the containing user profile/ACL and the post-replace
    ``os.chmod`` best effort rather than by calling a missing POSIX API.
    """

    fchmod = getattr(os, "fchmod", None)
    if fchmod is None:
        return
    try:
        fchmod(fd, mode)
    except OSError:
        # Some filesystems expose fchmod but do not support Unix mode bits.
        pass


def _atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(name)
    descriptor_open = True
    try:
        _best_effort_fd_mode(fd, mode)
        handle = os.fdopen(fd, "wb")
        descriptor_open = False  # ownership transferred to ``handle``
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        try:
            os.chmod(path, mode)
        except OSError:
            pass
        if os.name != "nt":
            dfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    except Exception:
        # Windows refuses to unlink an open temporary file. Always close the
        # raw descriptor before cleanup if fdopen did not take ownership.
        if descriptor_open:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            temp.unlink()
        except (FileNotFoundError, PermissionError):
            pass
        raise


def _decode_kek(value: bytes | str | None) -> bytes | None:
    if value is None:
        env = os.environ.get("ADAM_AUTHORITY_KEK")
        if not env:
            return None
        value = env
    if isinstance(value, bytes):
        raw = value
    else:
        text = value.strip()
        try:
            raw = bytes.fromhex(text)
        except ValueError:
            try:
                raw = base64.b64decode(text, validate=True)
            except Exception as exc:
                raise AuthorityError("Authority KEK must be raw bytes, hex, or base64") from exc
    # Normalize supplied material to an AES-256 key without retaining the original form.
    return bytes.fromhex(sha256_bytes(b"ADAM:AUTHORITY:KEK\0" + raw))


@dataclass(frozen=True)
class AuthorityDescriptor:
    authority_id: str
    public_key_hex: str


class Authority:
    """Durable Ed25519 signing authority with optional encrypted key-at-rest.

    Existing plaintext v0.41 keys are read for compatibility and can be migrated
    automatically when a KEK is supplied. New production deployments should set
    ``ADAM_AUTHORITY_KEK`` or pass ``key_encryption_key``. The public API remains
    compatible with earlier ADAM lineage code.
    """

    def __init__(self, root: Path, key_encryption_key: bytes | str | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.private_path = self.root / "authority_private.key"
        self.encrypted_private_path = self.root / "authority_private.key.enc"
        self.public_path = self.root / "authority.json"
        self._kek = _decode_kek(key_encryption_key)

        if self.public_path.exists() and (self.encrypted_private_path.exists() or self.private_path.exists()):
            cfg = json.loads(self.public_path.read_text(encoding="utf-8"))
            self.authority_id = str(cfg["authority_id"])
            self.public_key_hex = str(cfg["public_key_hex"])
            raw = self._load_private()
            self._private = Ed25519PrivateKey.from_private_bytes(raw)
            self._verify_consistency()
            if self._kek is not None and self.private_path.exists() and not self.encrypted_private_path.exists():
                self._store_encrypted(raw)
                self._secure_delete_plaintext()
        elif not self.public_path.exists() and not self.encrypted_private_path.exists() and not self.private_path.exists():
            self._private = Ed25519PrivateKey.generate()
            raw_private = self._private.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
            public = self._private.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
            self.public_key_hex = public.hex()
            self.authority_id = sha256_bytes(b"ADAM41:AUTHORITY\0" + public)
            if self._kek is not None:
                self._store_encrypted(raw_private)
            else:
                _atomic_write(self.private_path, raw_private, 0o600)
            _atomic_write(
                self.public_path,
                json.dumps(
                    {
                        "authority_id": self.authority_id,
                        "public_key_hex": self.public_key_hex,
                        "private_key_storage": "AES256_GCM" if self._kek is not None else "SOFTWARE_FILE_0600",
                    },
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8"),
                0o644,
            )
        else:
            raise AuthorityError(f"Incomplete authority state in {self.root}")

    def _load_private(self) -> bytes:
        if self.encrypted_private_path.exists():
            if self._kek is None:
                raise AuthorityError(
                    f"Encrypted authority key at {self.encrypted_private_path} requires ADAM_AUTHORITY_KEK"
                )
            envelope = json.loads(self.encrypted_private_path.read_text(encoding="utf-8"))
            aad = canonical_json_bytes({"format": envelope["format"], "authority_root": str(self.root.resolve())})
            try:
                raw = AESGCM(self._kek).decrypt(
                    bytes.fromhex(envelope["nonce"]),
                    bytes.fromhex(envelope["ciphertext"]),
                    aad,
                )
            except Exception as exc:
                raise AuthorityError("Authority private key decryption failed") from exc
            if len(raw) != 32:
                raise AuthorityError("Authority private key has invalid length")
            return raw
        try:
            raw = self.private_path.read_bytes()
        except OSError as exc:
            raise AuthorityError("Authority private key is unreadable") from exc
        if len(raw) != 32:
            raise AuthorityError("Authority private key has invalid length")
        try:
            os.chmod(self.private_path, 0o600)
        except OSError:
            pass
        return raw

    def _store_encrypted(self, raw: bytes) -> None:
        if self._kek is None:
            raise AuthorityError("Cannot encrypt authority key without a KEK")
        nonce = os.urandom(12)
        aad = canonical_json_bytes({"format": "ADAM-ED25519-KEY-v1", "authority_root": str(self.root.resolve())})
        ciphertext = AESGCM(self._kek).encrypt(nonce, raw, aad)
        envelope = {
            "format": "ADAM-ED25519-KEY-v1",
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
        }
        _atomic_write(self.encrypted_private_path, json.dumps(envelope, sort_keys=True).encode("utf-8"), 0o600)

    def _secure_delete_plaintext(self) -> None:
        if not self.private_path.exists():
            return
        try:
            size = self.private_path.stat().st_size
            with self.private_path.open("r+b", buffering=0) as handle:
                handle.write(os.urandom(size))
                handle.flush()
                os.fsync(handle.fileno())
            self.private_path.unlink()
        except OSError as exc:
            raise AuthorityError("Failed to remove migrated plaintext authority key") from exc

    def _verify_consistency(self) -> None:
        public = self._private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        expected_public = public.hex()
        expected_id = sha256_bytes(b"ADAM41:AUTHORITY\0" + public)
        if expected_public != self.public_key_hex or expected_id != self.authority_id:
            raise AuthorityError("Authority private key does not match its public descriptor")

    @property
    def descriptor(self) -> AuthorityDescriptor:
        return AuthorityDescriptor(self.authority_id, self.public_key_hex)

    @property
    def encrypted_at_rest(self) -> bool:
        return self.encrypted_private_path.exists() and not self.private_path.exists()

    def sign(self, data: bytes) -> str:
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Authority.sign requires bytes")
        return self._private.sign(bytes(data)).hex()

    @staticmethod
    def verify(public_key_hex: str, data: bytes, signature_hex: str) -> bool:
        try:
            key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            key.verify(bytes.fromhex(signature_hex), data)
            return True
        except (ValueError, TypeError, Exception):
            return False
