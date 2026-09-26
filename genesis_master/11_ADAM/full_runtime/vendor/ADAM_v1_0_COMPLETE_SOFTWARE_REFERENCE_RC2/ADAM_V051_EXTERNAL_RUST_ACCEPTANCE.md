# ADAM v0.51 External Rust Build and Acceptance

The current package contains a complete source candidate but no compiled Rust evidence. Execute this program on controlled Linux and Windows builders.

## 1. Bootstrap the locked build

1. Verify the source ZIP and file-level manifest.
2. Install the pinned toolchain from `rust_v051/rust-toolchain.toml`.
3. From `rust_v051/`, run `cargo generate-lockfile` on an approved networked builder.
4. Review the resolved dependency graph and licences.
5. Run `cargo deny check`.
6. Seal `Cargo.lock`; every later command uses `--locked`.
7. Regenerate the resolved CycloneDX SBOM.

The source package intentionally contains no fabricated lockfile.

## 2. Build matrix

Required:

- Linux x86-64 debug and release;
- Windows x86-64 debug and release;
- release with debug symbols;
- Linux aarch64 check and, where hardware is available, execution;
- sanitizer-compatible nightly builds.

Every one of the five binary targets and the library must build. Clippy warnings are errors.

## 3. Exact Python–Rust conformance

Run:

```bash
cargo run --release --locked --bin adam-v051-conformance -- \
  conformance/ADAM_V051_GOLDEN_VECTORS.json
```

The runner must reproduce all 24 primitive vectors, all 20 state transitions and final root:

`107a151ccc502420c650b69f6d98a41949fa2305bd39c0b8480f6a2676e11868`

Then generate randomized valid vectors from R4 and execute them independently in both languages. Any mismatch blocks promotion.

## 4. Tests and adversarial qualification

Run unit, integration and property tests with `--locked`. Add crash injection at every commit stage and retain every discovered failing case as a regression vector.

Required adversarial rejections include forged proofs, stale roots, duplicate commits, conflicting worldlines, invalid canonical forms, unknown reactions, valence violations, invalid membership, witness equivocation, replayed grants, journal reordering, rollback attempts, checkpoint corruption and authority-key substitution.

## 5. Miri and sanitizers

Run the pinned nightly jobs defined in CI:

- Miri;
- AddressSanitizer;
- ThreadSanitizer;
- leak and deadlock qualification;
- platform-specific filesystem durability tests.

Every unsafe block would require a documented invariant and independent review; the current production source audit reports no unsafe Rust.

## 6. Fuzzing

Build and execute all fifteen fuzz targets. Pull requests may use short smoke campaigns; release qualification requires a documented long-running campaign, retained corpora, crash triage and zero unresolved reproducible failures.

## 7. Reproducible binaries

Build on two clean builders with identical source, lockfile and toolchain. Prefer byte-identical binaries. When platform metadata prevents that, compare normalized executable code and read-only data sections and document every accepted difference. Hash and sign the accepted outputs.

## 8. Independent review

An independent Rust and distributed-systems reviewer must examine canonical serialization, identity construction, reaction validation, supersession, signatures, replay, checkpoints, concurrency, durability, dependency risk, denial-of-service limits and all cryptographic boundaries.

## Final v0.51 promotion record

The promotion bundle must contain:

- sealed `Cargo.lock`;
- compiler and platform inventory;
- complete build logs;
- test/property results;
- conformance report;
- Miri and sanitizer reports;
- fuzz campaign summary and corpora hashes;
- reproducible-build comparison;
- resolved SBOM;
- binary hashes and signatures;
- independent review and remediation report.

Only that bundle can change the release name to **ADAM v0.51 — Compiled Authority and Information-Physics Kernel**.
