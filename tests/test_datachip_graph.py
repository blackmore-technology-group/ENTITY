"""Adversarial tests for ENTITY DataChip graph assembly (no live ENTITY state)."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

p=Path(__file__).resolve().parents[1]/"src"/"42_ENTITY_Wallet"/"datachip_graph.py"
spec=importlib.util.spec_from_file_location("entity_composer_graph_tests",p)
import sys
g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)

OWNER="entity:btg-test-123"

def linked():
    x=g.Graph(OWNER)
    a=x.add("entity.edcf.source",x=30)
    b=x.add("entity.edcf.verify",x=280)
    c=x.add("entity.geo.decode",x=530)
    d=x.add("entity.geo.terrain",x=780)
    e=x.add("entity.host.visual",x=1020)
    x.connect(a,"archive",b,"archive")
    x.connect(b,"content",c,"content")
    x.connect(c,"layer",d,"layer")
    x.connect(d,"profile",e,"profile")
    return x,(a,b,c,d,e)

class ComposerTests(unittest.TestCase):
    def test_complete_typed_plan_is_not_authorized(self):
        graph,nodes=linked()
        result=graph.compile()
        self.assertEqual(result["state"],"COMPOSITION_ONLY")
        self.assertEqual(result["topological_order"],list(nodes))
        self.assertTrue(all(v is False for k,v in result["security"].items() if k!="host_authentication_required"))
        self.assertTrue(result["security"]["host_authentication_required"])
        self.assertRegex(result["sha256"],r"^[0-9a-f]{64}$")

    def test_port_mismatch_rejected(self):
        graph,_=linked()
        a=graph.add("entity.btdu.formula")
        b=graph.add("entity.host.visual")
        with self.assertRaisesRegex(g.ComposerError,"incompatible"):
            graph.connect(a,"formula",b,"profile")

    def test_duplicate_sink_binding_rejected(self):
        graph,_=linked()
        a=graph.add("entity.edcf.source")
        b=graph.add("entity.edcf.verify")
        c=graph.add("entity.edcf.source")
        graph.connect(a,"archive",b,"archive")
        with self.assertRaises(g.ComposerError):graph.connect(c,"archive",b,"archive")

    def test_acyclic_connection_enforced_and_rolled_back(self):
        spec={"schema":g.MODULE_SCHEMA,"module_id":"external.echo","version":"1.0.0",
              "name":"Echo","kind":"transform","inputs":[{"name":"in","type":"data.bytes","required":True}],
              "outputs":[{"name":"out","type":"data.bytes","required":False}]}
        graph=g.Graph(OWNER)
        graph.register(spec)
        a=graph.add("external.echo");b=graph.add("external.echo")
        graph.connect(a,"out",b,"in")
        with self.assertRaisesRegex(g.ComposerError,"cycle"):
            graph.connect(b,"out",a,"in")
        self.assertEqual(len(graph.edges),1)

    def test_required_missing_blocks_compilation(self):
        graph=g.Graph(OWNER)
        graph.add("entity.geo.terrain")
        with self.assertRaisesRegex(g.ComposerError,"unconnected"):
            graph.compile()

    def test_save_reload_is_exact_and_owner_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph,_=linked()
            store=g.GraphStore(tmp,OWNER)
            path=store.save(graph)
            self.assertEqual(path.parent,Path(tmp)/"wallet"/"composer"/"drafts")
            again=store.load(graph.graph_id)
            self.assertEqual(again.compile(),graph.compile())
            self.assertEqual(store.list_drafts()[0]["nodes"],5)
            with self.assertRaises(g.ComposerError):
                g.GraphStore(tmp,"entity:other").load(graph.graph_id)
            self.assertFalse(list(Path(tmp).rglob("*.sqlite")))

    def test_draft_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph,_=linked();store=g.GraphStore(tmp,OWNER)
            path=store.save(graph)
            raw=json.loads(path.read_text())
            raw["nodes"][0]["x"]+=10
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(g.ComposerError,"tampered"):
                store.load(graph.graph_id)

    def test_cannot_flip_rights_even_if_digest_recomputed(self):
        graph,_=linked()
        raw=graph.document()
        raw["rights_authorized"]=True
        body=dict(raw);body.pop("sha256")
        raw["sha256"]=g.sha256(g.canonical(body)).hexdigest()
        with self.assertRaisesRegex(g.ComposerError,"authority"):
            g.Graph.load(raw,OWNER)

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(g.ComposerError):
                g.GraphStore(tmp,OWNER).load("../identity")
            with self.assertRaises(g.ComposerError):
                g.GraphStore(tmp,OWNER).load("graph-../../../live")

    def test_nonfinite_coordinates_rejected(self):
        graph=g.Graph(OWNER)
        for v in (float("nan"),float("inf"),10001):
            with self.assertRaises(g.ComposerError):
                graph.add("entity.edcf.source",x=v)
        self.assertEqual(graph.nodes,[])

    def test_invalid_interfaces_rejected(self):
        graph=g.Graph(OWNER)
        bad=g.built_in_modules()["entity.edcf.source"].copy()
        bad["outputs"]=[{"name":"x","type":"any","required":False},
                        {"name":"x","type":"any","required":False}]
        with self.assertRaises(g.ComposerError):graph.register(bad)
        bad=g.built_in_modules()["entity.edcf.source"].copy()
        bad["outputs"]=[{"name":"out","type":"python.exec","required":False}]
        bad["module_id"]="external.exec.untrusted"
        # A port label is never actual execution authority.
        graph.register(bad)
        nid=graph.add(bad["module_id"])
        self.assertFalse(graph.compile()["security"]["execution_enabled"])

    def test_deleting_node_removes_connections(self):
        graph,ids=linked()
        graph.remove(ids[2])
        self.assertEqual(len(graph.edges),2)
        with self.assertRaises(g.ComposerError):
            graph.compile()

    def test_draft_body_rejects_unauthorized_extra_fields(self):
        graph,_=linked();raw=graph.document()
        raw["admin_override"]=True
        with self.assertRaises(g.ComposerError):g.Graph.load(raw,OWNER)

    def test_reconstructed_graph_revalidates_edges(self):
        graph,_=linked()
        raw=graph.document()
        raw["edges"][0]["in"]="not_declared"
        body=dict(raw);body.pop("sha256")
        raw["sha256"]=g.sha256(g.canonical(body)).hexdigest()
        with self.assertRaises(g.ComposerError):g.Graph.load(raw,OWNER)

if __name__=="__main__":unittest.main(verbosity=2)
