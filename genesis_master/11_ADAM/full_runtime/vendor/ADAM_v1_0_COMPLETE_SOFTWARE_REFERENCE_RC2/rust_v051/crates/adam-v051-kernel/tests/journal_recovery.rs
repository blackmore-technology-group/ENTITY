use adam_v051_kernel::{PersistentAuthority, assignment_intent, release_intent};
use std::fs::OpenOptions;
use std::io::Write;
use tempfile::tempdir;

#[test]
fn restart_and_checkpoint_reproduce_root() {
    let directory = tempdir().unwrap();
    let final_root;
    {
        let mut authority = PersistentAuthority::open(directory.path()).unwrap();
        for index in 0..8 {
            let intent = if index % 2 == 0 {
                assignment_intent(authority.kernel()).unwrap()
            } else {
                release_intent(authority.kernel()).unwrap()
            };
            authority.commit(&intent).unwrap();
        }
        authority.checkpoint().unwrap();
        final_root = authority.health().unwrap().root;
    }
    let reopened = PersistentAuthority::open(directory.path()).unwrap();
    assert_eq!(reopened.health().unwrap().root, final_root);
    assert_eq!(reopened.health().unwrap().sequence, 8);
}

#[test]
fn torn_tail_is_removed_but_complete_tamper_is_rejected() {
    let directory = tempdir().unwrap();
    {
        let mut authority = PersistentAuthority::open(directory.path()).unwrap();
        let intent = assignment_intent(authority.kernel()).unwrap();
        authority.commit(&intent).unwrap();
    }
    let journal = directory.path().join("authority.journal");
    let original = std::fs::read(&journal).unwrap();
    OpenOptions::new()
        .append(true)
        .open(&journal)
        .unwrap()
        .write_all(b"TORN")
        .unwrap();
    let reopened = PersistentAuthority::open(directory.path()).unwrap();
    assert_eq!(reopened.health().unwrap().sequence, 1);
    assert_eq!(std::fs::read(&journal).unwrap(), original);

    let mut corrupted = original;
    let midpoint = corrupted.len() / 2;
    corrupted[midpoint] ^= 0x01;
    std::fs::write(&journal, corrupted).unwrap();
    assert!(PersistentAuthority::open(directory.path()).is_err());
}
