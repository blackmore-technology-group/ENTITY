from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from sdk.datachip import (
    DataChipError, export_chip, inspect_chip, pack_btdu_formula,
    pack_file, pack_stream, verify_chip,
)
from sdk.datachip import processor as edc


def make_blob(n: int) -> bytes:
    part = hashlib.sha256(b"independent-datachip-fixture").digest()
    return (part * (n // len(part) + 1))[:n]


class DataChipPortableTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="entity-datac-")
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def chip(self, name="asset.edc"):
        return self.dir / name

    def _tamper(self, from_chip: Path, to_chip: Path,
                member: str, replacement: bytes):
        with zipfile.ZipFile(from_chip) as z:
            items = [(i, z.read(i.filename)) for i in z.infolist()]
        with zipfile.ZipFile(to_chip, "w") as z:
            for info, body in items:
                z.writestr(info, replacement if info.filename == member else body)

    def test_empty_roundtrip_and_deterministic_identity(self):
        first = pack_stream([], self.chip("a.edc"))
        second = pack_stream([b""], self.chip("b.edc"))
        self.assertEqual(first, second)
        self.assertEqual(first["content_sha256"], hashlib.sha256(b"").hexdigest())
        self.assertEqual(verify_chip(self.chip("a.edc"))["content_bytes"], 0)

    def test_streaming_multichunk_and_exact_authorized_export(self):
        data = make_blob(2 * edc.CHUNK_SIZE + 321)
        original = self.dir / "original.bin"
        original.write_bytes(data)
        chip = self.chip()
        record = pack_file(original, chip, claimed_issuer="example.entity",
                           rights_passport_ref="rp:example:unverified",
                           lineage_refs=["source:synthetic:001"])
        self.assertEqual(record["content_bytes"], len(data))
        self.assertEqual(len(record["chunks"]), 3)
        self.assertTrue(verify_chip(chip)["integrity_verified"])
        self.assertFalse(verify_chip(chip)["rights_authorized"])
        dest = self.dir / "output.bin"
        receipt = export_chip(chip, dest, authorize=lambda action, manifest:
                              action == "dataplane:export" and
                              manifest["chip_id"] == record["chip_id"])
        self.assertEqual(receipt["exported_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(dest.read_bytes(), data)
        self.assertEqual(original.read_bytes(), data)

    def test_export_defaults_to_deny(self):
        chip = self.chip()
        pack_stream([b"confidential"], chip, rights_passport_ref="rp:asserted")
        target = self.dir / "leak.txt"
        for policy in (None, lambda *_: False, lambda *_: 1):
            with self.assertRaises(PermissionError):
                export_chip(chip, target, authorize=policy)
            self.assertFalse(target.exists())

    def test_export_never_overwrites(self):
        chip = self.chip()
        pack_stream([b"hello"], chip)
        dest = self.dir / "exists"
        dest.write_bytes(b"unchanged")
        with self.assertRaises(FileExistsError):
            export_chip(chip, dest, authorize=lambda *_: True)
        self.assertEqual(dest.read_bytes(), b"unchanged")

    def test_chip_write_never_overwrites(self):
        chip = self.chip()
        chip.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            pack_stream([b"danger"], chip)
        self.assertEqual(chip.read_bytes(), b"keep")

    def test_corrupted_chunk_rejected(self):
        source = self.chip("valid.edc")
        pack_stream([b"ABC" * 60], source)
        bad = self.chip("bad.edc")
        with zipfile.ZipFile(source) as z:
            obj = json.loads(z.read("manifest.json"))
        path = "chunks/" + obj["chunks"][0]["sha256"] + ".bin"
        self._tamper(source, bad, path, b"X" * 180)
        with self.assertRaises(DataChipError):
            verify_chip(bad)
        out = self.dir / "bad_output"
        with self.assertRaises(DataChipError):
            export_chip(bad, out, authorize=lambda *_: True)
        self.assertFalse(out.exists())

    def test_schema_tampering_rejected(self):
        source = self.chip("valid.edc")
        pack_stream([b"data"], source)
        with zipfile.ZipFile(source) as z:
            doc = json.loads(z.read("manifest.json"))
        doc["rights_passport_ref"] = "rights:altered"
        bad = self.chip("changed.edc")
        self._tamper(source, bad, "manifest.json", edc._canon(doc))
        with self.assertRaises(DataChipError):
            inspect_chip(bad)

    def test_unsupported_schema_rejected_even_with_recomputed_digest(self):
        source = self.chip("valid.edc")
        pack_stream([b"data"], source)
        with zipfile.ZipFile(source) as z:
            doc = json.loads(z.read("manifest.json"))
        doc["schema"] = "entity-datachip-remote-code-v99"
        doc["chip_id"] = "edc:sha256:" + edc._sha(edc._canon({
            k: v for k, v in doc.items() if k != "chip_id"
        }))
        bad = self.chip("wrong-schema.edc")
        self._tamper(source, bad, "manifest.json", edc._canon(doc))
        with self.assertRaises(DataChipError):
            inspect_chip(bad)

    def test_traversal_member_and_duplicate_member_rejected(self):
        src = self.chip("valid.edc")
        pack_stream([b"one"], src)
        for name in ("../../unsafe", "chunks/extra.bin"):
            dst = self.chip(name.replace("/", "_") + ".edc")
            with zipfile.ZipFile(src) as z:
                items = [(i, z.read(i.filename)) for i in z.infolist()]
            with zipfile.ZipFile(dst, "w") as z:
                for info, body in items:
                    z.writestr(info, body)
                z.writestr(name, b"evil")
            with self.assertRaises(DataChipError):
                inspect_chip(dst)

    def test_duplicate_json_keys_rejected(self):
        src = self.chip("valid.edc")
        pack_stream([b"A"], src)
        with zipfile.ZipFile(src) as z:
            raw = z.read("manifest.json")
        bad_raw = raw.replace(b'"schema":', b'"schema":"untrusted","schema":', 1)
        dst = self.chip("dupjson.edc")
        self._tamper(src, dst, "manifest.json", bad_raw)
        with self.assertRaises(DataChipError):
            inspect_chip(dst)

    def test_bounded_ints_bool_rejected(self):
        src = self.chip("valid.edc")
        pack_stream([b"x"], src)
        with zipfile.ZipFile(src) as z:
            doc = json.loads(z.read("manifest.json"))
        doc["content_bytes"] = True
        doc["chip_id"] = "edc:sha256:" + edc._sha(edc._canon({
            k: v for k, v in doc.items() if k != "chip_id"
        }))
        dst = self.chip("badint.edc")
        self._tamper(src, dst, "manifest.json", edc._canon(doc))
        with self.assertRaises(DataChipError):
            inspect_chip(dst)

    def test_foreign_symlink_source_rejected(self):
        src = self.dir / "payload"
        src.write_bytes(b"data")
        link = self.dir / "link"
        try:
            link.symlink_to(src)
        except (NotImplementedError, OSError):
            self.skipTest("unprivileged symlink unavailable on this filesystem")
        with self.assertRaises(DataChipError):
            pack_file(link, self.chip())


class DataChipBTDUTests(unittest.TestCase):
    def test_existing_btdu_formula_produces_independently_readable_copy(self):
        spec = importlib.util.spec_from_file_location(
            "edc_btdu_formula", REPO / "src" / "40_BTDU" / "formula_kernel.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix="edc-kernel-") as td:
            root = Path(td)
            kernel = module.BTDUFormulaKernel(
                root / "store", min_chunk=16 * 1024,
                avg_chunk=64 * 1024, max_chunk=256 * 1024)
            try:
                raw = b"ENTITY|PORTABLE|BTDU|" * 8000
                obj = kernel.put_bytes(raw)
                chip = root / "portable.edc"
                doc = pack_btdu_formula(kernel, obj["formula_object_id"], chip)
                self.assertEqual(doc["btdu_formula_object_ref"], obj["formula_object_id"])
                self.assertTrue(verify_chip(chip)["integrity_verified"])
            finally:
                kernel.close()
            # After the source formula kernel is closed, the self-contained copy
            # remains independently verifiable and exportable.
            out = root / "offline-export.bin"
            export_chip(chip, out, authorize=lambda *_: True)
            self.assertEqual(out.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
