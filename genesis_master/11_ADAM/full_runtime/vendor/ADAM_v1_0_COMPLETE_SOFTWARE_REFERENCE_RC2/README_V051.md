# ADAM v0.51 — Rust Authority Kernel Source Qualification Candidate

**Version:** `0.51.0.dev1`  
**Frozen oracle:** ADAM v0.50.1 R4 (`0.50.1.dev4`)  
**Classification:** Rust authority source qualification candidate  
**Rust compiled in this environment:** **No**  
**Production certified:** **No**

## Purpose

v0.51 is the first production-program branch after the source-audited Python reference. It does not add another Python authority design. It preserves R4 as an immutable comparison oracle and supplies a new Rust workspace intended to become the canonical authority boundary after external compiler, conformance, fuzzing, sanitizer and independent-review gates pass.

## Locally verified evidence

- Frozen R4 wrapper SHA-256: `3c406f50710d3aad86952bf87b42ac27b5260a77f357461e21122054cb6812c4`
- R4 regression oracle: **117/117 tests passed**
- Inherited integrated logic audit: **9/9 gates passed**
- v0.51 source-adversarial qualification: **8/8 tests passed**
- Rust source audit: **0 blocking findings**
- Rust files scanned: **35**
- Rust executable targets defined: **5**
- Rust fuzz targets defined: **15**
- Canonical primitive vectors: **24**
- R4 reaction transitions: **20**
- Final R4 conformance root: `107a151ccc502420c650b69f6d98a41949fa2305bd39c0b8480f6a2676e11868`

## Implemented Rust source

The workspace under `rust_v051/` contains:

- exact R4-compatible canonical MessagePack encoding and a strict bounded decoder;
- atoms, first-class bonds, recursive bond atoms and hyperbonds;
- valence constraints, constitutional laws and deterministic reactions;
- immutable bond supersession and causal worldlines;
- reaction simulation, proof creation and authoritative commits;
- Ed25519 development signing with persistent identity binding;
- framed append-only journal with checksums, signatures, stale-root protection, `fsync`, torn-tail recovery and non-tail tamper rejection;
- immutable signed checkpoints and genesis-to-head replay verification;
- explicit quorum-certificate and witness-chain verification;
- bounded application, inference-authorization and novelty-closure protocol structures;
- five command-line targets, Rust tests, property tests and fifteen fuzz targets.

## Five executable targets

```text
adam-v051-authority-service
adam-v051-conformance
adam-v051-replay
adam-v051-checkpoint
adam-v051-proof-verify
```

These targets are source-complete but were not compiled here because neither `cargo` nor `rustc` is installed.

## Qualification commands

Local source qualification, which does not pretend to compile Rust:

```bash
./RUN_ADAM_V051_SOURCE_QUALIFICATION.sh
```

Windows PowerShell:

```powershell
./RUN_ADAM_V051_SOURCE_QUALIFICATION.ps1
```

Full Rust qualification on a controlled host after a real Cargo run generates and seals `rust_v051/Cargo.lock`:

```bash
./RUN_ADAM_V051_FULL_RUST_QUALIFICATION.sh
```

The external qualification path must run Linux and Windows builds, exact Python–Rust conformance, Miri, sanitizers, fuzzing, reproducible-build comparison and independent review before the release may be renamed **Compiled Authority and Information-Physics Kernel**.

## Claim boundary

This release demonstrates that the Rust authority implementation has been designed, source-audited and bound to a deterministic R4 oracle. It does **not** demonstrate that the source compiles, that dependencies resolve safely, that Miri or sanitizers pass, that fuzzing has completed, that binaries reproduce across hosts, or that an independent Rust reviewer has approved the kernel. Those are explicit promotion gates, not assumed results.
