#![no_main]
use libfuzzer_sys::fuzz_target;
use adam_v051_kernel::FirstClassBond;

fuzz_target!(|data: &[u8]| {
    if let Ok(bond) = serde_json::from_slice::<FirstClassBond>(data) {
        let _ = bond.validate();
        let _ = bond.id();
    }
});
