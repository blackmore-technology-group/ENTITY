#![no_main]
use libfuzzer_sys::fuzz_target;
use adam_v051_kernel::CheckpointStore;
use std::fs;

fuzz_target!(|data: &[u8]| {
    let name = adam_v051_kernel::canonical::sha256(data);
    let directory = std::env::temp_dir().join(format!("adam-v051-checkpoint-fuzz-{}", std::process::id()));
    let _ = fs::create_dir_all(&directory);
    let path = directory.join(format!("checkpoint-00000000000000000001-{name}.json"));
    if fs::write(&path, data).is_ok() {
        let store = CheckpointStore::new(&directory);
        let _ = store.load_latest(None);
        let _ = fs::remove_file(path);
    }
});
