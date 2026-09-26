#![no_main]
use adam_v051_kernel::AuthorityAtom;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(atom) = serde_json::from_slice::<AuthorityAtom>(data) {
        let _ = atom.validate();
    }
});
