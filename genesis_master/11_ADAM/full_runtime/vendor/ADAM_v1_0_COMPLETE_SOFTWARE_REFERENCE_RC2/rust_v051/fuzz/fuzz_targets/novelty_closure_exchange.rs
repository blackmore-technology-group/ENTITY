#![no_main]
use adam_v051_kernel::NoveltyClosureEnvelope;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(envelope) = serde_json::from_slice::<NoveltyClosureEnvelope>(data) {
        let _ = envelope.validate();
    }
});
