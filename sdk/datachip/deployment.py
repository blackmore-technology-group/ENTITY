"""Fail-closed signed DataChip update staging and atomic activation prototype.

Only installs *data artifacts*. Never downloads code, grants permissions,
deletes original data, invokes OS installers or changes ENTITY databases.

Local anti-rollback prevents accidental downgrade but is NOT tamperproof
without an OS-secure monotonic counter. No automatic rollback to vulnerable
content. Production rollout requires secure-host attestation and fault testing.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from .application import verify_bundle
from .processor import DataChipError, _canon

_SEQ = re.compile(r"^release-([0-9]{8})$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_MAX_RELEASE_BYTES = 4 * 1024 * 1024 * 1024
_POINTER_KEYS = {"schema", "release_seq", "release_dir", "signed_bundle_sha256"}
_POINTER_SCHEMA = "btg-datac-active-pointer-v0.1"


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _durable_file(path: Path, data: bytes) -> None:
    with path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def _fsync_dir(path: Path) -> None:
    if os.name != "posix":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class DataChipDeploymentManager:
    def __init__(self, root: str | Path, *, app_id: str,
                 platform: str, trusted_bundle_keys: Mapping[str, bytes]):
        self.root = Path(root)
        self.app = app_id
        self.platform = platform
        self.keys = trusted_bundle_keys
        self.releases = self.root / "releases"
        self.pointer = self.root / "active.json"
        if self.root.is_symlink() or self.releases.is_symlink():
            raise DataChipError("symlinked data store is forbidden")
        self.releases.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _exclusive_lock(self):
        """Serialize activation across processes on Windows and POSIX hosts."""
        lockfile = self.root / ".datac-activation.lock"
        if lockfile.is_symlink():
            raise DataChipError("unsafe lock file")
        with lockfile.open("a+b") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() == 0:
                f.write(b"\0")
                f.flush()
                os.fsync(f.fileno())
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _sequence(signed: dict[str, Any]) -> int:
        body = signed.get("body") if type(signed) is dict else None
        value = body.get("release_id") if type(body) is dict else None
        match = _SEQ.fullmatch(value) if type(value) is str else None
        if not match:
            raise DataChipError("deployment requires signed release-######## identifier")
        seq = int(match.group(1))
        if seq == 0:
            raise DataChipError("release zero is reserved")
        return seq

    @staticmethod
    def _bundle_digest(signed: dict[str, Any]) -> str:
        return hashlib.sha256(_canon(signed)).hexdigest()

    def _read_pointer(self) -> dict[str, Any] | None:
        if not self.pointer.exists():
            return None
        if self.pointer.is_symlink() or not self.pointer.is_file():
            raise DataChipError("unsafe active pointer")
        try:
            p = json.loads(self.pointer.read_bytes())
        except (OSError, ValueError) as e:
            raise DataChipError("active pointer damaged") from e
        if type(p) is not dict or set(p) != _POINTER_KEYS or p["schema"] != _POINTER_SCHEMA:
            raise DataChipError("invalid active pointer schema")
        seq = p["release_seq"]
        name = p["release_dir"]
        digest = p["signed_bundle_sha256"]
        if type(seq) is not int or not 1 <= seq <= 99999999:
            raise DataChipError("invalid active release number")
        if type(name) is not str or name != f"release-{seq:08d}-{digest[:16]}":
            raise DataChipError("invalid active directory")
        if type(digest) is not str or not _SHA.fullmatch(digest):
            raise DataChipError("invalid active digest")
        return p

    def active(self) -> dict[str, Any] | None:
        """Cold-read and independently reverify every installed active chip."""
        pointer = self._read_pointer()
        if pointer is None:
            return None
        folder = self.releases / pointer["release_dir"]
        if folder.is_symlink() or not folder.is_dir():
            raise DataChipError("active release directory missing")
        data = folder / "signed_bundle.json"
        if data.is_symlink() or not data.is_file():
            raise DataChipError("signed release lockfile missing")
        try:
            signed = json.loads(data.read_bytes())
        except (ValueError, OSError) as e:
            raise DataChipError("signed lockfile unreadable") from e
        if self._bundle_digest(signed) != pointer["signed_bundle_sha256"]:
            raise DataChipError("signed bundle lockfile changed")
        if self._sequence(signed) != pointer["release_seq"]:
            raise DataChipError("active version mismatch")
        mapping: dict[str, Path] = {}
        for module in signed["body"]["modules"]:
            chip_hash = module["sha256"]
            file = folder / (chip_hash + ".edc")
            if file.is_symlink() or not file.is_file():
                raise DataChipError("active module disappeared")
            mapping[module["chip_id"]] = file
        result = verify_bundle(signed, trusted_bundle_keys=self.keys,
                               expected_app=self.app,
                               expected_platform=self.platform,
                               available_chips=mapping)
        return {
            "schema": "btg-datac-active-release-v0.1",
            "sequence": pointer["release_seq"],
            "release_id": signed["body"]["release_id"],
            "release_dir": pointer["release_dir"],
            "signed_bundle_sha256": pointer["signed_bundle_sha256"],
            "verified_manifest": result,
            "chip_paths": mapping,
        }

    def stage_and_activate(self, signed: dict[str, Any], *,
                           local_chips: Mapping[str, str | Path],
                           before_commit: Callable[[], Any] | None = None
                           ) -> dict[str, Any]:
        """Serialize signed data updates and atomically activate a verified version."""
        with self._exclusive_lock():
            return self._stage_and_activate_locked(
                signed, local_chips=local_chips, before_commit=before_commit)

    def _stage_and_activate_locked(self, signed: dict[str, Any], *,
                                   local_chips: Mapping[str, str | Path],
                                   before_commit: Callable[[], Any] | None = None
                                   ) -> dict[str, Any]:
        """Stage all bytes, verify again, then switch one atomic pointer.

        Incomplete/malformed/revoked content is never made active. Signed
        release sequence must increase. Old version remains on disk for
        explicitly authorized later disaster recovery, not auto-downgrade.
        """
        newseq = self._sequence(signed)
        digest = self._bundle_digest(signed)
        current = self.active()
        if current:
            if newseq < current["sequence"]:
                raise PermissionError("anti-rollback downgrade rejected")
            if newseq == current["sequence"]:
                if digest == current["signed_bundle_sha256"]:
                    return {"status": "already-active", "sequence": newseq}
                raise PermissionError("signed release sequence collision")
        # Verify source authenticity before copying. Required rights remain
        # locked; installer does not turn a signed app package into a grant.
        check = verify_bundle(signed, trusted_bundle_keys=self.keys,
                              expected_app=self.app,
                              expected_platform=self.platform,
                              available_chips=local_chips)
        total = 0
        for module in signed["body"]["modules"]:
            src = local_chips[module["chip_id"]]
            size = Path(src).stat().st_size
            total += size
            if total > _MAX_RELEASE_BYTES:
                raise DataChipError("release exceeds physical data quota")
        name = f"release-{newseq:08d}-{digest[:16]}"
        final = self.releases / name
        if final.exists() or final.is_symlink():
            raise PermissionError("release directory already exists; no overwrite")
        temporary: Path | None = Path(tempfile.mkdtemp(
            prefix=".datac-stage-", dir=self.releases))
        try:
            entries = {}
            for module in signed["body"]["modules"]:
                cid, sha = module["chip_id"], module["sha256"]
                if sha in entries:
                    continue
                src = Path(local_chips[cid])
                if src.is_symlink() or not src.is_file():
                    raise DataChipError("source file is not a regular file")
                target = temporary / (sha + ".edc")
                with src.open("rb") as incoming, target.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if _file_digest(target) != sha:
                    raise DataChipError("source changed during staging")
                entries[sha] = target
            _durable_file(temporary / "signed_bundle.json", _canon(signed))
            staged = {m["chip_id"]: entries[m["sha256"]]
                      for m in signed["body"]["modules"]}
            verify_bundle(signed, trusted_bundle_keys=self.keys,
                          expected_app=self.app, expected_platform=self.platform,
                          available_chips=staged)
            _fsync_dir(temporary)
            if before_commit is not None:
                before_commit()  # injection point for power-loss/fault testing
            # Verify active state again before switch for concurrent mutation.
            old = self.active()
            if (old["sequence"] if old else None) != (
                    current["sequence"] if current else None):
                raise DataChipError("concurrent active release change")
            temporary.rename(final)
            temporary = None
            _fsync_dir(self.releases)
            p = {"schema": _POINTER_SCHEMA, "release_seq": newseq,
                 "release_dir": name, "signed_bundle_sha256": digest}
            temp_pointer = self.root / (".active-" + digest[:20] + ".tmp")
            if temp_pointer.exists():
                raise DataChipError("active pointer staging file collision")
            try:
                _durable_file(temp_pointer, _canon(p))
                os.replace(temp_pointer, self.pointer)
                _fsync_dir(self.root)
            finally:
                temp_pointer.unlink(missing_ok=True)
            return {"status": "activated", "sequence": newseq,
                    "signed_bundle_sha256": digest,
                    "rights_locked_modules": check["rights_locked_modules"],
                    "native_code_modified": False}
        finally:
            if temporary is not None and temporary.exists():
                shutil.rmtree(temporary)
