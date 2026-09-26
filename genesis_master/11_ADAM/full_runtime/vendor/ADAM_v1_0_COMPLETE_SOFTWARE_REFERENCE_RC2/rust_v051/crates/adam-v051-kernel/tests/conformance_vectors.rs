use adam_v051_kernel::{assignment_intent, build_equipment_physics, release_intent};
use serde_json::Value;

const VECTORS: &str = include_str!("../../../conformance/ADAM_V051_GOLDEN_VECTORS.json");

#[test]
fn twenty_reaction_roots_match_r4_oracle() {
    let vectors: Value = serde_json::from_str(VECTORS).unwrap();
    let transitions = vectors["transitions"].as_array().unwrap();
    let mut kernel = build_equipment_physics().unwrap();
    assert_eq!(kernel.root().unwrap(), vectors["initial_universe"]["root"]);
    for (index, expected) in transitions.iter().enumerate() {
        let intent = if index % 2 == 0 {
            assignment_intent(&kernel).unwrap()
        } else {
            release_intent(&kernel).unwrap()
        };
        let proof = kernel.commit(&intent).unwrap();
        assert_eq!(proof.reaction_id, expected["reaction_id"]);
        assert_eq!(proof.id().unwrap(), expected["proof_id"]);
        assert_eq!(proof.new_root, expected["new_root"]);
        assert_eq!(kernel.state.algebra.root().unwrap(), expected["algebra_root"]);
    }
    assert_eq!(kernel.root().unwrap(), vectors["final"]["root"]);
}
