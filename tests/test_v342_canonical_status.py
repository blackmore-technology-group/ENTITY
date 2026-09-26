import importlib.util,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"src"/"38_Global_Passports"/"canonical_status.py"
s=importlib.util.spec_from_file_location("cs",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class T(unittest.TestCase):
 def good(self):return {"origin_lineage_id":m.LINEAGE,"root_originator_entity_id":m.ROOT,"steward_entity_id":m.STEWARD,"protocol_entity_id":m.PROTOCOL}
 def test_canonical(self):self.assertTrue(m.classify(self.good())["canonical"])
 def test_removed_lineage_fails(self):x=self.good();x.pop("origin_lineage_id");self.assertFalse(m.classify(x)["valid"])
 def test_changed_root_fails(self):x=self.good();x["root_originator_entity_id"]="other";self.assertFalse(m.classify(x)["valid"])
 def test_changed_steward_fails(self):x=self.good();x["steward_entity_id"]="other";self.assertFalse(m.classify(x)["valid"])
 def test_derivative_allowed_not_canonical(self):r=m.classify({"status":m.DERIVED});self.assertTrue(r["valid"]);self.assertFalse(r["canonical"])
 def test_zero_royalty_and_sovereignty(self):p=m.policy();self.assertEqual(p["automatic_protocol_royalty_bps"],0);self.assertTrue(p["economic_participation_requires_explicit_terms"]);self.assertTrue(p["protocol_origin_does_not_create_asset_entitlement"]);self.assertTrue(p["protocol_origin_does_not_transfer_user_asset_ownership"])
 def test_release_boundary(self):b=self.good();b.update({"automatic_protocol_royalty_bps":0,"economic_participation_requires_explicit_terms":True,"asset_provenance_is_separate_from_protocol_origin":True});self.assertTrue(m.verify_release_body(b)["valid"]);b["automatic_protocol_royalty_bps"]=1;self.assertFalse(m.verify_release_body(b)["valid"])
