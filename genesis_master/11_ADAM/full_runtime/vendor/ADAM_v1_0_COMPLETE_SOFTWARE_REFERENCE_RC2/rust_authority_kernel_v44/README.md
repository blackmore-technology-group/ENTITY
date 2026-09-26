# ADAM v0.44 Rust atomic-physics authority kernel

This is the current compiled-kernel target for first-class bonds, hyperbonds and reaction proofs. The source now includes persistent restricted key storage, signed proof envelopes, signature verification during replay, stale-root checks, deterministic framing and `sync_all` durability.

The target is **source-audited but uncompiled in this environment** because `cargo` and `rustc` are unavailable. Compilation, Miri, fuzzing, dependency-vulnerability scanning, reproducible builds and independent review remain external qualification gates.
