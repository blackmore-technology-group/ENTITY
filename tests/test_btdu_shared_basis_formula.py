from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, shutil, sqlite3, tempfile, unittest

REPO=Path(__file__).resolve().parents[1]
MODPATH=REPO/"src"/"40_BTDU"/"shared_basis_formula.py"

def load_mod():
    spec=importlib.util.spec_from_file_location("btdu_shared_basis_formula_test",MODPATH)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

m=load_mod()

def sha(raw:bytes)->str: return hashlib.sha256(raw).hexdigest()

def make_basis(path:Path)->None:
    db=sqlite3.connect(path)
    db.executescript("""
    create table language_nodes(node_ref text primary key,atom_id text,node_kind text,language text,value_text text,metadata_json text);
    create table english_lemmas(lemma_ref text primary key,atom_id text,lemma text,pos text,synset_count integer);
    create table math_terms(ref text primary key,atom_id text,source text,module text,domain text,kind text,name text,source_sha256 text);
    """)
    for i,t in enumerate(["def","return","=","(",")",":","{","}",",","true","false"]):
        db.execute("insert into language_nodes values(?,?,?,?,?,?)",(f"code:{i}",f"a{i}","code_token",None,t,"{}"))
    for i,t in enumerate(["hello","world","value","result"]):
        db.execute("insert into english_lemmas values(?,?,?,?,?)",(f"eng:{i}",f"e{i}",t,"n",1))
    for i,t in enumerate(["AddConstMap","sum"]):
        db.execute("insert into math_terms values(?,?,?,?,?,?,?,?)",(f"math:{i}",f"m{i}","test","M","D","term",t,"0"*64))
    db.commit(); db.close()

def make_manifest(root:Path,path:Path)->dict:
    rows=[]
    for fp in sorted(p for p in root.rglob("*") if p.is_file()):
        raw=fp.read_bytes(); rel=fp.relative_to(root).as_posix()
        rows.append({"path":rel,"bytes":len(raw),"sha256":sha(raw)})
    h=hashlib.sha256()
    for r in rows:
        h.update(r["path"].encode()); h.update(b"\0"); h.update(str(r["bytes"]).encode()); h.update(b"\0"); h.update(r["sha256"].encode()); h.update(b"\n")
    doc={"schema":"test-corpus","files":len(rows),"bytes":sum(r["bytes"] for r in rows),"tree_manifest_sha256":h.hexdigest(),"manifest":rows}
    path.write_text(json.dumps(doc),encoding="utf-8"); return doc

class SharedBasisFormulaTests(unittest.TestCase):
    def test_exact_reconstruction_after_source_removed(self):
        with tempfile.TemporaryDirectory(prefix="btdu-shared-formula-") as td:
            root=Path(td); src=root/"src"; src.mkdir()
            (src/"a.py").write_bytes((b"def hello(value):\n    result = value\n    return result\n"*200))
            (src/"b.json").write_bytes((b'{"hello":"world","value":true}\n'*300))
            db=root/"basis.sqlite"; make_basis(db)
            manifest=root/"manifest.json"; doc=make_manifest(src,manifest)
            formula=root/"asset.btduform"
            built=m.build_formula(source_root=src,corpus_manifest=manifest,btdu_db=db,output=formula)
            shutil.rmtree(src)
            self.assertFalse(src.exists())
            out=root/"out"
            result=m.reconstruct_formula(formula=formula,btdu_db=db,output_root=out)
            self.assertTrue(result["pass"]); self.assertEqual(result["files_verified"],doc["files"])
            for row in doc["manifest"]:
                raw=(out/Path(*Path(row["path"]).parts)).read_bytes()
                self.assertEqual(sha(raw),row["sha256"])
            self.assertNotIn(str(src).encode(),formula.read_bytes())
            self.assertGreater(built["coverage"]["shared_basis_bytes"],0)

    def test_basis_drift_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="btdu-shared-basis-drift-") as td:
            root=Path(td); src=root/"src"; src.mkdir(); (src/"x.py").write_text("def hello():\n    return 1\n",encoding="utf-8")
            db=root/"basis.sqlite"; make_basis(db); manifest=root/"manifest.json"; make_manifest(src,manifest)
            formula=root/"asset.btduform"; m.build_formula(source_root=src,corpus_manifest=manifest,btdu_db=db,output=formula)
            con=sqlite3.connect(db); con.execute("insert into english_lemmas values(?,?,?,?,?)",("drift","drift","drift","n",1)); con.commit(); con.close()
            with self.assertRaisesRegex(ValueError,"basis root/count mismatch"):
                m.reconstruct_formula(formula=formula,btdu_db=db,output_root=root/"out")

if __name__=="__main__": unittest.main()
