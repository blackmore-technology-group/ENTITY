"""Streaming, integrity-verified formula DataChip shard set (EXPERIMENTAL).

Additive packaging for files larger than v0.2's 64MiB per-chip bound.
This is a byte-integrity format, NOT a signed identity, a rights passport,
a secure monotonic store, or permission to export. Consumers MUST provide an
externally authenticated, current and action-specific policy callback.
"""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable
import zipfile

from .formula_optimizer import pack_segmented_formula_bytes
from .formula_chip import MAX_OUTPUT, _open, _verified_chunks, verify_formula
from .processor import DataChipError, _canon, _pairwise_no_duplicates

SCHEMA = "entity-datachip-shardset-v0.1"
MAX_TOTAL = 4 * 1024 * 1024 * 1024
MAX_SHARDS = 4096
MAX_MANIFEST = 2 * 1024 * 1024
DEFAULT_SHARD = 16 * 1024 * 1024
ROOT_FIELDS = {"schema", "source_bytes", "source_sha256", "shard_bytes",
               "shards", "root_id"}
SHARD_FIELDS = {"index", "name", "content_bytes", "content_sha256",
                "archive_sha256", "chip_id"}

def _digest_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024*1024), b""):
            h.update(data)
    return h.hexdigest()

def _sha(s: Any) -> bool:
    return type(s) is str and len(s) == 64 and all(x in "0123456789abcdef" for x in s)

def _strict_number(n: Any, low: int, high: int) -> int:
    if type(n) is not int or n < low or n > high:
        raise DataChipError("invalid shard set integer")
    return n

def _validate(doc: Any) -> dict[str, Any]:
    if type(doc) is not dict or set(doc) != ROOT_FIELDS or doc["schema"] != SCHEMA:
        raise DataChipError("unsupported shard set manifest")
    total = _strict_number(doc["source_bytes"], 0, MAX_TOTAL)
    chunk_size = _strict_number(doc["shard_bytes"], 1024*1024, MAX_OUTPUT)
    if chunk_size & (chunk_size-1):
        raise DataChipError("non-power-of-two shard size")
    if not _sha(doc["source_sha256"]):
        raise DataChipError("invalid source hash")
    shards = doc["shards"]
    if type(shards) is not list or len(shards) > MAX_SHARDS:
        raise DataChipError("invalid shard collection")
    if len(shards) != ((total + chunk_size-1)//chunk_size):
        raise DataChipError("missing or extra shard")
    size = 0
    for idx, entry in enumerate(shards):
        if type(entry) is not dict or set(entry) != SHARD_FIELDS:
            raise DataChipError("invalid shard entry")
        if type(entry["index"]) is not int or entry["index"] != idx:
            raise DataChipError("out of sequence shard")
        if entry["name"] != "chunks/%08d.edcf" % idx:
            raise DataChipError("unsafe shard path")
        amount = _strict_number(entry["content_bytes"], 1, chunk_size)
        if idx < len(shards)-1 and amount != chunk_size:
            raise DataChipError("incomplete interior shard")
        if not (_sha(entry["content_sha256"]) and _sha(entry["archive_sha256"])):
            raise DataChipError("invalid shard hash")
        if (type(entry["chip_id"]) is not str or
                not entry["chip_id"].startswith("edc:formula:sha256:") or
                not _sha(entry["chip_id"][len("edc:formula:sha256:") :])):
            raise DataChipError("invalid formula chip identifier")
        size += amount
    if size != total:
        raise DataChipError("shard size total mismatch")
    identity = doc["root_id"]
    expected = "edc:shardset:sha256:" + sha256(_canon({k:v for k,v in doc.items()
                                                  if k != "root_id"})).hexdigest()
    if type(identity) is not str or identity != expected:
        raise DataChipError("invalid shard set identity")
    return doc

def _read(root: Path) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise DataChipError("invalid shard set directory")
    path = root / "manifest.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST:
        raise DataChipError("invalid shard set manifest file")
    try:
        raw = path.read_bytes()
        doc = json.loads(raw, object_pairs_hook=_pairwise_no_duplicates)
    except (UnicodeError, ValueError, OSError) as e:
        raise DataChipError("invalid shard set JSON") from e
    _validate(doc)
    if raw != _canon(doc):
        raise DataChipError("noncanonical shard set manifest")
    chunks = root / "chunks"
    if not chunks.is_dir() or chunks.is_symlink():
        raise DataChipError("unsafe chunks directory")
    actual = {p.name for p in chunks.iterdir()}
    expected = {("%08d.edcf" % i) for i in range(len(doc["shards"]))}
    if actual != expected:
        raise DataChipError("missing or unexpected shard members")
    if {p.name for p in root.iterdir()} != {"manifest.json", "chunks"}:
        raise DataChipError("unexpected shard set root entries")
    return doc

@contextmanager
def _publish_lock(parent: Path):
    lock = parent / ".entity-datac-shardset.lock"
    if lock.is_symlink():
        raise DataChipError("unsafe publication lock")
    with lock.open("a+b") as fd:
        fd.seek(0, os.SEEK_END)
        if not fd.tell():
            fd.write(b"\0")
            fd.flush()
            os.fsync(fd.fileno())
        fd.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)

def pack_shardset(source: str | Path, target: str | Path, *,
                  shard_bytes: int = DEFAULT_SHARD) -> dict[str, Any]:
    original = Path(source)
    dest = Path(target)
    if original.is_symlink() or not original.is_file():
        raise DataChipError("source must be an ordinary existing file")
    size = original.stat().st_size
    _strict_number(size, 0, MAX_TOTAL)
    shard_bytes = _strict_number(shard_bytes, 1024*1024, MAX_OUTPUT)
    if shard_bytes & (shard_bytes-1):
        raise DataChipError("shard size must be power of two")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".edc-shardset-stage-",dir=dest.parent))
    published = False
    try:
        (stage/"chunks").mkdir()
        source_stat = original.stat()
        full_digest = sha256()
        entries = []
        with original.open("rb") as stream:
            while True:
                raw = stream.read(shard_bytes)
                if not raw:
                    break
                if len(entries) >= MAX_SHARDS:
                    raise DataChipError("too many formula shards")
                i = len(entries)
                name = "chunks/%08d.edcf" % i
                path = stage / name
                doc = pack_segmented_formula_bytes(raw, path)
                full_digest.update(raw)
                entries.append({"index":i,"name":name,
                  "content_bytes":len(raw),"content_sha256":sha256(raw).hexdigest(),
                  "archive_sha256":_digest_file(path),"chip_id":doc["chip_id"]})
        final_stat = original.stat()
        if (final_stat.st_size != source_stat.st_size or
                final_stat.st_mtime_ns != source_stat.st_mtime_ns or
                sum(e["content_bytes"] for e in entries) != source_stat.st_size):
            raise DataChipError("source changed during packaging")
        doc = {"schema":SCHEMA,"source_bytes":size,
               "source_sha256":full_digest.hexdigest(),
               "shard_bytes":shard_bytes,"shards":entries}
        doc["root_id"] = "edc:shardset:sha256:" + sha256(_canon(doc)).hexdigest()
        body = _canon(doc)
        if len(body) > MAX_MANIFEST:
            raise DataChipError("shard set manifest too large")
        with (stage/"manifest.json").open("xb") as file:
            file.write(body)
            file.flush()
            os.fsync(file.fileno())
        verified = verify_shardset(stage)
        if verified["source_sha256"] != doc["source_sha256"]:
            raise DataChipError("staged shard set hash mismatch")
        with _publish_lock(dest.parent):
            if dest.exists() or dest.is_symlink():
                raise FileExistsError(str(dest))
            os.rename(stage, dest)
            published = True
        return doc
    finally:
        if not published:
            shutil.rmtree(stage, ignore_errors=True)

def _stream_verified(root: Path, doc: dict[str, Any], sink: Any = None) -> str:
    h = sha256()
    n = 0
    for entry in doc["shards"]:
        path = root / entry["name"]
        if path.is_symlink() or not path.is_file():
            raise DataChipError("unsafe or missing formula shard")
        if _digest_file(path) != entry["archive_sha256"]:
            raise DataChipError("formula shard archive tampered")
        with zipfile.ZipFile(path) as zf:
            chipdoc = _open(zf)
            if (chipdoc["chip_id"] != entry["chip_id"] or
                    chipdoc["content_bytes"] != entry["content_bytes"] or
                    chipdoc["content_sha256"] != entry["content_sha256"]):
                raise DataChipError("formula shard manifest mismatch")
            for part in _verified_chunks(zf, chipdoc):
                n += len(part)
                h.update(part)
                if sink is not None:
                    sink.write(part)
    if n != doc["source_bytes"] or h.hexdigest() != doc["source_sha256"]:
        raise DataChipError("full shard set content mismatch")
    return h.hexdigest()

def verify_shardset(root: str | Path) -> dict[str, Any]:
    source = Path(root)
    doc = _read(source)
    digest = _stream_verified(source, doc)
    return {"root_id":doc["root_id"],"source_sha256":digest,
            "source_bytes":doc["source_bytes"],"shards":len(doc["shards"]),
            "integrity_verified":True,"issuer_authenticated":False,
            "rights_authorized":False}

def export_shardset(root: str | Path, target: str | Path, *,
                    authorize: Callable[..., bool]) -> dict[str, Any]:
    if not callable(authorize):
        raise PermissionError("trusted host policy required")
    source = Path(root)
    doc = _read(source)
    if authorize("dataplane:export", doc) is not True:
        raise PermissionError("shard set export denied by host")
    output = Path(target)
    if output.exists() or output.is_symlink():
        raise FileExistsError(str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    tempname = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".edc-shardset-export-",
             suffix=".tmp",dir=output.parent,delete=False) as outputfile:
            tempname = outputfile.name
            # Re-evaluate current host policy before EACH chip and bind it to
            # the current complete root manifest; caller must check revocation.
            h = sha256()
            count = 0
            for entry in doc["shards"]:
                if authorize("dataplane:export", doc) is not True:
                    raise PermissionError("shard export authorization expired")
                shard = source / entry["name"]
                if shard.is_symlink() or not shard.is_file():
                    raise DataChipError("unsafe/missing shard")
                if _digest_file(shard) != entry["archive_sha256"]:
                    raise DataChipError("shard altered since inspection")
                with zipfile.ZipFile(shard) as zf:
                    form = _open(zf)
                    if (form["chip_id"] != entry["chip_id"] or
                            form["content_sha256"] != entry["content_sha256"] or
                            form["content_bytes"] != entry["content_bytes"]):
                        raise DataChipError("altered chip during export")
                    for part in _verified_chunks(zf, form):
                        outputfile.write(part)
                        h.update(part)
                        count += len(part)
            if count != doc["source_bytes"] or h.hexdigest() != doc["source_sha256"]:
                raise DataChipError("final reconstructed content mismatch")
            outputfile.flush()
            os.fsync(outputfile.fileno())
        os.link(tempname, output)
    finally:
        if tempname is not None:
            Path(tempname).unlink(missing_ok=True)
    return {"root_id":doc["root_id"],"bytes":doc["source_bytes"],
            "sha256":doc["source_sha256"],
            "authorized_by":"external_host_policy"}
