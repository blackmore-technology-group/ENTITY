#![no_main]
use adam_v051_kernel::QuorumCertificate;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(certificate) = serde_json::from_slice::<QuorumCertificate>(data) {
        let _ = certificate.verify();
    }
});
