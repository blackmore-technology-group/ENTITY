import hashlib, importlib.util, pathlib, sys, tempfile, unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
ID=REPO/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py"
CORE=REPO/"src"/"31_Profiles"/"profile_core.py"
GOV=REPO/"src"/"31_Profiles"/"governance_privacy.py"
RES=REPO/"src"/"31_Profiles"/"resilience_interop.py"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

identity_mod=load("profiles_identity",ID)
core=load("profiles_core",CORE)
gov=load("profiles_governance",GOV)
res=load("profiles_resilience",RES)

class V3ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=self.tmp.name
        self.identity=identity_mod.EntityIdentityVault(self.root)
        self.owner=self.identity.create("Owner","business")["entity_id"]
        self.a1=self.identity.create("Authority One","system")["entity_id"]
        self.a2=self.identity.create("Authority Two","system")["entity_id"]
        self.a3=self.identity.create("Authority Three","system")["entity_id"]

    def tearDown(self): self.tmp.cleanup()
    def test_profile_version_and_schema_are_immutable(self):
        reg=core.ProfileRegistry(self.root)
        d=core.ProfileDescriptor("data","1.0",hashlib.sha256(b"data-v1").hexdigest())
        reg.register(d)
        with self.assertRaises(ValueError):
            reg.register(core.ProfileDescriptor("data","1.0",hashlib.sha256(b"changed").hexdigest()))
        reg.register(core.ProfileDescriptor("exchange","1.0",hashlib.sha256(b"eep-v1").hexdigest(),("data@1.0",)))
        selected=reg.negotiate({"data":["1.0"],"exchange":["1.0"]},{"data":["1.0"],"exchange":["1.0"]})
        self.assertEqual(selected["selected_profiles"]["exchange"],"1.0")
        reg.register_schema("right","1.0",{"x":1})
        with self.assertRaises(ValueError): reg.register_schema("right","1.0",{"x":2})

    def test_rights_deny_precedence_and_rfc_threshold(self):
        rules=[{"effect":"ALLOW","actions":["TRAIN"]},{"effect":"PROHIBIT","actions":["READ"]}]
        decision=core.RightsOntology.evaluate(rules,"TRAIN")
        self.assertEqual(decision["decision"],"DENY")
        inverse=core.RightsOntology.evaluate([
            {"effect":"ALLOW","actions":["READ"]},
            {"effect":"PROHIBIT","actions":["TRAIN"]},
        ],"READ")
        self.assertEqual(inverse["decision"],"ALLOW")
        governance=core.StandardGovernance(self.root,self.identity)
        rfc=governance.propose(self.owner,{"change":"new profile"},threshold=2)
        self.assertEqual(governance.endorse(rfc["rfc_id"],self.a1)["rfc_status"],"OPEN")
        self.assertEqual(governance.endorse(rfc["rfc_id"],self.a2)["rfc_status"],"ACCEPTED")

    def test_selective_disclosure_and_tamper_detection(self):
        pkg=gov.SelectiveDisclosure.commit({"age_over_18":True,"name":"private","region":"BC"})
        proof=gov.SelectiveDisclosure.disclose(pkg,["age_over_18"])
        self.assertTrue(gov.SelectiveDisclosure.verify(proof)["valid"])
        self.assertNotIn("name",proof["revealed"])
        proof["revealed"]["age_over_18"]["value"]=False
        self.assertFalse(gov.SelectiveDisclosure.verify(proof)["valid"])
    def test_dispute_history_is_preserved(self):
        ledger=gov.DisputeLedger(self.root,self.identity)
        claim=ledger.record("CLAIM",self.owner,"asset-x",{"ownership":"asserted"})
        challenge=ledger.record("CHALLENGE",self.a1,"asset-x",{"reason":"prior title"},target_ref=claim["record_id"])
        ledger.record("EVIDENCE",self.a1,"asset-x",{"sha":"evidence"},target_ref=challenge["record_id"])
        ledger.record("RULING",self.a2,"asset-x",{"outcome":"claim invalid"},target_ref=claim["record_id"],authority_basis="order-1")
        state=ledger.state("asset-x")
        self.assertEqual(state["state"],"RULED")
        self.assertGreaterEqual(state["record_count"],4)
        self.assertTrue(state["cryptographic_validity_is_not_legal_truth"])

    def test_status_stale_and_revoked_fail_closed(self):
        status=gov.StatusTimeProfile(self.root,self.identity)
        status.publish_status(self.owner,"right-1","ACTIVE",epoch=1,ttl_ms=10,effective_at_ms=1000)
        self.assertEqual(status.evaluate("right-1",at_ms=1005)["decision"],"ALLOW")
        self.assertEqual(status.evaluate("right-1",at_ms=1011)["decision"],"DENY")
        status.publish_status(self.owner,"right-1","REVOKED",epoch=2,ttl_ms=100,effective_at_ms=2000)
        self.assertEqual(status.evaluate("right-1",at_ms=2001)["decision"],"DENY")
        stamp=status.timestamp(self.owner,hashlib.sha256(b"event").hexdigest(),uncertainty_ms=5)
        self.assertEqual(stamp["uncertainty_ms"],5)

    def test_recovery_requires_quorum(self):
        recovery=gov.RecoveryQuorum(self.root,self.identity)
        recovery.set_policy(self.owner,[self.a1,self.a2],2)
        req=recovery.request(self.owner,{"reason":"compromise"})
        recovery.approve(req["request_id"],self.a1)
        with self.assertRaises(PermissionError): recovery.execute(req["request_id"])
        recovery.approve(req["request_id"],self.a2)
        result=recovery.execute(req["request_id"])
        self.assertTrue(result["quorum_verified"])
    def test_resolution_quorum_and_equivocation(self):
        fr=res.FederatedResolutionProfile(self.root,self.identity)
        record={"version":1,"endpoint":"ent3://example"}
        fr.observe(self.a1,"obj-1",record,epoch=1,ttl_ms=100000)
        fr.observe(self.a2,"obj-1",record,epoch=1,ttl_ms=100000)
        proof=fr.resolve_quorum("obj-1",minimum_resolvers=2)
        self.assertTrue(proof["resolved"])
        with self.assertRaises(ValueError):
            fr.observe(self.a1,"obj-1",{"version":1,"endpoint":"ent3://evil"},epoch=1,ttl_ms=100000)

    def test_agent_attenuation_budget_and_cascading_kill(self):
        agents=res.AgentDelegationProfile(self.root,self.identity)
        expiry=10**15
        root=agents.grant(self.owner,self.owner,self.a1,["TRAIN","INFER"],max_depth=1,budget_units=10,expires_at_ms=expiry,policy_sha256="a"*64)
        child=agents.grant(self.owner,self.a1,self.a2,["INFER"],max_depth=0,budget_units=5,expires_at_ms=expiry,parent_grant_id=root["grant_id"],policy_sha256="a"*64)
        with self.assertRaises(PermissionError):
            agents.grant(self.owner,self.a1,self.a3,["EXECUTE"],max_depth=0,budget_units=1,expires_at_ms=expiry,parent_grant_id=root["grant_id"],policy_sha256="a"*64)
        self.assertEqual(agents.consume(child["grant_id"],"INFER",3)["remaining_units"],2)
        with self.assertRaises(PermissionError): agents.consume(child["grant_id"],"INFER",3)
        killed=agents.kill(root["grant_id"])
        self.assertIn(child["grant_id"],killed["revoked_grants"])
        with self.assertRaises(PermissionError): agents.consume(child["grant_id"],"INFER",1)

    def test_physical_clone_attribution_and_settlement_neutrality(self):
        physical=res.PhysicalBindingProfile(self.root,self.identity)
        first=physical.bind(self.owner,"object-a","hw-001","b"*64)
        self.assertTrue(first["bound"])
        self.assertTrue(physical.bind(self.owner,"object-b","hw-001","c"*64)["clone_suspected"])
        receipt=res.AttributionMethodology.receipt("object-a",self.a1,"declared-weight","1.0",{"source-a":6000,"source-b":4000},confidence_bps=7500)
        self.assertTrue(receipt["methodology_is_not_universal_truth"])
        adapters=res.SettlementAdapterRegistry()
        adapters.register("bank","FIAT_BANK",["AUTHORIZE","CONFIRM"])
        adapters.register("ledger","INTERNAL_ACCOUNTING",["POST"])
        self.assertEqual(len(adapters.route("FIAT_BANK")),1)

    def test_abuse_degradation_merkle_and_legacy_bridge(self):
        gate=res.AdmissionController(limit=2,window_ms=1000)
        self.assertTrue(gate.admit("anon",at_ms=100)["allowed"])
        self.assertTrue(gate.admit("anon",at_ms=200)["allowed"])
        self.assertFalse(gate.admit("anon",at_ms=300)["allowed"])
        self.assertFalse(gate.admit("anon",at_ms=300)["reputation_used"])
        mode=res.DegradationStateMachine(); mode.transition("OFFLINE_VERIFY")
        self.assertTrue(mode.permits("VERIFY")); self.assertFalse(mode.permits("TRADE"))
        values=[{"i":i} for i in range(7)]
        proof=res.MerkleBatcher.proof(values,3)
        self.assertTrue(res.MerkleBatcher.verify(proof))
        proof["leaf"]="00"*32
        self.assertFalse(res.MerkleBatcher.verify(proof))
        bridge=res.LegacyBridgeRegistry.map("OIDC","legacy-123","ent3:test",evidence_sha256="d"*64)
        self.assertTrue(bridge["legacy_identifier_is_not_entity_authority"])

if __name__=="__main__": unittest.main()
