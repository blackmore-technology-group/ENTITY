from __future__ import annotations
import hashlib, importlib.util, pathlib, tempfile, time, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

identity_mod = load("global_identity", "src/01_Core_Runtime/identity/canonical_identity.py")
inst = load("global_institutional", "src/35_Global_Infrastructure/institutional_semantics.py")
privacy = load("global_privacy", "src/35_Global_Infrastructure/privacy_provenance.py")
topology = load("global_topology", "src/35_Global_Infrastructure/topology_crypto.py")

class GlobalInfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.vault = identity_mod.EntityIdentityVault(self.root / "vault")
        self.steward = self.vault.create("Steward", "organization")["entity_id"]
        self.gov = self.vault.create("Government", "organization")["entity_id"]
        self.academia = self.vault.create("University", "organization")["entity_id"]
        self.vendor = self.vault.create("Vendor", "business")["entity_id"]
        self.user = self.vault.create("User", "person")["entity_id"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_jurisdiction_profiles_are_immutable_and_fail_closed_on_conflict(self):
        reg = inst.JurisdictionProfileRegistry(self.root, self.vault)
        schema = hashlib.sha256(b"jurisdiction-schema").hexdigest()
        ca = reg.register(self.gov, "CA-BC", "DATA", "1.0", schema,
                          [{"effect": "ALLOW", "actions": ["TRAIN"],
                            "conditions": {"classification": "NON_PERSONAL"},
                            "obligations": ["DISCLOSURE"]}], effective_from_ms=1)
        eu = reg.register(self.gov, "EU", "DATA", "1.0", schema,
                          [{"effect": "PROHIBIT", "actions": ["TRAIN"],
                            "conditions": {"classification": "NON_PERSONAL"}}],
                          effective_from_ms=1)
        decision = reg.evaluate(["CA-BC", "EU"], "DATA", "TRAIN",
                                {"classification": "NON_PERSONAL"})
        self.assertEqual(decision["decision"], "DENY")
        self.assertTrue(decision["conflict_detected"])
        self.assertTrue(decision["legal_determination_not_made"])
        with self.assertRaises(ValueError):
            reg.register(self.gov, "CA-BC", "DATA", "1.0", schema,
                         [{"effect": "ALLOW", "actions": ["COPY"]}], effective_from_ms=1)
        ca2 = reg.register(self.gov, "CA-BC", "DATA", "2.0", schema,
                           [{"effect": "REQUIRE", "actions": ["TRAIN"],
                             "obligations": ["NEW_DISCLOSURE"]}], effective_from_ms=2)
        sup = reg.supersede(self.gov, ca["profile_id"], ca2["profile_id"])
        self.assertTrue(sup["history_rewrite_prohibited"])
        self.assertNotEqual(ca["profile_id"], eu["profile_id"])

    def test_semantic_registry_never_silently_equates_terms(self):
        reg = inst.SemanticRegistry(self.root, self.vault)
        reg.register_namespace(self.steward, "btg", "BTG canonical semantics")
        reg.register_namespace(self.gov, "gov", "Government semantics")
        a = reg.register_term(self.steward, "btg", "RIGHT", "TRAIN", "1.0",
                              {"meaning": "model training use"})
        b = reg.register_term(self.gov, "gov", "RIGHT", "MODEL_TRAINING", "1.0",
                              {"meaning": "regulated model-training use"})
        aref = reg.term_ref("btg", "RIGHT", "TRAIN", "1.0")
        bref = reg.term_ref("gov", "RIGHT", "MODEL_TRAINING", "1.0")
        reg.map_terms(self.steward, aref, bref, "EXACT", hashlib.sha256(b"evidence").hexdigest(),
                      jurisdiction_scope=["CA"], confidence_bps=10000)
        result = reg.mappings(aref, target_namespace="gov")
        self.assertEqual(result["unambiguous_exact_candidate"], bref)
        self.assertFalse(result["automatic_translation_permitted"])
        self.assertTrue(result["profile_or_human_semantic_decision_required"])
        with self.assertRaises(ValueError):
            reg.register_term(self.steward, "btg", "RIGHT", "TRAIN", "1.0",
                              {"meaning": "different meaning"})
        self.assertEqual(a["status"], "ACTIVE")
        self.assertEqual(b["status"], "ACTIVE")

    def test_multistakeholder_governance_requires_class_diversity(self):
        gov = inst.MultiStakeholderGovernance(self.root, self.vault)
        body = gov.create_body(self.steward, "ENTITY Standards Council",
                               hashlib.sha256(b"charter").hexdigest(),
                               ["INDUSTRY", "GOVERNMENT", "ACADEMIA"],
                               approval_threshold=3, min_approval_classes=3)
        industry2 = self.vault.create("Industry Two", "business")["entity_id"]
        gov.add_member(body["body_id"], self.steward, self.steward, "INDUSTRY")
        gov.add_member(body["body_id"], self.steward, industry2, "INDUSTRY")
        gov.add_member(body["body_id"], self.steward, self.gov, "GOVERNMENT")
        gov.add_member(body["body_id"], self.steward, self.academia, "ACADEMIA")
        proposal = gov.propose(body["body_id"], self.steward, "PROFILE", "profile:jurisdiction",
                               {"version": "1.0", "change": "add jurisdiction layer"})
        gov.vote(proposal["proposal_id"], self.steward, "APPROVE")
        gov.vote(proposal["proposal_id"], industry2, "APPROVE")
        interim = gov.vote(proposal["proposal_id"], self.gov, "APPROVE")
        self.assertEqual(interim["proposal_status"], "OPEN")
        final = gov.vote(proposal["proposal_id"], self.academia, "APPROVE")
        self.assertEqual(final["proposal_status"], "ACCEPTED")
        tally = gov.tally(proposal["proposal_id"])
        self.assertTrue(tally["diversity_requirement_met"])
        self.assertEqual(tally["approval_classes"], ["ACADEMIA", "GOVERNMENT", "INDUSTRY"])

    def test_governance_recusal_blocks_vote(self):
        gov = inst.MultiStakeholderGovernance(self.root, self.vault)
        body = gov.create_body(self.steward, "Council", hashlib.sha256(b"c").hexdigest(),
                               ["INDUSTRY", "PUBLIC"], approval_threshold=2, min_approval_classes=2)
        gov.add_member(body["body_id"], self.steward, self.steward, "INDUSTRY")
        gov.add_member(body["body_id"], self.steward, self.gov, "PUBLIC")
        proposal = gov.propose(body["body_id"], self.steward, "GOVERNANCE", "charter", {"x": 1})
        gov.declare_conflict(proposal["proposal_id"], self.gov, {"reason": "direct interest"}, recuse=True)
        with self.assertRaises(PermissionError):
            gov.vote(proposal["proposal_id"], self.gov, "APPROVE")

    def test_purpose_bound_access_revocation_and_use_caps(self):
        access = privacy.PurposeBoundAccessRegistry(self.root, self.vault)
        grant = access.grant(self.steward, self.user, "dataset:alpha", ["RESEARCH"], ["TRAIN"],
                             expires_at_ms=int(time.time() * 1000) + 60000, max_uses=1)
        use = access.authorize_use(grant["grant_id"], self.user, "RESEARCH", "TRAIN",
                                   hashlib.sha256(b"use").hexdigest())
        self.assertTrue(use["authorized"])
        self.assertEqual(use["remaining_uses"], 0)
        with self.assertRaises(PermissionError):
            access.authorize_use(grant["grant_id"], self.user, "RESEARCH", "TRAIN",
                                 hashlib.sha256(b"again").hexdigest())
        rev = access.revoke(self.steward, grant["grant_id"])
        self.assertEqual(rev["status"], "REVOKED")

    def test_selective_retention_preserves_commitment_after_destruction(self):
        ledger = privacy.SelectiveRetentionLedger(self.root, self.vault)
        payload_hash = hashlib.sha256(b"personal payload").hexdigest()
        rec = ledger.register(self.steward, "subject:1", payload_hash, purpose="RESEARCH",
                              jurisdiction="CA-BC", retain_until_ms=1,
                              destruction_mode="DELETE_PAYLOAD")
        destroyed = ledger.destroy(self.steward, rec["record_id"], hashlib.sha256(b"destroyed").hexdigest())
        self.assertEqual(destroyed["status"], "DESTROYED")
        status = ledger.status(rec["record_id"])
        self.assertEqual(status["payload_sha256"], payload_hash)
        self.assertTrue(status["commitment_preserved"])
        hold = ledger.register(self.steward, "subject:2", payload_hash, purpose="LEGAL",
                               jurisdiction="CA", retain_until_ms=1, destruction_mode="LEGAL_HOLD")
        with self.assertRaises(PermissionError):
            ledger.destroy(self.steward, hold["record_id"], hashlib.sha256(b"x").hexdigest())

    def test_confidential_provenance_encrypts_metadata_and_detects_wrong_key(self):
        ledger = privacy.ConfidentialProvenanceLedger(self.root, self.vault)
        key = hashlib.sha256(b"confidential-key").digest()
        edge = ledger.add_edge(self.steward, "dataset:A", "model:B", "DERIVED_FROM",
                               hashlib.sha256(b"evidence").hexdigest(),
                               metadata={"private_detail": "sensitive lineage"}, encryption_key=key)
        revealed = ledger.reveal_metadata(edge["edge_id"], key)
        self.assertTrue(revealed["commitment_valid"])
        self.assertEqual(revealed["metadata"]["private_detail"], "sensitive lineage")
        with self.assertRaises(Exception):
            ledger.reveal_metadata(edge["edge_id"], hashlib.sha256(b"wrong").digest())

    def test_proof_verifier_registry_fails_closed_without_bound_verifier(self):
        reg = privacy.ProofVerifierRegistry(self.root, self.vault)
        verifier_hash = hashlib.sha256(b"zk-verifier-binary").hexdigest()
        reg.register_suite(self.steward, "ZK-SUITE-1", "Example external ZK verifier",
                           verifier_hash, "External suite; security review required")
        with self.assertRaises(RuntimeError):
            reg.verify("ZK-SUITE-1", self.steward, b"valid-proof", {"claim": 1})
        reg.bind_runtime_verifier("ZK-SUITE-1", verifier_hash,
                                  lambda proof, public: proof == b"valid-proof" and public == {"claim": 1})
        accepted = reg.verify("ZK-SUITE-1", self.steward, b"valid-proof", {"claim": 1})
        rejected = reg.verify("ZK-SUITE-1", self.steward, b"bad-proof", {"claim": 1})
        self.assertTrue(accepted["accepted"])
        self.assertFalse(rejected["accepted"])
        self.assertTrue(accepted["proof_acceptance_is_suite_specific_not_universal_truth"])

    def test_partition_merge_converges_or_fails_closed(self):
        sync = topology.PartitionSync(self.root, self.vault)
        a = self.vault.create("Node A Operator", "organization")["entity_id"]
        b = self.vault.create("Node B Operator", "organization")["entity_id"]
        root1 = hashlib.sha256(b"root-1").hexdigest()
        root2 = hashlib.sha256(b"root-2").hexdigest()
        ca1 = sync.publish("A", a, "P1", sequence=1, epoch=1, state_root_sha256=root1,
                           vector_clock={"A": 1})
        cb1 = sync.publish("B", b, "P1", sequence=1, epoch=1, state_root_sha256=root2,
                           vector_clock={"B": 1})
        conflict = sync.merge("P1")
        self.assertFalse(conflict["resolved"])
        self.assertTrue(conflict["partition_conflict"])
        ca2 = sync.publish("A", a, "P1", sequence=2, epoch=2, state_root_sha256=root1,
                           vector_clock={"A": 2, "B": 1},
                           previous_checkpoint_sha256=ca1["checkpoint_sha256"])
        resolved = sync.merge("P1")
        self.assertTrue(resolved["resolved"])
        self.assertEqual(resolved["checkpoint_id"], ca2["checkpoint_id"])
        self.assertEqual(resolved["reason"], "CAUSALLY_DOMINANT_CHECKPOINT")
        self.assertNotEqual(ca1["checkpoint_id"], cb1["checkpoint_id"])

    def test_offline_envelope_is_signed_expiry_bounded_and_tamper_evident(self):
        payload = {"events": [{"id": 1, "action": "OBSERVE"}]}
        env = topology.OfflineEnvelope.create(self.vault, self.steward, "edge-1", "P-OFF", 1,
                                              payload, expires_at_ms=int(time.time() * 1000) + 60000)
        self.assertTrue(topology.OfflineEnvelope.verify(self.vault, env)["valid"])
        tampered = dict(env); tampered["payload"] = {"events": [{"id": 2}]}
        result = topology.OfflineEnvelope.verify(self.vault, tampered)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "PAYLOAD_HASH")

    def test_topology_nodes_do_not_gain_authority_by_membership(self):
        reg = topology.TopologyRegistry(self.root, self.vault)
        node = reg.register_node(self.steward, "node-edge-ca-1", "EDGE", "CA-BC",
                                 "btg-edge", ["VERIFY", "SYNC"])
        self.assertEqual(node["topology_class"], "EDGE")
        self.assertTrue(node["infrastructure_membership_is_not_sovereign_authority"])
        duplicate = reg.register_node(self.steward, "node-edge-ca-1", "EDGE", "CA-BC",
                                      "btg-edge", ["SYNC", "VERIFY"])
        self.assertTrue(duplicate["existing"])
        with self.assertRaises(ValueError):
            reg.register_node(self.steward, "node-edge-ca-1", "CORE", "CA-BC",
                              "btg-edge", ["VERIFY"])

    def test_crypto_migration_requires_dual_signatures_and_rejects_downgrade(self):
        reg = topology.CryptoSuiteMigration(self.root, self.vault)
        base = int(time.time() * 1000)
        old_hash = hashlib.sha256(b"old-verifier").hexdigest()
        new_hash = hashlib.sha256(b"new-verifier").hexdigest()
        reg.register_suite(self.steward, "OLD", "Old Algorithm", 128, old_hash,
                           not_before_ms=base - 10000,
                           deprecate_at_ms=base + 1000,
                           retire_at_ms=base + 3000)
        reg.register_suite(self.steward, "NEW", "New Algorithm", 192, new_hash,
                           not_before_ms=base - 10000)
        reg.register_transition(self.steward, "OLD", "NEW",
                                dual_sign_from_ms=base + 1000,
                                old_retire_at_ms=base + 3000)
        reg.bind_verifier("OLD", old_hash,
                          lambda sig, raw: sig == hashlib.sha256(b"OLD" + raw).digest())
        reg.bind_verifier("NEW", new_hash,
                          lambda sig, raw: sig == hashlib.sha256(b"NEW" + raw).digest())
        payload = {"entity": "example", "state": 7}
        raw = topology.canon(payload)
        old_sig = hashlib.sha256(b"OLD" + raw).digest()
        new_sig = hashlib.sha256(b"NEW" + raw).digest()
        pre = reg.verify_transition_payload(payload, {"OLD": old_sig}, "OLD", "NEW", at_ms=base)
        self.assertTrue(pre["valid"])
        missing_new = reg.verify_transition_payload(payload, {"OLD": old_sig}, "OLD", "NEW",
                                                    at_ms=base + 1500)
        self.assertFalse(missing_new["valid"])
        self.assertEqual(missing_new["reason"], "MISSING_REQUIRED_SUITE")
        dual = reg.verify_transition_payload(payload, {"OLD": old_sig, "NEW": new_sig},
                                             "OLD", "NEW", at_ms=base + 1500)
        self.assertTrue(dual["valid"])
        self.assertEqual(dual["required_suites"], ["OLD", "NEW"])
        downgraded = reg.verify_transition_payload(payload, {"OLD": old_sig}, "OLD", "NEW",
                                                   at_ms=base + 4000)
        self.assertFalse(downgraded["valid"])
        self.assertEqual(downgraded["missing"], ["NEW"])
        post = reg.verify_transition_payload(payload, {"NEW": new_sig}, "OLD", "NEW",
                                             at_ms=base + 4000)
        self.assertTrue(post["valid"])
        self.assertEqual(post["required_suites"], ["NEW"])

if __name__ == "__main__":
    unittest.main()
