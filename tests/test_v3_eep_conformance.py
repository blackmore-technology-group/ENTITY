import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO / "protocol/v3/ENTITY_EXCHANGE_PROTOCOL.schema.json"
VECTOR_DIR = REPO / "protocol/v3/eep_vectors"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ref_eep = load("v3_eep_conf_ref", REPO / "src/31_Profiles/exchange_protocol.py")
mirror_eep = load("v3_eep_conf_mirror", REPO / "src/32_V3_Hardening/exchange_protocol.py")


class V3EEPConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads((VECTOR_DIR / "VECTOR_MANIFEST.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def _schema_valid(self, record):
        return not list(self.validator.iter_errors(record))

    def _wire_valid(self, module, record):
        try:
            module.validate_signed_wire(record)
            return True
        except (TypeError, ValueError):
            return False

    def test_checksum_seal(self):
        for raw in (VECTOR_DIR / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
            expected, rel = raw.split("  ", 1)
            target = VECTOR_DIR.parent / rel
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(actual, expected, rel)

    def test_vectors_match_schema_and_wire_expectations(self):
        signed = set(self.manifest["signed_wire_schemas"])
        for vector in self.manifest["vectors"]:
            with self.subTest(vector=vector["name"]):
                record = json.loads((VECTOR_DIR / vector["path"]).read_text(encoding="utf-8"))
                schema_valid = self._schema_valid(record)
                self.assertEqual(schema_valid, vector["expected_schema_valid"])

                wire_expected = vector.get("expected_wire_valid")
                if record.get("schema") in signed:
                    self.assertIsNotNone(wire_expected)
                    ref_valid = self._wire_valid(ref_eep, record)
                    mirror_valid = self._wire_valid(mirror_eep, record)
                    self.assertEqual(ref_valid, wire_expected)
                    self.assertEqual(mirror_valid, wire_expected)
                    combined = schema_valid and ref_valid and mirror_valid
                else:
                    self.assertIsNone(wire_expected)
                    combined = schema_valid

                self.assertEqual(combined, vector["expected_valid"])

    def test_every_signed_wire_schema_has_a_valid_vector(self):
        valid_schemas = {
            v["record_schema"] for v in self.manifest["vectors"]
            if v["expected_valid"]
        }
        self.assertTrue(set(self.manifest["signed_wire_schemas"]).issubset(valid_schemas))


    def test_eep_conformance_manifest_self_verifies(self):
        manifest_path = REPO / "ENTITY_V3_EEP_CONFORMANCE_MANIFEST.json"
        evidence = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in evidence["files"]:
            target = REPO / entry["path"]
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(actual, entry["sha256"], entry["path"])
        base = {k: v for k, v in evidence.items() if k not in {"files", "snapshot_sha256"}}
        seed = json.dumps(base, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        seed += b"\n".join((e["path"] + " " + e["sha256"]).encode() for e in evidence["files"])
        self.assertEqual(hashlib.sha256(seed).hexdigest(), evidence["snapshot_sha256"])


if __name__ == "__main__":
    unittest.main()
