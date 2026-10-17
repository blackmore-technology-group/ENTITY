from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/lineage_to_mermaid.py"
FIXTURE = ROOT / "examples/lineage_snapshot.json"
spec = importlib.util.spec_from_file_location("lineage_to_mermaid_example", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class LineageToMermaidTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_has_expected_direction_and_labels(self):
        self.assertEqual(
            tool.render_lineage(self.snapshot),
            "flowchart LR\n"
            "    %% Recorded relationships only; truth and rights are not verified.\n"
            '    n0["demo:edited"]\n'
            '    n1["demo:preview"]\n'
            '    n2["demo:source"]\n'
            '    n0 -->|"resize"| n1\n'
            '    n2 -->|"edit"| n0\n',
        )

    def test_record_and_object_order_do_not_change_output(self):
        other = dict(self.snapshot["parents"][0], parent_asset_id="demo:another")
        self.snapshot["parents"].append(other)
        reordered = dict(reversed(list(copy.deepcopy(self.snapshot).items())))
        reordered["parents"].reverse()
        self.assertEqual(
            tool.render_lineage(self.snapshot), tool.render_lineage(reordered)
        )

    def test_input_is_not_mutated(self):
        before = copy.deepcopy(self.snapshot)
        tool.render_lineage(self.snapshot)
        self.assertEqual(self.snapshot, before)

    def test_labels_are_data_even_when_they_look_like_mermaid_or_html(self):
        self.snapshot["parents"][0]["parent_asset_id"] = 'é #34; [x] " --> click <b>'
        self.snapshot["parents"][0]["relation"] = 'edit|"; %%{init}'
        diagram = tool.render_lineage(self.snapshot)
        self.assertIn("é #35;34#59; #91;x#93; #34; --#62; click #60;b#62;", diagram)
        self.assertIn("edit#124;#34;#59; #37;#37;#123;init#125;", diagram)
        self.assertNotIn("<b>", diagram)

    def test_duplicate_relationships_and_cycles_are_preserved(self):
        self.snapshot["parents"].append(copy.deepcopy(self.snapshot["parents"][0]))
        self.snapshot["children"].append(
            dict(
                parent_asset_id="demo:edited",
                child_asset_id="demo:edited",
                relation="edit",
            )
        )
        diagram = tool.render_lineage(self.snapshot)
        self.assertEqual(diagram.count('n2 -->|"edit"| n0'), 2)
        self.assertIn('n0 -->|"edit"| n0', diagram)

    def test_isolated_requested_asset_is_displayed(self):
        self.assertIn(
            'n0["unknown"]',
            tool.render_lineage(
                dict(asset_id="unknown", binding=None, parents=[], children=[])
            ),
        )

    def test_invalid_display_shapes_fail(self):
        bad = [None, [], {}, dict(asset_id="x", parents=[], children=None)]
        for field in ("asset_id",):
            for value in ("", " ", 1, True, "a\nb", "a" * 257, "\ud800"):
                item = copy.deepcopy(self.snapshot)
                item[field] = value
                bad.append(item)
        for field in ("parent_asset_id", "child_asset_id", "relation"):
            item = copy.deepcopy(self.snapshot)
            del item["parents"][0][field]
            bad.append(item)
        bad.append(dict(self.snapshot, parents=[None]))
        bad.append(
            dict(
                self.snapshot,
                parents=[dict(self.snapshot["parents"][0], child_asset_id="other")],
            )
        )
        bad.append(
            dict(
                self.snapshot,
                children=[dict(self.snapshot["children"][0], parent_asset_id="other")],
            )
        )
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):
                tool.render_lineage(item)

    def test_relationship_limit_includes_both_sides(self):
        self.snapshot["parents"] *= tool.MAX_EDGES - 1
        tool.render_lineage(self.snapshot)
        self.snapshot["children"] *= 2
        with self.assertRaisesRegex(ValueError, "at most"):
            tool.render_lineage(self.snapshot)

    def run_cli(self, raw):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_bytes(raw)
            return subprocess.run(
                [sys.executable, "-B", str(SCRIPT), str(path)], capture_output=True
            )

    def test_cli_uses_utf8_lf_and_repeats_exactly(self):
        raw = FIXTURE.read_bytes()
        one, two = self.run_cli(raw), self.run_cli(raw)
        self.assertEqual(one.returncode, 0, one.stderr)
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(one.stdout, tool.render_lineage(self.snapshot).encode("utf-8"))
        self.assertEqual(one.stderr, b"")

    def test_cli_accepts_utf8_bom(self):
        self.assertEqual(
            self.run_cli(b"\xef\xbb\xbf" + FIXTURE.read_bytes()).returncode, 0
        )

    def test_documented_malformed_fixture_fails(self):
        result = self.run_cli(
            (ROOT / "examples/lineage_snapshot_invalid.json").read_bytes()
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"child_asset_id", result.stderr)

    def test_exact_byte_and_label_limits_are_accepted(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(
            self.run_cli(raw + b" " * (tool.MAX_INPUT_BYTES - len(raw))).returncode, 0
        )
        self.assertIn(
            "a" * tool.MAX_LABEL_CHARS,
            tool.render_lineage(
                dict(asset_id="a" * tool.MAX_LABEL_CHARS, parents=[], children=[])
            ),
        )

    def test_readme_output_matches_the_fixture(self):
        doc = (ROOT / "examples/lineage_to_mermaid.md").read_text(encoding="utf-8")
        diagram = doc.split("```mermaid\n", 1)[1].split("```", 1)[0]
        self.assertEqual(diagram, tool.render_lineage(self.snapshot))

    def test_cli_rejects_invalid_json_without_partial_diagram(self):
        for raw in (
            b"{",
            b"[]",
            b"null",
            b"\xff",
            b'{"asset_id":"x","asset_id":"y"}',
            b'{"asset_id":NaN}',
            b" " * (tool.MAX_INPUT_BYTES + 1),
        ):
            with self.subTest(raw=raw[:60]):
                result = self.run_cli(raw)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertIn(b"Cannot render lineage:", result.stderr)

    def test_runtime_lineage_output_is_supported(self):
        runtime_spec = importlib.util.spec_from_file_location(
            "lineage_example_runtime",
            ROOT / "src/04_Entity_Registry/provenance/canonical_provenance.py",
        )
        runtime = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime)

        class SyntheticSigner:
            def sign(self, actor, body):
                return {"synthetic": True}

        with tempfile.TemporaryDirectory() as directory:
            graph = runtime.AssetProvenanceGraph(directory, SyntheticSigner())
            graph.add_derivation("demo:actor", "demo:source", "demo:edited", "edit")
            graph.add_derivation("demo:actor", "demo:edited", "demo:preview", "resize")
            self.assertEqual(
                tool.render_lineage(graph.lineage("demo:edited")),
                tool.render_lineage(self.snapshot),
            )


if __name__ == "__main__":
    unittest.main()
