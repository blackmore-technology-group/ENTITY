from __future__ import annotations
import hashlib
import importlib.util
import os
import pathlib
import tempfile
import unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
BTDU_PATH=REPO/"src"/"40_BTDU"/"canonical_btdu.py"

def load(name):
    spec=importlib.util.spec_from_file_location(name,BTDU_PATH)
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def deterministic_bytes(n:int,salt:bytes=b"BTDU")->bytes:
    out=bytearray()
    i=0
    while len(out)<n:
        out.extend(hashlib.sha256(salt+i.to_bytes(8,"big")).digest())
        i+=1
    return bytes(out[:n])

@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"verified ADAM source required")
class BTDUFormulaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.mod=load("btdu_storage_integration_"+self._testMethodName)
        self.tmp=tempfile.TemporaryDirectory(prefix="btdu-storage-integration-")
        self.owner="ent2-storageintegration000000000000000000000000000000000000"
        self.auth={"scope":"BTDU_WRITE","test":self._testMethodName}

    def tearDown(self):
        self.tmp.cleanup()

    def make(self,sub="state"):
        return self.mod.BlackmoreTechnologyDataUniverse(
            pathlib.Path(self.tmp.name)/sub,
            authorization_verifier=lambda r: r.get("scope")=="BTDU_WRITE",
            sovereign_entity_id=self.owner,
        )

    def ingest(self,u,path,data,source=None):
        return u.ingest_bytes(
            logical_path=path,data=data,authorization_receipt=self.auth,
            source_entity_id=source or self.owner,controller_entity_id=self.owner,
            rights_holder_entity_id=self.owner,provenance_ref="test://"+path,
            media_type="application/octet-stream",
        )

    def test_new_payload_bytes_are_not_embedded_in_adam_journal(self):
        u=self.make()
        journal=u.root/"adam"/"entity_atomic_universe"/"universe.a41log"
        before=journal.stat().st_size
        data=deterministic_bytes(8*1024*1024,b"journal")
        obj=self.ingest(u,"bulk.bin",data)
        after=journal.stat().st_size
        self.assertLess(after-before,2*1024*1024)
        self.assertEqual(u.reconstruct_object(obj["object_ref"]),data)
        atom_kinds={a.kind for a in u.atomic.atoms.values()}
        compound_kinds={c.kind for c in u.atomic.compounds.values()}
        self.assertNotIn("exact_chunk",atom_kinds)
        self.assertNotIn("exact_object",compound_kinds)
        self.assertNotIn("BTDU_BYTE_CHUNK",compound_kinds)
        self.assertIn("btdu_formula",atom_kinds)
        ctx=u.project_object_context(obj["object_ref"])
        self.assertIn("formulated_as",ctx["context"])
        self.assertNotIn("atomized_as",ctx["context"])
        self.assertTrue(u.storage_status(deep=True)["pass"])
        u.close()

    def test_same_payload_can_have_unlimited_semantic_views_without_duplicate_bytes(self):
        u=self.make()
        data=deterministic_bytes(4*1024*1024,b"views")
        a=self.ingest(u,"camera/frame-a.bin",data)
        b=self.ingest(u,"dco/evidence/frame-copy.bin",data,source="ent2-anothersource00000000000000000000000000000000000")
        self.assertNotEqual(a["object_ref"],b["object_ref"])
        self.assertEqual(a["formula_object_id"],b["formula_object_id"])
        stats=u.formulas.stats()
        self.assertEqual(stats["objects"],1)
        with u._db() as db:
            self.assertEqual(db.execute("select count(*) from object_formulas").fetchone()[0],2)
        formula_atoms=[x for x in u.atomic.atoms.values() if x.kind=="btdu_formula"]
        self.assertEqual(len(formula_atoms),1)
        self.assertTrue(u.verify(deep=True)["pass"])
        u.close()

    def test_streaming_file_range_read_materialize_and_restart(self):
        root=pathlib.Path(self.tmp.name)
        src=root/"input.bin"
        block=deterministic_bytes(1024*1024,b"file")
        with src.open("wb") as f:
            for _ in range(12): f.write(block)
        u=self.make()
        obj=u.ingest_file(
            src,self.auth,logical_path="large/input.bin",
            source_entity_id=self.owner,controller_entity_id=self.owner,
            rights_holder_entity_id=self.owner,provenance_ref="test://large",
        )
        expected=src.read_bytes()
        self.assertEqual(u.read_object_range(obj["object_ref"],1024*1024-111,300000),expected[1024*1024-111:1024*1024-111+300000])
        out=root/"materialized.bin"
        m=u.materialize_object(obj["object_ref"],out)
        self.assertFalse(m["legacy"])
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(),hashlib.sha256(expected).hexdigest())
        u.close()
        u2=self.make()
        self.assertEqual(u2.read_object_range(obj["object_ref"],55555,777777),expected[55555:55555+777777])
        self.assertTrue(u2.verify(deep=True)["pass"])
        u2.close()

    def test_legacy_exact_object_can_be_migrated_without_destroying_signed_history(self):
        u=self.make()
        raw=deterministic_bytes(512*1024,b"legacy")
        exact=u.evidence.ingest_evidence(raw,media_type="application/octet-stream",name="legacy.bin")
        encoded=u.encode_exact_bytes("legacy.bin",raw,self.auth,chunk_size=4096)
        object_ref="btdu-object:"+self.mod.sha256({"logical_path":"legacy.bin","content_sha256":self.mod.sha256(raw),"source_entity_id":self.owner})
        value={"schema":"entity-btdu-object-v1","object_ref":object_ref,"logical_path":"legacy.bin",
               "content_sha256":self.mod.sha256(raw),"size_bytes":len(raw),"evidence_object_id":exact.object_id,
               "exact_compound_id":encoded["compound_id"],"media_type":"application/octet-stream"}
        object_atom=u._put_atom("btdu_object",value,{"exact_content_externalized":True})
        u._bond(object_atom,"atomized_as",encoded["compound_id"],source_ref=object_ref,target_ref=encoded["compound_id"],
                context="BTDU_EXACT_ATOMIZATION",metadata={"sha256":self.mod.sha256(raw)})
        with u._db() as db:
            db.execute("""insert into objects(object_ref,atom_id,logical_path,content_sha256,size_bytes,media_type,
                        evidence_object_id,source_entity_id,controller_entity_id,rights_holder_entity_id,
                        provenance_ref,created_at_ms) values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (object_ref,object_atom,"legacy.bin",self.mod.sha256(raw),len(raw),"application/octet-stream",
                        exact.object_id,self.owner,self.owner,self.owner,"legacy://test",self.mod.now_ms()))
        old_root=u.atomic.root_hash
        result=u.migrate_legacy_object(object_ref,self.auth)
        self.assertFalse(result["already_migrated"])
        self.assertTrue(result["legacy_signed_history_preserved"])
        self.assertEqual(u.reconstruct_object(object_ref),raw)
        self.assertNotEqual(u.atomic.root_hash,old_root)
        self.assertTrue(u.verify(deep=True)["pass"])
        u.close()
        u2=self.make()
        self.assertEqual(u2.reconstruct_object(object_ref),raw)
        u2.close()

    def test_adam_checkpoint_compaction_preserves_storage_and_semantics(self):
        u=self.make()
        obj=self.ingest(u,"checkpoint.bin",deterministic_bytes(3*1024*1024,b"checkpoint"))
        formula_root=u.formulas.formula_root()
        root_before=u.atomic.root_hash
        seq_before=u.atomic.sequence
        receipt=u.atomic.compact_authority()
        self.assertEqual(receipt["root_hash"],root_before)
        self.assertEqual(receipt["sequence"],seq_before)
        self.assertEqual(u.formulas.formula_root(),formula_root)
        self.assertEqual(u.atomic.root_hash,root_before)
        self.assertEqual(u.atomic.sequence,seq_before)
        u.close()
        u2=self.make()
        self.assertEqual(u2.formulas.formula_root(),formula_root)
        self.assertEqual(u2.atomic.root_hash,root_before)
        self.assertEqual(u2.atomic.sequence,seq_before)
        self.assertTrue(u2.verify(deep=True)["pass"])
        self.assertEqual(hashlib.sha256(u2.reconstruct_object(obj["object_ref"])).hexdigest(),obj["content_sha256"])
        u2.close()

    def test_primitive_atoms_and_semantic_formula_basis_are_canonical_atom_identities(self):
        u=self.make()
        first=u.install_primitive_byte_atom_universe(self.auth)
        second=u.install_primitive_byte_atom_universe(self.auth)
        self.assertTrue(first["pass"])
        self.assertEqual(first["count"],256)
        self.assertEqual(first["root"],second["root"])
        summary=u.primitive_byte_atom_summary()
        self.assertTrue(summary["installed"])
        self.assertEqual(summary["count"],256)
        primitive_ids=set(first["atom_ids"])
        self.assertEqual(len(primitive_ids),256)
        self.assertTrue(all(aid in u.atomic.atoms for aid in primitive_ids))

        code_id=u._put_atom("btdu_code_token",{"token":"return"},{"shared":True})
        eng_id=u._put_atom("btdu_english_lemma",{"lemma":"trail","pos":"n"},{"shared":True})
        math_id=u._put_atom("btdu_math_term",{"name":"distance","kind":"definition"},{"shared":True})
        with u._db() as db:
            db.execute("insert or replace into language_nodes(node_ref,atom_id,node_kind,language,value_text,metadata_json) values(?,?,?,?,?,?)",
                       ("code-token:return",code_id,"code_token","python","return","{}"))
            db.execute("insert or replace into english_lemmas(lemma_ref,atom_id,lemma,pos,synset_count) values(?,?,?,?,?)",
                       ("lemma:trail",eng_id,"trail","n",1))
            db.execute("""create table if not exists math_terms(
                       ref text primary key,atom_id text not null,source text not null,module text not null,
                       domain text not null,kind text not null,name text not null,source_sha256 text not null)""")
            db.execute("insert or replace into math_terms values(?,?,?,?,?,?,?,?)",
                       ("math:distance",math_id,"test","M","Geometry","definition","distance","0"*64))
        basis=u.canonical_formula_basis()
        self.assertTrue(basis["basis_is_canonical_atom_identity"])
        self.assertFalse(basis["external_payload_reference_required"])
        self.assertIn((code_id,b"return"),basis["code"]["entries"])
        self.assertIn((eng_id,b"trail"),basis["english"]["entries"])
        self.assertIn((math_id,b"distance"),basis["math"]["entries"])
        u.close()

    def test_authorization_failure_happens_before_payload_write(self):
        u=self.make()
        before_formula=u.formulas.stats(); before_entropy=u.storage.stats()
        with self.assertRaises(PermissionError):
            u.ingest_bytes(
                logical_path="denied.bin",data=b"denied",
                authorization_receipt={"scope":"DENY"},
                source_entity_id=self.owner,controller_entity_id=self.owner,
                provenance_ref="test://denied",
            )
        after_formula=u.formulas.stats(); after_entropy=u.storage.stats()
        self.assertEqual(before_formula["objects"],after_formula["objects"])
        self.assertEqual(before_formula["formula_nodes"],after_formula["formula_nodes"])
        self.assertEqual(before_entropy["segment_bytes"],after_entropy["segment_bytes"])
        u.close()

    def test_storage_replication_root_converges_across_independent_authorities(self):
        data=deterministic_bytes(2*1024*1024,b"replica")
        roots=[]
        formula=[]
        atomic=[]
        for i in range(2):
            u=self.make("replica"+str(i))
            obj=self.ingest(u,"same.bin",data)
            roots.append(u.canonical_replication_root())
            formula.append(u.formulas.formula_root())
            atomic.append(u.atomic.root_hash)
            self.assertEqual(obj["content_sha256"],hashlib.sha256(data).hexdigest())
            u.close()
        self.assertEqual(formula[0],formula[1])
        self.assertEqual(roots[0],roots[1])
        self.assertNotEqual(atomic[0],atomic[1])

if __name__=="__main__":
    unittest.main()
