from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

des = load("data_economic_sovereignty", "src/35_Global_Infrastructure/data_economic_sovereignty.py")
Z = "0" * 64

class DataEconomicSovereigntyTests(unittest.TestCase):
    def test_doctrine_status_preserves_truth_boundaries(self):
        s = des.DataEconomicSovereignty.doctrine_status()
        self.assertTrue(s["data_may_be_productive_capital"])
        self.assertFalse(s["artificial_information_scarcity_required"])
        self.assertTrue(s["scarcity_may_exist_in_bounded_economic_interests"])
        self.assertFalse(s["protocol_determines_legal_title"])
        self.assertFalse(s["protocol_determines_fair_value"])
        self.assertFalse(s["protocol_determines_regulatory_classification"])

    def _capital(self):
        return des.DataEconomicSovereignty.declare_digital_capital(
            "obj3-dataset", "ent-originator", Z, Z, asset_class="DATASET")

    def test_bounded_interest_creates_rights_based_scarcity_not_byte_scarcity(self):
        capital = self._capital()
        interest = des.DataEconomicSovereignty.define_bounded_interest(
            capital, "ent-holder", actions=["TRAIN", "READ"], quantity=100,
            duration_ms=86_400_000, jurisdiction="CA-BC", transferable=True,
            derivation_allowed=True, participation_bps=125)
        result = des.DataEconomicSovereignty.validate_interest(interest)
        self.assertTrue(result["valid"])
        self.assertFalse(result["information_scarcity_required"])
        self.assertTrue(result["economic_scarcity_is_rights_based"])
        self.assertTrue(interest["underlying_information_remains_nonrival"])
        self.assertIn("USAGE_QUANTITY", interest["scarcity_sources"])
        self.assertIn("JURISDICTION", interest["scarcity_sources"])

    def test_market_instrument_cannot_silently_transfer_underlying_data(self):
        interest = des.DataEconomicSovereignty.define_bounded_interest(
            self._capital(), "ent-holder", actions=["TRAIN"], quantity=10)
        instrument = {"rights": {"actions": ["TRAIN"]}, "total_units": 10,
                      "underlying_data_ownership_transferred": True}
        result = des.DataEconomicSovereignty.validate_market_instrument(instrument, interest)
        self.assertFalse(result["valid"])
        self.assertIn("instrument_silently_transfers_data_ownership", result["failures"])

    def test_market_instrument_rejects_protocol_fair_value_or_classification_claims(self):
        interest = des.DataEconomicSovereignty.define_bounded_interest(
            self._capital(), "ent-holder", actions=["QUERY"], quantity=5)
        instrument = {"rights": {"actions": ["QUERY"]}, "total_units": 5,
                      "protocol_declares_fair_value": True,
                      "protocol_declares_regulatory_classification": True}
        result = des.DataEconomicSovereignty.validate_market_instrument(instrument, interest)
        self.assertFalse(result["valid"])
        self.assertIn("protocol_fair_value_claim_prohibited", result["failures"])
        self.assertIn("protocol_classification_claim_prohibited", result["failures"])

    def test_economic_consequence_preserves_full_provenance_chain_and_truth_boundaries(self):
        chain = des.DataEconomicSovereignty.bind_economic_consequence(
            dco_ref="obj3-dataset", interest_id="interest3-a", use_event_ref="event3-use",
            derivative_ref="obj3-model", value_ref="value3-revenue", evidence_sha256=Z,
            methodology_ref="attrib3-contractual")
        self.assertTrue(chain["provenance_chain_complete"])
        self.assertTrue(chain["economic_consequence_is_evidence_not_objective_truth"])
        self.assertTrue(chain["legal_title_not_determined"])
        self.assertTrue(chain["fair_value_not_determined"])
        self.assertTrue(chain["regulatory_classification_not_determined"])

    def test_invalid_interest_cannot_claim_information_itself_is_scarce(self):
        interest = des.DataEconomicSovereignty.define_bounded_interest(
            self._capital(), "ent-holder", actions=["READ"])
        interest["underlying_information_remains_nonrival"] = False
        result = des.DataEconomicSovereignty.validate_interest(interest)
        self.assertFalse(result["valid"])
        self.assertIn("information_scarcity_asserted", result["failures"])

if __name__ == "__main__":
    unittest.main()
