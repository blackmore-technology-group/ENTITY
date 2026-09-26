#![no_main]
use libfuzzer_sys::fuzz_target;
use adam_v051_kernel::{AuthorityJournal, build_equipment_physics};
use std::fs;

fuzz_target!(|data: &[u8]| {
    let Ok(kernel) = build_equipment_physics() else { return; };
    let Ok(root) = kernel.root() else { return; };
    let name = adam_v051_kernel::canonical::sha256(data);
    let directory = std::env::temp_dir().join(format!("adam-v051-fuzz-{}", std::process::id()));
    let _ = fs::create_dir_all(&directory);
    let path = directory.join(name);
    if fs::write(&path, data).is_ok() {
        let journal = AuthorityJournal::new(&path, root, None);
        let _ = journal.replay(true);
        let _ = fs::remove_file(path);
    }
});
