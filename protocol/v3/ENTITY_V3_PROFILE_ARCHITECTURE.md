# ENTITY v3 Profile Architecture

Status: RELEASED / BTG INTERNAL QUALIFIED

## Core rule

ENTITY v3 conformance is intentionally small. Core conformance requires the five primitives `ENTITY`, `AUTHORITY`, `RIGHT`, `EVENT`, `VALUE`, canonical serialization, signature verification, authority/right references, deterministic event/state semantics, recovery verification and sovereign verification. It does **not** require a marketplace, AI runtime, payment rail, physical-device stack or domain application.

Profiles are independently versioned extensions. A verifier can negotiate supported profiles while retaining core interoperability. Historical schema versions are immutable: reusing the same schema/profile identifier and version with different bytes is an error.

## Reference and qualification implementations

`src/31_Profiles` is the modular v3 reference-profile line. It exposes profile behavior separately so an implementation can adopt only the profiles it supports.

`src/32_V3_Hardening` is an in-repository qualification mirror and integration harness for overlapping profile semantics. It is intentionally separate code, not a normative substitute for the reference line.

Where both lines implement the same semantic surface, convergence tests MUST produce the same protocol decision and economic result. A capability implemented in only one line is development functionality until it has direct normative tests/vectors. Neither source tree defines conformance by itself: versioned protocol text, schemas, vectors and deterministic results are normative.

## Initial profiles

- `AI-AUTHORITY` — attenuated delegation, depth, capability, budget, time and kill semantics.
- `DATA-COMMODITY` — digital commodity identity and machine-readable data rights.
- `EEP` — exchange instruments, listings, orders, matching, clearing, settlement, entitlements, usage, revenue distribution, surveillance, RFQ and market data.
- `ORIGINATOR-PARTICIPATION` / EOPP ? issuer-defined treasury reserves, primary-sale participation, secondary royalties, derivative participation and service revenue without a protocol tax or protocol token.
- `PRIVACY` — selective disclosure, encrypted claims and relationship-specific pseudonyms.
- `DISPUTE` — claim, challenge, evidence, ruling, supersession and downstream consequence without history deletion.
- `STATUS-TIME` — signed status epochs, revocation, compromise, TTL, stale policies and time attestations.
- `RECOVERY-CONTINUITY` — recovery quorum and succession/continuity designations.
- `RESOLUTION` — signed federated resolver views, TTL and anti-equivocation quorum semantics.
- `PHYSICAL-ASSET` — hardware binding, clone suspicion, inspection, custody, rebinding and tamper evidence.
- `SETTLEMENT` — adapter-neutral fiat/bank, accounting, credit, token, invoice, government rail and zero-value routes.
- `ARCHIVAL` — Merkle batches, archival snapshots, partial proof and pruning-with-proof semantics.
- `INTEROP` — explicit legacy mappings for OAuth/OIDC, X.509, DID/VC, DNS, C2PA, ERP, PKI, supply-chain identifiers and databases.

## Invariants

Cryptographic validity is not legal truth. Custody is not ownership. Resolver infrastructure is not authority. A legacy identifier is not ENTITY authority. Policy satisfaction is not truth. Attribution methodology is not universal truth. Internal settlement is not proof of external payment. Possession of bytes is not possession of a market right.

## Standard governance

Core changes require an RFC record, a change class, a signed proposer and a configured multi-party approval threshold. No reference implementation—including BTG's—defines the standard merely by shipping new behavior. Conformance is determined by versioned protocol text, schemas and tests.
