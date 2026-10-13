"""Regressions for opt-in segment-aware formula compiler."""
import hashlib
import random
import tempfile
import unittest
from pathlib import Path

from sdk.datachip.formula_chip import (pack_formula_bytes, verify_formula,
                                       export_formula, inspect_formula)
from sdk.datachip.formula_optimizer import pack_segmented_formula_bytes
from sdk.datachip.processor import DataChipError


class SegmentedFormulaTests(unittest.TestCase):
    def _roundtrip(self, raw, segment_bytes=1 << 20):
        with tempfile.TemporaryDirectory() as d:
            chip = Path(d) / "subject.edcf"
            out = Path(d) / "decoded.bin"
            doc = pack_segmented_formula_bytes(raw, chip, segment_bytes=segment_bytes)
            proof = verify_formula(chip)
            self.assertEqual(proof["content_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(doc["content_sha256"], proof["content_sha256"])
            self.assertFalse(proof["rights_authorized"])
            self.assertEqual(inspect_formula(chip)["chip_id"], doc["chip_id"])
            with self.assertRaises(PermissionError):
                export_formula(chip, out, authorize=None)
            self.assertFalse(out.exists())
            export_formula(chip, out, authorize=lambda action, manifest:
                           action == "dataplane:export" and manifest["chip_id"] == doc["chip_id"])
            self.assertEqual(out.read_bytes(), raw)
            return chip.stat().st_size

    def test_empty_onebyte_and_boundary(self):
        for n in (0, 1, 7, 65535, 65536, 65537, 1048576, 1048577):
            with self.subTest(n=n):
                self._roundtrip(b"XYZ01234" * (n // 8) + b"XYZ01234"[:n % 8], 65536)

    def test_random_entropy_exact(self):
        raw = random.Random(113).randbytes(2 * 1024 * 1024 + 77)
        self._roundtrip(raw)

    def test_mixed_periodic_is_smaller_than_canonical(self):
        raw = random.Random(2026).randbytes(1024 * 1024) + (
            b"trail,49.03,-118.45,840,public\n" * 300000)[:7 * 1024 * 1024]
        with tempfile.TemporaryDirectory() as d:
            old = Path(d) / "legacy.edcf"
            pack_formula_bytes(raw, old)
            baseline = old.stat().st_size
        optimized = self._roundtrip(raw)
        self.assertLess(optimized, baseline // 2)

    def test_no_hidden_loss_for_period_phase_shift(self):
        raw = (b"Z" * 19) + (b"abcde" * 420000) + (b"x" * 13)
        self._roundtrip(raw, 65536)

    def test_invalid_limits_fail(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.edcf"
            for size in (False, 0, 131071, 2 * 1024 * 1024):
                with self.subTest(size=size):
                    with self.assertRaises(ValueError):
                        pack_segmented_formula_bytes(b"x", path, segment_bytes=size)
            with self.assertRaises(DataChipError):
                pack_segmented_formula_bytes(b"z" * (64 * 1024 * 1024 + 1), path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
