from __future__ import annotations
import gc, hashlib, importlib.util, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
def load(name, rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel); mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

identity_mod=load("adoption_identity","src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod=load("adoption_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
core_mod=load("adoption_core","src/31_Profiles/profile_core.py")
eep_mod=load("adoption_eep","src/31_Profiles/exchange_protocol.py")
res_mod=load("adoption_res","src/31_Profiles/resilience_interop.py")
inst_mod=load("adoption_inst","src/35_Global_Infrastructure/institutional_semantics.py")
passport_mod=load("adoption_passport","src/36_Adoption_Layer/rights_passport.py")
connector_mod=load("adoption_connectors","src/36_Adoption_Layer/custody_connectors.py")
standards_mod=load("adoption_standards","src/36_Adoption_Layer/standards_adapters.py")
profile_mod=load("adoption_profile","src/36_Adoption_Layer/adoption_profile.py")
conf_mod=load("adoption_conformance","src/36_Adoption_Layer/adoption_conformance.py")

class V32AdoptionLayerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
        self.identity=identity_mod.EntityIdentityVault(self.root); self.fabric=fabric_mod.UniversalTransactionFabric(self.root,self.identity)
        self.owner=self.identity.create("Owner","business")["entity_id"]; self.buyer=self.identity.create("Buyer","business")["entity_id"]
        self.gov=self.identity.create("Government","organization")["entity_id"]; self.r1=self.identity.create("Resolver One","system")["entity_id"]; self.r2=self.identity.create("Resolver Two","system")["entity_id"]
        self.dco=self.fabric.register_digital_commodity(self.owner,"AI Training Corpus",hashlib.sha256(b"corpus").hexdigest())
        self.passports=passport_mod.RightsPassportRegistry(self.root,self.identity,self.fabric)
    def tearDown(self):
        self.passports=None; gc.collect(); self.tmp.cleanup()

    def test_core_primitives_and_market_are_not_replaced(self):
        s=profile_mod.adoption_status(); self.assertEqual(s["core_primitives"],["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"])
        self.assertFalse(s["core_semantics_changed"]); self.assertTrue(s["market_engine_preserved"])
        self.assertEqual(s["market_lifecycle"][0:4],["DCO","INSTRUMENT","LISTING","DISCLOSURE"]); self.assertEqual(s["market_lifecycle"][-3:],["USAGE","DERIVED_OUTPUT","ECONOMIC_CONSEQUENCE"])

    def test_rights_passport_is_signed_and_provider_neutral(self):
        locator=connector_mod.CustodyConnectorRegistry.locator(self.dco["object_id"],"SNOWFLAKE","DB.SCHEMA.CORPUS",hashlib.sha256(b"corpus").hexdigest())
        p=self.passports.issue(self.owner,self.dco["object_id"],[{"effect":"ALLOW","actions":["TRAIN","DERIVE"]},{"effect":"PROHIBIT","actions":["REDISTRIBUTE"]}],custody=[locator],jurisdiction_profile_refs=["CA-BC:DATA@1.0"],semantic_refs=["btg:RIGHT:TRAIN@1.0"])
        self.assertTrue(self.passports.verify(p)["valid"]); self.assertFalse(p["custody"][0]["provider_is_authority"]); self.assertTrue(p["economic_terms"]["underlying_information_remains_nonrival"])

    def test_passport_rejects_provider_as_authority_and_information_scarcity(self):
        bad={"provider":"SNOWFLAKE","locator":"X","content_sha256":"0"*64,"provider_is_authority":True}
        with self.assertRaises(ValueError): self.passports.issue(self.owner,self.dco["object_id"],[{"effect":"ALLOW","actions":["TRAIN"]}],custody=[bad])
        with self.assertRaises(ValueError): self.passports.issue(self.owner,self.dco["object_id"],[{"effect":"ALLOW","actions":["TRAIN"]}],version="2.0",economic_terms={"underlying_information_remains_nonrival":False})

    def test_provider_migration_preserves_entity_object_id(self):
        old=connector_mod.CustodyConnectorRegistry.locator(self.dco["object_id"],"AWS_S3","s3://bucket/corpus","1"*64); new=connector_mod.CustodyConnectorRegistry.locator(self.dco["object_id"],"AZURE_BLOB","container/corpus","1"*64)
        m=connector_mod.CustodyConnectorRegistry.migration(old,new,evidence_sha256="2"*64,actor_entity_id=self.owner); self.assertTrue(m["entity_identity_preserved"]); self.assertFalse(m["authority_transfer_implied"])

    def test_odrl_round_trip_preserves_allow_and_prohibit(self):
        odrl={"permission":[{"action":["train","derive"]}],"prohibition":[{"action":"redistribute"}]}; mapped=standards_mod.StandardsAdapters.import_odrl(odrl)
        effects={(r["effect"],tuple(r["actions"])) for r in mapped["mapped_rights"]}; self.assertIn(("ALLOW",("DERIVE","TRAIN")),effects); self.assertIn(("PROHIBIT",("REDISTRIBUTE",)),effects)
        exported=standards_mod.StandardsAdapters.export_odrl(mapped["mapped_rights"],self.dco["object_id"]); self.assertEqual(len(exported["permission"]),1); self.assertEqual(len(exported["prohibition"]),1); self.assertFalse(mapped["silent_semantic_equivalence"])

    def test_vc_and_did_are_evidence_not_authority(self):
        vc={"issuer":"did:web:issuer.example","credentialSubject":{"id":"did:example:subject"},"proof":{"type":"DataIntegrityProof"}}
        self.assertTrue(standards_mod.StandardsAdapters.credential_evidence(vc)["credential_is_evidence_not_entity_authority"]); self.assertTrue(standards_mod.StandardsAdapters.did_evidence({"id":"did:example:subject"})["external_identifier_is_not_entity_authority"])

    def test_sdk_combines_rights_and_jurisdiction_fail_closed(self):
        jreg=inst_mod.JurisdictionProfileRegistry(self.root,self.identity); jreg.register(self.gov,"CA-BC","DATA","1.0",hashlib.sha256(b"jurisdiction").hexdigest(),[{"effect":"PROHIBIT","actions":["TRAIN"]}],effective_from_ms=1)
        p=self.passports.issue(self.owner,self.dco["object_id"],[{"effect":"ALLOW","actions":["TRAIN"]}],version="sdk-1")
        sdk=profile_mod.EntityAdoptionSDK(passport_registry=self.passports,rights_ontology=core_mod.RightsOntology,jurisdiction_registry=jreg); d=sdk.authorize(p,"TRAIN",jurisdictions=["CA-BC"],domain="DATA")
        self.assertEqual(d["decision"],"DENY"); self.assertTrue(d["sdk_does_not_create_authority"])

    def test_resolver_deployment_requires_independence(self):
        with self.assertRaises(ValueError): profile_mod.EntityAdoptionSDK.resolver_deployment(minimum_resolvers=1)
        cfg=profile_mod.EntityAdoptionSDK.resolver_deployment(minimum_resolvers=2); self.assertTrue(cfg["resolver_is_not_authority"]); self.assertTrue(cfg["fail_closed"])

    def test_sdk_exposes_existing_federated_resolution(self):
        fr=res_mod.FederatedResolutionProfile(self.root,self.identity); record={"version":1,"endpoint":"ent3://asset"}; fr.observe(self.r1,self.dco["object_id"],record,epoch=1,ttl_ms=60000); fr.observe(self.r2,self.dco["object_id"],record,epoch=1,ttl_ms=60000)
        self.assertTrue(profile_mod.EntityAdoptionSDK(federated_resolution=fr).resolver_quorum(self.dco["object_id"])["resolved"])

    def test_legal_classification_is_only_an_assertion(self):
        x=profile_mod.legal_classification_assertion("CA","ca:data-right@1",self.gov,"CONTRACTUAL_USAGE_RIGHT"); self.assertTrue(x["classification_is_assertion_not_protocol_legal_truth"])

    def test_existing_eep_full_lifecycle_survives_v32(self):
        eep=eep_mod.ExchangeProtocol(self.root,self.identity,self.fabric); venue=eep.create_venue(self.owner,"AI Rights Venue","CA",["ORDER_BOOK","RFQ"],hashlib.sha256(b"venue").hexdigest())
        inst=eep.define_instrument(self.owner,self.dco["object_id"],"SPOT_LICENSE",{"actions":["DERIVE","TRAIN"]},1000,"CAD",transferable=True); disclosure=eep.publish_disclosure(venue["venue_id"],inst["instrument_id"],self.owner,"LISTING",hashlib.sha256(b"disclosure").hexdigest())
        eep.list_instrument(venue["venue_id"],inst["instrument_id"],self.owner,min_lot=1,tick_size=1,disclosure_sha256=disclosure["content_sha256"]); eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",10,250,nonce="v32-sell"); eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",10,250,nonce="v32-buy")
        trade=eep.match_order_book(venue["venue_id"],inst["instrument_id"])[0]; settled=eep.settle_trade(trade["trade_id"],payment_ref="external:receipt",external_verified=False); eep.meter_usage(inst["instrument_id"],self.buyer,"TRAIN",1,nonce="v32-usage")
        market=profile_mod.EntityAdoptionSDK(exchange=eep).market_status(); self.assertTrue(market["market_engine_preserved"]); self.assertTrue(market["rights_are_traded_not_bytes"]); self.assertFalse(settled["entitlement"]["ownership_of_underlying_transferred"])

    def test_all_adoption_vector_schemas_have_truth_boundaries(self):
        records=[{"schema":"entity-v3-adoption-profile-status-v1","core_primitives":["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"],"core_semantics_changed":False,"market_engine_preserved":True},{"schema":"entity-v3-resolver-deployment-v1","mode":"FEDERATED","minimum_resolvers":2,"resolver_is_not_authority":True,"single_provider_dependency_prohibited":True,"fail_closed":True},{"schema":"entity-v3-legal-classification-assertion-v1","asserted_by":self.gov,"classification":"CONTRACTUAL_USAGE_RIGHT","classification_is_assertion_not_protocol_legal_truth":True}]
        self.assertTrue(all(conf_mod.validate_adoption_record(x) for x in records))

if __name__=="__main__": unittest.main()
