from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from adam_v41.canonical import sha256_bytes


class KeyStoreError(RuntimeError):
    pass


def _derive(passphrase: str, salt: bytes) -> bytes:
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=300_000).derive(passphrase.encode("utf-8"))


@dataclass(frozen=True)
class KeyDescriptor:
    key_id: str
    public_key_hex: str
    generation: int
    created_ns: int


class EncryptedSigningKeyStore:
    """Encrypted development keystore with rotation and public-key history.

    It materially closes plaintext-key storage for this prototype but is not an HSM.
    """

    def __init__(self, root: Path | str, passphrase: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "signing_keys.enc.json"
        self.passphrase = passphrase
        if not self.path.exists():
            self._create_initial()

    def _create_initial(self) -> None:
        private = Ed25519PrivateKey.generate()
        self._write(private, generation=1, history=[])

    def _write(self, private: Ed25519PrivateKey, generation: int, history: list[dict]) -> None:
        raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        key_id = sha256_bytes(b"ADAM42:KEY\0" + public)
        salt, nonce = os.urandom(16), os.urandom(12)
        aad = f"ADAM42:{generation}:{key_id}".encode()
        ciphertext = AESGCM(_derive(self.passphrase, salt)).encrypt(nonce, raw, aad)
        payload = {
            "format": "ADAM-v0.42-encrypted-keystore",
            "generation": generation,
            "key_id": key_id,
            "public_key_hex": public.hex(),
            "created_ns": time.time_ns(),
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "aad": aad.hex(),
            "ciphertext": ciphertext.hex(),
            "history": history,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def _load(self) -> tuple[Ed25519PrivateKey, dict]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        try:
            raw = AESGCM(_derive(self.passphrase, bytes.fromhex(payload["salt"]))).decrypt(
                bytes.fromhex(payload["nonce"]), bytes.fromhex(payload["ciphertext"]), bytes.fromhex(payload["aad"])
            )
        except (InvalidTag, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise KeyStoreError("Unable to decrypt signing key") from exc
        return Ed25519PrivateKey.from_private_bytes(raw), payload

    @property
    def descriptor(self) -> KeyDescriptor:
        _, p = self._load()
        return KeyDescriptor(p["key_id"], p["public_key_hex"], int(p["generation"]), int(p["created_ns"]))

    def sign(self, data: bytes) -> str:
        private, _ = self._load()
        return private.sign(data).hex()

    def verify(self, data: bytes, signature: str, key_id: str | None = None) -> bool:
        _, p = self._load()
        candidates = [{"key_id": p["key_id"], "public_key_hex": p["public_key_hex"]}] + list(p.get("history", []))
        for candidate in candidates:
            if key_id is not None and candidate["key_id"] != key_id:
                continue
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(candidate["public_key_hex"])).verify(bytes.fromhex(signature), data)
                return True
            except (InvalidSignature, ValueError):
                continue
        return False

    def rotate(self) -> KeyDescriptor:
        _, p = self._load()
        history = list(p.get("history", []))
        history.append({
            "key_id": p["key_id"], "public_key_hex": p["public_key_hex"],
            "generation": p["generation"], "created_ns": p["created_ns"], "retired_ns": time.time_ns(),
        })
        self._write(Ed25519PrivateKey.generate(), int(p["generation"]) + 1, history)
        return self.descriptor


class CryptoErasureStore:
    """Envelope-encrypted object store where deleting the data key makes ciphertext unrecoverable."""

    def __init__(self, root: Path | str, master_secret: bytes):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.master = sha256_bytes(master_secret).encode("ascii")[:32]
        self.index_path = self.root / "index.json"
        self.index = json.loads(self.index_path.read_text()) if self.index_path.exists() else {}

    def _save(self) -> None:
        self.index_path.write_text(json.dumps(self.index, indent=2, sort_keys=True), encoding="utf-8")

    def put(self, payload: bytes, metadata: dict | None = None) -> str:
        object_id = sha256_bytes(b"ADAM42:ERASURE:" + payload + os.urandom(16))
        data_key, nonce = os.urandom(32), os.urandom(12)
        ciphertext = AESGCM(data_key).encrypt(nonce, payload, object_id.encode())
        wrap_nonce = os.urandom(12)
        wrapped = AESGCM(self.master).encrypt(wrap_nonce, data_key, object_id.encode())
        (self.root / f"{object_id}.bin").write_bytes(ciphertext)
        self.index[object_id] = {
            "nonce": nonce.hex(), "wrap_nonce": wrap_nonce.hex(), "wrapped_key": wrapped.hex(),
            "payload_sha256": sha256_bytes(payload), "metadata": metadata or {}, "erased": False,
        }
        self._save()
        return object_id

    def get(self, object_id: str) -> bytes:
        item = self.index.get(object_id)
        if item is None:
            raise KeyError(object_id)
        if item.get("erased") or not item.get("wrapped_key"):
            raise KeyStoreError("Object has been cryptographically erased")
        key = AESGCM(self.master).decrypt(bytes.fromhex(item["wrap_nonce"]), bytes.fromhex(item["wrapped_key"]), object_id.encode())
        payload = AESGCM(key).decrypt(bytes.fromhex(item["nonce"]), (self.root / f"{object_id}.bin").read_bytes(), object_id.encode())
        if sha256_bytes(payload) != item["payload_sha256"]:
            raise KeyStoreError("Payload integrity failure")
        return payload

    def erase(self, object_id: str, reason: str, authority: str) -> dict:
        item = self.index[object_id]
        item["wrapped_key"] = None
        item["wrap_nonce"] = None
        item["erased"] = True
        item["erasure_tombstone"] = {
            "reason": reason, "authority": authority, "time_ns": time.time_ns(),
            "ciphertext_retained": (self.root / f"{object_id}.bin").exists(),
        }
        self._save()
        return dict(item["erasure_tombstone"])
