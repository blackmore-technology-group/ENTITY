# ADAM v0.43 Rust Authority Kernel — External Build and Acceptance

## Included source

`rust_authority_kernel/` contains a complete isolated authority-process reference with:

- deterministic SHA-256 authority roots;
- append-only atomic frames;
- stale-root rejection;
- restart replay and non-tail integrity rejection;
- Ed25519 commit signatures;
- synchronized durable writes;
- zeroized secret-key lifecycle;
- newline-delimited JSON protocol;
- CI configuration for formatting, clippy, tests and release build.

## Why it is not marked compiled here

The execution environment used to assemble this release did not contain `cargo` or `rustc`. A native C protocol conformance binary was compiled and tested to validate the isolated-process and hash-chain contract, but it is not substituted for the required Rust deliverable.

## External build

```bash
cd rust_authority_kernel
cargo generate-lockfile
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo build --release --locked
```

## Required qualification

1. Record Rust compiler and dependency versions.
2. Build twice in isolated clean environments and compare release hashes.
3. Run protocol conformance against the native reference and Python authority oracle.
4. Fuzz JSON framing, malformed lengths, stale roots and torn-tail recovery.
5. Run Miri where applicable and platform sanitizers for FFI or future native extensions.
6. Verify non-tail tamper rejection and torn-tail recovery.
7. Verify file synchronization semantics on the target filesystem.
8. Integrate HSM/KMS signing so the Rust process does not retain exportable production keys.
9. Run sustained load and crash-injection qualification.
10. Obtain independent security and code review.

The Rust gap is closed only after these external gates produce signed evidence.
