from __future__ import annotations

import multiprocessing as mp
import os
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from adam_v41.canonical import digest, sha256_bytes


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


class CustodyError(RuntimeError):
    pass


@dataclass(frozen=True)
class SignerDescriptor:
    provider: str
    key_id: str
    public_key_hex: str
    generation: int
    created_ns: int
    hardware_backed: bool


@dataclass(frozen=True)
class SignatureReceipt:
    key_id: str
    provider: str
    generation: int
    payload_sha256: str
    signature_hex: str
    signed_ns: int
    receipt_id: str


class SignerProvider(Protocol):
    @property
    def descriptor(self) -> SignerDescriptor: ...
    def sign(self, payload: bytes) -> SignatureReceipt: ...
    def verify(self, payload: bytes, receipt: SignatureReceipt) -> bool: ...
    def rotate(self) -> SignerDescriptor: ...


def _signer_process(conn, token: str, provider: str) -> None:
    generation = 1
    private = Ed25519PrivateKey.generate()
    created_ns = time.time_ns()

    def descriptor() -> dict[str, Any]:
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return asdict(SignerDescriptor(provider, sha256_bytes(b"ADAM43:KEY\0" + public), public.hex(), generation, created_ns, False))

    try:
        conn.send({"ok": True, "descriptor": descriptor()})
        while True:
            try:
                request = conn.recv()
            except EOFError:
                return
            if not secrets.compare_digest(str(request.get("token", "")), token):
                conn.send({"ok": False, "error": "AUTHENTICATION_FAILED"})
                continue
            command = request.get("command")
            if command == "stop":
                conn.send({"ok": True})
                return
            if command == "descriptor":
                conn.send({"ok": True, "descriptor": descriptor()})
                continue
            if command == "rotate":
                generation += 1
                private = Ed25519PrivateKey.generate()
                created_ns = time.time_ns()
                conn.send({"ok": True, "descriptor": descriptor()})
                continue
            if command == "sign":
                payload = bytes.fromhex(request["payload_hex"])
                info = descriptor()
                signed_ns = time.time_ns()
                signature = private.sign(payload).hex()
                receipt_payload = {
                    "key_id": info["key_id"], "provider": provider, "generation": generation,
                    "payload_sha256": sha256_bytes(payload), "signature_hex": signature, "signed_ns": signed_ns,
                }
                receipt_payload["receipt_id"] = digest("ADAM43:SIGNATURE_RECEIPT", receipt_payload)
                conn.send({"ok": True, "receipt": receipt_payload})
                continue
            conn.send({"ok": False, "error": "UNKNOWN_COMMAND"})
    finally:
        conn.close()


class IsolatedMemorySigner:
    """Signing key generated and retained only inside a separate OS process.

    This removes private-key material from the application process. It is a stronger
    development custody boundary, but remains software—not an HSM certification claim.
    """

    def __init__(self, provider: str = "isolated-memory-signer"):
        ctx = _adam_mp_context()
        parent, child = ctx.Pipe()
        self._conn = parent
        self._token = secrets.token_hex(32)
        self._process = ctx.Process(target=_signer_process, args=(child, self._token, provider), daemon=True)
        self._process.start()
        child.close()  # parent must not retain the worker endpoint after process start
        initial = self._conn.recv()
        if not initial.get("ok"):
            raise CustodyError("signer failed to start")
        self._descriptor = SignerDescriptor(**initial["descriptor"])
        self._public_history: dict[str, str] = {self._descriptor.key_id: self._descriptor.public_key_hex}

    @property
    def descriptor(self) -> SignerDescriptor:
        return self._descriptor

    @property
    def pid(self) -> int | None:
        return self._process.pid

    def _call(self, command: str, **payload: Any) -> dict[str, Any]:
        if not self._process.is_alive():
            raise CustodyError("signer process is unavailable")
        self._conn.send({"token": self._token, "command": command, **payload})
        reply = self._conn.recv()
        if not reply.get("ok"):
            raise CustodyError(str(reply.get("error", "signer failure")))
        return reply

    def sign(self, payload: bytes) -> SignatureReceipt:
        return SignatureReceipt(**self._call("sign", payload_hex=payload.hex())["receipt"])

    def verify(self, payload: bytes, receipt: SignatureReceipt) -> bool:
        public_hex = self._public_history.get(receipt.key_id)
        if not public_hex or receipt.payload_sha256 != sha256_bytes(payload):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(bytes.fromhex(receipt.signature_hex), payload)
            expected = digest("ADAM43:SIGNATURE_RECEIPT", {
                "key_id": receipt.key_id, "provider": receipt.provider, "generation": receipt.generation,
                "payload_sha256": receipt.payload_sha256, "signature_hex": receipt.signature_hex, "signed_ns": receipt.signed_ns,
            })
            return secrets.compare_digest(expected, receipt.receipt_id)
        except (InvalidSignature, ValueError):
            return False

    def rotate(self) -> SignerDescriptor:
        descriptor = SignerDescriptor(**self._call("rotate")["descriptor"])
        self._descriptor = descriptor
        self._public_history[descriptor.key_id] = descriptor.public_key_hex
        return descriptor

    def close(self) -> None:
        process = self._process
        if process.is_alive():
            try:
                self._conn.send({"token": self._token, "command": "stop"})
                if self._conn.poll(2.0):
                    self._conn.recv()
            except (BrokenPipeError, EOFError, OSError):
                pass  # worker failure is handled by forced shutdown below
            process.join(timeout=3)
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(timeout=3)
        self._conn.close()
        if not process.is_alive():
            process.close()

    def __enter__(self) -> "IsolatedMemorySigner":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


@dataclass(frozen=True)
class QuorumReceipt:
    payload_sha256: str
    threshold: int
    signatures: tuple[SignatureReceipt, ...]
    quorum_id: str


class QuorumCustody:
    def __init__(self, providers: list[SignerProvider], threshold: int):
        if not providers or threshold < 1 or threshold > len(providers):
            raise ValueError("invalid quorum")
        if len({p.descriptor.key_id for p in providers}) != len(providers):
            raise ValueError("quorum providers must use distinct keys")
        self.providers = providers
        self.threshold = threshold

    def sign(self, payload: bytes) -> QuorumReceipt:
        signatures: list[SignatureReceipt] = []
        for provider in self.providers:
            try:
                receipt = provider.sign(payload)
            except (CustodyError, OSError, TimeoutError):
                continue
            if provider.verify(payload, receipt):
                signatures.append(receipt)
        if len(signatures) < self.threshold:
            raise CustodyError("signing quorum was not reached")
        signature_tuple = tuple(signatures)
        payload_hash = sha256_bytes(payload)
        body = {
            "payload_sha256": payload_hash,
            "threshold": self.threshold,
            "signatures": [asdict(receipt) for receipt in signature_tuple],
        }
        return QuorumReceipt(payload_hash, self.threshold, signature_tuple, digest("ADAM43:QUORUM_RECEIPT", body))

    def verify(self, payload: bytes, receipt: QuorumReceipt) -> bool:
        if receipt.payload_sha256 != sha256_bytes(payload) or receipt.threshold != self.threshold:
            return False
        body = {
            "payload_sha256": receipt.payload_sha256,
            "threshold": receipt.threshold,
            "signatures": [asdict(signature) for signature in receipt.signatures],
        }
        if not secrets.compare_digest(digest("ADAM43:QUORUM_RECEIPT", body), receipt.quorum_id):
            return False
        provider_map = {provider.descriptor.key_id: provider for provider in self.providers}
        valid = 0
        seen: set[str] = set()
        for signature in receipt.signatures:
            provider = provider_map.get(signature.key_id)
            if provider and signature.key_id not in seen and provider.verify(payload, signature):
                seen.add(signature.key_id)
                valid += 1
        return valid >= self.threshold


@dataclass(frozen=True)
class PKCS11ProviderSpec:
    module_path: str
    token_label: str
    key_label: str
    pin_source: str
    mechanism: str = "CKM_EDDSA"

    def validate(self) -> None:
        if not self.module_path or not self.token_label or not self.key_label:
            raise CustodyError("PKCS#11 module, token and key labels are required")
        if self.pin_source.startswith("literal:"):
            raise CustodyError("literal PINs are forbidden; use environment, file descriptor or secret manager")


@dataclass(frozen=True)
class CloudKMSProviderSpec:
    provider: str
    key_resource: str
    region: str
    algorithm: str = "ED25519"
    endpoint: str | None = None

    def validate(self) -> None:
        if self.provider not in {"aws-kms", "gcp-kms", "azure-key-vault", "vault-transit"}:
            raise CustodyError("unsupported KMS provider")
        if not self.key_resource or not self.region:
            raise CustodyError("key resource and region are required")


class ExternalSignerAdapter:
    """Injects an externally implemented HSM/KMS sign operation into ADAM.

    The callback can wrap PKCS#11, cloud KMS, Vault Transit or another custody service.
    The private key never enters ADAM. Production qualification must verify the external
    provider's attestation, access policy, audit logs, rotation and disaster recovery.
    """

    def __init__(self, descriptor: SignerDescriptor, sign_callback: Callable[[bytes], bytes]):
        if not descriptor.hardware_backed:
            raise CustodyError("external production provider must declare hardware backing")
        self._descriptor = descriptor
        self._callback = sign_callback

    @property
    def descriptor(self) -> SignerDescriptor:
        return self._descriptor

    def sign(self, payload: bytes) -> SignatureReceipt:
        signature = self._callback(payload)
        signed_ns = time.time_ns()
        body = {
            "key_id": self._descriptor.key_id, "provider": self._descriptor.provider,
            "generation": self._descriptor.generation, "payload_sha256": sha256_bytes(payload),
            "signature_hex": signature.hex(), "signed_ns": signed_ns,
        }
        return SignatureReceipt(**body, receipt_id=digest("ADAM43:SIGNATURE_RECEIPT", body))

    def verify(self, payload: bytes, receipt: SignatureReceipt) -> bool:
        if (
            receipt.key_id != self._descriptor.key_id
            or receipt.provider != self._descriptor.provider
            or receipt.generation != self._descriptor.generation
            or receipt.payload_sha256 != sha256_bytes(payload)
        ):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self._descriptor.public_key_hex)).verify(
                bytes.fromhex(receipt.signature_hex), payload
            )
        except (InvalidSignature, ValueError):
            return False
        expected = digest("ADAM43:SIGNATURE_RECEIPT", {
            "key_id": receipt.key_id,
            "provider": receipt.provider,
            "generation": receipt.generation,
            "payload_sha256": receipt.payload_sha256,
            "signature_hex": receipt.signature_hex,
            "signed_ns": receipt.signed_ns,
        })
        return secrets.compare_digest(expected, receipt.receipt_id)

    def rotate(self) -> SignerDescriptor:
        raise CustodyError("rotation is controlled by the external custody provider")
