#![no_main]
use libfuzzer_sys::fuzz_target;
use adam_v051_kernel::{ReactionIntent, build_equipment_physics};

fuzz_target!(|data: &[u8]| {
    if let Ok(intent) = serde_json::from_slice::<ReactionIntent>(data) {
        if let Ok(kernel) = build_equipment_physics() {
            let _ = kernel.simulate(&intent);
        }
    }
});
