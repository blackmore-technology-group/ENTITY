# ADAM v0.51 Rust Workspace

This workspace is the source candidate for the ADAM canonical authority boundary.

- Toolchain: see `rust-toolchain.toml`
- Frozen oracle: `conformance/ADAM_V051_GOLDEN_VECTORS.json`
- Full qualification: `scripts/qualify.sh` or `scripts/qualify.ps1`
- Fuzz targets: `fuzz/fuzz_targets/`
- External acceptance: `../ADAM_V051_EXTERNAL_RUST_ACCEPTANCE.md`

The package does not include a generated `Cargo.lock` because Cargo was unavailable locally. Generate, review and seal it on the first controlled builder before running locked qualification.
