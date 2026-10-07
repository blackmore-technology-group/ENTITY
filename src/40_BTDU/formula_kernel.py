from __future__ import annotations

"""BTDU reconstructive formula kernel.

Persistent state is a canonical recipe over the shared atom universe. Full payloads are
materialized only on demand. Irreducible entropy is stored as content-addressed atom tapes
inside the BTDU entropy reservoir; conventional files/blobs are not the authority.

One authoritative payload. Unlimited semantic views.
"""

from pathlib import Path
from typing import Any, BinaryIO, Iterable, Iterator
import hashlib
import json
import os
import re
import sqlite3
import struct
import sys
import threading
import time
import zlib

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from storage_kernel import BTDUStorageKernel, BTDUStorageIntegrityError, _InterprocessLock

FORMULA_SCHEMA = "entity-btdu-formula-kernel-v1"
FORMULA_VERSION = "1.0.0"
OBJECT_SCHEMA = "entity-btdu-reconstructive-object-v1"

K_ATOM = "ATOM"
K_LITERAL = "LITERAL"
K_REPEAT = "REPEAT"
K_CONCAT = "CONCAT"
K_SLICE = "SLICE"
K_SEMANTIC_TAPE = "SEMANTIC_TAPE"

_SEM_TAG_LITERAL = 0
_SEM_TAG_ATOM = 1
_SEM_TOKEN_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\\.[0-9]+)*|[ \\t\\r\\n]+|[^A-Za-z0-9_\\s]+")

_FORMULA_JOURNAL_MAGIC = b"BTDUFJ01"
_FORMULA_JOURNAL_HEADER = struct.Struct(">8sBQI32s")
_FORMULA_JOURNAL_RAW = 0
_FORMULA_JOURNAL_ZLIB = 1


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def _sha(value: Any) -> str:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
    else:
        raw = _canon(value)
    return hashlib.sha256(raw).hexdigest()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _varint(value: int) -> bytes:
    n=int(value)
    if n < 0:
        raise ValueError("varint requires non-negative integer")
    out=bytearray()
    while True:
        b=n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _read_varint(raw: bytes, pos: int) -> tuple[int,int]:
    value=0
    shift=0
    while pos < len(raw):
        b=raw[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value,pos
        shift += 7
        if shift > 63:
            raise BTDUFormulaIntegrityError("semantic tape varint overflow")
    raise BTDUFormulaIntegrityError("truncated semantic tape varint")


class BTDUFormulaError(RuntimeError):
    pass


class BTDUFormulaIntegrityError(BTDUFormulaError):
    pass


class BTDUFormulaKernel:
    """Canonical reconstructive formula engine.

    Formula nodes are compact instructions, not expanded occurrence bonds. Their child
    references are latent structure that is traversed only when reconstruction/query is
    required. This prevents persistent atom-occurrence graphs from becoming the payload.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        reservoir: BTDUStorageKernel | None = None,
        min_chunk: int = 256 * 1024,
        avg_chunk: int = 1024 * 1024,
        max_chunk: int = 4 * 1024 * 1024,
        compression: bool = True,
        encryption_key: bytes | None = None,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "formulas.sqlite"
        self.journal_path = self.root / "formula.a1log"
        self.journal_lock_path = self.root / "formula.lock"
        self._lock = threading.RLock()
        self.reservoir = reservoir or BTDUStorageKernel(
            self.root / "entropy",
            min_chunk=min_chunk,
            avg_chunk=avg_chunk,
            max_chunk=max_chunk,
            compression=compression,
            encryption_key=encryption_key,
        )
        self.min_chunk = int(min_chunk)
        self.avg_chunk = int(avg_chunk)
        self.max_chunk = int(max_chunk)
        self._semantic_basis_root = None
        self._semantic_values = []
        self._semantic_atom_ids = []
        self._semantic_map = {}
        self._init_db()
        if self.journal_path.exists() and self.journal_path.stat().st_size:
            self._replay_unindexed_journal()
        else:
            self._bootstrap_journal_from_index()
        self._reconcile_literal_references()

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=30.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init_db(self) -> None:
        db = self._db()
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS formula_metadata(
                  key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS formula_nodes(
                  node_id TEXT PRIMARY KEY,kind TEXT NOT NULL,output_sha256 TEXT NOT NULL,
                  output_bytes INTEGER NOT NULL,recipe_json TEXT NOT NULL,
                  created_at_ms INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_formula_output
                  ON formula_nodes(output_sha256,output_bytes);
                CREATE TABLE IF NOT EXISTS formula_objects(
                  formula_object_id TEXT PRIMARY KEY,content_sha256 TEXT NOT NULL UNIQUE,
                  size_bytes INTEGER NOT NULL,root_node_id TEXT NOT NULL,
                  formula_sha256 TEXT NOT NULL,created_at_ms INTEGER NOT NULL,
                  FOREIGN KEY(root_node_id) REFERENCES formula_nodes(node_id));
                CREATE TABLE IF NOT EXISTS formula_chunk_index(
                  chunk_sha256 TEXT PRIMARY KEY,node_id TEXT NOT NULL,
                  output_bytes INTEGER NOT NULL,
                  FOREIGN KEY(node_id) REFERENCES formula_nodes(node_id));
                """
            )
            db.execute(
                "INSERT OR REPLACE INTO formula_metadata VALUES(?,?)",
                (
                    "contract",
                    json.dumps(
                        {
                            "schema": FORMULA_SCHEMA,
                            "version": FORMULA_VERSION,
                            "one_authoritative_payload": True,
                            "full_payload_persisted": False,
                            "formula_is_authority": True,
                            "latent_bonds": True,
                            "temporary_materialization_only": True,
                            "entropy_floor_acknowledged": True,
                        },
                        sort_keys=True,
                    ),
                ),
            )
            db.commit()
        finally:
            db.close()

    def configure_semantic_basis(self, basis: dict[str, Any]) -> dict[str, Any]:
        """Bind formula reconstruction to canonical BTDU semantic atom identities.

        The formula recipe stores only a compact ordinal into this deterministic
        atom-ID-ordered basis plus the basis root. Token text remains authoritative
        in the BTDU atom universe, not duplicated in formula nodes.
        """
        by_value: dict[bytes, str] = {}
        for namespace in ("code", "english", "math"):
            section = dict(basis.get(namespace) or {})
            for item in section.get("entries", []):
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                atom_id = str(item[0])
                raw = item[1]
                if isinstance(raw, str):
                    raw = raw.encode("utf-8")
                raw = bytes(raw)
                if not raw:
                    continue
                previous = by_value.get(raw)
                if previous is None or atom_id < previous:
                    by_value[raw] = atom_id
        ordered = sorted(((atom_id, raw) for raw, atom_id in by_value.items()),
                         key=lambda item: item[0])
        root = _sha({
            "schema": "entity-btdu-semantic-formula-basis-v1",
            "entries": [[atom_id, raw.hex()] for atom_id, raw in ordered],
        })
        self._semantic_basis_root = root
        self._semantic_atom_ids = [atom_id for atom_id, _ in ordered]
        self._semantic_values = [raw for _, raw in ordered]
        self._semantic_map = {raw: i for i, raw in enumerate(self._semantic_values)}
        return {
            "schema": "entity-btdu-semantic-formula-basis-status-v1",
            "basis_root": root,
            "atoms": len(ordered),
            "canonical_atom_identity": True,
        }

    def semantic_basis_status(self) -> dict[str, Any]:
        return {
            "schema": "entity-btdu-semantic-formula-basis-status-v1",
            "configured": self._semantic_basis_root is not None,
            "basis_root": self._semantic_basis_root,
            "atoms": len(self._semantic_values),
            "canonical_atom_identity": True,
        }

    @staticmethod
    def _semantic_literal(tape: bytearray, raw: bytes) -> None:
        if not raw:
            return
        tape.append(_SEM_TAG_LITERAL)
        tape.extend(_varint(len(raw)))
        tape.extend(raw)

    def _encode_semantic_tape(self, raw: bytes) -> dict[str, Any] | None:
        """Compile exact bytes into canonical semantic-atom refs plus residual entropy."""
        if self._semantic_basis_root is None or not self._semantic_map or not raw:
            return None
        tape=bytearray()
        pos=0
        semantic_refs=0
        semantic_bytes=0
        literal_bytes=0
        for match in _SEM_TOKEN_RE.finditer(raw):
            if match.start()>pos:
                gap=raw[pos:match.start()]
                self._semantic_literal(tape,gap)
                literal_bytes+=len(gap)
            token=match.group(0)
            idx=self._semantic_map.get(token)
            if idx is None:
                self._semantic_literal(tape,token)
                literal_bytes+=len(token)
            else:
                tape.append(_SEM_TAG_ATOM)
                tape.extend(_varint(idx))
                semantic_refs+=1
                semantic_bytes+=len(token)
            pos=match.end()
        if pos<len(raw):
            tail=raw[pos:]
            self._semantic_literal(tape,tail)
            literal_bytes+=len(tail)
        if semantic_refs==0:
            return None
        # Use semantic formulation only when the persistent recipe is smaller.
        if len(tape)+64 >= len(raw):
            return None
        return {
            "tape":bytes(tape),
            "semantic_refs":semantic_refs,
            "semantic_bytes":semantic_bytes,
            "literal_bytes":literal_bytes,
        }

    def _decode_semantic_tape(self, recipe: dict[str, Any]) -> bytes:
        expected_root=str(recipe.get("basis_root") or "")
        if self._semantic_basis_root is None or expected_root!=self._semantic_basis_root:
            raise BTDUFormulaIntegrityError("semantic formula basis root mismatch")
        tape=self.reservoir.read_literal_atom_tape(str(recipe["tape_sha256"]))
        if len(tape)!=int(recipe["tape_bytes"]):
            raise BTDUFormulaIntegrityError("semantic tape length mismatch")
        out=bytearray()
        pos=0
        while pos<len(tape):
            tag=tape[pos]; pos+=1
            if tag==_SEM_TAG_LITERAL:
                n,pos=_read_varint(tape,pos)
                end=pos+n
                if end>len(tape):
                    raise BTDUFormulaIntegrityError("semantic tape literal exceeds tape")
                out.extend(tape[pos:end]); pos=end
            elif tag==_SEM_TAG_ATOM:
                idx,pos=_read_varint(tape,pos)
                if idx<0 or idx>=len(self._semantic_values):
                    raise BTDUFormulaIntegrityError("semantic atom ordinal out of range")
                out.extend(self._semantic_values[idx])
            else:
                raise BTDUFormulaIntegrityError("unknown semantic tape tag")
        return bytes(out)

    def _metadata_int(self, key: str, default: int = 0) -> int:
        db = self._db()
        try:
            row = db.execute(
                "SELECT value_json FROM formula_metadata WHERE key=?", (str(key),)
            ).fetchone()
        finally:
            db.close()
        if row is None:
            return int(default)
        try:
            return int(json.loads(row["value_json"]))
        except Exception:
            return int(default)

    @staticmethod
    def _set_metadata_value(db: sqlite3.Connection, key: str, value: Any) -> None:
        db.execute(
            "INSERT OR REPLACE INTO formula_metadata(key,value_json) VALUES(?,?)",
            (str(key), json.dumps(value, sort_keys=True, separators=(",", ":"))),
        )

    def _append_journal_record_unlocked(self, record: dict[str, Any]) -> int:
        raw = _canon(record)
        stored = raw
        codec = _FORMULA_JOURNAL_RAW
        compressed = zlib.compress(raw, level=6)
        if len(compressed) + 16 < int(len(raw) * 0.94):
            stored = compressed
            codec = _FORMULA_JOURNAL_ZLIB
        header = _FORMULA_JOURNAL_HEADER.pack(
            _FORMULA_JOURNAL_MAGIC,
            codec,
            len(stored),
            zlib.crc32(stored) & 0xFFFFFFFF,
            hashlib.sha256(raw).digest(),
        )
        with self.journal_path.open("ab", buffering=0) as fh:
            fh.write(header)
            fh.write(stored)
            fh.flush()
            os.fsync(fh.fileno())
            return int(fh.tell())

    def _iter_journal(self, start_offset: int = 0):
        if not self.journal_path.exists():
            return
        with self.journal_path.open("rb") as fh:
            fh.seek(int(start_offset))
            while True:
                record_offset = int(fh.tell())
                header = fh.read(_FORMULA_JOURNAL_HEADER.size)
                if not header:
                    break
                if len(header) != _FORMULA_JOURNAL_HEADER.size:
                    raise BTDUFormulaIntegrityError(
                        f"truncated formula journal header at {record_offset}"
                    )
                magic, codec, stored_n, crc, raw_sha = _FORMULA_JOURNAL_HEADER.unpack(header)
                if magic != _FORMULA_JOURNAL_MAGIC:
                    raise BTDUFormulaIntegrityError(
                        f"invalid formula journal magic at {record_offset}"
                    )
                stored = fh.read(int(stored_n))
                if len(stored) != int(stored_n):
                    raise BTDUFormulaIntegrityError(
                        f"truncated formula journal record at {record_offset}"
                    )
                if (zlib.crc32(stored) & 0xFFFFFFFF) != int(crc):
                    raise BTDUFormulaIntegrityError(
                        f"formula journal CRC mismatch at {record_offset}"
                    )
                if codec == _FORMULA_JOURNAL_ZLIB:
                    try:
                        raw = zlib.decompress(stored)
                    except Exception as exc:
                        raise BTDUFormulaIntegrityError(
                            f"formula journal decompression failed at {record_offset}"
                        ) from exc
                elif codec == _FORMULA_JOURNAL_RAW:
                    raw = stored
                else:
                    raise BTDUFormulaIntegrityError(
                        f"unsupported formula journal codec {codec}"
                    )
                if hashlib.sha256(raw).digest() != raw_sha:
                    raise BTDUFormulaIntegrityError(
                        f"formula journal SHA-256 mismatch at {record_offset}"
                    )
                try:
                    record = json.loads(raw.decode("utf-8"))
                except Exception as exc:
                    raise BTDUFormulaIntegrityError(
                        f"invalid formula journal JSON at {record_offset}"
                    ) from exc
                yield record, int(fh.tell())

    def _apply_journal_record(
        self,
        db: sqlite3.Connection,
        record: dict[str, Any],
        literal_refs: list[tuple[str, str]],
    ) -> None:
        record_type = str(record.get("record_type", ""))
        if record_type == "NODE":
            body = {
                "schema": "entity-btdu-formula-node-v1",
                "kind": str(record["kind"]),
                "output_sha256": str(record["output_sha256"]),
                "output_bytes": int(record["output_bytes"]),
                "recipe": dict(record["recipe"]),
            }
            expected = "btdu-formula:" + _sha(body)
            if expected != str(record["node_id"]):
                raise BTDUFormulaIntegrityError("formula journal node identity mismatch")
            db.execute(
                """INSERT OR IGNORE INTO formula_nodes(
                node_id,kind,output_sha256,output_bytes,recipe_json,created_at_ms)
                VALUES(?,?,?,?,?,?)""",
                (
                    expected,
                    body["kind"],
                    body["output_sha256"],
                    body["output_bytes"],
                    json.dumps(body["recipe"], sort_keys=True, separators=(",", ":")),
                    int(record.get("created_at_ms", 0) or 0),
                ),
            )
            db.execute(
                """INSERT OR IGNORE INTO formula_chunk_index(
                chunk_sha256,node_id,output_bytes) VALUES(?,?,?)""",
                (body["output_sha256"], expected, body["output_bytes"]),
            )
            if body["kind"] in (K_LITERAL,K_SEMANTIC_TAPE):
                key="literal_sha256" if body["kind"]==K_LITERAL else "tape_sha256"
                literal_sha = str(body["recipe"].get(key, ""))
                if not literal_sha:
                    raise BTDUFormulaIntegrityError("formula node missing atom tape")
                literal_refs.append((expected, literal_sha))
            return

        if record_type == "OBJECT":
            content_sha = str(record["content_sha256"])
            object_id = str(record["formula_object_id"])
            if object_id != "btdu-formula-object:" + content_sha:
                raise BTDUFormulaIntegrityError("formula journal object identity mismatch")
            root_id = str(record["root_node_id"])
            if not db.execute(
                "SELECT 1 FROM formula_nodes WHERE node_id=?", (root_id,)
            ).fetchone():
                raise BTDUFormulaIntegrityError(
                    "formula journal object references missing root node"
                )
            db.execute(
                """INSERT OR IGNORE INTO formula_objects(
                formula_object_id,content_sha256,size_bytes,root_node_id,
                formula_sha256,created_at_ms) VALUES(?,?,?,?,?,?)""",
                (
                    object_id,
                    content_sha,
                    int(record["size_bytes"]),
                    root_id,
                    str(record["formula_sha256"]),
                    int(record.get("created_at_ms", 0) or 0),
                ),
            )
            return

        raise BTDUFormulaIntegrityError(
            "unknown formula journal record type " + record_type
        )

    def _replay_unindexed_journal(self) -> dict[str, Any]:
        if not self.journal_path.exists():
            return {"records": 0, "indexed_bytes": 0}
        with self._lock, _InterprocessLock(self.journal_lock_path):
            journal_bytes = int(self.journal_path.stat().st_size)
            indexed = self._metadata_int("journal_indexed_bytes", 0)
            if indexed < 0 or indexed > journal_bytes:
                raise BTDUFormulaIntegrityError(
                    "formula journal indexed offset is outside journal"
                )
            if indexed == journal_bytes:
                return {"records": 0, "indexed_bytes": indexed}
            db = self._db()
            literal_refs: list[tuple[str, str]] = []
            records = 0
            end = indexed
            try:
                for record, end in self._iter_journal(indexed):
                    self._apply_journal_record(db, record, literal_refs)
                    records += 1
                self._set_metadata_value(db, "journal_indexed_bytes", int(end))
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        for node_id, literal_sha in literal_refs:
            self.reservoir.retain_chunk(
                literal_sha, ref_id=node_id, ref_kind="FORMULA_LITERAL"
            )
        return {"records": records, "indexed_bytes": int(end)}

    def _bootstrap_journal_from_index(self) -> dict[str, Any]:
        if self.journal_path.exists() and self.journal_path.stat().st_size:
            return self._replay_unindexed_journal()
        db = self._db()
        try:
            nodes = [dict(r) for r in db.execute(
                """SELECT node_id,kind,output_sha256,output_bytes,recipe_json,created_at_ms
                FROM formula_nodes ORDER BY created_at_ms,node_id"""
            )]
            objects = [dict(r) for r in db.execute(
                """SELECT formula_object_id,content_sha256,size_bytes,root_node_id,
                formula_sha256,created_at_ms FROM formula_objects
                ORDER BY created_at_ms,formula_object_id"""
            )]
        finally:
            db.close()
        if not nodes and not objects:
            db = self._db()
            try:
                self._set_metadata_value(db, "journal_indexed_bytes", 0)
                db.commit()
            finally:
                db.close()
            return {"nodes": 0, "objects": 0, "journal_bytes": 0}

        literal_refs: list[tuple[str, str]] = []
        with self._lock, _InterprocessLock(self.journal_lock_path):
            end = 0
            for row in nodes:
                recipe = json.loads(row["recipe_json"])
                record = {
                    "schema": "entity-btdu-formula-journal-record-v1",
                    "record_type": "NODE",
                    "node_id": row["node_id"],
                    "kind": row["kind"],
                    "output_sha256": row["output_sha256"],
                    "output_bytes": int(row["output_bytes"]),
                    "recipe": recipe,
                    "created_at_ms": int(row["created_at_ms"]),
                }
                end = self._append_journal_record_unlocked(record)
                if row["kind"] in (K_LITERAL,K_SEMANTIC_TAPE):
                    key="literal_sha256" if row["kind"]==K_LITERAL else "tape_sha256"
                    literal_refs.append(
                        (str(row["node_id"]), str(recipe[key]))
                    )
            for row in objects:
                record = {
                    "schema": "entity-btdu-formula-journal-record-v1",
                    "record_type": "OBJECT",
                    "formula_object_id": row["formula_object_id"],
                    "content_sha256": row["content_sha256"],
                    "size_bytes": int(row["size_bytes"]),
                    "root_node_id": row["root_node_id"],
                    "formula_sha256": row["formula_sha256"],
                    "created_at_ms": int(row["created_at_ms"]),
                }
                end = self._append_journal_record_unlocked(record)
            db = self._db()
            try:
                self._set_metadata_value(db, "journal_indexed_bytes", int(end))
                db.commit()
            finally:
                db.close()
        for node_id, literal_sha in literal_refs:
            self.reservoir.retain_chunk(
                literal_sha, ref_id=node_id, ref_kind="FORMULA_LITERAL"
            )
        return {
            "nodes": len(nodes),
            "objects": len(objects),
            "journal_bytes": int(end),
        }

    def _reconcile_literal_references(self) -> dict[str, Any]:
        db = self._db()
        try:
            rows = db.execute(
                """SELECT node_id,kind,recipe_json FROM formula_nodes
                WHERE kind IN (?,?) ORDER BY node_id""",
                (K_LITERAL,K_SEMANTIC_TAPE),
            ).fetchall()
        finally:
            db.close()
        refs: list[tuple[str, str, str]] = []
        for row in rows:
            recipe = json.loads(row["recipe_json"])
            key="literal_sha256" if row["kind"]==K_LITERAL else "tape_sha256"
            literal_sha = str(recipe.get(key, ""))
            if not literal_sha:
                raise BTDUFormulaIntegrityError(
                    "formula node missing atom tape during reference reconciliation"
                )
            refs.append((str(row["node_id"]), literal_sha, "FORMULA_LITERAL"))
        if not refs:
            return {"checked": 0, "added": 0}
        return self.reservoir.retain_references(refs)

    def journal_status(self, *, deep: bool = False) -> dict[str, Any]:
        size = self.journal_path.stat().st_size if self.journal_path.exists() else 0
        indexed = self._metadata_int("journal_indexed_bytes", 0)
        problems: list[str] = []
        records = 0
        node_records = 0
        object_records = 0
        last_end = 0
        if indexed != size:
            problems.append("unindexed_tail")
        if deep and size:
            try:
                for record, last_end in self._iter_journal(0):
                    records += 1
                    if record.get("record_type") == "NODE":
                        node_records += 1
                    elif record.get("record_type") == "OBJECT":
                        object_records += 1
                    else:
                        problems.append("unknown_record")
                if last_end != size:
                    problems.append("journal_length")
            except Exception as exc:
                problems.append("journal:" + type(exc).__name__)
        return {
            "schema": "entity-btdu-formula-journal-status-v1",
            "pass": not problems,
            "bytes": int(size),
            "indexed_bytes": int(indexed),
            "records": records if deep else None,
            "node_records": node_records if deep else None,
            "object_records": object_records if deep else None,
            "problems": problems,
        }

    def recover_index(self) -> dict[str, Any]:
        if not self.journal_path.exists():
            raise BTDUFormulaIntegrityError("formula journal is required for index recovery")
        import shutil
        with self._lock, _InterprocessLock(self.journal_lock_path):
            backup = self.db_path.with_suffix(f".pre-recover-{_now_ms()}.sqlite")
            if self.db_path.exists():
                shutil.copy2(self.db_path, backup)
                self.db_path.unlink()
            for suffix in ("-wal", "-shm"):
                Path(str(self.db_path) + suffix).unlink(missing_ok=True)
            self._init_db()
            db = self._db()
            literal_refs: list[tuple[str, str]] = []
            records = 0
            end = 0
            try:
                for record, end in self._iter_journal(0):
                    self._apply_journal_record(db, record, literal_refs)
                    records += 1
                self._set_metadata_value(db, "journal_indexed_bytes", int(end))
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        for node_id, literal_sha in literal_refs:
            self.reservoir.retain_chunk(
                literal_sha, ref_id=node_id, ref_kind="FORMULA_LITERAL"
            )
        check = self.verify(deep=False)
        return {
            "schema": "entity-btdu-formula-index-recovery-v1",
            "pass": bool(check["pass"]),
            "records": records,
            "indexed_bytes": int(end),
            "backup_index": str(backup) if backup.exists() else None,
            "verification": check,
        }

    def _node(self, node_id: str) -> sqlite3.Row:
        db = self._db()
        try:
            row = db.execute(
                "SELECT * FROM formula_nodes WHERE node_id=?", (str(node_id),)
            ).fetchone()
        finally:
            db.close()
        if row is None:
            raise KeyError(node_id)
        return row

    def _put_node(
        self,
        *,
        kind: str,
        output_sha256: str,
        output_bytes: int,
        recipe: dict[str, Any],
    ) -> str:
        body = {
            "schema": "entity-btdu-formula-node-v1",
            "kind": str(kind),
            "output_sha256": str(output_sha256),
            "output_bytes": int(output_bytes),
            "recipe": recipe,
        }
        node_id = "btdu-formula:" + _sha(body)
        created_at = _now_ms()
        inserted = False
        with self._lock, _InterprocessLock(self.journal_lock_path):
            db = self._db()
            try:
                if db.execute(
                    "SELECT 1 FROM formula_nodes WHERE node_id=?", (node_id,)
                ).fetchone():
                    return node_id
                record = {
                    "schema": "entity-btdu-formula-journal-record-v1",
                    "record_type": "NODE",
                    "node_id": node_id,
                    "kind": str(kind),
                    "output_sha256": str(output_sha256),
                    "output_bytes": int(output_bytes),
                    "recipe": dict(recipe),
                    "created_at_ms": created_at,
                }
                journal_end = self._append_journal_record_unlocked(record)
                db.execute(
                    """INSERT INTO formula_nodes(
                    node_id,kind,output_sha256,output_bytes,recipe_json,created_at_ms)
                    VALUES(?,?,?,?,?,?)""",
                    (
                        node_id,
                        str(kind),
                        str(output_sha256),
                        int(output_bytes),
                        json.dumps(recipe, sort_keys=True, separators=(",", ":")),
                        created_at,
                    ),
                )
                db.execute(
                    """INSERT OR IGNORE INTO formula_chunk_index(
                    chunk_sha256,node_id,output_bytes) VALUES(?,?,?)""",
                    (str(output_sha256), node_id, int(output_bytes)),
                )
                self._set_metadata_value(
                    db, "journal_indexed_bytes", int(journal_end)
                )
                db.commit()
                inserted = True
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        if inserted and str(kind) == K_LITERAL:
            literal_sha = str(recipe.get("literal_sha256", ""))
            if not literal_sha:
                raise BTDUFormulaIntegrityError("literal formula missing atom tape")
            self.reservoir.retain_chunk(
                literal_sha, ref_id=node_id, ref_kind="FORMULA_LITERAL"
            )
        return node_id

    def _atom_node(self, atom_value: int) -> str:
        if not 0 <= int(atom_value) <= 255:
            raise ValueError("primitive byte atom must be 0..255")
        raw = bytes([int(atom_value)])
        return self._put_node(
            kind=K_ATOM,
            output_sha256=_sha(raw),
            output_bytes=1,
            recipe={"atom": int(atom_value)},
        )

    @staticmethod
    def _minimal_period(data: bytes, max_period: int = 64 * 1024) -> int | None:
        n = len(data)
        if n < 4:
            return None
        # Prefix-function gives the shortest candidate basis. The final input does
        # not have to end on an exact period boundary: "abcab" is still generated
        # by basis "abc" plus the first two basis atoms.
        pi = [0] * n
        for i in range(1, n):
            j = pi[i - 1]
            while j and data[i] != data[j]:
                j = pi[j - 1]
            if data[i] == data[j]:
                j += 1
            pi[i] = j
        p = n - pi[-1]
        if p < n and p <= max_period and data[p:] == data[:-p]:
            return p
        return None

    def _compile_unit(self, raw: bytes) -> str:
        if not raw:
            return self._put_node(
                kind=K_CONCAT,
                output_sha256=_sha(b""),
                output_bytes=0,
                recipe={"children": []},
            )

        digest = _sha(raw)
        db = self._db()
        try:
            existing = db.execute(
                "SELECT node_id FROM formula_chunk_index WHERE chunk_sha256=?",
                (digest,),
            ).fetchone()
        finally:
            db.close()
        if existing is not None:
            return str(existing["node_id"])

        if len(raw) == 1:
            node_id = self._atom_node(raw[0])
        elif len(set(raw)) == 1:
            child = self._atom_node(raw[0])
            node_id = self._put_node(
                kind=K_REPEAT,
                output_sha256=digest,
                output_bytes=len(raw),
                recipe={"child": child, "count": len(raw)},
            )
        else:
            period = self._minimal_period(raw)
            if period is not None and period * 4 <= len(raw):
                basis = self._compile_unit(raw[:period])
                full_count, remainder = divmod(len(raw), period)
                repeat_bytes = period * full_count
                repeat_sha = _sha(raw[:repeat_bytes])
                repeat_node = self._put_node(
                    kind=K_REPEAT,
                    output_sha256=repeat_sha,
                    output_bytes=repeat_bytes,
                    recipe={"child": basis, "count": full_count},
                )
                if remainder:
                    tail = self._compile_unit(raw[:remainder])
                    node_id = self._put_node(
                        kind=K_CONCAT,
                        output_sha256=digest,
                        output_bytes=len(raw),
                        recipe={"children": [repeat_node, tail]},
                    )
                else:
                    node_id = repeat_node
            else:
                semantic=self._encode_semantic_tape(raw)
                if semantic is not None:
                    tape=self.reservoir.put_literal_atom_tape(semantic["tape"])
                    node_id=self._put_node(
                        kind=K_SEMANTIC_TAPE,
                        output_sha256=digest,
                        output_bytes=len(raw),
                        recipe={
                            "basis_root":self._semantic_basis_root,
                            "tape_sha256":tape["literal_sha256"],
                            "tape_bytes":len(semantic["tape"]),
                            "semantic_refs":int(semantic["semantic_refs"]),
                            "semantic_bytes":int(semantic["semantic_bytes"]),
                            "literal_bytes":int(semantic["literal_bytes"]),
                        },
                    )
                else:
                    literal = self.reservoir.put_literal_atom_tape(raw)
                    node_id = self._put_node(
                        kind=K_LITERAL,
                        output_sha256=digest,
                        output_bytes=len(raw),
                        recipe={
                            "literal_sha256": literal["literal_sha256"],
                            "atom_count": literal["atom_count"],
                        },
                    )

        with self._lock:
            db = self._db()
            try:
                db.execute(
                    "INSERT OR IGNORE INTO formula_chunk_index(chunk_sha256,node_id,output_bytes) VALUES(?,?,?)",
                    (digest, node_id, len(raw)),
                )
                db.commit()
            finally:
                db.close()
        return node_id

    def _cdc_units(self, parts: Iterable[bytes]) -> Iterator[bytes]:
        # Reuse the exact deterministic content-defined splitter from the reservoir.
        yield from self.reservoir._iter_cdc(parts)

    @staticmethod
    def _file_parts(fh: BinaryIO, read_size: int = 1024 * 1024) -> Iterator[bytes]:
        while True:
            part = fh.read(read_size)
            if not part:
                break
            yield part

    def put_iterable(self, parts: Iterable[bytes]) -> dict[str, Any]:
        h = hashlib.sha256()
        size = 0
        children: list[str] = []
        child_hashes: list[str] = []
        child_sizes: list[int] = []

        for unit in self._cdc_units(parts):
            h.update(unit)
            size += len(unit)
            child = self._compile_unit(unit)
            children.append(child)
            child_hashes.append(_sha(unit))
            child_sizes.append(len(unit))

        content_sha = h.hexdigest()
        if not children:
            root = self._compile_unit(b"")
        elif len(children) == 1:
            root = children[0]
        else:
            root = self._put_node(
                kind=K_CONCAT,
                output_sha256=content_sha,
                output_bytes=size,
                recipe={"children": children},
            )

        formula_doc = {
            "schema": OBJECT_SCHEMA,
            "formula_version": FORMULA_VERSION,
            "content_sha256": content_sha,
            "size_bytes": size,
            "root_node_id": root,
            "unit_count": len(children),
            "unit_sha256": child_hashes,
            "unit_bytes": child_sizes,
        }
        formula_sha = _sha(formula_doc)
        formula_object_id = "btdu-formula-object:" + content_sha

        created_at = _now_ms()
        with self._lock, _InterprocessLock(self.journal_lock_path):
            db = self._db()
            try:
                existing = db.execute(
                    """SELECT content_sha256,size_bytes,root_node_id,formula_sha256
                    FROM formula_objects WHERE formula_object_id=?""",
                    (formula_object_id,),
                ).fetchone()
                if existing is not None:
                    if (
                        str(existing["content_sha256"]) != content_sha
                        or int(existing["size_bytes"]) != size
                        or str(existing["root_node_id"]) != root
                        or str(existing["formula_sha256"]) != formula_sha
                    ):
                        raise BTDUFormulaIntegrityError(
                            "one-authoritative-payload formula conflict"
                        )
                else:
                    record = {
                        "schema": "entity-btdu-formula-journal-record-v1",
                        "record_type": "OBJECT",
                        "formula_object_id": formula_object_id,
                        "content_sha256": content_sha,
                        "size_bytes": size,
                        "root_node_id": root,
                        "formula_sha256": formula_sha,
                        "created_at_ms": created_at,
                    }
                    journal_end = self._append_journal_record_unlocked(record)
                    db.execute(
                        """INSERT INTO formula_objects(
                        formula_object_id,content_sha256,size_bytes,root_node_id,
                        formula_sha256,created_at_ms) VALUES(?,?,?,?,?,?)""",
                        (
                            formula_object_id,
                            content_sha,
                            size,
                            root,
                            formula_sha,
                            created_at,
                        ),
                    )
                    self._set_metadata_value(
                        db, "journal_indexed_bytes", int(journal_end)
                    )
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        return dict(
            formula_doc,
            formula_object_id=formula_object_id,
            formula_sha256=formula_sha,
        )

    def put_bytes(self, data: bytes) -> dict[str, Any]:
        return self.put_iterable((bytes(data),))

    def put_path(self, path: str | Path) -> dict[str, Any]:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(str(p))
        with p.open("rb") as fh:
            return self.put_iterable(self._file_parts(fh))

    def object_record(self, formula_object_id: str) -> dict[str, Any]:
        db = self._db()
        try:
            row = db.execute(
                "SELECT * FROM formula_objects WHERE formula_object_id=?",
                (str(formula_object_id),),
            ).fetchone()
        finally:
            db.close()
        if row is None:
            raise KeyError(formula_object_id)
        return dict(row)

    def _iter_node(self, node_id: str) -> Iterator[bytes]:
        row = self._node(node_id)
        kind = str(row["kind"])
        recipe = json.loads(row["recipe_json"])

        if kind == K_ATOM:
            yield bytes([int(recipe["atom"])])
            return
        if kind == K_LITERAL:
            raw = self.reservoir.read_literal_atom_tape(str(recipe["literal_sha256"]))
            if len(raw) != int(row["output_bytes"]) or _sha(raw) != str(row["output_sha256"]):
                raise BTDUFormulaIntegrityError("literal atom tape does not match formula node")
            yield raw
            return
        if kind == K_SEMANTIC_TAPE:
            raw=self._decode_semantic_tape(recipe)
            if len(raw)!=int(row["output_bytes"]) or _sha(raw)!=str(row["output_sha256"]):
                raise BTDUFormulaIntegrityError("semantic atom tape does not match formula node")
            yield raw
            return
        if kind == K_REPEAT:
            child = str(recipe["child"])
            count = int(recipe["count"])
            child_len = self._node_length(child)
            if count <= 0:
                return
            # Reconstruct a small repeated basis once, then stream batched repetitions.
            # This keeps a formula such as REPEAT(ATOM("A"), 2_000_000) efficient
            # without creating two million runtime yields/bonds.
            if child_len <= 1024 * 1024:
                basis = b"".join(self._iter_node(child))
                if len(basis) != child_len:
                    raise BTDUFormulaIntegrityError("repeat basis length mismatch")
                batch_count = max(1, (1024 * 1024) // max(1, child_len))
                remaining = count
                while remaining:
                    n = min(remaining, batch_count)
                    yield basis * n
                    remaining -= n
            else:
                for _ in range(count):
                    yield from self._iter_node(child)
            return
        if kind == K_CONCAT:
            for child in recipe.get("children", []):
                yield from self._iter_node(str(child))
            return
        if kind == K_SLICE:
            child = str(recipe["child"])
            offset = int(recipe["offset"])
            length = int(recipe["length"])
            data = b"".join(self._iter_node(child))
            yield data[offset : offset + length]
            return
        raise BTDUFormulaIntegrityError(f"unknown formula node kind {kind}")

    def iter_object(self, formula_object_id: str) -> Iterator[bytes]:
        obj = self.object_record(formula_object_id)
        yield from self._iter_node(str(obj["root_node_id"]))

    def read_all(self, formula_object_id: str) -> bytes:
        raw = b"".join(self.iter_object(formula_object_id))
        obj = self.object_record(formula_object_id)
        if len(raw) != int(obj["size_bytes"]) or _sha(raw) != str(obj["content_sha256"]):
            raise BTDUFormulaIntegrityError("reconstructed object hash/length mismatch")
        return raw

    def materialize(self, formula_object_id: str, output_path: str | Path) -> dict[str, Any]:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".btdu-materializing")
        h = hashlib.sha256()
        size = 0
        with tmp.open("wb") as fh:
            for block in self.iter_object(formula_object_id):
                fh.write(block)
                h.update(block)
                size += len(block)
            fh.flush()
            import os
            os.fsync(fh.fileno())
        obj = self.object_record(formula_object_id)
        if h.hexdigest() != obj["content_sha256"] or size != int(obj["size_bytes"]):
            tmp.unlink(missing_ok=True)
            raise BTDUFormulaIntegrityError("materialized object failed exact verification")
        import os
        os.replace(tmp, target)
        return {
            "schema": "entity-btdu-materialization-v1",
            "formula_object_id": str(formula_object_id),
            "path": str(target),
            "bytes": size,
            "sha256": h.hexdigest(),
            "temporary_materialization": True,
        }

    def _node_length(self, node_id: str) -> int:
        return int(self._node(node_id)["output_bytes"])

    def _range_node(self, node_id: str, offset: int, end: int) -> Iterator[bytes]:
        if end <= offset:
            return
        row = self._node(node_id)
        kind = str(row["kind"])
        total = int(row["output_bytes"])
        if offset <= 0 and end >= total:
            yield from self._iter_node(node_id)
            return
        recipe = json.loads(row["recipe_json"])

        if kind in (K_ATOM, K_LITERAL, K_SEMANTIC_TAPE):
            raw = b"".join(self._iter_node(node_id))
            yield raw[max(0, offset) : min(len(raw), end)]
            return

        if kind == K_REPEAT:
            child = str(recipe["child"])
            child_len = self._node_length(child)
            count = int(recipe["count"])
            repeat_bytes = child_len * count
            left = max(0, offset)
            right = min(repeat_bytes, end)
            if right <= left:
                return
            # Range reads over a repeated basis must never expand occurrence-by-
            # occurrence. Reconstruct the basis once and formulate only the
            # requested window.
            if child_len <= 1024 * 1024:
                basis = b"".join(self._iter_node(child))
                if len(basis) != child_len:
                    raise BTDUFormulaIntegrityError("repeat range basis length mismatch")
                start_mod = left % child_len
                needed = right - left
                copies = (start_mod + needed + child_len - 1) // child_len
                yield (basis * copies)[start_mod : start_mod + needed]
            else:
                first = left // child_len
                last = min(count, ((right - 1) // child_len) + 1)
                for i in range(first, last):
                    base = i * child_len
                    yield from self._range_node(child, left - base, right - base)
            return

        if kind == K_CONCAT:
            cursor = 0
            for child in recipe.get("children", []):
                child = str(child)
                child_len = self._node_length(child)
                child_end = cursor + child_len
                if child_end > offset and cursor < end:
                    yield from self._range_node(child, offset - cursor, end - cursor)
                cursor = child_end
                if cursor >= end:
                    break
            return

        if kind == K_SLICE:
            child = str(recipe["child"])
            base = int(recipe["offset"])
            yield from self._range_node(child, base + offset, base + end)
            return

        raise BTDUFormulaIntegrityError(f"unknown formula node kind {kind}")

    def read_range(self, formula_object_id: str, offset: int, length: int) -> bytes:
        offset = int(offset)
        length = int(length)
        if offset < 0 or length < 0:
            raise ValueError("offset and length must be non-negative")
        if length == 0:
            return b""
        obj = self.object_record(formula_object_id)
        size = int(obj["size_bytes"])
        if offset >= size:
            return b""
        end = min(size, offset + length)
        return b"".join(self._range_node(str(obj["root_node_id"]), offset, end))

    def transient_bond_plan(self, formula_object_id: str) -> dict[str, Any]:
        """Return an in-memory bond plan without persisting occurrence-level bonds."""
        obj = self.object_record(formula_object_id)
        seen: set[str] = set()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        def walk(node_id: str) -> None:
            if node_id in seen:
                return
            seen.add(node_id)
            row = self._node(node_id)
            recipe = json.loads(row["recipe_json"])
            nodes.append(
                {
                    "node_id": node_id,
                    "kind": row["kind"],
                    "output_sha256": row["output_sha256"],
                    "output_bytes": int(row["output_bytes"]),
                }
            )
            if row["kind"] == K_CONCAT:
                for order, child in enumerate(recipe.get("children", [])):
                    edges.append(
                        {
                            "source": node_id,
                            "predicate": "CONCAT_CHILD",
                            "target": str(child),
                            "order": order,
                        }
                    )
                    walk(str(child))
            elif row["kind"] == K_REPEAT:
                child = str(recipe["child"])
                edges.append(
                    {
                        "source": node_id,
                        "predicate": "REPEAT_CHILD",
                        "target": child,
                        "count": int(recipe["count"]),
                    }
                )
                walk(child)
            elif row["kind"] == K_SLICE:
                child = str(recipe["child"])
                edges.append(
                    {
                        "source": node_id,
                        "predicate": "SLICE_CHILD",
                        "target": child,
                        "offset": int(recipe["offset"]),
                        "length": int(recipe["length"]),
                    }
                )
                walk(child)

        walk(str(obj["root_node_id"]))
        return {
            "schema": "entity-btdu-transient-bond-plan-v1",
            "formula_object_id": str(formula_object_id),
            "persistent_occurrence_bonds_created": False,
            "nodes": nodes,
            "edges": edges,
        }

    def verify_object(self, formula_object_id: str, *, deep: bool = True) -> dict[str, Any]:
        problems: list[str] = []
        obj = self.object_record(formula_object_id)
        root = self._node(str(obj["root_node_id"]))
        if int(root["output_bytes"]) != int(obj["size_bytes"]):
            problems.append("root_size")
        if str(root["output_sha256"]) != str(obj["content_sha256"]):
            problems.append("root_hash")
        if deep:
            try:
                h = hashlib.sha256()
                size = 0
                for block in self.iter_object(formula_object_id):
                    h.update(block)
                    size += len(block)
                if h.hexdigest() != obj["content_sha256"]:
                    problems.append("reconstruct_hash")
                if size != int(obj["size_bytes"]):
                    problems.append("reconstruct_size")
            except Exception as exc:
                problems.append("reconstruct:" + type(exc).__name__)
        return {
            "schema": "entity-btdu-formula-object-verification-v1",
            "pass": not problems,
            "formula_object_id": str(formula_object_id),
            "deep": bool(deep),
            "problems": problems,
        }

    def stats(self) -> dict[str, Any]:
        db = self._db()
        try:
            objects = int(db.execute("SELECT count(*) FROM formula_objects").fetchone()[0])
            logical = int(
                db.execute("SELECT COALESCE(sum(size_bytes),0) FROM formula_objects").fetchone()[0]
            )
            nodes = int(db.execute("SELECT count(*) FROM formula_nodes").fetchone()[0])
            by_kind = {
                row["kind"]: int(row["n"])
                for row in db.execute(
                    "SELECT kind,count(*) n FROM formula_nodes GROUP BY kind"
                )
            }
            formula_db_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        finally:
            db.close()
        reservoir = self.reservoir.stats()
        journal_bytes = self.journal_path.stat().st_size if self.journal_path.exists() else 0
        entropy_index_bytes = (
            self.reservoir.db_path.stat().st_size
            if self.reservoir.db_path.exists()
            else 0
        )
        authoritative_physical = int(reservoir["segment_bytes"]) + int(journal_bytes)
        operational_physical = (
            authoritative_physical
            + int(formula_db_bytes)
            + int(entropy_index_bytes)
        )
        return {
            "schema": "entity-btdu-formula-stats-v2",
            "objects": objects,
            "logical_object_bytes": logical,
            "formula_nodes": nodes,
            "nodes_by_kind": by_kind,
            "irreducible_atom_tape_bytes": int(reservoir["unique_raw_chunk_bytes"]),
            "entropy_reservoir_stored_bytes": int(reservoir["stored_chunk_bytes"]),
            "entropy_segment_bytes": int(reservoir["segment_bytes"]),
            "formula_journal_bytes": int(journal_bytes),
            "formula_index_bytes": int(formula_db_bytes),
            "entropy_index_bytes": int(entropy_index_bytes),
            "authoritative_primary_physical_bytes": authoritative_physical,
            "operational_physical_bytes": operational_physical,
            "logical_to_primary_reduction_fraction": 0.0
            if logical == 0
            else 1.0 - authoritative_physical / logical,
            "formula_is_authority": True,
            "indexes_are_rebuildable": True,
            "reservoir": reservoir,
        }

    def formula_root(self) -> str:
        db = self._db()
        try:
            rows = [
                tuple(r)
                for r in db.execute(
                    """SELECT formula_object_id,content_sha256,size_bytes,root_node_id,formula_sha256
                    FROM formula_objects ORDER BY formula_object_id"""
                )
            ]
        finally:
            db.close()
        return _sha({"schema": FORMULA_SCHEMA, "objects": rows})

    def verify(self, *, deep: bool = False) -> dict[str, Any]:
        problems: list[str] = []
        db = self._db()
        try:
            quick = db.execute("PRAGMA quick_check").fetchone()[0]
            if quick != "ok":
                problems.append("sqlite:" + str(quick))
            objects = [
                row["formula_object_id"]
                for row in db.execute("SELECT formula_object_id FROM formula_objects")
            ]
        finally:
            db.close()
        reservoir = self.reservoir.verify(deep=False)
        if not reservoir["pass"]:
            problems.append("entropy_reservoir")
        journal = self.journal_status(deep=deep)
        if not journal["pass"]:
            problems.append("formula_journal")
        if deep:
            for object_id in objects:
                check = self.verify_object(str(object_id), deep=True)
                if not check["pass"]:
                    problems.append("object:" + str(object_id))
        return {
            "schema": "entity-btdu-formula-kernel-verification-v2",
            "pass": not problems,
            "deep": bool(deep),
            "formula_root": self.formula_root(),
            "journal": journal,
            "stats": self.stats(),
            "problems": problems,
        }

    def close(self) -> None:
        self.reservoir.close()
