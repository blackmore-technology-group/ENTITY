import importlib.util, json, tempfile, unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"node.py"
spec=importlib.util.spec_from_file_location("inp",P); inp=importlib.util.module_from_spec(spec); spec.loader.exec_module(inp)

class TestINP(unittest.TestCase):
    def test_hash_is_canonical(self):
        self.assertEqual(inp.sha({"b":2,"a":1}),inp.sha({"a":1,"b":2}))
    def test_tamper_rejected(self):
        e=inp.make_envelope({"x":1},"node-a"); e["object"]["x"]=2
        ok,msg=inp.verify_env(e); self.assertFalse(ok); self.assertIn("hash",msg)
    def test_receive_preserves_origin_and_appends_hop(self):
        with tempfile.TemporaryDirectory() as t:
            old=inp.STATE; inp.STATE=Path(t)
            try:
                e=inp.make_envelope({"x":1},"node-a"); origin=e["origin_sha256"]
                status,r,out=inp.receive(e,"node-b")
                self.assertEqual(status,200); self.assertEqual(r["result"],"PASS")
                self.assertEqual(out["origin_sha256"],origin); self.assertEqual(len(out["lineage"]),1)
            finally: inp.STATE=old

if __name__=="__main__": unittest.main()
