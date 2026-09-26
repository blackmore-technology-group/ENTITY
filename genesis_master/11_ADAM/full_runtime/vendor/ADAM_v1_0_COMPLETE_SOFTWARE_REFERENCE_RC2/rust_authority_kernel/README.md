# ADAM v0.43 Rust authority kernel source

This source target is retained for lineage compatibility and has been hardened to use a persistent Ed25519 key, signed replay envelopes, stale-root rejection, fsync, and signature verification during replay.

It is **source-audited but uncompiled in this environment** because `cargo` and `rustc` are unavailable. The v0.44 target is the current authority-physics design; this v0.43 target is a predecessor and must not be described as production-certified.
