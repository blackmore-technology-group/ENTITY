"""ENTITY DataChip v0.1 experimental portable binary transport.

The DataChip is a verified *copy* of data, not BTDU primary storage. Its
rights, issuer and lineage fields are UNTRUSTED references: a host must supply
its own trusted authority/rights decision before extracting plaintext.

No formula evaluation, uploaded executable, filesystem path or network action
is supported by this parser. The v0.1 format is intentionally non-normative.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, BinaryIO, Callable, Iterable, Iterator
import zipfile

SCHEMA = "entity-datachip-portable-v0.1"
FORMAT = "portable-copy-chunks-sha256-v1"
CHUNK_SIZE = 1024 * 1024
MAX_BYTES = 1024 * 1024 * 1024
MAX_CHUNKS = 4096
MAX_MANIFEST_BYTES = 256 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHIP_ID = re.compile(r"^edc:sha256:[0-9a-f]{64}$")
_KEYS = frozenset({
    "schema", "format", "content_sha256", "content_bytes", "chunk_size",
    "chunks", "claimed_issuer", "rights_passport_ref",
    "lineage_refs", "btdu_formula_object_ref",
    "data_authority", "chip_id",
})


class DataChipError(ValueError):
    """Invalid, incomplete or corrupted portable DataChip."""


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairwise_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise DataChipError("duplicate manifest key")
        obj[key] = value
    return obj


def _reference(value: Any, *, optional: bool = True) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not (1 <= len(value) <= 300):
        raise DataChipError("invalid bounded reference")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise DataChipError("invalid reference control characters")
    return value


def _validate(manifest: Any) -> dict[str, Any]:
    if type(manifest) is not dict or set(manifest) != _KEYS:
        raise DataChipError("unsupported manifest field set")
    if manifest["schema"] != SCHEMA or manifest["format"] != FORMAT:
        raise DataChipError("unsupported schema or format")
    if manifest["data_authority"] != "export-copy-not-primary-storage":
        raise DataChipError("unsupported data authority")
    size = manifest["content_bytes"]
    if type(size) is not int or not 0 <= size <= MAX_BYTES:
        raise DataChipError("invalid or oversized content length")
    if type(manifest["chunk_size"]) is not int or manifest["chunk_size"] != CHUNK_SIZE:
        raise DataChipError("unsupported chunk size")
    if not isinstance(manifest["content_sha256"], str) or not SHA256.fullmatch(manifest["content_sha256"]):
        raise DataChipError("invalid content digest")
    entries = manifest["chunks"]
    if type(entries) is not list or len(entries) > MAX_CHUNKS:
        raise DataChipError("invalid chunk list")
    total = 0
    for i, entry in enumerate(entries):
        if type(entry) is not dict or set(entry) != {"sha256", "bytes"}:
            raise DataChipError("invalid chunk entry")
        n, digest = entry["bytes"], entry["sha256"]
        if type(n) is not int or not 1 <= n <= CHUNK_SIZE:
            raise DataChipError("invalid chunk length")
        if type(digest) is not str or not SHA256.fullmatch(digest):
            raise DataChipError("invalid chunk digest")
        if i < len(entries) - 1 and n != CHUNK_SIZE:
            raise DataChipError("non-final chunk has invalid length")
        total += n
        if total > MAX_BYTES:
            raise DataChipError("object exceeds cap")
    if total != size or (size == 0) != (len(entries) == 0):
        raise DataChipError("length does not match chunk list")
    for key in ("claimed_issuer", "rights_passport_ref", "btdu_formula_object_ref"):
        _reference(manifest[key])
    lineage = manifest["lineage_refs"]
    if type(lineage) is not list or len(lineage) > 32:
        raise DataChipError("invalid lineage list")
    for ref in lineage:
        _reference(ref, optional=False)
    if len(set(lineage)) != len(lineage):
        raise DataChipError("duplicate lineage reference")
    chip = manifest["chip_id"]
    if type(chip) is not str or not CHIP_ID.fullmatch(chip):
        raise DataChipError("invalid DataChip ID")
    body = {k: v for k, v in manifest.items() if k != "chip_id"}
    if chip != "edc:sha256:" + _sha(_canon(body)):
        raise DataChipError("DataChip manifest digest mismatch")
    return manifest


def _chunk_name(digest: str) -> str:
    return "chunks/" + digest + ".bin"


def _zipinfo(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.compress_type = zipfile.ZIP_STORED
    item.create_system = 3
    item.external_attr = (0o100644 << 16)
    return item


def _parts(stream: Iterable[bytes]) -> Iterator[bytes]:
    buff = bytearray()
    for part in stream:
        if not isinstance(part, (bytes, bytearray, memoryview)):
            raise TypeError("byte stream must contain only bytes")
        block = memoryview(part)
        pos = 0
        while pos < len(block):
            n = min(CHUNK_SIZE - len(buff), len(block) - pos)
            buff.extend(block[pos:pos + n])
            pos += n
            if len(buff) == CHUNK_SIZE:
                yield bytes(buff)
                buff.clear()
    if buff:
        yield bytes(buff)


def _new_manifest(*, content_sha256: str, size: int,
                  chunks: list[dict[str, Any]], claimed_issuer: str | None,
                  rights_passport_ref: str | None, lineage_refs: list[str],
                  btdu_formula_object_ref: str | None) -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "format": FORMAT,
        "content_sha256": content_sha256,
        "content_bytes": size,
        "chunk_size": CHUNK_SIZE,
        "chunks": chunks,
        "claimed_issuer": claimed_issuer,
        "rights_passport_ref": rights_passport_ref,
        "lineage_refs": lineage_refs,
        "btdu_formula_object_ref": btdu_formula_object_ref,
        "data_authority": "export-copy-not-primary-storage",
    }
    m = {**body, "chip_id": "edc:sha256:" + _sha(_canon(body))}
    _validate(m)
    return m


def pack_stream(stream: Iterable[bytes], target: str | Path, *,
                claimed_issuer: str | None = None,
                rights_passport_ref: str | None = None,
                lineage_refs: Iterable[str] = (),
                btdu_formula_object_ref: str | None = None,
                expected_sha256: str | None = None,
                expected_bytes: int | None = None) -> dict[str, Any]:
    """Create deterministic self-contained portable DataChip in a NEW output file.

    Trusted status/rights verification is out of scope. Caller-provided metadata
    is not evidence of issuer identity, valid rights or real-world truth.
    """
    for ref in (claimed_issuer, rights_passport_ref, btdu_formula_object_ref):
        _reference(ref)
    refs = list(lineage_refs)
    if len(refs) > 32 or len(set(refs)) != len(refs):
        raise DataChipError("invalid lineage references")
    for ref in refs:
        _reference(ref, optional=False)
    dest = Path(target)
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".edc-", suffix=".tmp",
                                         dir=dest.parent, delete=False) as temp:
            temp_name = temp.name
        digest = hashlib.sha256()
        chunks: list[dict[str, Any]] = []
        seen: set[str] = set()
        size = 0
        with zipfile.ZipFile(temp_name, "w", allowZip64=True) as zf:
            for chunk in _parts(stream):
                size += len(chunk)
                if size > MAX_BYTES or len(chunks) >= MAX_CHUNKS:
                    raise DataChipError("DataChip size limit exceeded")
                digest.update(chunk)
                name = _sha(chunk)
                chunks.append({"sha256": name, "bytes": len(chunk)})
                if name not in seen:
                    zf.writestr(_zipinfo(_chunk_name(name)), chunk)
                    seen.add(name)
            if expected_bytes is not None and (type(expected_bytes) is not int or size != expected_bytes):
                raise DataChipError("BTDU source size changed during export")
            if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
                raise DataChipError("BTDU source digest changed during export")
            manifest = _new_manifest(content_sha256=digest.hexdigest(), size=size,
                                     chunks=chunks, claimed_issuer=claimed_issuer,
                                     rights_passport_ref=rights_passport_ref,
                                     lineage_refs=refs,
                                     btdu_formula_object_ref=btdu_formula_object_ref)
            raw = _canon(manifest)
            if len(raw) > MAX_MANIFEST_BYTES:
                raise DataChipError("manifest exceeds size limit")
            zf.writestr(_zipinfo("manifest.json"), raw)
        # Never overwrite another file; a hard-link creates an atomic new name.
        os.link(temp_name, dest)
        return manifest
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)


def pack_file(source: str | Path, target: str | Path, **kw: Any) -> dict[str, Any]:
    """Package a local regular file; no source file is deleted or modified."""
    src = Path(source)
    if not src.is_file() or src.is_symlink():
        raise DataChipError("source must be a regular non-symlink file")
    with src.open("rb") as fh:
        return pack_stream(iter(lambda: fh.read(CHUNK_SIZE), b""), target, **kw)


def pack_btdu_formula(kernel: Any, object_id: str, target: str | Path,
                      **kw: Any) -> dict[str, Any]:
    """Export a verified portable *copy* through the existing BTDU formula API.

    This does not migrate/delete/alter the source kernel and is not a native
    portable formula interpreter. It carries the exact payload for offline use.
    """
    record = kernel.object_record(object_id)
    result = kernel.verify_object(object_id, deep=True)
    if result.get("pass") is not True:
        raise DataChipError("BTDU object deep verification failed")
    return pack_stream(kernel.iter_object(object_id), target,
                       btdu_formula_object_ref=str(object_id),
                       expected_sha256=record["content_sha256"],
                       expected_bytes=record["size_bytes"], **kw)


def _open_manifest(zf: zipfile.ZipFile) -> dict[str, Any]:
    entries = zf.infolist()
    if len(entries) > MAX_CHUNKS + 1:
        raise DataChipError("archive entry limit exceeded")
    names = [z.filename for z in entries]
    if len(names) != len(set(names)) or "manifest.json" not in names:
        raise DataChipError("duplicate or missing archive members")
    manifest_entry = zf.getinfo("manifest.json")
    if manifest_entry.compress_type != zipfile.ZIP_STORED or manifest_entry.file_size > MAX_MANIFEST_BYTES:
        raise DataChipError("manifest has invalid storage format or size")
    for item in entries:
        if item.flag_bits & 1 or item.compress_type != zipfile.ZIP_STORED:
            raise DataChipError("encrypted or compressed archive member unsupported")
        mode = (item.external_attr >> 16) & 0o170000
        if mode not in (0, 0o100000):
            raise DataChipError("non-regular archive member unsupported")
    try:
        raw = zf.read(manifest_entry)
        doc = json.loads(raw, object_pairs_hook=_pairwise_no_duplicates)
    except (UnicodeError, json.JSONDecodeError, OverflowError) as exc:
        raise DataChipError("invalid manifest JSON") from exc
    _validate(doc)
    if raw != _canon(doc):
        raise DataChipError("manifest JSON is not canonical")
    permitted = {"manifest.json"} | {_chunk_name(e["sha256"]) for e in doc["chunks"]}
    if set(names) != permitted:
        raise DataChipError("missing or unexpected archive member")
    for name in permitted - {"manifest.json"}:
        info = zf.getinfo(name)
        expected = next(e["bytes"] for e in doc["chunks"] if _chunk_name(e["sha256"]) == name)
        if info.file_size != expected:
            raise DataChipError("chunk stored size mismatch")
    return doc


def inspect_chip(path: str | Path) -> dict[str, Any]:
    """Parse strictly without accepting metadata as verified provenance."""
    try:
        with zipfile.ZipFile(path) as zf:
            return _open_manifest(zf)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, OSError) as exc:
        raise DataChipError("cannot read DataChip archive") from exc


def _read_verified(zf: zipfile.ZipFile, doc: dict[str, Any],
                   write_to: BinaryIO | None = None) -> None:
    total = 0
    digest = hashlib.sha256()
    for item in doc["chunks"]:
        hasher = hashlib.sha256()
        got = 0
        with zf.open(_chunk_name(item["sha256"])) as input_file:
            while True:
                block = input_file.read(65536)
                if not block:
                    break
                got += len(block)
                if got > item["bytes"]:
                    raise DataChipError("oversized chunk during read")
                hasher.update(block)
                digest.update(block)
                total += len(block)
                if write_to is not None:
                    write_to.write(block)
        if got != item["bytes"] or hasher.hexdigest() != item["sha256"]:
            raise DataChipError("chunk hash/length mismatch")
    if total != doc["content_bytes"] or digest.hexdigest() != doc["content_sha256"]:
        raise DataChipError("reconstructed content hash/length mismatch")


def verify_chip(path: str | Path) -> dict[str, Any]:
    """Integrity only: NEVER proof of identity, permissions, claims or signatures."""
    try:
        with zipfile.ZipFile(path) as zf:
            doc = _open_manifest(zf)
            _read_verified(zf, doc)
            return {
                "schema": "entity-datachip-verification-v0.1",
                "chip_id": doc["chip_id"],
                "content_sha256": doc["content_sha256"],
                "content_bytes": doc["content_bytes"],
                "integrity_verified": True,
                "issuer_authenticated": False,
                "rights_authorized": False,
                "lineage_authenticated": False,
            }
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, OSError) as exc:
        raise DataChipError("DataChip verification failed") from exc


def export_chip(path: str | Path, output: str | Path, *,
                authorize: Callable[[str, dict[str, Any]], bool]) -> dict[str, Any]:
    """Export with explicit trusted host policy. Default deny; cannot overwrite.

    Never pass a policy derived solely from the manifest's rights fields.
    Production clients must authenticate the user and active Rights Passport
    independently, including revocation, intended action and scope.
    """
    if not callable(authorize):
        raise PermissionError("trusted authorization callback required")
    doc = inspect_chip(path)
    if authorize("dataplane:export", doc) is not True:
        raise PermissionError("trusted host policy denied export")
    target = Path(output)
    if target.exists() or target.is_symlink():
        raise FileExistsError(str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".edc-export-", suffix=".tmp",
                                         dir=target.parent, delete=False) as temp:
            name = temp.name
            with zipfile.ZipFile(path) as zf:
                actual = _open_manifest(zf)
                if actual != doc:
                    raise DataChipError("manifest changed before export")
                _read_verified(zf, doc, write_to=temp)
            temp.flush()
            os.fsync(temp.fileno())
        os.link(name, target)
    finally:
        if name is not None:
            Path(name).unlink(missing_ok=True)
    return {"chip_id": doc["chip_id"], "exported_sha256": doc["content_sha256"],
            "bytes": doc["content_bytes"], "authority_source": "external-host-policy"}
