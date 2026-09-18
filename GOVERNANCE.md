# ENTITY Open-Source Governance

## Stewardship

Blackmore Technology Group Limited stewards the ENTITY specifications, reference implementation, and public release process.

Stewardship does not make BTG the sovereign authority over conforming Entity identities or data merely because BTG publishes software, specifications, resolvers, or infrastructure.

## Published protocol versions

A published protocol version is immutable in meaning. Corrections are handled through documented errata or a new version.

A conforming implementation of a published version must not require:

- BTG hosting;
- BTG DNS;
- a BTG resolver;
- a mandatory BTG cloud service;
- a paid BTG subscription

unless that dependency is explicitly outside core conformance and chosen by the Entity.

## Conformance

Conformance is determined by public specifications, schemas, test vectors, and reproducible verification—not by access to private BTG infrastructure.

ENTITY Protocol 1.0 is currently **FROZEN_FOR_EXTERNAL_CONFORMANCE**. Independent external interoperability qualification is still pending.

## Decision classes

Implementation-only fixes may be accepted without a protocol revision when they preserve published semantics.

Changes affecting identity, authority, signature meaning, portability, recovery, provider independence, evidence semantics, or wire compatibility require documented architecture/governance review.

## Extensions

Vendor- or application-specific extensions must be namespaced and must not silently redefine core ENTITY records.

## Historical integrity

Signed historical records are never silently reinterpreted under newer policy or protocol semantics.
