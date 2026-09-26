from __future__ import annotations

import base64
import json
import os
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes


class CustodyError(RuntimeError):
    """Raised when a custody operation violates key policy or integrity."""


@dataclass(frozen=True)
class KeyHandle:
    provider: str
    key_id: str
    purpose: str
    jurisdiction: str
    version: int

    @property
    def handle_id(self) -> str:
        return digest("ADAM52:KEY_HANDLE", asdict(self))


@dataclass(frozen=True)
class CustodyAttestation:
    provider: str
    provider_instance: str
    key_handle: KeyHandle
    public_key: bytes
    non_exportable: bool
    algorithm: str
    state: str
    evidence: Mapping[str, Any]
    signature: bytes

    def unsigned(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_instance": self.provider_instance,
            "key_handle": asdict(self.key_handle),
            "public_key": self.public_key.hex(),
            "non_exportable": self.non_exportable,
            "algorithm": self.algorithm,
            "state": self.state,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class SigningReceipt:
    provider: str
    provider_instance: str
    key_handle: KeyHandle
    payload_hash: str
    purpose: str
    context: Mapping[str, Any]
    signature: bytes
    receipt_signature: bytes

    def unsigned(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_instance": self.provider_instance,
            "key_handle": asdict(self.key_handle),
            "payload_hash": self.payload_hash,
            "purpose": self.purpose,
            "context": dict(self.context),
            "signature": self.signature.hex(),
        }

    @property
    def receipt_id(self) -> str:
        return digest("ADAM52:SIGNING_RECEIPT", {**self.unsigned(), "receipt_signature": self.receipt_signature})


class KeyCustodyProvider(Protocol):
    provider_name: str

    def create_key(self, *, key_id: str, purpose: str, jurisdiction: str) -> KeyHandle: ...
    def get_public_key(self, handle: KeyHandle) -> bytes: ...
    def sign(self, handle: KeyHandle, payload: bytes, *, purpose: str, context: Mapping[str, Any]) -> SigningReceipt: ...
    def verify_receipt(self, receipt: SigningReceipt, payload: bytes) -> bool: ...
    def rotate(self, handle: KeyHandle) -> KeyHandle: ...
    def disable(self, handle: KeyHandle) -> None: ...
    def destroy(self, handle: KeyHandle) -> None: ...
    def attest(self, handle: KeyHandle) -> CustodyAttestation: ...
    def list_versions(self, key_id: str) -> tuple[KeyHandle, ...]: ...
    def health(self) -> Mapping[str, Any]: ...


@dataclass
class _StoredKey:
    handle: KeyHandle
    public_key: bytes
    encrypted_private: bytes
    nonce: bytes
    state: str = "ACTIVE"

    def to_json(self) -> dict[str, Any]:
        return {
            "handle": asdict(self.handle),
            "public_key": base64.b64encode(self.public_key).decode("ascii"),
            "encrypted_private": base64.b64encode(self.encrypted_private).decode("ascii"),
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "state": self.state,
        }

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "_StoredKey":
        return cls(
            handle=KeyHandle(**dict(value["handle"])),
            public_key=base64.b64decode(value["public_key"]),
            encrypted_private=base64.b64decode(value["encrypted_private"]),
            nonce=base64.b64decode(value["nonce"]),
            state=str(value["state"]),
        )


class EncryptedSoftwareCustodyProvider:
    """Operational software custody reference.

    Private key bytes are encrypted at rest under a caller-supplied master key and
    are only decrypted inside the signing method. This is intentionally not an HSM
    and reports ``non_exportable=False`` in attestations.
    """

    provider_name = "ENCRYPTED_SOFTWARE_REFERENCE"

    def __init__(self, directory: str | os.PathLike[str], master_key: bytes, *, instance_id: str = "local-custody") -> None:
        if len(master_key) not in {16, 24, 32}:
            raise ValueError("master_key must be 128, 192 or 256 bits")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._master = bytearray(master_key)
        self.instance_id = instance_id
        self._lock = threading.RLock()
        self._store_path = self.directory / "custody.json"
        self._audit_path = self.directory / "custody.audit.jsonl"
        self._attestation_private = self._load_or_create_attestation_key()
        self._keys: dict[tuple[str, int], _StoredKey] = {}
        self._load()

    def _load_or_create_attestation_key(self) -> Ed25519PrivateKey:
        path = self.directory / "provider-attestation.key"
        aad = canonical_json_bytes({"provider": self.provider_name, "instance": self.instance_id})
        if path.exists():
            raw = path.read_bytes()
            nonce, ciphertext = raw[:12], raw[12:]
            private_raw = AESGCM(bytes(self._master)).decrypt(nonce, ciphertext, aad)
            return Ed25519PrivateKey.from_private_bytes(private_raw)
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        nonce = os.urandom(12)
        ciphertext = AESGCM(bytes(self._master)).encrypt(nonce, raw, aad)
        self._atomic_write(path, nonce + ciphertext)
        return key

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        payload = json.loads(self._store_path.read_text("utf-8"))
        if payload.get("format") != "ADAM52_SOFTWARE_CUSTODY_V1":
            raise CustodyError("unsupported custody store format")
        keys = [_StoredKey.from_json(item) for item in payload.get("keys", [])]
        self._keys = {(item.handle.key_id, item.handle.version): item for item in keys}

    def _persist(self) -> None:
        body = {
            "format": "ADAM52_SOFTWARE_CUSTODY_V1",
            "provider": self.provider_name,
            "instance": self.instance_id,
            "keys": [self._keys[key].to_json() for key in sorted(self._keys)],
        }
        self._atomic_write(self._store_path, canonical_json_bytes(body))

    def _audit(self, event: str, details: Mapping[str, Any]) -> None:
        previous = None
        if self._audit_path.exists():
            last = self._audit_path.read_text("utf-8").splitlines()
            if last:
                previous = json.loads(last[-1])["event_id"]
        unsigned = {"event": event, "details": dict(details), "previous": previous}
        event_id = digest("ADAM52:CUSTODY_EVENT", unsigned)
        record = {**unsigned, "event_id": event_id}
        with self._audit_path.open("ab") as handle:
            handle.write(canonical_json_bytes(record) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _aad(self, handle: KeyHandle, public_key: bytes) -> bytes:
        return canonical_json_bytes({"handle": asdict(handle), "public_key": public_key.hex(), "provider": self.provider_name})

    def _stored(self, handle: KeyHandle) -> _StoredKey:
        item = self._keys.get((handle.key_id, handle.version))
        if item is None or item.handle != handle:
            raise CustodyError("unknown key handle")
        return item

    def create_key(self, *, key_id: str, purpose: str, jurisdiction: str) -> KeyHandle:
        if not key_id or not purpose or not jurisdiction:
            raise ValueError("key_id, purpose and jurisdiction are required")
        with self._lock:
            version = max((v for (kid, v) in self._keys if kid == key_id), default=0) + 1
            handle = KeyHandle(self.provider_name, key_id, purpose, jurisdiction, version)
            private = Ed25519PrivateKey.generate()
            public = private.public_key().public_bytes_raw()
            private_raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
            nonce = os.urandom(12)
            encrypted = AESGCM(bytes(self._master)).encrypt(nonce, private_raw, self._aad(handle, public))
            self._keys[(key_id, version)] = _StoredKey(handle, public, encrypted, nonce)
            self._persist()
            self._audit("CREATE", {"handle_id": handle.handle_id})
            return handle

    def get_public_key(self, handle: KeyHandle) -> bytes:
        return self._stored(handle).public_key

    def sign(self, handle: KeyHandle, payload: bytes, *, purpose: str, context: Mapping[str, Any]) -> SigningReceipt:
        if purpose != handle.purpose:
            raise CustodyError("requested signing purpose does not match key purpose")
        with self._lock:
            item = self._stored(handle)
            if item.state != "ACTIVE":
                raise CustodyError(f"key is {item.state.lower()}")
            private_raw = AESGCM(bytes(self._master)).decrypt(item.nonce, item.encrypted_private, self._aad(handle, item.public_key))
            try:
                signature = Ed25519PrivateKey.from_private_bytes(private_raw).sign(payload)
            finally:
                mutable = bytearray(private_raw)
                for index in range(len(mutable)):
                    mutable[index] = 0
            receipt = SigningReceipt(
                provider=self.provider_name,
                provider_instance=self.instance_id,
                key_handle=handle,
                payload_hash=sha256_bytes(payload),
                purpose=purpose,
                context=dict(context),
                signature=signature,
                receipt_signature=b"",
            )
            receipt_signature = self._attestation_private.sign(canonical_json_bytes(receipt.unsigned()))
            receipt = SigningReceipt(**{**receipt.__dict__, "receipt_signature": receipt_signature})
            self._audit("SIGN", {"receipt_id": receipt.receipt_id, "handle_id": handle.handle_id})
            return receipt

    def verify_receipt(self, receipt: SigningReceipt, payload: bytes) -> bool:
        if receipt.provider != self.provider_name or receipt.provider_instance != self.instance_id:
            return False
        if receipt.payload_hash != sha256_bytes(payload) or receipt.purpose != receipt.key_handle.purpose:
            return False
        try:
            stored = self._stored(receipt.key_handle)
            Ed25519PublicKey.from_public_bytes(stored.public_key).verify(receipt.signature, payload)
            self._attestation_private.public_key().verify(receipt.receipt_signature, canonical_json_bytes(receipt.unsigned()))
        except (CustodyError, InvalidSignature, ValueError):
            return False
        return True

    def rotate(self, handle: KeyHandle) -> KeyHandle:
        with self._lock:
            item = self._stored(handle)
            if item.state == "DESTROYED":
                raise CustodyError("destroyed key cannot be rotated")
            item.state = "RETIRED"
            new_handle = self.create_key(key_id=handle.key_id, purpose=handle.purpose, jurisdiction=handle.jurisdiction)
            self._audit("ROTATE", {"from": handle.handle_id, "to": new_handle.handle_id})
            return new_handle

    def disable(self, handle: KeyHandle) -> None:
        with self._lock:
            item = self._stored(handle)
            if item.state == "DESTROYED":
                raise CustodyError("key is destroyed")
            item.state = "DISABLED"
            self._persist()
            self._audit("DISABLE", {"handle_id": handle.handle_id})

    def destroy(self, handle: KeyHandle) -> None:
        with self._lock:
            item = self._stored(handle)
            item.encrypted_private = os.urandom(len(item.encrypted_private))
            item.nonce = os.urandom(len(item.nonce))
            item.state = "DESTROYED"
            self._persist()
            self._audit("DESTROY", {"handle_id": handle.handle_id})

    def attest(self, handle: KeyHandle) -> CustodyAttestation:
        item = self._stored(handle)
        attestation = CustodyAttestation(
            provider=self.provider_name,
            provider_instance=self.instance_id,
            key_handle=handle,
            public_key=item.public_key,
            non_exportable=False,
            algorithm="Ed25519",
            state=item.state,
            evidence={
                "storage": "AES-GCM encrypted software keystore",
                "hardware_backed": False,
                "production_hsm_certified": False,
            },
            signature=b"",
        )
        signature = self._attestation_private.sign(canonical_json_bytes(attestation.unsigned()))
        return CustodyAttestation(**{**attestation.__dict__, "signature": signature})

    def verify_attestation(self, attestation: CustodyAttestation) -> bool:
        try:
            self._attestation_private.public_key().verify(attestation.signature, canonical_json_bytes(attestation.unsigned()))
        except InvalidSignature:
            return False
        return attestation.provider == self.provider_name and attestation.provider_instance == self.instance_id

    def list_versions(self, key_id: str) -> tuple[KeyHandle, ...]:
        return tuple(self._keys[(kid, version)].handle for kid, version in sorted(self._keys) if kid == key_id)

    def health(self) -> Mapping[str, Any]:
        states: dict[str, int] = {}
        for item in self._keys.values():
            states[item.state] = states.get(item.state, 0) + 1
        return {
            "provider": self.provider_name,
            "instance": self.instance_id,
            "hardware_backed": False,
            "keys": len(self._keys),
            "states": states,
            "audit_exists": self._audit_path.exists(),
        }

    def close(self) -> None:
        for index in range(len(self._master)):
            self._master[index] = 0


class AuthorityKeyHierarchy:
    PURPOSES = {
        "ROOT_GOVERNANCE",
        "NODE_IDENTITY",
        "REACTION_SIGNING",
        "WITNESS",
        "CHECKPOINT",
        "RELEASE_SIGNING",
        "ENCRYPTION_DOMAIN",
        "SESSION",
    }

    def __init__(self, provider: KeyCustodyProvider) -> None:
        self.provider = provider
        self.handles: dict[tuple[str, str], KeyHandle] = {}

    def provision(self, *, jurisdiction: str, purposes: Iterable[str] | None = None) -> Mapping[str, KeyHandle]:
        requested = tuple(sorted(set(purposes or self.PURPOSES)))
        unknown = set(requested) - self.PURPOSES
        if unknown:
            raise ValueError(f"unknown key purposes: {sorted(unknown)}")
        created: dict[str, KeyHandle] = {}
        for purpose in requested:
            key_id = f"adam-{jurisdiction.lower()}-{purpose.lower().replace('_', '-')}"
            existing = tuple(self.provider.list_versions(key_id))
            active = None
            for candidate in reversed(existing):
                try:
                    if self.provider.attest(candidate).state == "ACTIVE":
                        active = candidate
                        break
                except Exception:
                    continue
            handle = active or self.provider.create_key(
                key_id=key_id,
                purpose=purpose,
                jurisdiction=jurisdiction,
            )
            self.handles[(jurisdiction, purpose)] = handle
            created[purpose] = handle
        return created

    def require(self, jurisdiction: str, purpose: str) -> KeyHandle:
        try:
            return self.handles[(jurisdiction, purpose)]
        except KeyError as exc:
            raise CustodyError(f"no {purpose} key provisioned for {jurisdiction}") from exc
