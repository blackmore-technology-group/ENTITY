#![no_main]
use adam_v051_kernel::WitnessChain;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(chain) = serde_json::from_slice::<WitnessChain>(data) {
        let _ = chain.verify();
    }
});
