from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, shutil, tempfile, unittest

REPO=Path(__file__).resolve().parents[1]
MOD=REPO/"src"/"40_BTDU"/"corpus_formula.py"
spec=importlib.util.spec_from_file_location("btdu_corpus_formula_test",MOD)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def manifest(root:Path,path:Path):
    rows=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        raw=p.read_bytes(); rows.append({"path":p.relative_to(root).as_posix(),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
    h=hashlib.sha256()
    for r in rows:
        h.update(r["path"].encode()); h.update(b"\0"); h.update(str(r["bytes"]).encode()); h.update(b"\0"); h.update(r["sha256"].encode()); h.update(b"\n")
    doc={"schema":"test","files":len(rows),"bytes":sum(r["bytes"] for r in rows),"tree_manifest_sha256":h.hexdigest(),"manifest":rows}
    path.write_text(json.dumps(doc),encoding="utf-8"); return doc

class CorpusFormulaTests(unittest.TestCase):
    def test_mixed_corpus_reconstructs_after_original_removed_without_payload_objects(self):
        with tempfile.TemporaryDirectory(prefix="btdu-corpus-") as td:
            root=Path(td); src=root/"src"; src.mkdir()
            (src/"trail.geojson").write_bytes((b'{"type":"Feature","geometry":{"coordinates":[-118.5,49.0]}}\n'*20000))
            (src/"model.bin").write_bytes(bytes(range(256))*4096)
            (src/"nested").mkdir(); (src/"nested"/"readme.txt").write_text("trail water hunt\n"*5000,encoding="utf-8")
            man=root/"manifest.json"; original=manifest(src,man)
            state=root/"state"; formula=root/"corpus.btduformula"
            built=m.build_corpus_formula(source_root=src,manifest_path=man,state_root=state,formula_path=formula,read_size=64*1024)
            self.assertTrue(built["pass"]); self.assertEqual(built["payload_objects"],0)
            shutil.rmtree(src); self.assertFalse(src.exists())
            out=root/"out"
            restored=m.reconstruct_corpus_formula(formula_path=formula,state_root=state,output_root=out)
            self.assertTrue(restored["pass"])
            self.assertEqual(restored["tree_sha256"],original["tree_manifest_sha256"])
            self.assertEqual(restored["files_verified"],3)

if __name__=="__main__": unittest.main()
