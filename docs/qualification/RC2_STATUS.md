# ENTITY 1.0.0-rc2.2 Qualification Status

Date: 2026-09-17

## Current public claim

The published reference implementation is 1.0.0-rc2.2. It preserves RC2 protocol semantics, supersedes RC2.1 for public checkout/use, and repairs repository-wide UTF-8 mojibake in public text/source literals.

ENTITY Protocol 1.0 is **FROZEN_FOR_EXTERNAL_CONFORMANCE**.

## Not yet claimed

The project does **not** currently claim that an unrelated non-BTG implementation has passed full interoperability qualification.

The sovereign-domain external qualification gate remains pending.

## Why this distinction matters

Internal reference tests can demonstrate consistency, fail-closed behavior, portability, recovery, and protocol enforcement in the reference implementation. They cannot by themselves prove that an independently authored implementation reaches the same result from the public specification.

The external milestone requires independent implementation/conformance evidence.

## Public reproducibility

This repository publishes the requirements, protocol freeze, reference source, schemas, SDK contracts, public verification material, and tests needed to support external conformance work without requiring private BTG production state.

## Clean-clone packaging validation

RC2.1 was cloned into a separate directory from Git-tracked content only. Required portability, credential-authority, sovereign-domain recovery, and principal-binding schema files were present; compileall and the public contract/repository-safety suite passed 4/4.

## UTF-8 repository validation

RC2.2 scans every tracked public text/source file for invalid UTF-8, Unicode replacement characters, and reconstructable Windows-1252/UTF-8 mojibake. The release gate requires zero findings.

Release evidence: 61 affected files / 219 mojibake sequences repaired; clean-clone public test suite 5/5 PASS; GitHub Actions Ubuntu run 35293106040 PASS.
