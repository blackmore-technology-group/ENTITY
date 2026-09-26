#![no_main]
use adam_v051_kernel::ApplicationManifest;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(manifest) = serde_json::from_slice::<ApplicationManifest>(data) {
        let _ = manifest.validate();
    }
});
