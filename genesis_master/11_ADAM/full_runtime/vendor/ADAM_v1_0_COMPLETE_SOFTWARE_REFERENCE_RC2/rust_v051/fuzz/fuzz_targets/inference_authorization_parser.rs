#![no_main]
use adam_v051_kernel::InferenceAuthorizationRequest;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(request) = serde_json::from_slice::<InferenceAuthorizationRequest>(data) {
        let _ = request.validate();
    }
});
