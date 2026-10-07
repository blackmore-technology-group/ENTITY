from __future__ import annotations
from pathlib import Path
import importlib.util, tempfile, unittest

REPO=Path(__file__).resolve().parents[1]
MOD=REPO/"src"/"40_BTDU"/"directory_asset.py"
spec=importlib.util.spec_from_file_location("btdu_directory_asset_test",MOD)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class DirectoryAssetTests(unittest.TestCase):
    def test_lineage_bound_directory_formulate_export_and_gate(self):
        with tempfile.TemporaryDirectory(prefix="btdu-dir-asset-") as td:
            root=Path(td); src=root/"source"; src.mkdir()
            (src/"docs").mkdir(); (src/"empty").mkdir()
            (src/"docs"/"notes.txt").write_text("trail water hunt\n"*5000,encoding="utf-8")
            (src/"terrain.geojson").write_bytes((b'{"coordinates":[-118.5,49.0]}\n'*10000))
            (src/"binary.bin").write_bytes(bytes(range(256))*1024)
            asset_root=root/"asset"
            asset=m.formulate_directory_asset(
                source_root=src,asset_root=asset_root,
                owner_lineage="example.user.entity",
                owner_entity_id="ent2-example-user",
                controller_entity_id="ent2-example-user",
                read_size=64*1024,
            )
            self.assertEqual(asset["schema"],m.ASSET_SCHEMA)
            self.assertEqual(asset["owner_lineage"],"example.user.entity")
            self.assertEqual(asset["build"]["payload_objects"],0)
            self.assertLess(asset["build"]["primary_authoritative_bytes"],asset["source_bytes"])
            exported=root/"exported"
            receipt=m.export_directory_asset(asset_root=asset_root,output_root=exported)
            self.assertTrue(receipt["pass"])
            self.assertEqual((exported/"docs"/"notes.txt").read_bytes(),(src/"docs"/"notes.txt").read_bytes())
            self.assertTrue((exported/"empty").is_dir())
            gate=m.retirement_gate(asset_root=asset_root,source_root=src,verification_root=root/"verify")
            self.assertTrue(gate["pass"])
            self.assertTrue(gate["retirement_authorized"])
            self.assertFalse(gate["source_deleted"])

    def test_gate_rejects_changed_source(self):
        with tempfile.TemporaryDirectory(prefix="btdu-dir-change-") as td:
            root=Path(td); src=root/"source"; src.mkdir()
            (src/"x.txt").write_text("original",encoding="utf-8")
            asset_root=root/"asset"
            m.formulate_directory_asset(source_root=src,asset_root=asset_root,
                                        owner_lineage="user.entity",owner_entity_id="ent2-user",
                                        read_size=4096)
            (src/"x.txt").write_text("changed",encoding="utf-8")
            gate=m.retirement_gate(asset_root=asset_root,source_root=src,verification_root=root/"verify")
            self.assertFalse(gate["pass"])
            self.assertFalse(gate["source_stable"])

if __name__=="__main__": unittest.main()
