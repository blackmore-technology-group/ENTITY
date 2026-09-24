from __future__ import annotations
import gc, hashlib, importlib.util, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

identity_mod = load("v33_identity", "src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod = load("v33_fabric", "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
eep_mod = load("v33_eep", "src/31_Profiles/exchange_protocol.py")
passport_mod = load("v33_passport", "src/36_Adoption_Layer/rights_passport.py")
reality_profile = load("reality_profile", "src/37_Verifiable_Reality/reality_profile.py")
evidence_mod = load("v33_evidence", "src/37_Verifiable_Reality/evidence_objects.py")
attest_mod = load("v33_attest", "src/37_Verifiable_Reality/attestation_authority.py")
anchors_mod = load("v33_anchors", "src/37_Verifiable_Reality/reality_anchors.py")
causal_mod = load("v33_causal", "src/37_Verifiable_Reality/causal_economic_graph.py")
conf_mod = load("v33_conformance", "src/37_Verifiable_Reality/reality_conformance.py")

class V33VerifiableRealityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.identity = identity_mod.EntityIdentityVault(self.root)
        self.fabric = fabric_mod.UniversalTransactionFabric(self.root, self.identity)
        self.owner = self.identity.create("Owner", "business")["entity_id"]
        self.buyer = self.identity.create("Buyer", "business")["entity_id"]
        self.lab = self.identity.create("Lab", "organization")["entity_id"]
        self.registry = self.identity.create("Registry", "organization")["entity_id"]
        self.dco = self.fabric.register_digital_commodity(self.owner, "Training Corpus", hashlib.sha256(b"corpus").hexdigest())
        self.evidence = evidence_mod.EvidenceRegistry(self.root, self.identity)
        self.attest = attest_mod.AttestationAuthorityRegistry(self.root, self.identity)
        self.anchors = anchors_mod.ExternalRealityAnchorRegistry(self.root, self.identity)
        self.causal = causal_mod.CausalEconomicAttributionGraph(self.root, self.identity)
        self.passports = passport_mod.RightsPassportRegistry(self.root, self.identity, self.fabric)

    def tearDown(self):
        self.evidence = self.attest = self.anchors = self.causal = self.passports = None
        gc.collect()
        self.tmp.cleanup()

    def test_01_core_and_market_semantics_are_preserved(self):
        status = reality_profile.reality_status()
        self.assertEqual(status["core_primitives"], ["ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE"])
        self.assertFalse(status["core_semantics_changed"])
        self.assertTrue(status["market_engine_preserved"])

    def test_02_evidence_object_is_signed_and_truth_bounded(self):
        ev = self.evidence.issue_evidence(self.lab, "LAB_RESULT", self.dco["object_id"], hashlib.sha256(b"result").hexdigest())
        checked = self.evidence.verify_evidence(ev)
        self.assertTrue(checked["valid"])
        self.assertFalse(checked["objective_truth_claimed"])
        self.assertTrue(ev["signature_proves_attribution_not_objective_truth"])

    def test_03_tampered_evidence_fails_verification(self):
        ev = self.evidence.issue_evidence(self.lab, "DOCUMENT", "doc:1", hashlib.sha256(b"doc").hexdigest())
        ev["content_sha256"] = "0" * 64
        self.assertFalse(self.evidence.verify_evidence(ev)["valid"])

    def test_04_claim_states_are_typed_not_absolute(self):
        ev = self.evidence.issue_evidence(self.lab, "LAB_RESULT", "sample:1", hashlib.sha256(b"sample").hexdigest())
        claim = self.evidence.issue_claim(self.owner, "sample:1", "temperature_c", 21.4, state="ASSERTED", evidence_refs=[ev["evidence_id"]])
        self.assertEqual(claim["state"], "ASSERTED")
        self.assertTrue(claim["claim_is_not_objective_truth"])

    def test_05_stronger_claim_state_requires_governed_transition_and_evidence(self):
        claim = self.evidence.issue_claim(self.owner, "asset:1", "registered_owner", "Owner", state="ASSERTED")
        with self.assertRaises(ValueError):
            self.evidence.issue_claim(self.owner, "asset:1", "registered_owner", "Owner", state="EXTERNALLY_VERIFIED")
        with self.assertRaises(ValueError):
            self.evidence.transition_claim(self.registry, claim["claim_id"], "EXTERNALLY_VERIFIED", "registry check")
        tx = self.evidence.transition_claim(self.registry, claim["claim_id"], "EXTERNALLY_VERIFIED", "registry check", evidence_refs=["snapshot:1"])
        self.assertTrue(tx["transition_does_not_establish_objective_truth"])

    def test_06_dispute_preserves_claim_history(self):
        claim = self.evidence.issue_claim(self.owner, "asset:2", "controller", self.owner)
        self.evidence.transition_claim(self.buyer, claim["claim_id"], "DISPUTED", "counterclaim", evidence_refs=["evidence:counter"])
        history = self.evidence.claim_history(claim["claim_id"])
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0]["history_rewrite_prohibited"])
        self.assertEqual(self.evidence.get_claim(claim["claim_id"])["state"], "DISPUTED")

    def test_07_attestation_authority_is_scope_limited(self):
        grant = self.attest.grant(self.registry, self.lab, ["LAB_CALIBRATION"], hashlib.sha256(b"grant").hexdigest())
        att = self.attest.attest(self.lab, "claim:calibration", "LAB_CALIBRATION", ["evidence:certificate"], "CALIBRATED")
        self.assertEqual(att["grant_id"], grant["grant_id"])
        self.assertTrue(att["attestation_is_evidence_not_objective_truth"])

    def test_08_unauthorized_attestation_is_denied(self):
        self.attest.grant(self.registry, self.lab, ["LAB_CALIBRATION"], hashlib.sha256(b"grant").hexdigest())
        with self.assertRaises(PermissionError):
            self.attest.attest(self.lab, "claim:title", "LAND_TITLE", ["evidence:title"], "OWNER")

    def test_09_revoked_attestation_grant_is_denied(self):
        grant = self.attest.grant(self.registry, self.lab, ["LAB_CALIBRATION"], hashlib.sha256(b"grant").hexdigest())
        self.attest.revoke(self.registry, grant["grant_id"])
        with self.assertRaises(PermissionError):
            self.attest.attest(self.lab, "claim:calibration", "LAB_CALIBRATION", ["evidence:certificate"], "CALIBRATED")

    def test_10_external_anchor_does_not_become_entity_authority(self):
        anchor = self.anchors.register(self.registry, "GOVERNMENT_REGISTRY", hashlib.sha256(b"endpoint").hexdigest(), jurisdiction="CA")
        self.assertFalse(anchor["credentials_included"])
        self.assertTrue(anchor["external_system_is_not_automatic_entity_authority"])

    def test_11_external_snapshot_is_evidence_and_contestable(self):
        anchor = self.anchors.register(self.registry, "CORPORATE_REGISTRY", hashlib.sha256(b"endpoint").hexdigest())
        snap = self.anchors.snapshot(self.registry, anchor["anchor_id"], "corp:123", hashlib.sha256(b"record").hexdigest(), verifier_evidence_refs=["transport-proof"])
        self.assertTrue(snap["external_record_is_evidence_not_protocol_truth"])
        self.assertTrue(snap["record_may_be_contested_or_superseded"])

    def test_12_causal_graph_requires_evidence_and_is_acyclic(self):
        a = self.causal.add_node(self.owner, "SOURCE_DATA", "dataset:A", evidence_refs=["evidence:A"])
        b = self.causal.add_node(self.owner, "DERIVED_ASSET", "model:B")
        with self.assertRaises(ValueError):
            self.causal.add_edge(self.owner, a["node_id"], b["node_id"], "DERIVED_FROM", evidence_refs=[])
        self.causal.add_edge(self.owner, a["node_id"], b["node_id"], "DERIVED_FROM", evidence_refs=["usage:1"])
        with self.assertRaises(ValueError):
            self.causal.add_edge(self.owner, b["node_id"], a["node_id"], "DERIVED_FROM", evidence_refs=["bad-cycle"])

    def test_13_causal_chain_reaches_economic_consequence(self):
        source = self.causal.add_node(self.owner, "SOURCE_DATA", "dataset:A", evidence_refs=["origin:A"])
        model = self.causal.add_node(self.owner, "DERIVED_ASSET", "model:B")
        product = self.causal.add_node(self.owner, "PRODUCT", "product:C")
        revenue = self.causal.add_node(self.owner, "REVENUE", "revenue:D", economic_observation={"amount": 5000, "currency": "CAD"})
        self.causal.add_edge(self.owner, source["node_id"], model["node_id"], "DERIVED_FROM", evidence_refs=["usage:1"])
        self.causal.add_edge(self.owner, model["node_id"], product["node_id"], "PRODUCED", evidence_refs=["build:1"])
        self.causal.add_edge(self.owner, product["node_id"], revenue["node_id"], "GENERATED", evidence_refs=["sale:1"], participation_rule_refs=["eopp:1"])
        trace = self.causal.trace(source["node_id"], revenue["node_id"])
        self.assertTrue(trace["connected"])
        self.assertTrue(trace["causal_chain_is_evidence_bound"])
        self.assertTrue(trace["economic_attribution_is_not_accounting_fair_value"])

    def test_14_v32_rights_passport_composes_without_rewrite(self):
        passport = self.passports.issue(self.owner, self.dco["object_id"], [{"effect":"ALLOW","actions":["TRAIN"]}], provenance_refs=["evidence:origin"])
        self.assertTrue(self.passports.verify(passport)["valid"])
        node = self.causal.add_node(self.owner, "DCO", self.dco["object_id"], evidence_refs=["evidence:origin"])
        right = self.causal.add_node(self.owner, "RIGHT", passport["passport_id"])
        edge = self.causal.add_edge(self.owner, node["node_id"], right["node_id"], "LICENSED_AS", evidence_refs=[passport["passport_sha256"]])
        self.assertTrue(edge["causality_is_evidence_bound_not_assumed"])

    def test_15_existing_exchange_lifecycle_survives_v33(self):
        eep = eep_mod.ExchangeProtocol(self.root, self.identity, self.fabric)
        venue = eep.create_venue(self.owner, "Reality Rights Venue", "CA", ["ORDER_BOOK"], hashlib.sha256(b"venue").hexdigest())
        inst = eep.define_instrument(self.owner, self.dco["object_id"], "SPOT_LICENSE", {"actions":["TRAIN"]}, 100, "CAD", transferable=True)
        disclosure = eep.publish_disclosure(venue["venue_id"], inst["instrument_id"], self.owner, "LISTING", hashlib.sha256(b"disc").hexdigest())
        eep.list_instrument(venue["venue_id"], inst["instrument_id"], self.owner, min_lot=1, tick_size=1, disclosure_sha256=disclosure["content_sha256"])
        eep.submit_order(venue["venue_id"], inst["instrument_id"], self.owner, "SELL", 1, 10, nonce="v33-sell")
        eep.submit_order(venue["venue_id"], inst["instrument_id"], self.buyer, "BUY", 1, 10, nonce="v33-buy")
        trade = eep.match_order_book(venue["venue_id"], inst["instrument_id"])[0]
        settled = eep.settle_trade(trade["trade_id"], payment_ref="external:receipt", external_verified=False)
        self.assertFalse(settled["entitlement"]["ownership_of_underlying_transferred"])

    def test_16_conformance_truth_boundaries(self):
        records = [
            reality_profile.reality_status(),
            {"schema":"entity-v3-evidence-object-v1","evidence_type":"DOCUMENT","content_sha256":"0"*64,"signature_proves_attribution_not_objective_truth":True,"immutable_evidence_record":True},
            {"schema":"entity-v3-evidence-bound-claim-v1","state":"ASSERTED","value_sha256":"1"*64,"evidence_refs":[],"claim_is_not_objective_truth":True,"state_is_typed_not_absolute":True},
            {"schema":"entity-v3-attestation-authority-grant-v1","scopes":["LAB"],"authority_evidence_sha256":"2"*64,"attestation_authority_is_scope_limited":True,"attestation_does_not_create_legal_truth":True},
            {"schema":"entity-v3-external-reality-anchor-v1","anchor_type":"LAB_SYSTEM","endpoint_descriptor_sha256":"3"*64,"credentials_included":False,"external_system_is_not_automatic_entity_authority":True},
            {"schema":"entity-v3-causal-economic-edge-v1","edge_type":"DERIVED_FROM","from_node_id":"A","to_node_id":"B","evidence_refs":["proof"],"authority_refs":[],"participation_rule_refs":[],"causality_is_evidence_bound_not_assumed":True,"economic_attribution_is_not_accounting_fair_value":True},
        ]
        self.assertTrue(all(conf_mod.validate_reality_record(record) for record in records))

if __name__ == "__main__":
    unittest.main()
