from __future__ import annotations
from pathlib import Path
from threading import RLock
from typing import Any
import base64, hashlib, hmac, json, os, re, secrets, time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

ENTITY_ID_RE = re.compile(r"^(?:ent1|ent2)-[a-z2-7]{52}$")
RELATIONSHIP_ID_RE = re.compile(r"^rel1-[a-z2-7]{52}$")
ENTITY_TYPES = {"person", "family", "business", "product", "application", "system", "community", "service", "organization", "project"}
SIG_SUITE = "ENTITY-SIG-ED25519-v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _b32(value: bytes) -> str:
    return base64.b32encode(value).decode("ascii").lower().rstrip("=")


def entity_id_from_public_key(public_key_raw: bytes) -> str:
    return "ent1-" + _b32(hashlib.sha256(public_key_raw).digest())


def _new_entity_id() -> str:
    return "ent2-" + _b32(secrets.token_bytes(32))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _public_raw(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _private_raw(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())


class EntityIdentityVault:
    """Persistent root identity with rotatable operational keys and private pairwise identities."""
    def __init__(self, state_dir: str | Path, key_protector=None):
        self.root = Path(state_dir) / "identity"
        self.keys = self.root / "keys"
        self.manifests = self.root / "manifests"
        self.pairwise = self.root / "pairwise"
        for p in (self.keys, self.manifests, self.pairwise):
            p.mkdir(parents=True, exist_ok=True)
        self.key_protector = key_protector
        self._lock = RLock()

    def _entity_key_dir(self, entity_id: str) -> Path:
        if not ENTITY_ID_RE.fullmatch(entity_id):
            raise ValueError("invalid Entity ID")
        path = self.keys / entity_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _manifest_path(self, entity_id: str) -> Path:
        if not ENTITY_ID_RE.fullmatch(entity_id):
            raise ValueError("invalid Entity ID")
        return self.manifests / f"{entity_id}.json"

    def _write_private(self, path: Path, raw: bytes) -> None:
        path.write_bytes(raw)
        try: os.chmod(path, 0o600)
        except OSError: pass

    def _read_private_key_bytes(self, entity_id: str, key_id: str) -> bytes:
        raw_path=self._entity_key_dir(entity_id)/f"{key_id}.key"
        if raw_path.is_file(): return raw_path.read_bytes()
        wrapped_path=self._entity_key_dir(entity_id)/f"{key_id}.key.tpm"
        if wrapped_path.is_file():
            if self.key_protector is None: raise RuntimeError("hardware-protected private key requires configured key protector")
            return self.key_protector.unwrap(wrapped_path.read_bytes())
        raise FileNotFoundError(str(raw_path))

    def create(self, display_name: str, entity_type: str, aliases: list[str] | None = None, metadata: dict | None = None) -> dict:
        name = str(display_name or "").strip()
        kind = str(entity_type or "").strip().lower()
        if not name or len(name) > 256:
            raise ValueError("display_name must be 1..256 characters")
        if kind not in ENTITY_TYPES:
            raise ValueError(f"unsupported entity_type: {kind}")
        entity_id = _new_entity_id()
        signing = Ed25519PrivateKey.generate()
        recovery = Ed25519PrivateKey.generate()
        signing_id = "sig-" + secrets.token_hex(8)
        recovery_id = "rec-" + secrets.token_hex(8)
        now = int(time.time() * 1000)
        methods = [
            {"key_id": signing_id, "algorithm": "Ed25519", "suite": SIG_SUITE, "purpose": ["assertion", "authentication", "contract"], "public_key": _b64(_public_raw(signing)), "status": "active", "created_at_ms": now},
            {"key_id": recovery_id, "algorithm": "Ed25519", "suite": SIG_SUITE, "purpose": ["recovery"], "public_key": _b64(_public_raw(recovery)), "status": "active", "created_at_ms": now},
        ]
        manifest = {
            "schema": "sovereign-entity-manifest-v2",
            "entity_id": entity_id,
            "entity_type": kind,
            "display_name": name,
            "aliases": sorted({str(x).strip() for x in (aliases or []) if str(x).strip()}),
            "metadata": dict(metadata or {}),
            "verification_methods": methods,
            "active_signing_key_id": signing_id,
            "recovery_policy": {"threshold": 1, "authorities": [recovery_id], "delayed_recovery_supported": True},
            "crypto_agility": {"manifest_suite": SIG_SUITE, "supported_suites": [SIG_SUITE], "future_hybrid_allowed": True},
            "created_at_ms": now,
            "manifest_revision": 1,
        }
        signature = {"key_id": signing_id, "suite": SIG_SUITE, "signature": _b64(signing.sign(canonical_json(manifest)))}
        signed = dict(manifest, signature=signature)
        with self._lock:
            kd = self._entity_key_dir(entity_id)
            self._write_private(kd / f"{signing_id}.key", _private_raw(signing))
            self._write_private(kd / f"{recovery_id}.key", _private_raw(recovery))
            self._write_private(self.pairwise / f"{entity_id}.secret", secrets.token_bytes(32))
            self._manifest_path(entity_id).write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
        return signed

    @staticmethod
    def _verify_v1(signed: dict) -> bool:
        data = dict(signed)
        signature = _unb64(str(data.pop("signature")))
        pub_raw = _unb64(str(data["public_key"]))
        if data.get("entity_id") != entity_id_from_public_key(pub_raw):
            return False
        Ed25519PublicKey.from_public_bytes(pub_raw).verify(signature, canonical_json(data))
        return True

    @staticmethod
    def _method(manifest: dict, key_id: str) -> dict | None:
        for method in manifest.get("verification_methods") or []:
            if method.get("key_id") == key_id:
                return method
        return None

    @classmethod
    def verify_manifest(cls, signed: dict) -> bool:
        try:
            if signed.get("schema") == "sovereign-entity-manifest-v1":
                return cls._verify_v1(signed)
            if signed.get("schema") != "sovereign-entity-manifest-v2":
                return False
            data = dict(signed)
            signature = dict(data.pop("signature"))
            if not ENTITY_ID_RE.fullmatch(str(data.get("entity_id") or "")):
                return False
            method = cls._method(data, str(signature.get("key_id") or ""))
            if not method or method.get("status") != "active" or method.get("suite") != SIG_SUITE:
                return False
            rotation = data.get("rotation_proof")
            if rotation:
                proof=dict(rotation); proof_sig=dict(proof.pop("signature")); old=cls._method(data,str(proof_sig.get("key_id") or ""))
                if not old or old.get("status") not in {"retired","active"}: return False
                if proof.get("entity_id")!=data.get("entity_id") or proof.get("new_key_id")!=data.get("active_signing_key_id") or int(proof.get("manifest_revision",0))!=int(data.get("manifest_revision",0)): return False
                if proof.get("new_public_key")!=method.get("public_key") or proof.get("new_suite")!=method.get("suite"): return False
                Ed25519PublicKey.from_public_bytes(_unb64(str(old["public_key"]))).verify(_unb64(str(proof_sig["signature"])),canonical_json(proof))
            recovery = data.get("recovery_proof")
            if recovery:
                proof=dict(recovery); proof_sig=dict(proof.pop("signature")); authority=cls._method(data,str(proof_sig.get("key_id") or ""))
                if not authority or "recovery" not in set(authority.get("purpose") or []) or authority.get("status")!="active": return False
                if proof.get("entity_id")!=data.get("entity_id") or proof.get("new_key_id")!=data.get("active_signing_key_id") or int(proof.get("manifest_revision",0))!=int(data.get("manifest_revision",0)): return False
                if proof.get("new_public_key")!=method.get("public_key") or proof.get("new_suite")!=method.get("suite"): return False
                Ed25519PublicKey.from_public_bytes(_unb64(str(authority["public_key"]))).verify(_unb64(str(proof_sig["signature"])),canonical_json(proof))
            public_raw = _unb64(str(method["public_key"]))
            Ed25519PublicKey.from_public_bytes(public_raw).verify(_unb64(str(signature["signature"])), canonical_json(data))
            return True
        except Exception:
            return False

    def load_manifest(self, entity_id: str) -> dict:
        data = json.loads(self._manifest_path(entity_id).read_text(encoding="utf-8"))
        if not self.verify_manifest(data):
            raise RuntimeError("Entity manifest signature verification failed")
        return data

    def _active_key(self, entity_id: str) -> tuple[dict, Ed25519PrivateKey]:
        manifest = self.load_manifest(entity_id)
        if manifest.get("schema") == "sovereign-entity-manifest-v1":
            raw = (self.keys / f"{entity_id}.ed25519.key").read_bytes()
            return {"key_id": "legacy", "suite": SIG_SUITE}, Ed25519PrivateKey.from_private_bytes(raw)
        key_id = str(manifest["active_signing_key_id"])
        raw = self._read_private_key_bytes(entity_id,key_id)
        return {"key_id": key_id, "suite": SIG_SUITE}, Ed25519PrivateKey.from_private_bytes(raw)

    def open_signing_session(self, entity_id: str):
        """Cache one validated operational signing key for bounded bulk work.
        The returned callable preserves the normal signature-record schema but avoids
        reloading and re-verifying the manifest/key for every record in one batch.
        """
        info, key = self._active_key(entity_id)
        def _sign(payload: Any) -> dict:
            body = canonical_json(payload); signed_at = int(time.time()*1000)
            record = {"signature_schema":"entity-signature-record-v2","entity_id":entity_id,
                      "key_id":info["key_id"],"suite":info["suite"],"signed_at_ms":signed_at,
                      "payload_sha256":hashlib.sha256(body).hexdigest()}
            record["signature"] = _b64(key.sign(canonical_json(record)))
            return record
        return _sign

    def sign(self, entity_id: str, payload: Any) -> dict:
        return self.open_signing_session(entity_id)(payload)

    def rotate_signing_key(self, entity_id: str) -> dict:
        manifest=self.load_manifest(entity_id)
        if manifest.get("schema") != "sovereign-entity-manifest-v2":
            raise RuntimeError("legacy ent1 identity must be migrated before key rotation")
        old_id=str(manifest["active_signing_key_id"]); old_raw=self._read_private_key_bytes(entity_id,old_id); old_key=Ed25519PrivateKey.from_private_bytes(old_raw)
        new_key=Ed25519PrivateKey.generate(); new_id="sig-"+secrets.token_hex(8); now=int(time.time()*1000); revision=int(manifest.get("manifest_revision",1))+1
        data={k:v for k,v in manifest.items() if k not in {"signature","rotation_proof"}}
        methods=[]
        for item in data.get("verification_methods") or []:
            item=dict(item)
            if item.get("key_id")==old_id: item["status"]="retired"; item["retired_at_ms"]=now
            methods.append(item)
        new_pub=_b64(_public_raw(new_key)); methods.append({"key_id":new_id,"algorithm":"Ed25519","suite":SIG_SUITE,"purpose":["assertion","authentication","contract"],"public_key":new_pub,"status":"active","created_at_ms":now})
        data["verification_methods"]=methods; data["active_signing_key_id"]=new_id; data["manifest_revision"]=revision; data["previous_manifest_sha256"]=hashlib.sha256(canonical_json(manifest)).hexdigest()
        proof={"entity_id":entity_id,"old_key_id":old_id,"new_key_id":new_id,"new_public_key":new_pub,"new_suite":SIG_SUITE,"manifest_revision":revision}
        proof["signature"]={"key_id":old_id,"suite":SIG_SUITE,"signature":_b64(old_key.sign(canonical_json(proof)))}
        data["rotation_proof"]=proof
        signed=dict(data,signature={"key_id":new_id,"suite":SIG_SUITE,"signature":_b64(new_key.sign(canonical_json(data)))})
        self._write_private(self._entity_key_dir(entity_id)/f"{new_id}.key",_private_raw(new_key)); self._manifest_path(entity_id).write_text(json.dumps(signed,indent=2,sort_keys=True),encoding="utf-8")
        if not self.verify_manifest(signed): raise RuntimeError("rotated manifest failed continuity verification")
        return signed

    def recover_signing_key(self, entity_id: str) -> dict:
        manifest=self.load_manifest(entity_id)
        if manifest.get("schema") != "sovereign-entity-manifest-v2": raise RuntimeError("legacy ent1 identity must be migrated before recovery")
        authorities=list((manifest.get("recovery_policy") or {}).get("authorities") or [])
        if not authorities: raise RuntimeError("no recovery authority configured")
        recovery_id=str(authorities[0]); recovery_method=self._method(manifest,recovery_id)
        if not recovery_method or recovery_method.get("status")!="active" or "recovery" not in set(recovery_method.get("purpose") or []): raise RuntimeError("active recovery authority unavailable")
        recovery_key=Ed25519PrivateKey.from_private_bytes(self._read_private_key_bytes(entity_id,recovery_id))
        old_id=str(manifest["active_signing_key_id"]); now=int(time.time()*1000); revision=int(manifest.get("manifest_revision",1))+1
        new_key=Ed25519PrivateKey.generate(); new_id="sig-"+secrets.token_hex(8); new_pub=_b64(_public_raw(new_key))
        data={k:v for k,v in manifest.items() if k not in {"signature","rotation_proof","recovery_proof"}}
        methods=[]
        for item in data.get("verification_methods") or []:
            item=dict(item)
            if item.get("key_id")==old_id: item["status"]="revoked"; item["revoked_at_ms"]=now
            methods.append(item)
        methods.append({"key_id":new_id,"algorithm":"Ed25519","suite":SIG_SUITE,"purpose":["assertion","authentication","contract"],"public_key":new_pub,"status":"active","created_at_ms":now})
        data["verification_methods"]=methods; data["active_signing_key_id"]=new_id; data["manifest_revision"]=revision; data["previous_manifest_sha256"]=hashlib.sha256(canonical_json(manifest)).hexdigest()
        proof={"entity_id":entity_id,"recovery_key_id":recovery_id,"replaced_key_id":old_id,"new_key_id":new_id,"new_public_key":new_pub,"new_suite":SIG_SUITE,"manifest_revision":revision}
        proof["signature"]={"key_id":recovery_id,"suite":SIG_SUITE,"signature":_b64(recovery_key.sign(canonical_json(proof)))}
        data["recovery_proof"]=proof
        signed=dict(data,signature={"key_id":new_id,"suite":SIG_SUITE,"signature":_b64(new_key.sign(canonical_json(data)))})
        self._write_private(self._entity_key_dir(entity_id)/f"{new_id}.key",_private_raw(new_key)); self._manifest_path(entity_id).write_text(json.dumps(signed,indent=2,sort_keys=True),encoding="utf-8")
        if not self.verify_manifest(signed): raise RuntimeError("recovered manifest failed verification")
        return signed


    def hardware_protect_key(self, entity_id: str, key_id: str, protector=None) -> dict:
        protector=protector or self.key_protector
        if protector is None: raise RuntimeError("hardware key protector required")
        kd=self._entity_key_dir(entity_id); raw_path=kd/f"{key_id}.key"; wrapped_path=kd/f"{key_id}.key.tpm"
        if wrapped_path.is_file() and not raw_path.is_file(): return {"entity_id":entity_id,"key_id":key_id,"hardware_protected":True,"wrapped_path":str(wrapped_path)}
        if not raw_path.is_file(): raise FileNotFoundError(str(raw_path))
        raw=raw_path.read_bytes(); wrapped=protector.wrap(raw)
        if protector.unwrap(wrapped)!=raw: raise RuntimeError("TPM key protection round-trip failed")
        self._write_private(wrapped_path,wrapped); raw_path.unlink()
        return {"entity_id":entity_id,"key_id":key_id,"hardware_protected":True,"wrapped_path":str(wrapped_path),"raw_private_key_removed":True}

    def hardware_protect_recovery(self, entity_id: str, protector=None) -> list[dict]:
        manifest=self.load_manifest(entity_id); authorities=list((manifest.get("recovery_policy") or {}).get("authorities") or [])
        if not authorities: raise RuntimeError("no recovery authority configured")
        return [self.hardware_protect_key(entity_id,str(k),protector) for k in authorities]

    def pairwise_id(self, entity_id: str, relationship: str) -> str:
        relationship = str(relationship or "").strip().lower()
        if not relationship or len(relationship) > 512:
            raise ValueError("relationship identifier required")
        secret_path=self.pairwise / f"{entity_id}.secret"
        if not secret_path.exists(): self._write_private(secret_path,secrets.token_bytes(32))
        secret = secret_path.read_bytes()
        digest = hmac.new(secret, relationship.encode("utf-8"), hashlib.sha256).digest()
        return "rel1-" + _b32(digest)

    @classmethod
    def verify_signature(cls, manifest: dict, payload: Any, signature_record: dict) -> bool:
        try:
            if not cls.verify_manifest(manifest) or signature_record.get("entity_id") != manifest.get("entity_id"):
                return False
            body = canonical_json(payload); payload_hash = hashlib.sha256(body).hexdigest()
            if signature_record.get("payload_sha256") != payload_hash: return False
            record_schema = signature_record.get("signature_schema")
            if record_schema == "entity-signature-record-v2":
                signed_record={"signature_schema":record_schema,"entity_id":signature_record.get("entity_id"),
                               "key_id":signature_record.get("key_id"),"suite":signature_record.get("suite"),
                               "signed_at_ms":signature_record.get("signed_at_ms"),"payload_sha256":payload_hash}
                signed_bytes=canonical_json(signed_record)
            elif record_schema in {None,""}:
                signed_bytes=body
            else: return False
            if manifest.get("schema") == "sovereign-entity-manifest-v1":
                public_raw = _unb64(str(manifest["public_key"]))
            else:
                method = cls._method(manifest, str(signature_record.get("key_id") or ""))
                if not method or method.get("status") not in {"active","retired","revoked"} or method.get("suite") != signature_record.get("suite"): return False
                if method.get("status") == "revoked":
                    if record_schema != "entity-signature-record-v2": return False
                    signed_at=signature_record.get("signed_at_ms"); revoked_at=method.get("revoked_at_ms")
                    if signed_at is None or revoked_at is None or int(signed_at) > int(revoked_at): return False
                public_raw = _unb64(str(method["public_key"]))
            Ed25519PublicKey.from_public_bytes(public_raw).verify(_unb64(str(signature_record["signature"])), signed_bytes)
            return True
        except Exception:
            return False

    def list_local(self) -> list[dict]:
        out = []
        for path in sorted(self.manifests.glob("ent*.json")):
            try: out.append(self.load_manifest(path.stem))
            except Exception: continue
        return out

    def status(self) -> dict:
        return {"ready": True, "local_entity_count": len(self.list_local()), "identity_root": str(self.root), "default_schema": "sovereign-entity-manifest-v2", "root_id_key_derived": False, "pairwise_identities": True, "crypto_suite": SIG_SUITE}
