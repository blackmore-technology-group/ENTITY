# ENTITY Market State Recovery Profile (MSRP) — v3 Development Draft

Status: RELEASED / BTG INTERNAL QUALIFIED

## Purpose

MSRP defines provider-independent logical recovery for ENTITY Exchange Protocol (EEP) and ENTITY Originator Participation Profile (EOPP) state. It protects market semantics from loss of a venue database or treasury database without making raw SQLite bytes authoritative.

The recoverable state includes market venues, instruments, rights balances, listings, signed orders, trades, clearing obligations, entitlements, disclosures, usage receipts, revenue rules, execution-time trade revenue bindings, RFQs, surveillance records, settlement attestations, treasuries, participation policies, reserve allocations, economic events, obligations, position snapshots and settlement-verifier authorizations.

## Logical state, not database bytes

A recovery bundle serializes table columns and normalized logical rows. JSON-bearing database fields are parsed before hashing so insignificant database serialization differences do not define authority.

Each table has a semantic SHA-256. Each EEP/EOPP database has a state root over its table snapshots. The bundle has a semantic root over both market domains, embedded public identity manifests, linked Core sovereign bundles and recovery policy metadata.

## Controller authorization

A checksum alone is not sufficient authorization to restore market state because an attacker could alter data and recompute hashes. MSRP therefore requires the market-state semantic root to be attested by every active venue operator and every active EOPP treasury owner present in the exported state.

Each controller signs `entity-v3-market-recovery-attestation-v1`, binding its ENTITY identity to the exact market-state root. Verification uses embedded public ENTITY manifests; restoration does not require the controller's private key.

A recovery verifier MUST reject a missing, duplicated, unexpected, root-mismatched or cryptographically invalid controller attestation.

## Restore semantics

Reference restoration requires initialized but empty target EEP and EOPP databases with schemas matching the exported logical state. Restore MUST fail closed rather than overwrite existing market state.

Trade revenue bindings are part of required EEP recovery state so recovery cannot silently replace execution-time economics with a later live rule set.

EEP and EOPP rows are restored inside one SQLite transaction with the EOPP database attached to the exchange connection. A failure in either domain MUST roll back both domains. After commit, both logical state roots are recomputed and MUST exactly equal the exported roots.

## Core linkage

The market bundle may embed underlying `entity-v3-sovereign-bundle-v1` records for ENTITY objects referenced by EEP instruments. Their semantic hashes are checked independently; when a Core bundle verifier is supplied, its embedded identity/signature and provenance verification is also required.

MSRP does not redefine ENTITY Core recovery. It composes market recovery with the existing provider-independent Core bundle rather than placing exchange state inside Core.

## Claim boundaries

MSRP does not export private signing keys. Identity key recovery remains governed by ENTITY identity/recovery mechanisms.

MSRP proves recoverability of logical EEP/EOPP state. It does not by itself prove recovery of every host operating-system component, external bank rail, off-platform database or third-party service.

Settlement evidence remains attestation evidence. Restoring an `external_verified` record restores the signed evidence and state that existed before failure; it does not transform that evidence into absolute truth.

The current implementation and destructive-recovery campaign are development evidence. Cross-language independent MSRP reimplementation and full-node destructive qualification remain pending.
