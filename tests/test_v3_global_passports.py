from __future__ import annotations
import gc, hashlib, importlib.util, pathlib, sys, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel); mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

identity_mod=load("v34_identity","src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod=load("v34_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
eep_mod=load("v34_eep","src/31_Profiles/exchange_protocol.py")
rights_mod=load("v34_rights","src/36_Adoption_Layer/rights_passport.py")
reality_profile=load("reality_profile","src/37_Verifiable_Reality/reality_profile.py")
evidence_mod=load("v34_evidence","src/37_Verifiable_Reality/evidence_objects.py")
profile_mod=load("v34_profiles","src/38_Global_Passports/profile_registry.py")
industry_mod=load("v34_industry","src/38_Global_Passports/industry_profiles.py")
global_mod=load("v34_global","src/38_Global_Passports/global_passport.py")
ingest_mod=load("v34_ingest","src/38_Global_Passports/continuous_ingestion.py")
status_mod=load("v34_status","src/38_Global_Passports/global_passport_profile.py")
conf_mod=load("v34_conf","src/38_Global_Passports/passport_conformance.py")
sdk_mod=load("v34_sdk","sdk/global_passport_sdk/canonical_global_passport_sdk.py")

class V34GlobalPassportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=pathlib.Path(self.tmp.name); self.state=self.base/"state"; self.source=self.base/"source"; self.source.mkdir()
        self.identity=identity_mod.EntityIdentityVault(self.state); self.fabric=fabric_mod.UniversalTransactionFabric(self.state,self.identity)
        self.owner=self.identity.create("BTG Owner","business")["entity_id"]; self.buyer=self.identity.create("Buyer","business")["entity_id"]
        self.evidence=evidence_mod.EvidenceRegistry(self.state,self.identity); self.rights=rights_mod.RightsPassportRegistry(self.state,self.identity,self.fabric)
        self.profiles=profile_mod.GlobalProfileRegistry(self.state,self.identity); self.installed=industry_mod.install_builtin_profiles(self.profiles,self.owner)
        self.globals=global_mod.GlobalPassportRegistry(self.state,self.identity,self.fabric,self.rights,self.profiles)
        self.ingest=ingest_mod.ContinuousProvenanceEngine(self.state,self.identity,self.fabric,self.evidence,self.rights,self.globals)
        self.dco=self.fabric.register_digital_commodity(self.owner,"AI Corpus",hashlib.sha256(b"corpus").hexdigest())
    def tearDown(self):
        self.ingest=self.globals=self.profiles=self.rights=self.evidence=None; gc.collect(); self.tmp.cleanup()

    def _rights_passport(self,version="1.0"):
        return self.rights.issue(self.owner,self.dco["object_id"],[{"effect":"ALLOW","actions":["READ","TRAIN","DERIVE"]}],version=version)

    def test_01_core_market_and_truth_boundaries_preserved(self):
        s=status_mod.passport_status(); self.assertEqual(s["core_primitives"],["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"])
        self.assertFalse(s["core_semantics_changed"]); self.assertTrue(s["market_engine_preserved"]); self.assertTrue(s["evidence_truth_boundary_preserved"])

    def test_02_builtin_global_and_six_industry_profiles_install(self):
        self.assertEqual(len(self.installed),7); self.assertIn("entity-profile:global@1.0",self.installed)
        self.assertTrue(all(self.profiles.verify(p)["valid"] for p in self.installed.values()))

    def test_03_profile_stack_requires_global_profile(self):
        with self.assertRaises(ValueError): self.profiles.resolve_stack(["entity-profile:ai@1.0"])

    def test_04_profile_stack_requires_declared_parents(self):
        p=self.installed["entity-profile:healthcare@1.0"]
        self.assertIn("entity-profile:global@1.0",p["parent_refs"])
        with self.assertRaises(ValueError): self.profiles.resolve_stack([p["profile_ref"]])

    def test_05_global_passport_binds_existing_rights_and_profile_stack(self):
        rp=self._rights_passport(); gp=self.globals.issue(self.owner,self.dco["object_id"],rp["passport_id"],["entity-profile:global@1.0","entity-profile:ai@1.0"],evidence_refs=["evidence:origin"])
        checked=self.globals.verify(gp); self.assertTrue(checked["valid"]); self.assertFalse(checked["objective_truth_claimed"]); self.assertFalse(checked["legal_compliance_claimed"])

    def test_06_standards_mapping_cannot_claim_equivalence(self):
        rp=self._rights_passport()
        with self.assertRaises(ValueError): self.globals.issue(self.owner,self.dco["object_id"],rp["passport_id"],["entity-profile:global@1.0","entity-profile:ai@1.0"],standards_mappings=[{"standard":"SPDX-3","normative_equivalence_claimed":True}])

    def test_07_healthcare_and_ai_profiles_compose(self):
        stack=self.profiles.resolve_stack(["entity-profile:global@1.0","entity-profile:healthcare@1.0","entity-profile:ai@1.0"])
        self.assertEqual(len(stack["profile_refs"]),3); self.assertTrue(stack["fail_closed"]); self.assertTrue(stack["profile_composition_does_not_create_authority"])

    def test_08_defence_robotics_ai_profiles_compose_and_remain_public(self):
        stack=self.profiles.resolve_stack(["entity-profile:global@1.0","entity-profile:defence-public@1.0","entity-profile:robotics@1.0","entity-profile:ai@1.0"])
        defence=self.profiles.get("entity-profile:defence-public@1.0"); self.assertTrue(defence["public_unclassified"]); self.assertEqual(len(stack["profile_refs"]),4)

    def test_09_healthcare_profile_maps_not_redefines_standards(self):
        p=self.profiles.get("entity-profile:healthcare@1.0"); names={x["standard"] for x in p["standards"]}
        self.assertEqual(names,{"HL7-FHIR","DICOM"}); self.assertTrue(p["policy"]["technical_interoperability_not_regulatory_compliance"])

    def test_10_finance_profile_contains_iso20022_fix_lei(self):
        names={x["standard"] for x in self.profiles.get("entity-profile:finance@1.0")["standards"]}; self.assertEqual(names,{"ISO-20022","FIX","LEI"})

    def test_11_manufacturing_profile_contains_opcua_aas(self):
        names={x["standard"] for x in self.profiles.get("entity-profile:manufacturing@1.0")["standards"]}; self.assertEqual(names,{"OPC-UA","ASSET-ADMINISTRATION-SHELL"})

    def test_12_ai_profile_contains_risk_and_supply_chain_mappings(self):
        names={x["standard"] for x in self.profiles.get("entity-profile:ai@1.0")["standards"]}; self.assertEqual(names,{"NIST-AI-RMF","SPDX-3","CYCLONEDX"})

    def test_13_robotics_profile_contains_ros_and_openrmf(self):
        names={x["standard"] for x in self.profiles.get("entity-profile:robotics@1.0")["standards"]}; self.assertEqual(names,{"ROS-2","OPEN-RMF"})

    def test_14_continuous_ingest_registers_bytes_evidence_rights_and_global_passport(self):
        f=self.source/"model.py"; f.write_text("print('entity')\n",encoding="utf-8")
        r=self.ingest.ingest_file(f,self.owner,["entity-profile:global@1.0","entity-profile:ai@1.0"],logical_path="models/model.py")
        self.assertEqual(r["object"]["object_type"],"SOFTWARE"); self.assertTrue(pathlib.Path(r["vault_path"]).is_file())
        self.assertTrue(self.evidence.verify_evidence(r["evidence"])["valid"]); self.assertTrue(self.rights.verify(r["rights_passport"])["valid"]); self.assertTrue(self.globals.verify(r["global_passport"])["valid"])
        self.assertEqual(r["value"]["amount_units"],0); self.assertTrue(r["custody_is_not_authority"])

    def test_15_version_ingest_creates_zero_weight_provenance_not_fake_economics(self):
        f1=self.source/"v1.py"; f2=self.source/"v2.py"; f1.write_text("a=1\n"); f2.write_text("a=2\n")
        a=self.ingest.ingest_file(f1,self.owner,["entity-profile:global@1.0","entity-profile:ai@1.0"],version="1")
        b=self.ingest.ingest_file(f2,self.owner,["entity-profile:global@1.0","entity-profile:ai@1.0"],version="2",previous_object_id=a["object"]["object_id"])
        self.assertEqual(len(b["provenance"]),1); self.assertEqual(b["provenance"][0]["contribution_bps"],0); self.assertTrue(b["provenance"][0]["provenance_is_not_ownership"])

    def test_16_directory_ingest_excludes_machine_noise(self):
        (self.source/"a.py").write_text("x=1\n"); cache=self.source/"__pycache__"; cache.mkdir(); (cache/"a.pyc").write_bytes(b"noise")
        r=self.ingest.ingest_directory(self.source,self.owner,["entity-profile:global@1.0","entity-profile:ai@1.0"],prefix="repo")
        self.assertEqual(r["files"],1); self.assertTrue(r["content_addressed"]); self.assertFalse(r["economic_value_invented"]); self.assertTrue(conf_mod.validate_global_passport_record(r))

    def test_17_tampered_global_passport_fails(self):
        rp=self._rights_passport(); gp=self.globals.issue(self.owner,self.dco["object_id"],rp["passport_id"],["entity-profile:global@1.0"])
        gp["industry_context"]={"tampered":True}; self.assertFalse(self.globals.verify(gp)["valid"])

    def test_18_v33_evidence_truth_boundary_composes(self):
        ev=self.evidence.issue_evidence(self.owner,"DOCUMENT",self.dco["object_id"],hashlib.sha256(b"source").hexdigest())
        rp=self._rights_passport(); gp=self.globals.issue(self.owner,self.dco["object_id"],rp["passport_id"],["entity-profile:global@1.0","entity-profile:ai@1.0"],evidence_refs=[ev["evidence_id"]])
        self.assertTrue(ev["signature_proves_attribution_not_objective_truth"]); self.assertTrue(gp["evidence_does_not_establish_objective_truth"])

    def test_19_existing_exchange_lifecycle_survives_v34(self):
        eep=eep_mod.ExchangeProtocol(self.state,self.identity,self.fabric); venue=eep.create_venue(self.owner,"Global Rights Venue","CA",["ORDER_BOOK"],hashlib.sha256(b"venue").hexdigest())
        inst=eep.define_instrument(self.owner,self.dco["object_id"],"SPOT_LICENSE",{"actions":["TRAIN"]},100,"CAD",transferable=True)
        disc=eep.publish_disclosure(venue["venue_id"],inst["instrument_id"],self.owner,"LISTING",hashlib.sha256(b"disc").hexdigest())
        eep.list_instrument(venue["venue_id"],inst["instrument_id"],self.owner,min_lot=1,tick_size=1,disclosure_sha256=disc["content_sha256"])
        eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",1,10,nonce="v34-sell"); eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",1,10,nonce="v34-buy")
        settled=eep.settle_trade(eep.match_order_book(venue["venue_id"],inst["instrument_id"])[0]["trade_id"],payment_ref="external:receipt",external_verified=False)
        self.assertFalse(settled["entitlement"]["ownership_of_underlying_transferred"])

    def test_20_conformance_validator_accepts_release_semantics(self):
        status=status_mod.passport_status(); profile=self.installed["entity-profile:global@1.0"]
        stack=self.profiles.resolve_stack(["entity-profile:global@1.0"])
        rp=self._rights_passport(); gp=self.globals.issue(self.owner,self.dco["object_id"],rp["passport_id"],["entity-profile:global@1.0"])
        records=[status,{k:v for k,v in profile.items() if k not in {"body_sha256","issuer_entity_id","signature"}},stack,{k:v for k,v in gp.items() if k not in {"body_sha256","signature"}}]
        self.assertTrue(all(conf_mod.validate_global_passport_record(x) for x in records))

    def test_21_defence_profile_cannot_be_registered_as_nonpublic(self):
        with self.assertRaises(ValueError):
            self.profiles.register(self.owner,"entity-profile:restricted-defence","1.0","INDUSTRY",schema_sha256="0"*64,public_unclassified=False)

    def test_22_sdk_composes_industry_profiles_and_registers_file(self):
        sdk=sdk_mod.EntityGlobalPassportSDK(self.profiles,self.globals,self.ingest)
        stack=sdk.compose_profiles("healthcare","ai"); self.assertEqual(stack["profile_refs"][0],"entity-profile:global@1.0")
        f=self.source/"clinical_model.onnx"; f.write_bytes(b"model")
        out=sdk.register_file(f,self.owner,"healthcare","ai",logical_path="models/clinical_model.onnx")
        self.assertIn("entity-profile:healthcare@1.0",out["profile_refs"]); self.assertFalse(out["economic_value_invented"])

    def test_23_sdk_status_preserves_authority_and_compliance_boundaries(self):
        status=sdk_mod.EntityGlobalPassportSDK.capability_status(); self.assertTrue(status["sdk_does_not_create_authority"])
        self.assertTrue(status["profile_is_not_regulatory_compliance"]); self.assertTrue(status["external_standards_are_mapped_not_redefined"])

if __name__=="__main__": unittest.main()
