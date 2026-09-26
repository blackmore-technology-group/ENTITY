$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
.\RUN_ADAM_V051_SOURCE_QUALIFICATION.ps1
Set-Location (Join-Path $PSScriptRoot "rust_v051")
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { throw "cargo is required" }
if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) { throw "rustc is required" }
if (-not (Test-Path "Cargo.lock")) { throw "Generate, review and seal Cargo.lock before qualification." }
.\scripts\qualify.ps1
cargo deny check
cargo +nightly-2026-08-01 fuzz build
Write-Host "Windows Rust gates completed. Linux sanitizers, long fuzzing, reproducible cross-builder comparison and independent review remain required."
