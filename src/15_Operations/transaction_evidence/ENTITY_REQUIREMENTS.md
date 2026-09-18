# ENTITY Transaction Evidence Bundle Requirements
Source: SERS-ENTITY-003 v2.2 — Sections 171–172
Protocol specification: `14_Protocols_SDK/schemas/ENTITY_TRANSACTION_EVIDENCE_BUNDLE_v1.md`
Status: Authoritative repository requirement mapping

## Independent Reproducibility
- ENTITY SHALL produce a self-contained transaction evidence bundle whose material conclusions can be reproduced without executing the originating BTG production application.
- The transaction root SHALL deterministically commit to the complete rooted evidence object.
- The bundle SHALL bind identity, provenance, rights, licence, usage, settlement, accounting/value, Digital Commodity contribution, corporate authorization, share issuance/cap table, capital accounting, disclosure and ledger checkpoint evidence.
- Broken or contradictory cross-links SHALL fail closed.

## Sovereign Recovery
- ENTITY SHALL support an encrypted sovereign state package associated with the transaction bundle.
- The public recovery manifest SHALL bind the transaction root, bundle hash and encrypted-state hash while excluding the private recovery key.
- Live-state loss SHALL NOT prevent independent verification of the public transaction bundle and recovery package.
- Post-restore regeneration SHALL reproduce the same transaction root for unchanged rooted evidence.
## Evidence Boundary
- Cryptographic validity SHALL remain distinct from legal ownership, factual truth, real-world authority and market value.
- Possession, custody, storage or processing SHALL NOT silently establish sovereign authority, consent authority, licensing authority or economic participation.
- Provider-confirmed external payment SHALL require cryptographically verified provider evidence when the strong external-verification path is enabled.
- Digital Commodity economic events SHALL be signed and SHALL reference the underlying usage/licence/settlement evidence used for attribution.

## Verification and Tamper Resistance
- The standalone verifier SHALL recompute the transaction root and validate all required signatures, cross-links, accounting and capitalization invariants.
- The standalone verifier SHALL run without importing ENTITY production runtime modules.
- Tampering with any rooted material economic/capital evidence SHALL cause verification failure.
- Qualification SHALL compare pre-loss, live-state-unavailable and post-restore verification results.

## Publication
- Bundle v1 schema and canonicalization rules SHALL be versioned and documented.
- Historical v1 evidence SHALL remain interpretable under v1 rules after future protocol changes.
