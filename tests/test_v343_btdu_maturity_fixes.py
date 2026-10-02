import concurrent.futures, hashlib, importlib.util, os, pathlib, sys, tempfile, unittest
REPO=pathlib.Path(__file__).resolve().parents[1]
BTDU_PATH=REPO/"src"/"40_BTDU"/"canonical_btdu.py"
def load(name):
    spec=importlib.util.spec_from_file_location(name,BTDU_PATH)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"ENTITY_ADAM_V1_ROOT required")
class V343MaturityFixTests(unittest.TestCase):
    def make(self,mod,path):
        return mod.BlackmoreTechnologyDataUniverse(path,authorization_verifier=lambda r:True,
            sovereign_entity_id="ent2-v343maturityfix00000000000000000000000000000000000000")
    def seed_bridge(self,u):
        auth={"body":{"scope":"BTDU_WRITE"}}
        lemma=u._put_atom("english_lemma",{"lemma":"add","pos":"v"},{"source":"test"})
        code=u._put_atom("code_token",{"token":"+"},{"source":"test"})
        with u._db() as db:
            db.execute("INSERT OR REPLACE INTO english_lemmas VALUES(?,?,?,?,?)",("lemma:v:add",lemma,"add","v",1))
            db.execute("INSERT OR REPLACE INTO language_nodes VALUES(?,?,?,?,?,?)",("code-token:+",code,"code_token",None,"+",'{"shared":true}'))
        u.register_oriented_relations([{"left_ref":"a","operator":"+","right_ref":"b","source_ref":"math-test",
            "context":{"semantic_profile":"mathematics","commutative_proved":True}}],auth)
        return auth
    def test_governed_cross_domain_bridge(self):
        m=load("v343_bridge_fix")
        with tempfile.TemporaryDirectory(prefix="v343-bridge-",ignore_cleanup_errors=True) as td:
            u=self.make(m,td); auth=self.seed_bridge(u)
            sequence_before=u.atomic.sequence
            out=u.install_cross_domain_semantic_bridge(auth)
            self.assertEqual(u.atomic.sequence,sequence_before)
            self.assertFalse(out["signed_adam_journal_mutated"])
            self.assertGreaterEqual(out["concepts"],1); self.assertGreaterEqual(out["relations"],2)
            res=u.resolve_cross_domain_concept("add")
            self.assertTrue(any(x["math_operator"]=="+" and x["code_token_ref"]=="code-token:+" for x in res["matches"]))
            self.assertFalse(out["rights_created"]); u.close()
    def test_8_writer_120_chain_admission(self):
        m=load("v343_concurrency_fix")
        with tempfile.TemporaryDirectory(prefix="v343-concurrent-",ignore_cleanup_errors=True) as td:
            u=self.make(m,td); errors=[]
            def worker(w):
                for j in range(15):
                    p=f"w{w}:c{j}"; nodes=[{"ref":p+":DCO","kind":"DCO"},{"ref":p+":TRADE","kind":"TRADE"},{"ref":p+":DERIVED","kind":"DERIVED_OUTPUT"}]
                    edges=[{"source":p+":DCO","predicate":"precedes","target":p+":TRADE"},{"source":p+":TRADE","predicate":"precedes","target":p+":DERIVED"}]
                    try: u.mirror_economic_lineage(nodes=nodes,edges=edges,authorization_receipt={"x":1},evidence_sha256=hashlib.sha256(p.encode()).hexdigest())
                    except Exception as e: errors.append(repr(e))
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: list(ex.map(worker,range(8)))
            with u._db() as db:
                self.assertEqual(db.execute("select count(*) from economic_nodes").fetchone()[0],360)
                self.assertEqual(db.execute("select count(*) from economic_edges").fetchone()[0],240)
                self.assertEqual(db.execute("pragma quick_check").fetchone()[0],"ok")
            self.assertEqual(errors,[]); self.assertTrue(u.verify(deep=False)["pass"]); u.close()
    def test_authority_neutral_replication_root_converges(self):
        m=load("v343_replication_fix")
        roots=[]; atomic=[]
        with tempfile.TemporaryDirectory(prefix="v343-repl-",ignore_cleanup_errors=True) as td:
            for k in ("a","b"):
                u=self.make(m,pathlib.Path(td)/k)
                nodes=[{"ref":"rep:DCO","kind":"DCO"},{"ref":"rep:TRADE","kind":"TRADE"},{"ref":"rep:DERIVED","kind":"DERIVED_OUTPUT"}]
                edges=[{"source":"rep:DCO","predicate":"precedes","target":"rep:TRADE"},{"source":"rep:TRADE","predicate":"precedes","target":"rep:DERIVED"}]
                u.mirror_economic_lineage(nodes=nodes,edges=edges,authorization_receipt={"x":1},evidence_sha256="ab"*32)
                roots.append(u.canonical_replication_root()); atomic.append(u.atomic.root_hash); u.close()
        self.assertEqual(roots[0],roots[1])
        self.assertNotEqual(atomic[0],atomic[1],"independent ADAM authority envelopes should remain distinct")
if __name__=="__main__": unittest.main()
