# Cargo.lock Is Required for Promotion

`rust_v051/Cargo.lock` is intentionally absent from this source-qualified package because Cargo is unavailable in the qualification environment. A lockfile has not been invented by hand.

The first approved Rust builder must:

1. verify the source manifest;
2. install the pinned Rust toolchain;
3. run `cargo generate-lockfile`;
4. review dependency sources, versions and licences;
5. run `cargo deny check`;
6. seal and sign the resulting lockfile;
7. use `--locked` for every qualification and release command.

Absence of `Cargo.lock` is an open execution gate, not a source defect.
