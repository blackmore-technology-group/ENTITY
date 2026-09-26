#![no_main]
use libfuzzer_sys::fuzz_target;
use adam_v051_kernel::HyperBond;

fuzz_target!(|data: &[u8]| {
    if let Ok(hyperbond) = serde_json::from_slice::<HyperBond>(data) {
        let _ = hyperbond.validate();
        let _ = hyperbond.id();
    }
});
