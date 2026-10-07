from __future__ import annotations
import hashlib
import importlib.util
import os
import pathlib
import tempfile
import unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
FORMULA_PATH=REPO/"src"/"40_BTDU"/"formula_kernel.py"

def load_formula():
    spec=importlib.util.spec_from_file_location("btdu_formula_test",FORMULA_PATH)
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

m=load_formula()

def deterministic_bytes(n:int,salt:bytes=b"BTDU")->bytes:
    out=bytearray(); i=0
    while len(out)<n:
        out.extend(hashlib.sha256(salt+i.to_bytes(8,"big")).digest()); i+=1
    return bytes(out[:n])

class BTDUFormulaKernelTests(unittest.TestCase):
    def make(self,path):
        return m.BTDUFormulaKernel(
            path,min_chunk=16*1024,avg_chunk=64*1024,max_chunk=256*1024
        )

    def test_apple_is_formula_not_persisted_file(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-apple-") as td:
            f=self.make(td)
            raw=b"APPLE"
            obj=f.put_bytes(raw)
            self.assertEqual(f.read_all(obj["formula_object_id"]),raw)
            plan=f.transient_bond_plan(obj["formula_object_id"])
            self.assertFalse(plan["persistent_occurrence_bonds_created"])
            self.assertTrue(f.verify_object(obj["formula_object_id"],deep=True)["pass"])

    def test_repeat_uses_atoms_and_formula_with_zero_literal_entropy(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-repeat-") as td:
            f=self.make(td)
            raw=b"A"*(2*1024*1024)
            obj=f.put_bytes(raw)
            stats=f.stats()
            self.assertEqual(f.read_all(obj["formula_object_id"]),raw)
            self.assertEqual(stats["irreducible_atom_tape_bytes"],0)
            self.assertGreater(stats["nodes_by_kind"].get("REPEAT",0),0)
            self.assertGreater(stats["nodes_by_kind"].get("ATOM",0),0)

    def test_periodic_formula_reconstructs_without_storing_all_occurrences(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-periodic-") as td:
            f=self.make(td)
            raw=(b"APPLE|ENTITY|BTDU|"*100000)
            obj=f.put_bytes(raw)
            stats=f.stats()
            self.assertEqual(hashlib.sha256(f.read_all(obj["formula_object_id"])).hexdigest(),hashlib.sha256(raw).hexdigest())
            self.assertLess(stats["irreducible_atom_tape_bytes"],len(raw)//10)
            self.assertGreater(stats["nodes_by_kind"].get("REPEAT",0),0)

    def test_high_entropy_data_hits_information_theoretic_floor_but_remains_exact(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-entropy-") as td:
            f=self.make(td)
            raw=deterministic_bytes(3*1024*1024,b"entropy")
            obj=f.put_bytes(raw)
            stats=f.stats()
            self.assertEqual(f.read_all(obj["formula_object_id"]),raw)
            self.assertGreater(stats["irreducible_atom_tape_bytes"],len(raw)*0.85)
            self.assertTrue(f.verify(deep=True)["pass"])

    def test_identical_content_reuses_one_formula_and_one_entropy_basis(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-reuse-") as td:
            f=self.make(td)
            raw=deterministic_bytes(2*1024*1024,b"reuse")
            a=f.put_bytes(raw); before=f.stats()
            b=f.put_bytes(raw); after=f.stats()
            self.assertEqual(a["formula_object_id"],b["formula_object_id"])
            self.assertEqual(a["root_node_id"],b["root_node_id"])
            self.assertEqual(before["formula_nodes"],after["formula_nodes"])
            self.assertEqual(before["entropy_reservoir_stored_bytes"],after["entropy_reservoir_stored_bytes"])
            self.assertEqual(after["objects"],1)

    def test_content_defined_formulas_reuse_after_prefix_insertion(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-cdc-") as td:
            f=self.make(td)
            base=deterministic_bytes(6*1024*1024,b"base")
            a=f.put_bytes(base)
            before=f.stats()
            prefix=b"BTDU-FORMULA-PREFIX-"*37
            b=f.put_bytes(prefix+base)
            after=f.stats()
            self.assertNotEqual(a["formula_object_id"],b["formula_object_id"])
            combined=len(base)+len(prefix+base)
            self.assertLess(after["irreducible_atom_tape_bytes"],combined*0.70)
            self.assertEqual(f.read_all(b["formula_object_id"]),prefix+base)

    def test_range_read_does_not_materialize_full_object(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-range-") as td:
            f=self.make(td)
            raw=(b"0123456789ABCDEF"*200000)
            obj=f.put_bytes(raw)
            for off,n in [(0,19),(65000,333333),(len(raw)-1000,5000)]:
                self.assertEqual(f.read_range(obj["formula_object_id"],off,n),raw[off:off+n])

    def test_transient_bond_plan_does_not_mutate_formula_state(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-plan-") as td:
            f=self.make(td)
            raw=(b"ABCD"*300000)
            obj=f.put_bytes(raw)
            root_before=f.formula_root(); stats_before=f.stats()
            plan=f.transient_bond_plan(obj["formula_object_id"])
            root_after=f.formula_root(); stats_after=f.stats()
            self.assertEqual(root_before,root_after)
            self.assertEqual(stats_before["formula_nodes"],stats_after["formula_nodes"])
            self.assertFalse(plan["persistent_occurrence_bonds_created"])
            self.assertGreater(len(plan["nodes"]),0)

    def test_materialization_is_exact_export_not_authoritative_state(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-export-") as td:
            root=pathlib.Path(td)
            f=self.make(root/"formula")
            raw=(b"ENTITY\x00BTDU\xff"*50000)
            obj=f.put_bytes(raw)
            out=root/"export.bin"
            self.assertFalse(out.exists())
            receipt=f.materialize(obj["formula_object_id"],out)
            self.assertTrue(receipt["temporary_materialization"])
            self.assertEqual(out.read_bytes(),raw)
            out.unlink()
            self.assertFalse(out.exists())
            self.assertEqual(f.read_all(obj["formula_object_id"]),raw)

    def test_formula_corruption_or_entropy_corruption_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-corrupt-") as td:
            f=self.make(td)
            raw=deterministic_bytes(1024*1024,b"corrupt")
            obj=f.put_bytes(raw)
            db=f._db()
            try:
                row=db.execute("select recipe_json from formula_nodes where kind='LITERAL' limit 1").fetchone()
            finally:
                db.close()
            import json
            recipe=json.loads(row["recipe_json"])
            digest=recipe["literal_sha256"]
            crow=f.reservoir._chunk_row(digest)
            path=f.reservoir.root/crow["path"]
            pos=int(crow["record_offset"])+m.BTDUStorageKernel.__module__.count("x")*0
            # Use the reservoir header size through its defining module.
            import storage_kernel
            pos=int(crow["record_offset"])+storage_kernel._HEADER.size
            with path.open("r+b") as fh:
                fh.seek(pos); one=fh.read(1); fh.seek(pos); fh.write(bytes([one[0]^1])); fh.flush(); os.fsync(fh.fileno())
            with self.assertRaises(Exception):
                f.read_all(obj["formula_object_id"])

    def test_formula_root_is_authority_neutral(self):
        raw=(b"FORMULA-ROOT-"*100000)+deterministic_bytes(512*1024,b"tail")
        with tempfile.TemporaryDirectory(prefix="btdu-fa-") as a, tempfile.TemporaryDirectory(prefix="btdu-fb-") as b:
            fa=self.make(a); fb=self.make(b)
            oa=fa.put_bytes(raw); ob=fb.put_bytes(raw)
            self.assertEqual(oa["formula_object_id"],ob["formula_object_id"])
            self.assertEqual(oa["root_node_id"],ob["root_node_id"])
            self.assertEqual(fa.formula_root(),fb.formula_root())
            self.assertTrue(fa.verify(deep=True)["pass"])
            self.assertTrue(fb.verify(deep=True)["pass"])

    def test_formula_journal_recovers_rebuildable_sqlite_index(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-recover-") as td:
            root=pathlib.Path(td)
            f=self.make(root)
            raw=(b"RECOVER-ME|"*100000)+deterministic_bytes(512*1024,b"recover")
            obj=f.put_bytes(raw)
            formula_root=f.formula_root()
            journal=f.journal_status(deep=True)
            self.assertTrue(journal["pass"])
            self.assertGreater(journal["node_records"],0)
            self.assertGreater(journal["object_records"],0)
            f.close()
            for path in (
                root/"formulas.sqlite",
                pathlib.Path(str(root/"formulas.sqlite")+"-wal"),
                pathlib.Path(str(root/"formulas.sqlite")+"-shm"),
            ):
                path.unlink(missing_ok=True)
            recovered=self.make(root)
            self.assertEqual(recovered.formula_root(),formula_root)
            self.assertEqual(recovered.read_all(obj["formula_object_id"]),raw)
            self.assertTrue(recovered.verify(deep=True)["pass"])

    def test_formula_literal_references_protect_entropy_from_gc(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-refcount-") as td:
            f=self.make(td)
            raw=deterministic_bytes(2*1024*1024,b"retain")
            obj=f.put_bytes(raw)
            self.assertEqual(f.read_all(obj["formula_object_id"]),raw)
            report=f.reservoir.gc_report()
            self.assertEqual(report["reclaimable_chunks"],0)
            self.assertEqual(report["reclaimable_stored_bytes"],0)
            with f.reservoir._db() as db:
                refs=db.execute(
                    "select count(*) from chunk_references where ref_kind='FORMULA_LITERAL'"
                ).fetchone()[0]
            self.assertGreater(refs,0)

    def test_formula_journal_corruption_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="btdu-formula-journal-corrupt-") as td:
            f=self.make(td)
            f.put_bytes((b"JOURNAL|"*20000)+b"END")
            self.assertTrue(f.journal_status(deep=True)["pass"])
            import formula_kernel
            with f.journal_path.open("r+b") as fh:
                fh.seek(formula_kernel._FORMULA_JOURNAL_HEADER.size+3)
                one=fh.read(1)
                self.assertTrue(one)
                fh.seek(formula_kernel._FORMULA_JOURNAL_HEADER.size+3)
                fh.write(bytes([one[0]^1]))
                fh.flush(); os.fsync(fh.fileno())
            self.assertFalse(f.journal_status(deep=True)["pass"])
            self.assertFalse(f.verify(deep=True)["pass"])

if __name__=="__main__":
    unittest.main()
