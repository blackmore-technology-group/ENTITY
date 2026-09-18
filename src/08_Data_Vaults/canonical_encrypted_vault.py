from __future__ import annotations
from pathlib import Path
from threading import RLock
from contextlib import contextmanager
import base64, hashlib, json, os, secrets, sqlite3, time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT_STATES={"ACTIVE","LOCAL_DELETED","CRYPTOGRAPHICALLY_ERASED","REMOTE_DELETION_REQUESTED","REMOTE_DELETION_ATTESTED","REMOTE_DELETION_UNVERIFIED","RETENTION_LEGALLY_REQUIRED"}


def _now() -> int:
    return int(time.time()*1000)


def _b64(v: bytes) -> str:
    return base64.urlsafe_b64encode(v).decode("ascii").rstrip("=")


def _unb64(v: str) -> bytes:
    return base64.urlsafe_b64decode(v + "="*(-len(v)%4))


def _id(prefix: str) -> str:
    return f"{prefix}-"+secrets.token_hex(20)


class EncryptedDataVault:
    """Owner-controlled encrypted content store; ledger/state contains metadata, never plaintext."""
    def __init__(self,state_dir: str|Path):
        self.root=Path(state_dir)/"vault"
        self.objects=self.root/"objects"; self.keys=self.root/"keys"
        self.objects.mkdir(parents=True,exist_ok=True); self.keys.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"vault.sqlite"; self._lock=RLock(); self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS objects(vault_object_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,content_sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,media_type TEXT NOT NULL,classification TEXT NOT NULL,state TEXT NOT NULL,cipher_path TEXT NOT NULL,key_path TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_vault_controller ON objects(controller_entity_id,state)")

    @staticmethod
    def _write_secret(path: Path, data: bytes) -> None:
        path.write_bytes(data)
        try: os.chmod(path,0o600)
        except OSError: pass

    def put_bytes(self,controller_entity_id: str,data: bytes,*,media_type: str="application/octet-stream",classification: str="PRIVATE",metadata: dict|None=None) -> dict:
        if not isinstance(data,(bytes,bytearray)): raise TypeError("vault data must be bytes")
        raw=bytes(data); object_id=_id("vobj1"); key=AESGCM.generate_key(bit_length=256); nonce=secrets.token_bytes(12)
        aad=json.dumps({"vault_object_id":object_id,"controller_entity_id":controller_entity_id},sort_keys=True,separators=(",",":")).encode()
        ciphertext=nonce+AESGCM(key).encrypt(nonce,raw,aad)
        cipher_path=self.objects/f"{object_id}.bin"; key_path=self.keys/f"{object_id}.key"
        cipher_path.write_bytes(ciphertext); self._write_secret(key_path,key)
        now=_now(); digest=hashlib.sha256(raw).hexdigest(); classification=str(classification or "PRIVATE").upper()
        with self._lock,self._connect() as db:
            db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(object_id,controller_entity_id,digest,len(raw),str(media_type)[:256],classification,"ACTIVE",str(cipher_path.relative_to(self.root)),str(key_path.relative_to(self.root)),json.dumps(dict(metadata or {}),sort_keys=True),now,now))
        return {"vault_object_id":object_id,"controller_entity_id":controller_entity_id,"content_sha256":digest,"size_bytes":len(raw),"media_type":str(media_type),"classification":classification,"state":"ACTIVE","plaintext_on_ledger":False}

    def put_file(self,controller_entity_id: str,path: str|Path,**kwargs) -> dict:
        target=Path(path).resolve()
        if not target.is_file(): raise FileNotFoundError(str(target))
        meta=dict(kwargs.pop("metadata",{}) or {}); meta.setdefault("source_filename",target.name)
        return self.put_bytes(controller_entity_id,target.read_bytes(),metadata=meta,**kwargs)

    def _row(self,object_id: str):
        with self._connect() as db: return db.execute("SELECT * FROM objects WHERE vault_object_id=?",(object_id,)).fetchone()

    def metadata(self,object_id: str) -> dict|None:
        row=self._row(object_id)
        if not row: return None
        out=dict(row); out.pop("cipher_path",None); out.pop("key_path",None); out["metadata"]=json.loads(out.pop("metadata_json")); return out

    def _storage_path(self,stored: str,kind: str) -> Path:
        raw=Path(str(stored))
        if not raw.is_absolute(): return self.root/raw
        if raw.exists(): return raw
        base=self.keys if kind=="key" else self.objects
        return base/raw.name

    def read_bytes(self,controller_entity_id: str,object_id: str) -> bytes:
        row=self._row(object_id)
        if not row: raise KeyError("vault object not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("vault object controller mismatch")
        if row["state"]!="ACTIVE": raise PermissionError(f"vault object unavailable: {row['state']}")
        key_path=self._storage_path(row["key_path"],"key"); cipher_path=self._storage_path(row["cipher_path"],"cipher")
        if not key_path.exists(): raise RuntimeError("vault encryption key unavailable")
        blob=cipher_path.read_bytes(); nonce,ciphertext=blob[:12],blob[12:]
        aad=json.dumps({"vault_object_id":object_id,"controller_entity_id":controller_entity_id},sort_keys=True,separators=(",",":")).encode()
        plain=AESGCM(key_path.read_bytes()).decrypt(nonce,ciphertext,aad)
        if hashlib.sha256(plain).hexdigest()!=row["content_sha256"]: raise RuntimeError("vault plaintext commitment mismatch")
        return plain

    def lifecycle(self,controller_entity_id: str,object_id: str,state: str) -> dict:
        state=str(state or "").upper()
        if state not in VAULT_STATES: raise ValueError("invalid vault lifecycle state")
        row=self._row(object_id)
        if not row: raise KeyError("vault object not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("vault object controller mismatch")
        if state=="CRYPTOGRAPHICALLY_ERASED":
            kp=self._storage_path(row["key_path"],"key")
            if kp.exists(): kp.unlink()
        if state=="LOCAL_DELETED":
            cp=self._storage_path(row["cipher_path"],"cipher")
            if cp.exists(): cp.unlink()
        with self._connect() as db: db.execute("UPDATE objects SET state=?,updated_at_ms=? WHERE vault_object_id=?",(state,_now(),object_id))
        return {"vault_object_id":object_id,"state":state,"remote_deletion_verified":state=="REMOTE_DELETION_ATTESTED"}

    def export_manifest(self,controller_entity_id: str) -> dict:
        with self._connect() as db: rows=db.execute("SELECT * FROM objects WHERE controller_entity_id=? ORDER BY created_at_ms",(controller_entity_id,)).fetchall()
        return {"schema":"entity-vault-manifest-v1","controller_entity_id":controller_entity_id,"objects":[self.metadata(r["vault_object_id"]) for r in rows]}

    def status(self) -> dict:
        with self._connect() as db: count=db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
        return {"ready":True,"encrypted_at_rest":True,"cipher":"AES-256-GCM","per_object_keys":True,"object_count":int(count),"raw_content_on_ledger":False,"database":str(self.path)}
