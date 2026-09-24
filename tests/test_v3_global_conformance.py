from __future__ import annotations
import hashlib, json, pathlib, unittest
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO = ROOT / "protocol" / "v3"
VECTORS = PROTO / "global_vectors"
SCHEMA_PATH = PROTO / "ENTITY_GLOBAL_INFRASTRUCTURE.schema.json"
MANIFEST_PATH = VECTORS / "VECTOR_MANIFEST.json"

class GlobalInfrastructureConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
        cls.validator = Draft202012Validator(cls.schema)
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.schema)
        self.assertGreaterEqual(len(self.schema.get("$defs", {})), 10)

    def test_vector_manifest_counts_and_hashes(self):
        entries = self.manifest["vectors"]
        self.assertEqual(self.manifest["valid_vectors"], 8)
        self.assertEqual(self.manifest["invalid_vectors"], 8)
        self.assertEqual(len(entries), 16)
        self.assertEqual(self.manifest["schema_sha256"], hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest())
        for entry in entries:
            path = VECTORS / entry["file"]
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_checksum_seal(self):
        for raw in (VECTORS / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
            if not raw.strip():
                continue
            expected, rel = raw.split(None, 1)
            path = (VECTORS / rel.strip()).resolve()
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(expected, hashlib.sha256(path.read_bytes()).hexdigest(), rel)

    def test_valid_and_invalid_vectors(self):
        valid = invalid = 0
        for entry in self.manifest["vectors"]:
            payload = json.loads((VECTORS / entry["file"]).read_text(encoding="utf-8-sig"))
            errors = list(self.validator.iter_errors(payload["record"]))
            if payload["expect"] == "VALID":
                self.assertEqual(errors, [], entry["file"])
                valid += 1
            else:
                self.assertTrue(errors, entry["file"])
                invalid += 1
        self.assertEqual(valid, 8)
        self.assertEqual(invalid, 8)

if __name__ == "__main__":
    unittest.main()


