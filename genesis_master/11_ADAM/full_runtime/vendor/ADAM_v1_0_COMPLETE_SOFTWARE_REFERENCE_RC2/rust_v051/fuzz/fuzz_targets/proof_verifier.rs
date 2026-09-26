#![no_main]
use adam_v051_kernel::{ReactionIntent, ReactionProof, build_equipment_physics};
use libfuzzer_sys::fuzz_target;
use serde::Deserialize;

#[derive(Deserialize)]
struct Candidate {
    intent: ReactionIntent,
    proof: ReactionProof,
}

fuzz_target!(|data: &[u8]| {
    if let Ok(candidate) = serde_json::from_slice::<Candidate>(data) {
        if let Ok(kernel) = build_equipment_physics() {
            if let Ok(simulation) = kernel.simulate(&candidate.intent) {
                let _ = simulation.proof == candidate.proof;
            }
        }
    }
});
