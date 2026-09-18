# ENTITY Implementation Compatibility
Authoritative source: SERS-ENTITY-001 — Target Architecture v1.0
Repository scope: this public ENTITY repository and compatible integrations
Status: Unified implementation contract — 2026-09-15

## Authority Semantics
- ENTITY canonical authority remains in the owning root subsystem; NIKI remains reasoning/integration even though `10_NIKI` is now in the same implementation workstream.
- C2PA provenance validity, signer trust and factual truth remain separate states.
- Evidence origins and assurance levels SHALL never be silently upgraded.
- UNKNOWN, DERIVED_INFERENCE, DIRECT_OBSERVATION and external/counterparty evidence remain semantically distinct.
- Federation downgrade, credential revocation, source enrollment and evidence adoption fail closed where required.
- Repeated signed requests and evidence adoption are idempotent/deduplicated.

## NIKI Boundary
- NIKI may consume minimum-necessary projections, explain policy, produce proposals and reasoning receipts.
- NIKI SHALL NOT become authoritative for identity, rights, policy, vault content, contracts, settlement, peer trust, recovery or BSIE world state.
- Embedded NIKI persistence remains fallback/development state until canonical root bindings become READY.

## Runtime Binding
- `entity-runtime-binding-v1` supports both single-authority and multi-authority manifests.
- READY requires current owner `ENTITY_REQUIREMENTS.md` SHA-256, declared exports and qualification evidence.
- Multi-authority owner collisions are resolved by the active NIKI resolver; see `CANONICAL_BINDING_COLLISION_REGISTER.md`.

## Global Invariant
No implementation adapter may manufacture stronger ownership, truth, consent, privacy, usage, payment or monetary-value claims than the evidence establishes.

## SERS-ENTITY-003 / v2.1 Corporate-Capital Extension
- New canonical owner: `21_Corporate_Capital\capital_structure` for corporate-capital evidence and analytics.
- `10_NIKI` remains untouched by this implementation slice; NIKI may consume future minimum-necessary projections but SHALL NOT mutate capital state.
- Digital Commodity usage SHALL NOT mint equity, alter shareholder percentages, or create market price.
- Capital/share state accepted by core requires explicit corporate authority plus an external authoritative record/attestation.
- Modelled valuation remains `DERIVED_INFERENCE`; externally observed market price remains a separate evidence class.
- Regulated securities execution is disabled in core and requires a separately authorized/qualified external integration.
- External authority evidence is now cryptographically verified against explicit trusted authority keys and bound to subject, jurisdiction and evidence type.
- Corporate-action result evidence must bind the exact share class, action type and post-action capitalization before adoption.
- Capital accounting remains separate from legal ownership and from verified external cash; provider-confirmed settlement evidence is required for the latter.
- Section 170 Golden Scenario now verifies dilution, transfer, tamper rejection, per-share metrics, encrypted restore, signed portable export and standalone verification of restored/exported corporate-capital evidence.
- Current runtime scope: `CORPORATE_CAPITAL_SECTION_170_GOLDEN_SCENARIO`.
