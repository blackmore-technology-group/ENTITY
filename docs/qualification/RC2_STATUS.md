# ENTITY 1.0.0-rc2.1 Qualification Status

Date: 2026-09-17

## Current public claim

The published reference implementation is 1.0.0-rc2.1. It preserves the RC2 protocol semantics and corrects public source packaging from the initial rc2 tag.

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
