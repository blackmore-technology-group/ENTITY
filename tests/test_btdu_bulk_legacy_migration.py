from __future__ import annotations
import hashlib, importlib.util, os, pathlib, sys, tempfile, unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
BTDU_PATH=REPO/"src"/"40_BTDU"/"canonical_btdu.py"

def load(name):
    spec=importlib.util.spec_from_file_location(name,BTDU_PATH)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod)
    return mod

def deterministic_bytes(n:int,salt:bytes)->bytes:
    out=bytearray(); i=0
    while len(out)<n:
        out.extend(hashlib.sha256(salt+i.to_bytes(8,"big")).digest()); i+=1
    return bytes(out[:n])

@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"verified ADAM source required")
class BTDUBulkLegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.mod=load("btdu_bulk_legacy_"+self._testMethodName)
        self.tmp=tempfile.TemporaryDirectory(prefix="btdu-bulk-legacy-")
        self.owner="ent2-bulklegacy0000000000000000000000000000000000000"
        self.auth={"scope":"BTDU_WRITE","test":"bulk-legacy"}
    def tearDown(self): self.tmp.cleanup()
    def make(self):
        return self.mod.BlackmoreTechnologyDataUniverse(
            pathlib.Path(self.tmp.name)/"state",
            authorization_verifier=lambda r:isinstance(r,dict) and r.get("scope")=="BTDU_WRITE",
            sovereign_entity_id=self.owner)
    def add_legacy(self,u,index:int):
        raw=deterministic_bytes(64*1024,("legacy-%d"%index).encode())
        name="legacy-%d.bin"%index
        exact=u.evidence.ingest_evidence(raw,media_type="application/octet-stream",name=name)
        encoded=u.encode_exact_bytes(name,raw,self.auth,chunk_size=4096)
        object_ref="btdu-object:"+self.mod.sha256({"logical_path":name,"content_sha256":self.mod.sha256(raw),"source_entity_id":self.owner})
        value={"schema":"entity-btdu-object-v1","object_ref":object_ref,"logical_path":name,
               "content_sha256":self.mod.sha256(raw),"size_bytes":len(raw),"evidence_object_id":exact.object_id,
               "exact_compound_id":encoded["compound_id"],"media_type":"application/octet-stream"}
        object_atom=u._put_atom("btdu_object",value,{"exact_content_externalized":True})
        u._bond(object_atom,"atomized_as",encoded["compound_id"],source_ref=object_ref,target_ref=encoded["compound_id"],
                context="BTDU_EXACT_ATOMIZATION",metadata={"sha256":self.mod.sha256(raw)})
        with u._db() as db:
            db.execute("""insert into objects(object_ref,atom_id,logical_path,content_sha256,size_bytes,media_type,
                        evidence_object_id,source_entity_id,controller_entity_id,rights_holder_entity_id,
                        provenance_ref,created_at_ms) values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (object_ref,object_atom,name,self.mod.sha256(raw),len(raw),"application/octet-stream",
                        exact.object_id,self.owner,self.owner,self.owner,"legacy://bulk",self.mod.now_ms()+index))
        return object_ref,raw

    def test_durable_batch_migration_restart_and_exactness(self):
        u=self.make()
        expected=[self.add_legacy(u,i) for i in range(5)]
        seq_before=u.atomic.sequence
        result=u.migrate_legacy_objects(self.auth,batch_size=3)
        self.assertEqual(result["schema"],"entity-btdu-formula-bulk-migration-v2")
        self.assertEqual(result["migrated"],5)
        self.assertEqual(result["remaining"],0)
        self.assertEqual(u.atomic.sequence-seq_before,2)
        with u._db() as db:
            self.assertEqual(db.execute("select count(*) from object_formulas").fetchone()[0],5)
            self.assertEqual(db.execute("select count(*) from edges where predicate='formulated_as'").fetchone()[0],5)
        for object_ref,raw in expected:
            self.assertEqual(u.reconstruct_object(object_ref),raw)
        self.assertTrue(u.verify(deep=True)["pass"])
        u.close()

        u2=self.make()
        self.assertTrue(u2.verify(deep=True)["pass"])
        for object_ref,raw in expected:
            self.assertEqual(u2.reconstruct_object(object_ref),raw)
        u2.close()

if __name__=="__main__":
    unittest.main()
