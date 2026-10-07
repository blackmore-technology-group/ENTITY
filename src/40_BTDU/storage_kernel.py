from __future__ import annotations

"""BTDU primary payload storage kernel.

One authoritative payload. Unlimited semantic views.

The kernel stores exact payload bytes once in append-only, content-addressed segment
records. Object manifests are immutable canonical sidecars. SQLite is a rebuildable
index, never the sole source of payload truth. ENTITY/ADAM store only compact payload
identity and governance/semantic relationships, not duplicate raw payload bytes.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Iterator
import hashlib
import json
import lzma
import os
import sqlite3
import struct
import threading
import time
import uuid
import zlib

STORAGE_SCHEMA = "entity-btdu-storage-kernel-v1"
PAYLOAD_SCHEMA = "entity-btdu-authoritative-payload-v1"
STORAGE_VERSION = "1.0.0"

_MAGIC = b"BTDUCH01"
_HEADER = struct.Struct(">8s32sQQBBBBI12s")
_CODEC_RAW = 0
_CODEC_ZLIB = 1
_CODEC_LZMA = 2
_CIPHER_NONE = 0
_CIPHER_AES256_GCM = 1

_GEAR = [
    int.from_bytes(hashlib.sha256(f"BTDU-STORAGE-GEAR-{i}".encode("ascii")).digest()[:8], "big")
    for i in range(256)
]


class BTDUStorageError(RuntimeError):
    pass


class BTDUStorageIntegrityError(BTDUStorageError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _merkle_root(chunks: list[tuple[str, int]]) -> str:
    if not chunks:
        return hashlib.sha256(b"").hexdigest()
    level = [
        hashlib.sha256(bytes.fromhex(digest) + int(length).to_bytes(8, "big")).digest()
        for digest, length in chunks
    ]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            nxt.append(hashlib.sha256(left + right).digest())
        level = nxt
    return level[0].hex()


class _InterprocessLock:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a+b")
        self._fh.seek(0, os.SEEK_END)
        if self._fh.tell() == 0:
            self._fh.write(b"\0")
            self._fh.flush()
        self._fh.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fh is not None:
            try:
                self._fh.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None


class BTDUStorageKernel:
    def __init__(
        self,
        root: str | Path,
        *,
        min_chunk: int = 256 * 1024,
        avg_chunk: int = 1024 * 1024,
        max_chunk: int = 4 * 1024 * 1024,
        target_segment_bytes: int = 1024 * 1024 * 1024,
        compression: bool = True,
        encryption_key: bytes | None = None,
    ):
        if min_chunk < 4096 or not (min_chunk <= avg_chunk <= max_chunk):
            raise ValueError("chunk sizes must satisfy 4096 <= min <= avg <= max")
        if avg_chunk & (avg_chunk - 1):
            raise ValueError("avg_chunk must be a power of two")
        if target_segment_bytes < max_chunk + _HEADER.size:
            raise ValueError("target_segment_bytes is too small")
        if encryption_key is not None and len(encryption_key) != 32:
            raise ValueError("BTDU storage encryption key must be exactly 32 bytes")

        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.segments_dir = self.root / "segments"
        self.manifests_dir = self.root / "manifests"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "storage.sqlite"
        self.lock_path = self.root / "storage.lock"
        self.min_chunk = int(min_chunk)
        self.avg_chunk = int(avg_chunk)
        self.max_chunk = int(max_chunk)
        self.target_segment_bytes = int(target_segment_bytes)
        self.compression = bool(compression)
        self.encryption_key = encryption_key
        self._thread_lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=30.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_db(self) -> None:
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS storage_metadata(
                  key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS segments(
                  segment_id INTEGER PRIMARY KEY,path TEXT NOT NULL UNIQUE,
                  bytes INTEGER NOT NULL,sealed INTEGER NOT NULL DEFAULT 0,
                  created_at_ms INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks(
                  chunk_sha256 TEXT PRIMARY KEY,segment_id INTEGER NOT NULL,
                  record_offset INTEGER NOT NULL,record_bytes INTEGER NOT NULL,
                  raw_bytes INTEGER NOT NULL,stored_bytes INTEGER NOT NULL,
                  codec INTEGER NOT NULL,cipher INTEGER NOT NULL,
                  crc32 INTEGER NOT NULL,ref_count INTEGER NOT NULL DEFAULT 0,
                  created_at_ms INTEGER NOT NULL,
                  FOREIGN KEY(segment_id) REFERENCES segments(segment_id));
                CREATE TABLE IF NOT EXISTS chunk_references(
                  ref_id TEXT NOT NULL,chunk_sha256 TEXT NOT NULL,ref_kind TEXT NOT NULL,
                  created_at_ms INTEGER NOT NULL,
                  PRIMARY KEY(ref_id,chunk_sha256),
                  FOREIGN KEY(chunk_sha256) REFERENCES chunks(chunk_sha256));
                CREATE INDEX IF NOT EXISTS idx_chunk_references_chunk
                  ON chunk_references(chunk_sha256);
                CREATE TABLE IF NOT EXISTS payloads(
                  storage_object_id TEXT PRIMARY KEY,content_sha256 TEXT NOT NULL UNIQUE,
                  size_bytes INTEGER NOT NULL,chunk_count INTEGER NOT NULL,
                  merkle_root TEXT NOT NULL,manifest_sha256 TEXT NOT NULL UNIQUE,
                  manifest_path TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS payload_chunks(
                  storage_object_id TEXT NOT NULL,ordinal INTEGER NOT NULL,
                  chunk_sha256 TEXT NOT NULL,logical_offset INTEGER NOT NULL,
                  raw_bytes INTEGER NOT NULL,
                  PRIMARY KEY(storage_object_id,ordinal),
                  FOREIGN KEY(storage_object_id) REFERENCES payloads(storage_object_id) ON DELETE CASCADE,
                  FOREIGN KEY(chunk_sha256) REFERENCES chunks(chunk_sha256));
                CREATE INDEX IF NOT EXISTS idx_payload_chunks_range
                  ON payload_chunks(storage_object_id,logical_offset);
                CREATE INDEX IF NOT EXISTS idx_chunks_segment
                  ON chunks(segment_id,record_offset);
                """
            )
            db.execute(
                "INSERT OR REPLACE INTO storage_metadata VALUES(?,?)",
                (
                    "contract",
                    json.dumps(
                        {
                            "schema": STORAGE_SCHEMA,
                            "version": STORAGE_VERSION,
                            "one_authoritative_payload": True,
                            "sqlite_is_rebuildable_index": True,
                            "segment_records_are_content_addressed": True,
                        },
                        sort_keys=True,
                    ),
                ),
            )

    def _iter_cdc(self, parts: Iterable[bytes]) -> Iterator[bytes]:
        mask = self.avg_chunk - 1
        buf = bytearray()
        rolling = 0
        for part in parts:
            if not isinstance(part, (bytes, bytearray, memoryview)):
                raise TypeError("payload iterator must yield bytes-like objects")
            for byte in bytes(part):
                buf.append(byte)
                rolling = ((rolling << 1) + _GEAR[byte]) & 0xFFFFFFFFFFFFFFFF
                n = len(buf)
                if n >= self.min_chunk and ((rolling & mask) == 0 or n >= self.max_chunk):
                    yield bytes(buf)
                    buf.clear()
                    rolling = 0
        if buf:
            yield bytes(buf)

    @staticmethod
    def _file_parts(fh: BinaryIO, read_size: int = 1024 * 1024) -> Iterator[bytes]:
        while True:
            block = fh.read(read_size)
            if not block:
                break
            yield block

    def _encode_chunk(self, raw: bytes) -> tuple[bytes, int, int, bytes]:
        payload = raw
        codec = _CODEC_RAW
        if self.compression and len(raw) >= 4096:
            # Zlib is the cheap compressibility probe. Do not invoke LZMA for
            # high-entropy chunks: doing so wastes CPU/RAM while providing no
            # useful reduction. For compressible chunks, compare against a
            # bounded-memory LZMA preset and retain the smaller representation.
            z_payload = zlib.compress(raw, level=6)
            if len(z_payload) + 32 < int(len(raw) * 0.94):
                payload = z_payload
                codec = _CODEC_ZLIB
                x_payload = lzma.compress(raw, format=lzma.FORMAT_XZ, preset=3)
                if len(x_payload) < len(payload):
                    payload = x_payload
                    codec = _CODEC_LZMA

        cipher = _CIPHER_NONE
        nonce = b"\0" * 12
        if self.encryption_key is not None:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = os.urandom(12)
            payload = AESGCM(self.encryption_key).encrypt(nonce, payload, None)
            cipher = _CIPHER_AES256_GCM
        return payload, codec, cipher, nonce

    def _decode_chunk(
        self, payload: bytes, *, codec: int, cipher: int, nonce: bytes, expected_raw: int
    ) -> bytes:
        data = payload
        if cipher == _CIPHER_AES256_GCM:
            if self.encryption_key is None:
                raise BTDUStorageIntegrityError("encrypted chunk requires storage key")
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            try:
                data = AESGCM(self.encryption_key).decrypt(nonce, data, None)
            except Exception as exc:
                raise BTDUStorageIntegrityError("chunk decryption/authentication failed") from exc
        elif cipher != _CIPHER_NONE:
            raise BTDUStorageIntegrityError(f"unsupported BTDU cipher {cipher}")

        if codec == _CODEC_ZLIB:
            try:
                data = zlib.decompress(data)
            except Exception as exc:
                raise BTDUStorageIntegrityError("zlib chunk decompression failed") from exc
        elif codec == _CODEC_LZMA:
            try:
                data = lzma.decompress(data)
            except Exception as exc:
                raise BTDUStorageIntegrityError("lzma chunk decompression failed") from exc
        elif codec != _CODEC_RAW:
            raise BTDUStorageIntegrityError(f"unsupported BTDU codec {codec}")

        if len(data) != int(expected_raw):
            raise BTDUStorageIntegrityError("chunk raw length mismatch")
        return data

    def _select_segment(self, db: sqlite3.Connection, required_bytes: int) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM segments WHERE sealed=0 ORDER BY segment_id DESC LIMIT 1"
        ).fetchone()
        if row is not None and int(row["bytes"]) + int(required_bytes) <= self.target_segment_bytes:
            return row
        if row is not None:
            db.execute("UPDATE segments SET sealed=1 WHERE segment_id=?", (int(row["segment_id"]),))
        next_id = int(
            db.execute("SELECT COALESCE(MAX(segment_id),0)+1 FROM segments").fetchone()[0]
        )
        rel = f"segments/segment-{next_id:08d}.btdu"
        db.execute(
            "INSERT INTO segments(segment_id,path,bytes,sealed,created_at_ms) VALUES(?,?,?,?,?)",
            (next_id, rel, 0, 0, _now_ms()),
        )
        return db.execute("SELECT * FROM segments WHERE segment_id=?", (next_id,)).fetchone()

    def _ensure_chunk(self, raw: bytes) -> str:
        digest = _sha256_bytes(raw)
        with self._thread_lock, _InterprocessLock(self.lock_path):
            with self._db() as db:
                if db.execute(
                    "SELECT 1 FROM chunks WHERE chunk_sha256=?", (digest,)
                ).fetchone():
                    return digest

                stored, codec, cipher, nonce = self._encode_chunk(raw)
                crc = zlib.crc32(stored) & 0xFFFFFFFF
                record_bytes = _HEADER.size + len(stored)
                segment = self._select_segment(db, record_bytes)
                seg_path = self.root / str(segment["path"])
                seg_path.parent.mkdir(parents=True, exist_ok=True)
                offset = seg_path.stat().st_size if seg_path.exists() else 0
                header = _HEADER.pack(
                    _MAGIC,
                    bytes.fromhex(digest),
                    len(raw),
                    len(stored),
                    codec,
                    cipher,
                    12 if cipher else 0,
                    0,
                    crc,
                    nonce,
                )
                with seg_path.open("ab", buffering=0) as fh:
                    fh.write(header)
                    fh.write(stored)
                    fh.flush()
                    os.fsync(fh.fileno())
                actual_size = seg_path.stat().st_size
                if actual_size != offset + record_bytes:
                    raise BTDUStorageIntegrityError("segment append length mismatch")
                db.execute(
                    """INSERT INTO chunks(
                    chunk_sha256,segment_id,record_offset,record_bytes,raw_bytes,stored_bytes,
                    codec,cipher,crc32,ref_count,created_at_ms)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        digest,
                        int(segment["segment_id"]),
                        offset,
                        record_bytes,
                        len(raw),
                        len(stored),
                        codec,
                        cipher,
                        crc,
                        0,
                        _now_ms(),
                    ),
                )
                db.execute(
                    "UPDATE segments SET bytes=? WHERE segment_id=?",
                    (actual_size, int(segment["segment_id"])),
                )
        return digest

    def _manifest_path(self, content_sha256: str) -> Path:
        return self.manifests_dir / content_sha256[:2] / f"{content_sha256}.json"

    def _write_manifest(self, manifest: dict[str, Any]) -> tuple[Path, str]:
        canonical = _canon(manifest)
        manifest_sha = _sha256_bytes(canonical)
        path = self._manifest_path(str(manifest["content_sha256"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            current = path.read_bytes()
            if current != canonical:
                raise BTDUStorageIntegrityError("payload manifest collision")
            return path, manifest_sha
        tmp = path.with_name(path.name + f".tmp-{uuid.uuid4().hex}")
        with tmp.open("wb") as fh:
            fh.write(canonical)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return path, manifest_sha

    def put_iterable(self, parts: Iterable[bytes]) -> dict[str, Any]:
        content = hashlib.sha256()
        ordered: list[tuple[str, int, int]] = []
        logical_offset = 0
        for chunk in self._iter_cdc(parts):
            content.update(chunk)
            digest = self._ensure_chunk(chunk)
            ordered.append((digest, len(chunk), logical_offset))
            logical_offset += len(chunk)

        content_sha = content.hexdigest()
        storage_object_id = "btdu-payload:" + content_sha
        chunk_pairs = [(digest, raw_bytes) for digest, raw_bytes, _ in ordered]
        manifest = {
            "schema": PAYLOAD_SCHEMA,
            "storage_version": STORAGE_VERSION,
            "storage_object_id": storage_object_id,
            "content_sha256": content_sha,
            "size_bytes": logical_offset,
            "chunk_count": len(ordered),
            "merkle_root": _merkle_root(chunk_pairs),
            "chunks": [
                {
                    "ordinal": i,
                    "chunk_sha256": digest,
                    "logical_offset": offset,
                    "raw_bytes": raw_bytes,
                }
                for i, (digest, raw_bytes, offset) in enumerate(ordered)
            ],
        }
        manifest_path, manifest_sha = self._write_manifest(manifest)

        with self._thread_lock, _InterprocessLock(self.lock_path):
            with self._db() as db:
                existing = db.execute(
                    "SELECT * FROM payloads WHERE storage_object_id=?", (storage_object_id,)
                ).fetchone()
                if existing is None:
                    db.execute(
                        """INSERT INTO payloads(
                        storage_object_id,content_sha256,size_bytes,chunk_count,merkle_root,
                        manifest_sha256,manifest_path,created_at_ms)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            storage_object_id,
                            content_sha,
                            logical_offset,
                            len(ordered),
                            manifest["merkle_root"],
                            manifest_sha,
                            str(manifest_path.relative_to(self.root)).replace("\\", "/"),
                            _now_ms(),
                        ),
                    )
                    db.executemany(
                        """INSERT INTO payload_chunks(
                        storage_object_id,ordinal,chunk_sha256,logical_offset,raw_bytes)
                        VALUES(?,?,?,?,?)""",
                        [
                            (storage_object_id, i, digest, offset, raw_bytes)
                            for i, (digest, raw_bytes, offset) in enumerate(ordered)
                        ],
                    )
                    for digest, _, _ in ordered:
                        db.execute(
                            "UPDATE chunks SET ref_count=ref_count+1 WHERE chunk_sha256=?",
                            (digest,),
                        )
                else:
                    if (
                        str(existing["content_sha256"]) != content_sha
                        or str(existing["manifest_sha256"]) != manifest_sha
                    ):
                        raise BTDUStorageIntegrityError("payload identity collision")

        return dict(manifest, manifest_sha256=manifest_sha)

    def retain_chunk(self, chunk_sha256: str, *, ref_id: str, ref_kind: str) -> bool:
        """Idempotently retain a chunk for a named BTDU structure.

        Reference identity prevents retries/restarts from inflating ref_count.
        """
        digest = str(chunk_sha256)
        with self._thread_lock, _InterprocessLock(self.lock_path):
            with self._db() as db:
                if not db.execute(
                    "SELECT 1 FROM chunks WHERE chunk_sha256=?", (digest,)
                ).fetchone():
                    raise KeyError(digest)
                cur = db.execute(
                    """INSERT OR IGNORE INTO chunk_references(
                    ref_id,chunk_sha256,ref_kind,created_at_ms) VALUES(?,?,?,?)""",
                    (str(ref_id), digest, str(ref_kind), _now_ms()),
                )
                inserted = int(cur.rowcount or 0) > 0
                if inserted:
                    db.execute(
                        "UPDATE chunks SET ref_count=ref_count+1 WHERE chunk_sha256=?",
                        (digest,),
                    )
        return inserted

    def retain_references(
        self, references: Iterable[tuple[str, str, str]]
    ) -> dict[str, Any]:
        """Idempotently retain many chunks in one durable transaction."""
        added = 0
        checked = 0
        with self._thread_lock, _InterprocessLock(self.lock_path):
            with self._db() as db:
                for ref_id, chunk_sha256, ref_kind in references:
                    checked += 1
                    digest = str(chunk_sha256)
                    if not db.execute(
                        "SELECT 1 FROM chunks WHERE chunk_sha256=?", (digest,)
                    ).fetchone():
                        raise KeyError(digest)
                    cur = db.execute(
                        """INSERT OR IGNORE INTO chunk_references(
                        ref_id,chunk_sha256,ref_kind,created_at_ms) VALUES(?,?,?,?)""",
                        (str(ref_id), digest, str(ref_kind), _now_ms()),
                    )
                    if int(cur.rowcount or 0) > 0:
                        db.execute(
                            "UPDATE chunks SET ref_count=ref_count+1 WHERE chunk_sha256=?",
                            (digest,),
                        )
                        added += 1
        return {"checked": checked, "added": added}

    def release_reference(self, ref_id: str) -> dict[str, Any]:
        """Release all chunk references owned by a BTDU structure."""
        released = 0
        with self._thread_lock, _InterprocessLock(self.lock_path):
            with self._db() as db:
                rows = db.execute(
                    "SELECT chunk_sha256 FROM chunk_references WHERE ref_id=?",
                    (str(ref_id),),
                ).fetchall()
                for row in rows:
                    db.execute(
                        "UPDATE chunks SET ref_count=MAX(0,ref_count-1) WHERE chunk_sha256=?",
                        (str(row["chunk_sha256"]),),
                    )
                    released += 1
                db.execute("DELETE FROM chunk_references WHERE ref_id=?", (str(ref_id),))
        return {"ref_id": str(ref_id), "released_chunks": released}

    def put_literal_atom_tape(self, data: bytes) -> dict[str, Any]:
        """Store one irreducible atom tape in the content-addressed entropy reservoir.

        Each byte is the canonical ID of one of BTDU's 256 primitive byte atoms.
        This is not an object/file record; it is only the entropy BTDU could not
        derive from already-shared formula structure.
        """
        raw = bytes(data)
        digest = self._ensure_chunk(raw)
        row = self._chunk_row(digest)
        return {
            "schema": "entity-btdu-literal-atom-tape-v1",
            "literal_sha256": digest,
            "atom_count": len(raw),
            "stored_bytes": int(row["stored_bytes"]),
            "codec": int(row["codec"]),
            "cipher": int(row["cipher"]),
        }

    def read_literal_atom_tape(self, literal_sha256: str) -> bytes:
        return self.read_chunk(str(literal_sha256))

    def put_atom_tape_iterable(
        self, parts: Iterable[bytes], *, recipe_ref: str | None = None,
        content_defined: bool = True
    ) -> dict[str, Any]:
        """Formulate arbitrary bytes as an ordered recipe over primitive atom tapes.

        Unlike put_iterable(), this creates no conventional payload object or payload
        manifest. The only durable byte-bearing state is the deduplicated entropy
        chunks; the returned recipe is sufficient to reconstruct the exact sequence.
        """
        h = hashlib.sha256()
        size = 0
        chunks: list[dict[str, Any]] = []
        units = self._iter_cdc(parts) if content_defined else (
            bytes(part) for part in parts if part
        )
        for ordinal, raw in enumerate(units):
            h.update(raw)
            digest = self._ensure_chunk(raw)
            chunks.append(
                {
                    "ordinal": ordinal,
                    "chunk_sha256": digest,
                    "atom_count": len(raw),
                }
            )
            size += len(raw)
        content_sha = h.hexdigest()
        ref_id = str(recipe_ref or ("btdu-atom-tape-recipe:" + content_sha))
        unique = sorted({str(row["chunk_sha256"]) for row in chunks})
        self.retain_references(
            (ref_id, digest, "ATOM_TAPE_RECIPE") for digest in unique
        )
        return {
            "schema": "entity-btdu-atom-tape-recipe-v1",
            "recipe_ref": ref_id,
            "content_sha256": content_sha,
            "size_bytes": size,
            "chunk_count": len(chunks),
            "chunks": chunks,
            "conventional_payload_object_created": False,
            "primitive_atom_universe_size": 256,
            "chunking": "content-defined" if content_defined else "fixed-stream-blocks",
        }

    def put_atom_tape_path(
        self, path: str | Path, *, recipe_ref: str | None = None,
        content_defined: bool = True, read_size: int = 1024 * 1024
    ) -> dict[str, Any]:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(str(p))
        with p.open("rb") as fh:
            return self.put_atom_tape_iterable(
                self._file_parts(fh, read_size=read_size), recipe_ref=recipe_ref,
                content_defined=content_defined
            )

    def iter_atom_tape_recipe(self, recipe: dict[str, Any]) -> Iterator[bytes]:
        if str(recipe.get("schema")) != "entity-btdu-atom-tape-recipe-v1":
            raise BTDUStorageIntegrityError("unsupported atom tape recipe schema")
        h = hashlib.sha256()
        total = 0
        for expected_ordinal, row in enumerate(recipe.get("chunks", [])):
            if int(row.get("ordinal", -1)) != expected_ordinal:
                raise BTDUStorageIntegrityError("atom tape recipe ordinal mismatch")
            raw = self.read_chunk(str(row["chunk_sha256"]))
            if len(raw) != int(row["atom_count"]):
                raise BTDUStorageIntegrityError("atom tape chunk length mismatch")
            h.update(raw)
            total += len(raw)
            yield raw
        if total != int(recipe.get("size_bytes", -1)):
            raise BTDUStorageIntegrityError("atom tape recipe size mismatch")
        if h.hexdigest() != str(recipe.get("content_sha256")):
            raise BTDUStorageIntegrityError("atom tape recipe hash mismatch")

    def materialize_atom_tape_recipe(
        self, recipe: dict[str, Any], output_path: str | Path
    ) -> dict[str, Any]:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.parent / (".btdu-" + hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:16] + ".tmp")
        h = hashlib.sha256()
        total = 0
        with tmp.open("wb") as fh:
            for raw in self.iter_atom_tape_recipe(recipe):
                fh.write(raw)
                h.update(raw)
                total += len(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        return {
            "schema": "entity-btdu-atom-tape-materialization-v1",
            "path": str(target),
            "bytes": total,
            "sha256": h.hexdigest(),
            "temporary_materialization": True,
        }

    def put_bytes(self, data: bytes) -> dict[str, Any]:
        raw = bytes(data)
        return self.put_iterable((raw,))

    def put_path(self, path: str | Path) -> dict[str, Any]:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(str(p))
        with p.open("rb") as fh:
            return self.put_iterable(self._file_parts(fh))

    def _chunk_row(self, chunk_sha256: str) -> sqlite3.Row:
        with self._db() as db:
            row = db.execute(
                """SELECT c.*,s.path FROM chunks c JOIN segments s ON s.segment_id=c.segment_id
                WHERE c.chunk_sha256=?""",
                (str(chunk_sha256),),
            ).fetchone()
        if row is None:
            raise KeyError(chunk_sha256)
        return row

    def read_chunk(self, chunk_sha256: str) -> bytes:
        row = self._chunk_row(chunk_sha256)
        path = self.root / str(row["path"])
        with path.open("rb") as fh:
            fh.seek(int(row["record_offset"]))
            header = fh.read(_HEADER.size)
            if len(header) != _HEADER.size:
                raise BTDUStorageIntegrityError("truncated BTDU segment header")
            magic, digest, raw_n, stored_n, codec, cipher, nonce_len, _, crc, nonce = _HEADER.unpack(header)
            if magic != _MAGIC or digest.hex() != str(row["chunk_sha256"]):
                raise BTDUStorageIntegrityError("BTDU segment chunk identity mismatch")
            payload = fh.read(int(stored_n))
        if len(payload) != int(stored_n):
            raise BTDUStorageIntegrityError("truncated BTDU segment payload")
        if (zlib.crc32(payload) & 0xFFFFFFFF) != int(crc):
            raise BTDUStorageIntegrityError("BTDU stored-chunk CRC mismatch")
        raw = self._decode_chunk(
            payload,
            codec=int(codec),
            cipher=int(cipher),
            nonce=nonce if nonce_len else b"\0" * 12,
            expected_raw=int(raw_n),
        )
        if _sha256_bytes(raw) != str(row["chunk_sha256"]):
            raise BTDUStorageIntegrityError("BTDU raw-chunk SHA-256 mismatch")
        return raw

    def payload_manifest(self, storage_object_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute(
                "SELECT manifest_path,manifest_sha256 FROM payloads WHERE storage_object_id=?",
                (str(storage_object_id),),
            ).fetchone()
        if row is None:
            raise KeyError(storage_object_id)
        path = self.root / str(row["manifest_path"])
        raw = path.read_bytes()
        if _sha256_bytes(raw) != str(row["manifest_sha256"]):
            raise BTDUStorageIntegrityError("payload manifest hash mismatch")
        manifest = json.loads(raw.decode("utf-8"))
        if manifest.get("storage_object_id") != str(storage_object_id):
            raise BTDUStorageIntegrityError("payload manifest object mismatch")
        return manifest

    def iter_payload(self, storage_object_id: str) -> Iterator[bytes]:
        manifest = self.payload_manifest(storage_object_id)
        for row in manifest["chunks"]:
            yield self.read_chunk(str(row["chunk_sha256"]))

    def read_all(self, storage_object_id: str) -> bytes:
        return b"".join(self.iter_payload(storage_object_id))

    def read_range(self, storage_object_id: str, offset: int, length: int) -> bytes:
        offset = int(offset)
        length = int(length)
        if offset < 0 or length < 0:
            raise ValueError("offset and length must be non-negative")
        if length == 0:
            return b""
        manifest = self.payload_manifest(storage_object_id)
        size = int(manifest["size_bytes"])
        if offset >= size:
            return b""
        end = min(size, offset + length)
        out = bytearray()
        for row in manifest["chunks"]:
            start = int(row["logical_offset"])
            stop = start + int(row["raw_bytes"])
            if stop <= offset:
                continue
            if start >= end:
                break
            raw = self.read_chunk(str(row["chunk_sha256"]))
            left = max(0, offset - start)
            right = min(len(raw), end - start)
            out.extend(raw[left:right])
        return bytes(out)

    def materialize(self, storage_object_id: str, output_path: str | Path) -> dict[str, Any]:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + f".tmp-{uuid.uuid4().hex}")
        h = hashlib.sha256()
        size = 0
        with tmp.open("wb") as fh:
            for block in self.iter_payload(storage_object_id):
                fh.write(block)
                h.update(block)
                size += len(block)
            fh.flush()
            os.fsync(fh.fileno())
        manifest = self.payload_manifest(storage_object_id)
        if h.hexdigest() != manifest["content_sha256"] or size != int(manifest["size_bytes"]):
            tmp.unlink(missing_ok=True)
            raise BTDUStorageIntegrityError("materialized payload verification failed")
        os.replace(tmp, target)
        return {
            "storage_object_id": storage_object_id,
            "path": str(target),
            "bytes": size,
            "sha256": h.hexdigest(),
        }

    def verify_payload(self, storage_object_id: str, *, deep: bool = True) -> dict[str, Any]:
        problems: list[str] = []
        manifest = self.payload_manifest(storage_object_id)
        chunks = manifest.get("chunks", [])
        if int(manifest.get("chunk_count", -1)) != len(chunks):
            problems.append("chunk_count")
        if _merkle_root(
            [(str(r["chunk_sha256"]), int(r["raw_bytes"])) for r in chunks]
        ) != str(manifest.get("merkle_root")):
            problems.append("merkle_root")

        content = hashlib.sha256()
        size = 0
        if deep:
            for row in chunks:
                try:
                    raw = self.read_chunk(str(row["chunk_sha256"]))
                    content.update(raw)
                    size += len(raw)
                except Exception:
                    problems.append("chunk:" + str(row.get("chunk_sha256")))
            if size != int(manifest["size_bytes"]):
                problems.append("size")
            if content.hexdigest() != str(manifest["content_sha256"]):
                problems.append("content_sha256")
        return {
            "schema": "entity-btdu-storage-payload-verification-v1",
            "pass": not problems,
            "storage_object_id": str(storage_object_id),
            "deep": bool(deep),
            "problems": problems,
        }

    def stats(self) -> dict[str, Any]:
        with self._db() as db:
            p = db.execute(
                "SELECT count(*) n,COALESCE(sum(size_bytes),0) b FROM payloads"
            ).fetchone()
            c = db.execute(
                """SELECT count(*) n,COALESCE(sum(raw_bytes),0) raw,
                COALESCE(sum(stored_bytes),0) stored,
                COALESCE(sum(CASE WHEN ref_count=0 THEN stored_bytes ELSE 0 END),0) orphan
                FROM chunks"""
            ).fetchone()
            logical = int(
                db.execute("SELECT COALESCE(sum(size_bytes),0) FROM payloads").fetchone()[0]
            )
            segment_bytes = int(
                db.execute("SELECT COALESCE(sum(bytes),0) FROM segments").fetchone()[0]
            )
        unique_raw = int(c["raw"])
        return {
            "schema": "entity-btdu-storage-stats-v1",
            "payloads": int(p["n"]),
            "logical_payload_bytes": logical,
            "unique_chunks": int(c["n"]),
            "unique_raw_chunk_bytes": unique_raw,
            "stored_chunk_bytes": int(c["stored"]),
            "segment_bytes": segment_bytes,
            "orphan_stored_bytes": int(c["orphan"]),
            "dedup_fraction": 0.0 if logical == 0 else max(0.0, 1.0 - unique_raw / logical),
            "physical_reduction_fraction": 0.0 if logical == 0 else 1.0 - int(c["stored"]) / logical,
        }

    def storage_root(self) -> str:
        with self._db() as db:
            rows = [
                tuple(r)
                for r in db.execute(
                    """SELECT storage_object_id,content_sha256,size_bytes,chunk_count,
                    merkle_root,manifest_sha256 FROM payloads ORDER BY storage_object_id"""
                )
            ]
        return _sha256_bytes(_canon({"schema": STORAGE_SCHEMA, "payloads": rows}))

    def snapshot_manifest(self, *, hash_segments: bool = False) -> dict[str, Any]:
        with self._db() as db:
            segments = [dict(r) for r in db.execute("SELECT * FROM segments ORDER BY segment_id")]
            payloads = int(db.execute("SELECT count(*) FROM payloads").fetchone()[0])
        for row in segments:
            path = self.root / str(row["path"])
            row["exists"] = path.is_file()
            row["actual_bytes"] = path.stat().st_size if path.exists() else -1
            if hash_segments and path.exists():
                h = hashlib.sha256()
                with path.open("rb") as fh:
                    for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
                        h.update(block)
                row["sha256"] = h.hexdigest()
        return {
            "schema": "entity-btdu-storage-snapshot-v1",
            "storage_root": self.storage_root(),
            "payloads": payloads,
            "segments": segments,
        }

    def verify(self, *, deep: bool = False) -> dict[str, Any]:
        problems: list[str] = []
        with self._db() as db:
            quick = db.execute("PRAGMA quick_check").fetchone()[0]
            if quick != "ok":
                problems.append("sqlite:" + str(quick))
            dangling = int(
                db.execute(
                    """SELECT count(*) FROM payload_chunks pc
                    LEFT JOIN chunks c ON c.chunk_sha256=pc.chunk_sha256
                    WHERE c.chunk_sha256 IS NULL"""
                ).fetchone()[0]
            )
            if dangling:
                problems.append("dangling_payload_chunks:" + str(dangling))
            segments = [dict(r) for r in db.execute("SELECT * FROM segments")]
            payload_ids = [r[0] for r in db.execute("SELECT storage_object_id FROM payloads")]
        for row in segments:
            path = self.root / str(row["path"])
            if not path.is_file() or path.stat().st_size != int(row["bytes"]):
                problems.append("segment:" + str(row["segment_id"]))
        if deep:
            for payload_id in payload_ids:
                result = self.verify_payload(str(payload_id), deep=True)
                if not result["pass"]:
                    problems.append("payload:" + str(payload_id))
        return {
            "schema": "entity-btdu-storage-verification-v1",
            "pass": not problems,
            "deep": bool(deep),
            "storage_root": self.storage_root(),
            "stats": self.stats(),
            "problems": problems,
        }

    def recover_index(self) -> dict[str, Any]:
        """Rebuild the SQLite index from authoritative segment records and manifests."""
        recovered_chunks = 0
        recovered_payloads = 0
        with self._thread_lock, _InterprocessLock(self.lock_path):
            backup = self.db_path.with_suffix(f".pre-recover-{_now_ms()}.sqlite")
            if self.db_path.exists():
                import shutil
                shutil.copy2(self.db_path, backup)
                self.db_path.unlink()
            for suffix in ("-wal", "-shm"):
                Path(str(self.db_path) + suffix).unlink(missing_ok=True)
            self._init_db()

            with self._db() as db:
                for seg_path in sorted(self.segments_dir.glob("segment-*.btdu")):
                    try:
                        segment_id = int(seg_path.stem.split("-")[-1])
                    except Exception as exc:
                        raise BTDUStorageIntegrityError(f"invalid segment name {seg_path}") from exc
                    db.execute(
                        "INSERT OR REPLACE INTO segments(segment_id,path,bytes,sealed,created_at_ms) VALUES(?,?,?,?,?)",
                        (
                            segment_id,
                            str(seg_path.relative_to(self.root)).replace("\\", "/"),
                            seg_path.stat().st_size,
                            1,
                            int(seg_path.stat().st_mtime * 1000),
                        ),
                    )
                    offset = 0
                    with seg_path.open("rb") as fh:
                        while offset < seg_path.stat().st_size:
                            fh.seek(offset)
                            header = fh.read(_HEADER.size)
                            if len(header) != _HEADER.size:
                                raise BTDUStorageIntegrityError("truncated segment during index recovery")
                            magic, digest, raw_n, stored_n, codec, cipher, _, _, crc, _nonce = _HEADER.unpack(header)
                            if magic != _MAGIC:
                                raise BTDUStorageIntegrityError("invalid segment magic during recovery")
                            payload = fh.read(int(stored_n))
                            if len(payload) != int(stored_n):
                                raise BTDUStorageIntegrityError("truncated segment payload during recovery")
                            if (zlib.crc32(payload) & 0xFFFFFFFF) != int(crc):
                                raise BTDUStorageIntegrityError("segment CRC failure during recovery")
                            db.execute(
                                """INSERT OR IGNORE INTO chunks(
                                chunk_sha256,segment_id,record_offset,record_bytes,raw_bytes,
                                stored_bytes,codec,cipher,crc32,ref_count,created_at_ms)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                (
                                    digest.hex(),
                                    segment_id,
                                    offset,
                                    _HEADER.size + int(stored_n),
                                    int(raw_n),
                                    int(stored_n),
                                    int(codec),
                                    int(cipher),
                                    int(crc),
                                    0,
                                    int(seg_path.stat().st_mtime * 1000),
                                ),
                            )
                            recovered_chunks += 1
                            offset += _HEADER.size + int(stored_n)

                for manifest_path in sorted(self.manifests_dir.rglob("*.json")):
                    raw = manifest_path.read_bytes()
                    manifest = json.loads(raw.decode("utf-8"))
                    if manifest.get("schema") != PAYLOAD_SCHEMA:
                        continue
                    manifest_sha = _sha256_bytes(raw)
                    storage_object_id = str(manifest["storage_object_id"])
                    db.execute(
                        """INSERT OR REPLACE INTO payloads(
                        storage_object_id,content_sha256,size_bytes,chunk_count,merkle_root,
                        manifest_sha256,manifest_path,created_at_ms)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            storage_object_id,
                            str(manifest["content_sha256"]),
                            int(manifest["size_bytes"]),
                            int(manifest["chunk_count"]),
                            str(manifest["merkle_root"]),
                            manifest_sha,
                            str(manifest_path.relative_to(self.root)).replace("\\", "/"),
                            int(manifest_path.stat().st_mtime * 1000),
                        ),
                    )
                    for row in manifest["chunks"]:
                        digest = str(row["chunk_sha256"])
                        if not db.execute(
                            "SELECT 1 FROM chunks WHERE chunk_sha256=?", (digest,)
                        ).fetchone():
                            raise BTDUStorageIntegrityError(
                                f"manifest references absent chunk {digest}"
                            )
                        db.execute(
                            """INSERT OR REPLACE INTO payload_chunks(
                            storage_object_id,ordinal,chunk_sha256,logical_offset,raw_bytes)
                            VALUES(?,?,?,?,?)""",
                            (
                                storage_object_id,
                                int(row["ordinal"]),
                                digest,
                                int(row["logical_offset"]),
                                int(row["raw_bytes"]),
                            ),
                        )
                    recovered_payloads += 1

                db.execute("UPDATE chunks SET ref_count=0")
                db.execute(
                    """UPDATE chunks SET ref_count=(
                    SELECT count(*) FROM payload_chunks pc
                    WHERE pc.chunk_sha256=chunks.chunk_sha256)"""
                )

        verify = self.verify(deep=False)
        return {
            "schema": "entity-btdu-storage-index-recovery-v1",
            "pass": bool(verify["pass"]),
            "recovered_chunks": recovered_chunks,
            "recovered_payloads": recovered_payloads,
            "backup_index": str(backup) if backup.exists() else None,
            "verification": verify,
        }

    def delete_payload(self, storage_object_id: str) -> dict[str, Any]:
        """Delete a payload manifest/index reference; append-only segment bytes await compaction."""
        with self._thread_lock, _InterprocessLock(self.lock_path):
            with self._db() as db:
                row = db.execute(
                    "SELECT manifest_path FROM payloads WHERE storage_object_id=?",
                    (str(storage_object_id),),
                ).fetchone()
                if row is None:
                    return {"deleted": False, "storage_object_id": str(storage_object_id)}
                chunk_rows = db.execute(
                    "SELECT chunk_sha256 FROM payload_chunks WHERE storage_object_id=?",
                    (str(storage_object_id),),
                ).fetchall()
                db.execute("DELETE FROM payloads WHERE storage_object_id=?", (str(storage_object_id),))
                for chunk in chunk_rows:
                    db.execute(
                        "UPDATE chunks SET ref_count=MAX(0,ref_count-1) WHERE chunk_sha256=?",
                        (str(chunk["chunk_sha256"]),),
                    )
            manifest_path = self.root / str(row["manifest_path"])
            manifest_path.unlink(missing_ok=True)
        return {
            "deleted": True,
            "storage_object_id": str(storage_object_id),
            "gc": self.gc_report(),
        }

    def gc_report(self) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute(
                """SELECT count(*) chunks,COALESCE(sum(stored_bytes),0) stored
                FROM chunks WHERE ref_count=0"""
            ).fetchone()
        return {
            "schema": "entity-btdu-storage-gc-report-v1",
            "reclaimable_chunks": int(row["chunks"]),
            "reclaimable_stored_bytes": int(row["stored"]),
            "segment_compaction_required": int(row["stored"]) > 0,
        }

    def close(self) -> None:
        return None
