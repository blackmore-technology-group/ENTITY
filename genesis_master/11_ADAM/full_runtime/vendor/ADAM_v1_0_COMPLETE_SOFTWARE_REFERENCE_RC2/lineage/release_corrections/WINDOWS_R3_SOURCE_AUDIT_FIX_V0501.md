# Windows R3 Source-Audit Correction

The Windows R2 run correctly detected two Rust-target findings. They were caused by an audit policy error: `cargo check --locked` was invoked for crates that had no sealed `Cargo.lock`.

R3 corrects the policy and the Rust source:

1. `--locked` is enforced only when a lockfile is included.
2. A lockfile-free crate is copied to a temporary directory for dependency resolution and checking.
3. Standard qualification records an unavailable or failed optional Rust check without failing the Python production-reference gate.
4. `ADAM_REQUIRE_RUST=1` makes Rust compilation mandatory and blocking.
5. Both Rust response writers now serialize successful and failed responses through the same `serde_json::Value` envelope.
6. Blocking findings print their exact file, line and compiler output instead of only a count.

No Rust compilation success is claimed in the sealed evidence because this build environment did not provide Cargo.
