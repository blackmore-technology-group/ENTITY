ADAM v1.0 RC2 COMPLETE SOFTWARE REFERENCE

Use the external launcher distributed beside the ZIP:

  powershell -ExecutionPolicy Bypass -File .\START_ADAM_V1_RC2_WINDOWS.ps1 -InstallDependencies -Full

The launcher verifies the ZIP SHA-256, extracts to a clean R2 directory, then the internal launcher verifies the signed  v1 RC2 manifest before importing source.

Strict inherited Rust qualification can be added with -RequireRust. It requires Cargo, rustc, a reviewed Cargo.lock, cargo-deny, and the configured nightly toolchain.

A successful software run ends with:

  ADAM_V1_RC2_SOFTWARE_QUALIFICATION_PASS tests=148 gates=12

This package does not self-issue HSM, physical multi-host, certified-device, 30-day, or independent-assessor evidence.
