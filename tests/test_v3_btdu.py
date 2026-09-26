import importlib.util, json, os, pathlib, tempfile, unittest
REPO=pathlib.Path(__file__).resolve().parents[1]
BTDU_PATH=REPO/"src"/"40_BTDU"/"canonical_btdu.py"; IDENTITY_PATH=REPO/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py"; PIN_PATH=REPO/"src"/"11_ADAM"/"full_runtime"/"ADAM_REFERENCE_PIN.json"
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
btdu=load("entity_btdu_test",BTDU_PATH)
class BTDUPublicContractTests(unittest.TestCase):
 def test_adam_reference_is_genesis_pin(self):
  pin=json.loads(PIN_PATH.read_text(encoding="utf-8")); self.assertEqual(pin["adam_version"],"1.0.0-rc2"); self.assertEqual(pin["authoritative_inner_sha256"],"3cc6541f2d00dd0580989cc7fe6e8abd56974d1069f61c710e230568e00b8da3"); self.assertTrue(pin["authoritative_inner_sidecar_matches"])
 def test_canonical_btg_universe_is_under_shawn_entity(self):
  self.assertEqual(btdu.BTDU_CANONICAL_OWNER_ENTITY_ID,"ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica"); self.assertEqual(btdu.BTDU_CANONICAL_OWNER_ALIAS,"shawn.blackmore.entity"); self.assertNotEqual(btdu.BTDU_CANONICAL_OWNER_ENTITY_ID,btdu.ENTITY_PROTOCOL_ENTITY_ID)
 def test_genesis_semantics_are_complete(self):
  self.assertEqual(btdu.GENESIS_PRIMITIVES,("ENTITY","AUTHORITY","RIGHT","EVENT","VALUE")); self.assertEqual(btdu.GENESIS_MARKET_LIFECYCLE,("DCO","INSTRUMENT","LISTING","DISCLOSURE","ORDER_RFQ_AUCTION","PRICE_DISCOVERY","TRADE","CLEARING","SETTLEMENT","ENTITLEMENT","USAGE","DERIVED_OUTPUT","ECONOMIC_CONSEQUENCE"))
@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"verified ADAM source required for BTDU integration tests")
class BTDUIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.identity_mod=load("entity_btdu_identity_"+self._testMethodName,IDENTITY_PATH); self.tmp=tempfile.TemporaryDirectory(prefix="entity-btdu-"); self.identity=self.identity_mod.EntityIdentityVault(pathlib.Path(self.tmp.name)/"entity_state"); self.owner=self.identity.create("BTDU Test Sovereign","person")["entity_id"]; self.protocol=self.identity.create("BTDU Protocol Test","system")["entity_id"]; self.steward=self.identity.create("BTDU Steward Test","organization")["entity_id"]
  self.auth_body={"schema":"entity-btdu-authorization-v1","actor_entity_id":self.owner,"scope":"BTDU_WRITE","nonce":"unit-test"}; self.receipt={"body":self.auth_body,"signature":self.identity.sign(self.owner,self.auth_body)}
  def verifier(record):
   try:
    body=dict(record["body"]); sig=dict(record["signature"]); manifest=self.identity.load_manifest(body["actor_entity_id"]); return body.get("scope")=="BTDU_WRITE" and self.identity.verify_signature(manifest,body,sig)
   except Exception: return False
  self.verifier=verifier
 def tearDown(self): self.tmp.cleanup()
 def make(self): return btdu.BlackmoreTechnologyDataUniverse(pathlib.Path(self.tmp.name)/"btdu",authorization_verifier=self.verifier,sovereign_entity_id=self.owner,protocol_entity_id=self.protocol,steward_entity_id=self.steward)
 def test_exact_primitive_reconstruction_restart_and_object_atomization(self):
  payload="APPLE ∑ 2+2=4\nprint('BTDU')".encode(); u=self.make(); encoded=u.encode_exact_bytes("universal-sample",payload,self.receipt,chunk_size=32); self.assertEqual(u.reconstruct_exact_bytes(encoded["compound_id"]),payload)
  obj=u.ingest_bytes(logical_path="sample.txt",data=payload,authorization_receipt=self.receipt,source_entity_id=self.owner,controller_entity_id=self.owner,rights_holder_entity_id=self.owner,provenance_ref="test://sample",media_type="text/plain"); self.assertEqual(u.reconstruct_object(obj["object_ref"]),payload); ctx=u.project_object_context(obj["object_ref"]); self.assertIn("atomized_as",ctx["context"]); self.assertIn("provenance_recorded_as",ctx["context"]); self.assertTrue(u.verify(deep=True)["pass"]); u.close(); u2=self.make(); self.assertEqual(u2.reconstruct_object(obj["object_ref"]),payload); self.assertTrue(u2.verify(deep=True)["pass"]); u2.close()
 def test_economic_lineage_is_mirror_not_entitlement(self):
  u=self.make(); result=u.mirror_genesis_market_chain(self.receipt,prefix="unit"); self.assertTrue(result["mirror_only"]); self.assertFalse(result["rights_created"]); self.assertFalse(result["economic_entitlements_created"]); self.assertEqual(result["protocol_tax_bps"],0); check=u.verify(); self.assertTrue(check["pass"]); self.assertTrue(check["genesis_primitives_preserved"]); self.assertEqual(check["automatic_protocol_royalty_bps"],0); u.close()
 def test_unauthorized_mutation_is_rejected(self):
  u=self.make();
  with self.assertRaises(PermissionError): u.materialize_primitive_bytes({"body":dict(self.auth_body,nonce="tampered"),"signature":self.receipt["signature"]})
  u.close()
if __name__=="__main__": unittest.main()