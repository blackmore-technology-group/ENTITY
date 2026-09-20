import importlib.util
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = load("entity_public_causal_niki", REPO / "src" / "10_NIKI" / "causal_intelligence.py")
R = load("entity_public_cognition_router", REPO / "src" / "10_NIKI" / "cognition_router.py")


def model():
    return {
        "schema": "niki-causal-model-v1",
        "model_id": "public-test-v1",
        "provenance": {"source": "public-conformance-test"},
        "variables": {
            "x": {"parents": [], "equation": {"kind": "input", "default": 0}},
            "y": {"parents": ["x"], "equation": {"kind": "linear", "intercept": 0, "weights": {"x": 2}}},
        },
    }


class PublicCausalNikiTests(unittest.TestCase):
    def test_intervention_and_authority_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            engine = C.CausalIntelligenceEngine(td)
            out = engine.analyze({
                "model": model(),
                "observed": {"x": 1},
                "interventions": [{"scenario_id": "raise-x", "set": {"x": 3}}],
                "objectives": [{"variable": "y", "direction": "maximize"}],
            })
        self.assertEqual(out["baseline"]["y"], 2.0)
        self.assertEqual(out["best_positive_intervention"]["state"]["y"], 6.0)
        self.assertFalse(out["authoritative_state_mutation"])
        self.assertEqual(out["execution_authority"], "ENTITY")
        self.assertEqual(out["executor"], "ADAM")

    def test_persistent_model_activation_requires_entity(self):
        with tempfile.TemporaryDirectory() as td:
            registry = C.CausalModelRegistry(td)
            with self.assertRaises(PermissionError):
                registry.register(model(), {"approved": True, "authority": "NIKI", "approval_id": "bad"})
            self.assertTrue(registry.register(model(), {"approved": True, "authority": "ENTITY", "approval_id": "ok"})["registered"])

    def test_router_never_grants_execution(self):
        route = R.AdaptiveCognitionRouter().route(
            analysis={"intent": "prediction", "requires_spatial_context": True},
            evidence_count=2, conflicts={}, domain_intelligence={"present": True},
            metadata={"causal_analysis": {}}, causal_available=True,
        )
        self.assertIn("counterfactual_reasoning", route["stages"])
        self.assertFalse(route["autonomous_side_effects"])
        self.assertEqual(route["execution_authority"], "ENTITY")


if __name__ == "__main__":
    unittest.main()