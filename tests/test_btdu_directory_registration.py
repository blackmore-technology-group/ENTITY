from __future__ import annotations
import importlib.util, os, pathlib, tempfile, unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
BTDU_PATH=REPO/"src"/"40_BTDU"/"canonical_btdu.py"

def load():
    spec=importlib.util.spec_from_file_location("btdu_directory_registration_test",BTDU_PATH)
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"verified ADAM source required")
class DirectoryRegistrationTests(unittest.TestCase):
    def test_registration_binds_directory_formula_to_sovereign_lineage(self):
        mod=load()
        with tempfile.TemporaryDirectory(prefix="btdu-dir-registration-") as td:
            owner="ent2-directorytest000000000000000000000000000000000000"
            auth={"scope":"BTDU_WRITE"}
            u=mod.BlackmoreTechnologyDataUniverse(
                pathlib.Path(td)/"state",
                authorization_verifier=lambda r:r.get("scope")=="BTDU_WRITE",
                sovereign_entity_id=owner)
            descriptor={
                "schema":"entity-btdu-directory-asset-v1",
                "asset_ref":"btdu-dir:"+"a"*64,
                "owner_lineage":"example.user.entity",
                "owner_entity_id":owner,
                "controller_entity_id":owner,
                "tree_sha256":"1"*64,
                "metadata_sha256":"2"*64,
                "formula_sha256":"3"*64,
                "entropy_storage_root":"4"*64,
                "source_bytes":123456,
                "file_count":42,
            }
            receipt=u.register_directory_asset(descriptor,auth)
            self.assertEqual(receipt["asset_ref"],descriptor["asset_ref"])
            self.assertEqual(receipt["lineage"],"example.user.entity")
            self.assertFalse(receipt["conventional_payload_required"])
            binding=u.directory_asset_binding(descriptor["asset_ref"])
            self.assertEqual(binding["owner_entity_id"],owner)
            self.assertEqual(binding["formula_sha256"],"3"*64)
            self.assertFalse(binding["conventional_payload_required"])
            u.close()

if __name__=="__main__":
    unittest.main()
