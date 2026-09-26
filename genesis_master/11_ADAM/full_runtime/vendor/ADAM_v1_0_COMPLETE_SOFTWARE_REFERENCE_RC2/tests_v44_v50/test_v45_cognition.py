from __future__ import annotations

from adam_v44 import BondAlgebra, BondFamily, FirstClassBond, HyperBond, HyperRole
from adam_v45 import CausalDiscoveryOrgan, ConfidenceCalibrator, NeuralSymbolicCognitionFabric, ProofGuidedScorer


def graph():
    a = BondAlgebra()
    for node, typ in [("S1", "PERSON"), ("S2", "PERSON"), ("P1", "PROJECT"), ("P2", "PROJECT"), ("E1", "EQUIPMENT")]:
        a.declare_entity(node, typ)
    a.add_bond(FirstClassBond("S1", "WORKS_ON", "P1", BondFamily.SEMANTIC, authority="OPS"))
    a.add_bond(FirstClassBond("S2", "WORKS_ON", "P2", BondFamily.SEMANTIC, authority="OPS"))
    a.add_bond(FirstClassBond("E1", "ASSIGNED_TO", "P1", BondFamily.OPERATIONAL, authority="OPS"))
    a.add_hyperbond(HyperBond("ASSIGNMENT_EVENT", (HyperRole("ACTOR", "S1"), HyperRole("DESTINATION", "P1")), authority="OPS"))
    a.add_hyperbond(HyperBond("ASSIGNMENT_EVENT", (HyperRole("ACTOR", "S2"), HyperRole("DESTINATION", "P2")), authority="OPS"))
    return a


def test_masked_bond_and_atom_training():
    fabric = NeuralSymbolicCognitionFabric()
    runs = fabric.train(graph())
    assert runs["masked_bond"].examples == 3
    assert fabric.masked_bond.predict("PERSON", "PROJECT").value == "WORKS_ON"
    assert fabric.masked_atom.predict("PERSON", "WORKS_ON").value == "PROJECT"
    assert fabric.masked_atom.predict("UNKNOWN", "UNKNOWN").abstained


def test_compound_discovery_promotes_repeated_hyperbond_shape():
    fabric = NeuralSymbolicCognitionFabric()
    candidates = fabric.compounds.discover(graph().hyperbonds.values())
    assert candidates[0].signature[0] == "ASSIGNMENT_EVENT"
    assert candidates[0].occurrences == 2


def test_causal_discovery_does_not_call_correlation_verified_cause():
    organ = CausalDiscoveryOrgan()
    episodes = [
        {"id": "1", "features": ["RAIN"], "outcomes": ["DELAY"]},
        {"id": "2", "features": ["RAIN"], "outcomes": ["DELAY"]},
        {"id": "3", "features": [], "outcomes": []},
    ]
    claim = organ.discover(episodes, "RAIN", "DELAY")
    assert claim.classification == "possible_cause"
    episodes.append({"id": "4", "features": ["RAIN"], "outcomes": ["DELAY"], "intervention": "RAIN", "verified_causal": True})
    assert organ.discover(episodes, "RAIN", "DELAY").classification == "verified_cause"


def test_calibration_and_proof_guided_scoring():
    report = ConfidenceCalibrator().evaluate([(0.9, True), (0.8, True), (0.2, False), (0.4, False)])
    assert report.accuracy == 1.0
    scorer = ProofGuidedScorer()
    assert scorer.score(validation_passed=False, evidence_coverage=1, authority_valid=True,
                        reconstruction_preserved=True, predictive_gain=1, cost_reduction=1) == 0.0
    assert scorer.score(validation_passed=True, evidence_coverage=1, authority_valid=True,
                        reconstruction_preserved=True, predictive_gain=1, cost_reduction=1) == 1.0


def test_graph_embedding_organ_trains_and_keeps_parameters_in_worldline():
    fabric = NeuralSymbolicCognitionFabric()
    runs = fabric.train(graph())
    assert runs["graph_embedding"].examples == 3
    assert fabric.graph_embedding.model_id is not None
    assert fabric.graph_embedding.worldline.versions[-1][0] == fabric.graph_embedding.model_id
    prediction = fabric.graph_embedding.predict_tail("S1", "WORKS_ON")
    assert prediction.alternatives
    assert fabric.graph_embedding.predict_tail("UNKNOWN", "WORKS_ON").abstained


def test_model_parameters_and_training_can_be_proposed_as_universe_state():
    from adam_v45 import CognitionUniverseBinder, ModelArtifact
    artifact = ModelArtifact(
        "risk_model", "8", "DATASET1", b"parameter-bytes", {"accuracy": 0.97},
        "PROJECT_RISK", "OPS", supersedes="MODEL7",
    )
    proposal = CognitionUniverseBinder().propose(artifact, authority="OPS", logical_time=4, evidence_id="TRAINING_LOG")
    predicates = {bond.predicate for bond in proposal.bonds}
    assert {"TRAINED_ON", "HAS_PARAMETERS", "ACHIEVED_METRIC", "AUTHORIZED_FOR", "SUPERSEDES"} <= predicates
    assert proposal.training_event.event_type == "MODEL_TRAINING_EVENT"
    assert proposal.exact_parameter_bytes == b"parameter-bytes"


def test_concept_atom_remains_expandable_and_explainable():
    from adam_v45 import ConceptAtom
    concept = ConceptAtom("PROJECT_RISK", "P204", ("DELAY", "COST", "FAILURE"), "MODEL8", 0.81, "OPS", 5)
    hb = concept.explanatory_hyperbond()
    assert hb.metadata["concept_id"] == concept.concept_id
    assert {r.participant for r in hb.roles} >= {"P204", "MODEL8", "DELAY", "COST", "FAILURE"}
