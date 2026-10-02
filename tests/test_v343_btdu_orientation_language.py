import importlib.util, os, pathlib, sys, tempfile, unittest
REPO=pathlib.Path(__file__).resolve().parents[1]
BTDU=REPO/"src"/"40_BTDU"/"canonical_btdu.py"
def load():
    spec=importlib.util.spec_from_file_location("v343_orientation_btdu_test",BTDU)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod
@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"ENTITY_ADAM_V1_ROOT required")
class V343OrientationTests(unittest.TestCase):
    def test_orientation_root_and_language_summary(self):
        m=load()
        with tempfile.TemporaryDirectory(prefix="v343-orient-",ignore_cleanup_errors=True) as td:
            u=m.BlackmoreTechnologyDataUniverse(td,authorization_verifier=lambda r:True,
                sovereign_entity_id="ent2-v343orientationtest000000000000000000000000000000000000000")
            math={"semantic_profile":"mathematics"}
            code={"semantic_profile":"code"}
            self.assertEqual(u.normalize_oriented_relation("a","<","b",math)["topology_id"],
                             u.normalize_oriented_relation("b",">","a",math)["topology_id"])
            self.assertNotEqual(u.normalize_oriented_relation("a","<","b",code)["topology_id"],
                                u.normalize_oriented_relation("b",">","a",code)["topology_id"])
            self.assertEqual(m.BTDU_VERSION,"3.4.2")
            self.assertTrue(m.BTDU_BUILD_REVISION.startswith("v3.4.3+"))
            self.assertEqual(u.language_summary()["language_nodes"],0)
            self.assertTrue(u.verify(deep=False)["pass"])
            u.close()
if __name__=="__main__": unittest.main()
