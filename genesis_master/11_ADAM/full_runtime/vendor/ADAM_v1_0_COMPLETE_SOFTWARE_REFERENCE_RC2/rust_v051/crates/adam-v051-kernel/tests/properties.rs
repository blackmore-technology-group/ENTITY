use adam_v051_kernel::{CanonicalValue, assignment_intent, build_equipment_physics, digest, pack};
use proptest::prelude::*;

proptest! {
    #[test]
    fn canonical_map_order_does_not_change_identity(a in any::<i64>(), b in any::<i64>()) {
        let left = CanonicalValue::map([
            ("z", CanonicalValue::Int(a)),
            ("a", CanonicalValue::Int(b)),
        ]);
        let right = CanonicalValue::map([
            ("a", CanonicalValue::Int(b)),
            ("z", CanonicalValue::Int(a)),
        ]);
        prop_assert_eq!(pack(&left).unwrap(), pack(&right).unwrap());
        prop_assert_eq!(digest("ADAM51:PROPERTY", &left).unwrap(), digest("ADAM51:PROPERTY", &right).unwrap());
    }

    #[test]
    fn changed_authoritative_value_changes_identity(value in any::<i64>()) {
        let first = CanonicalValue::map([("value", CanonicalValue::Int(value))]);
        let second = CanonicalValue::map([("value", CanonicalValue::Int(value.wrapping_add(1)))]);
        prop_assert_ne!(digest("ADAM51:PROPERTY", &first).unwrap(), digest("ADAM51:PROPERTY", &second).unwrap());
    }
}

#[test]
fn simulation_and_invalid_reaction_never_change_authority() {
    let kernel = build_equipment_physics().unwrap();
    let initial = kernel.root().unwrap();
    let intent = assignment_intent(&kernel).unwrap();
    let simulation = kernel.simulate(&intent).unwrap();
    assert_ne!(simulation.proof.new_root, initial);
    assert_eq!(kernel.root().unwrap(), initial);

    let mut stale = intent;
    stale.expected_root = "00".repeat(32);
    assert!(kernel.simulate(&stale).is_err());
    assert_eq!(kernel.root().unwrap(), initial);
}
