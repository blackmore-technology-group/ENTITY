$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) { throw "rustc not found" }
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { throw "cargo not found" }
$version = (& rustc --version).Split(' ')[1]
if ($version -ne "1.97.1") { throw "Expected Rust 1.97.1, found $version" }
if (-not (Test-Path "Cargo.lock")) { throw "Cargo.lock is required" }
cargo fmt --all -- --check
cargo check --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --all-targets --locked
cargo build --workspace --release --locked
cargo run --release --locked --bin adam-v051-conformance -- conformance/ADAM_V051_GOLDEN_VECTORS.json
