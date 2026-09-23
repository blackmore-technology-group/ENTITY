import hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
IDENTITY=REPO/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py"
FABRIC=REPO/"src"/"30_Universal_Transaction_Fabric"/"canonical_universal_fabric.py"
ECONOMICS=REPO/"src"/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

identity_mod=load("entity_v3_identity",IDENTITY)
fabric_mod=load("entity_v3_fabric",FABRIC)
economics_mod=load("entity_v3_economics",ECONOMICS)

class UniversalFabricV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.identity=identity_mod.EntityIdentityVault(self.tmp.name)
        self.owner=self.identity.create("Data Owner","business")["entity_id"]
        self.buyer=self.identity.create("Licensed Principal","business")["entity_id"]
        self.agent=self.identity.create("Delegated AI Agent","system")["entity_id"]
        self.rogue=self.identity.create("Untrusted Actor","system")["entity_id"]
        self.fabric=fabric_mod.UniversalTransactionFabric(self.tmp.name,self.identity)

    def tearDown(self): self.tmp.cleanup()

    def test_five_primitive_status(self):
        status=self.fabric.status()
        self.assertEqual(status["primitives"],["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"])
        self.assertTrue(status["infrastructure_possession_is_not_authority"])
        self.assertTrue(status["provider_independent_exports"])
    def test_ai_authority_right_and_metered_settlement_obligation(self):
        digest=hashlib.sha256(b"governed training corpus").hexdigest()
        commodity=self.fabric.register_digital_commodity(self.owner,"Training Corpus",digest,commodity_class="TRAINING_DATA",measurement_unit="INFERENCE")
        agent_obj=self.fabric.register_ai_agent(self.owner,self.agent,"Buyer Agent",model_ref="model:test",capabilities=["TRAIN","INFER"])
        self.assertEqual(agent_obj["object_type"],"AI_AGENT")
        self.fabric.delegate_authority(self.buyer,self.buyer,self.agent,["ACCESS_DATA","EXECUTE"],scope={"purpose":"research"})
        self.fabric.grant_right(commodity["object_id"],self.owner,self.buyer,["TRAIN","INFER"],constraints={"purposes":["research"],"jurisdictions":["CA"]},economic_terms={"pricing":{"mode":"PER_UNIT","unit_price_units":5,"currency":"CAD"}})
        result=self.fabric.authorize_use(self.agent,self.buyer,commodity["object_id"],"TRAIN",quantity=3,purpose="research",jurisdiction="CA",nonce="use-001")
        self.assertTrue(result["authorized"])
        self.assertEqual(result["settlement_obligation"]["amount_units"],15)
        self.assertEqual(result["settlement_obligation"]["currency"],"CAD")
        self.assertFalse(result["settlement_obligation"]["external_money_movement_verified"])
        self.assertFalse(result["ownership_transferred"])
        with self.assertRaises(ValueError):
            self.fabric.authorize_use(self.agent,self.buyer,commodity["object_id"],"TRAIN",quantity=1,purpose="research",jurisdiction="CA",nonce="use-001")
        with self.assertRaises(PermissionError):
            self.fabric.authorize_use(self.rogue,self.buyer,commodity["object_id"],"TRAIN",quantity=1,purpose="research",jurisdiction="CA",nonce="use-rogue")

    def test_right_constraints_fail_closed(self):
        obj=self.fabric.register_digital_commodity(self.owner,"Restricted Data",hashlib.sha256(b"restricted").hexdigest())
        self.fabric.grant_right(obj["object_id"],self.owner,self.buyer,["INFER"],constraints={"purposes":["safety"],"jurisdictions":["CA"]})
        with self.assertRaises(PermissionError):
            self.fabric.authorize_use(self.buyer,self.buyer,obj["object_id"],"INFER",purpose="advertising",jurisdiction="CA",nonce="bad-purpose")
    def test_causal_provenance_and_derived_value_distribution(self):
        a=self.fabric.register_digital_commodity(self.owner,"Source A",hashlib.sha256(b"a").hexdigest())
        b=self.fabric.register_digital_commodity(self.buyer,"Source B",hashlib.sha256(b"b").hexdigest())
        child=self.fabric.register_object(self.owner,"MODEL","Derived Model",descriptor={"model_family":"test"})
        self.fabric.add_provenance(self.owner,a["object_id"],child["object_id"],"TRAINED_FROM",contribution_bps=6000,evidence={"method":"declared"})
        self.fabric.add_provenance(self.owner,b["object_id"],child["object_id"],"TRAINED_FROM",contribution_bps=4000,evidence={"method":"declared"})
        distribution=self.fabric.contribution_distribution(child["object_id"],101)
        self.assertEqual(distribution["allocated_total"],101)
        self.assertEqual(distribution["root_contribution_bps"][a["object_id"]],6000)
        self.assertEqual(distribution["root_contribution_bps"][b["object_id"]],4000)
        self.assertEqual(distribution["distribution"][a["object_id"]],61)
        self.assertEqual(distribution["distribution"][b["object_id"]],40)
        with self.assertRaises(ValueError):
            self.fabric.add_provenance(self.owner,child["object_id"],a["object_id"],"DERIVED_FROM",contribution_bps=1000)

    def test_trust_policy_threshold_is_evidence_not_truth(self):
        obj=self.fabric.register_object(self.owner,"PHYSICAL_ASSET","Inspected Machine")
        policy=self.fabric.create_trust_policy(self.owner,"INSPECTION",minimum_attestations=2,required_attestors=[self.buyer],allowed_attestors=[self.buyer,self.rogue])
        self.fabric.attest(self.buyer,obj["object_id"],"INSPECTION",hashlib.sha256(b"buyer inspection").hexdigest(),claim={"result":"PASS"})
        first=self.fabric.evaluate_trust(policy["policy_id"],obj["object_id"])
        self.assertFalse(first["policy_satisfied"])
        self.assertFalse(first["truth_inferred"])
        self.fabric.attest(self.rogue,obj["object_id"],"INSPECTION",hashlib.sha256(b"second inspection").hexdigest(),claim={"result":"PASS"})
        second=self.fabric.evaluate_trust(policy["policy_id"],obj["object_id"])
        self.assertTrue(second["policy_satisfied"])
        self.assertEqual(second["valid_attestation_count"],2)
        self.assertFalse(second["truth_inferred"])

    def test_usage_obligation_opens_existing_double_entry_settlement(self):
        obj=self.fabric.register_digital_commodity(self.owner,"Metered Dataset",hashlib.sha256(b"metered").hexdigest())
        self.fabric.grant_right(obj["object_id"],self.owner,self.buyer,["INFER"],economic_terms={"pricing":{"mode":"PER_UNIT","unit_price_units":7,"currency":"CAD"}})
        use=self.fabric.authorize_use(self.buyer,self.buyer,obj["object_id"],"INFER",quantity=4,nonce="settle-use-001")
        engine=economics_mod.SettlementEngine(self.tmp.name,self.identity)
        opened=self.fabric.open_settlement(engine,use["settlement_obligation"],transaction_nonce="v3-settlement-001")
        self.assertEqual(opened["amount_units"],28)
        self.assertEqual(opened["state"],"CREATED")
        authorized=engine.authorize(self.buyer,opened["settlement_id"])
        self.assertEqual(authorized["state"],"AUTHORIZED")
        confirmed=engine.confirm(self.buyer,opened["settlement_id"])
        self.assertTrue(confirmed["double_entry_balanced"])
        self.assertFalse(confirmed["external_money_movement_verified"])
    def test_resolution_attestation_and_portable_bundle(self):
        obj=self.fabric.register_object(self.owner,"PHYSICAL_ASSET","Machine 001",descriptor={"serial":"SYNTH-001"})
        self.fabric.publish_resolution(self.owner,obj["object_id"],[{"service":"verify","uri":"ent3://verify/example","protocol":"ENTITY"}],version=1)
        resolved=self.fabric.resolve(obj["object_id"])
        self.assertTrue(resolved["verified"])
        self.assertTrue(resolved["resolver_is_not_authority"])
        self.fabric.attest(self.buyer,obj["object_id"],"INSPECTION",hashlib.sha256(b"inspection evidence").hexdigest(),claim={"result":"PASS"})
        self.fabric.record_value(self.owner,obj["object_id"],250000,"CAD",basis_ref="owner_assertion")
        bundle=self.fabric.export_bundle(obj["object_id"])
        proof=self.fabric.verify_bundle(bundle)
        self.assertTrue(proof["valid"],proof["failures"])
        self.assertTrue(proof["primitive_set_complete"])
        self.assertTrue(proof["provider_independent"])
        self.assertGreaterEqual(proof["verified_manifest_count"],2)
        with tempfile.TemporaryDirectory() as foreign_tmp:
            foreign_identity=identity_mod.EntityIdentityVault(foreign_tmp)
            foreign_fabric=fabric_mod.UniversalTransactionFabric(foreign_tmp,foreign_identity)
            foreign_proof=foreign_fabric.verify_bundle(bundle)
            self.assertTrue(foreign_proof["valid"],foreign_proof["failures"])
            self.assertTrue(foreign_proof["portable_verification_uses_embedded_manifests"])
        tampered=dict(bundle); tampered["root_object_id"]="obj3-tampered"
        self.assertFalse(self.fabric.verify_bundle(tampered)["valid"])

    def test_standalone_bundle_verifier_has_no_source_vault_dependency(self):
        obj=self.fabric.register_object(self.owner,"DOCUMENT","Portable Evidence")
        bundle=self.fabric.export_bundle(obj["object_id"])
        bundle_path=pathlib.Path(self.tmp.name)/"bundle.json"
        bundle_path.write_text(json.dumps(bundle,sort_keys=True),encoding="utf-8")
        tool=REPO/"tools"/"verify_v3_bundle.py"
        run=subprocess.run([sys.executable,str(tool),str(bundle_path)],capture_output=True,text=True,check=False)
        self.assertEqual(run.returncode,0,run.stderr or run.stdout)
        result=json.loads(run.stdout)
        self.assertTrue(result["valid"],result["failures"])
        self.assertTrue(result["portable_verification_uses_embedded_manifests"])
if __name__=="__main__": unittest.main()


