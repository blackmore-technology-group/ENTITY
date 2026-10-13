import pathlib
import subprocess
import sys
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO / "examples" / "verify_published_receipt.py"
FIXTURES = REPO / "examples" / "fixtures"
VALID = FIXTURES / "independent_node_receipt_valid.json"
TAMPERED = FIXTURES / "independent_node_receipt_tampered.json"


def run_tool(fixture: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), str(fixture)],
        capture_output=True,
        text=True,
        check=False,
    )


class VerifyPublishedReceiptExampleTests(unittest.TestCase):
    def test_valid_fixture_exits_zero(self):
        run = run_tool(VALID)
        self.assertEqual(run.returncode, 0, run.stderr or run.stdout)
        self.assertIn("file_sha256=", run.stdout)
        self.assertIn("PASS:", run.stdout)
        # The authenticity boundary stays in the output.
        self.assertIn("does not verify signatures", run.stderr)

    def test_tampered_fixture_exits_nonzero(self):
        run = run_tool(TAMPERED)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("receipt_sha256", run.stderr)

    def test_malformed_json_fails_closed(self):
        run = run_tool(FIXTURES / "independent_node_receipt_malformed.json")
        self.assertEqual(run.returncode, 2)
        self.assertIn("invalid JSON", run.stderr)

    def test_missing_required_field_fails_closed(self):
        run = run_tool(FIXTURES / "independent_node_receipt_missing_field.json")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("missing required field", run.stderr)
        self.assertIn("lineage_depth", run.stderr)

    def test_unsupported_schema_fails_closed(self):
        run = run_tool(FIXTURES / "independent_node_receipt_unsupported_schema.json")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("unsupported or missing receipt schema", run.stderr)

    def test_boolean_lineage_depth_is_rejected(self):
        # Python bool is an int subclass; the verifier must not accept it as depth.
        run = run_tool(FIXTURES / "independent_node_receipt_bool_depth.json")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("lineage_depth", run.stderr)

    def test_malformed_node_id_is_rejected(self):
        run = run_tool(FIXTURES / "independent_node_receipt_bad_node_id.json")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("receiver_node_id", run.stderr)


if __name__ == "__main__":
    unittest.main()
