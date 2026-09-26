#![no_main]
use libfuzzer_sys::fuzz_target;
use adam_v051_kernel::unpack;

fuzz_target!(|data: &[u8]| {
    let _ = unpack(data);
});
