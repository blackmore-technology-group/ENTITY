# ENTITY Corporate Capital & Digital Commodity Requirements
Source: SERS-ENTITY-003 — Complete Master Engineering Design v2.1, Sections 151–170
Status: Authoritative repository requirement mapping — Sections 151–170 qualified in declared evidence/reconciliation scope; regulated execution disabled by default

## Corporate Digital Economy
- A corporate Entity SHALL govern Digital Commodities as productive digital assets under existing rights, provenance, policy, licensing and usage controls.
- Usage, billable activity, obligations, recognized revenue, settlement, cash and market value SHALL remain semantically separate.
- Usage activity SHALL NOT directly issue shares, change ownership percentages, or manufacture market price.
- Non-commercializable assets SHALL NOT create commercial economic evidence merely because they are used.

## Capital Evidence
- Corporate capitalization SHALL distinguish authorized, recorded issued and recorded outstanding quantities.
- Share classes and shareholder positions SHALL be recorded only from explicit corporate authority plus an external authoritative record/attestation in this implementation scope.
- Recorded shareholder positions SHALL reconcile exactly to recorded outstanding shares before a snapshot is accepted.
- Capital evidence events SHALL be signed, replay-resistant and linked to the ENTITY evidence ledger when configured.
- The core subsystem SHALL NOT operate as a broker, dealer, exchange, transfer agent or public securities venue.

## Valuation Boundary
- Modelled valuation SHALL be tagged DERIVED_INFERENCE.
- External market observations SHALL remain separate evidence objects with source and observation time.
- Internal economic metrics SHALL never overwrite or masquerade as externally observed market price.
- Corporate disclosures SHALL carry limitations and distinguish internal evidence from externally authoritative state.

## External Authority and Reconciliation
- External capital evidence SHALL be accepted only from explicitly trusted cryptographic authorities and SHALL be bound to subject, jurisdiction and evidence type.
- Jurisdiction/instrument action policy SHALL be versioned, effective-dated and fail closed to authorized review when no applicable rule exists.
- Corporate-action evidence SHALL bind the exact action, class and externally attested post-action capitalization before ENTITY adopts the resulting cap-table state.
- Capital-accounting evidence SHALL balance by currency and SHALL remain separate from legal ownership and verified cash movement.

## Current Qualification Boundary
- Implemented and qualified in declared corporate-capital evidence/reconciliation scope: Sections 151–170, including signed external-authority verification, jurisdiction fail-closed policy, corporate-action reconciliation, capital-accounting reconciliation, dilution/transfer checks, encrypted recovery, portable export and standalone independent verification.
- Section 170 Golden Scenario SHALL prove live-state unavailability followed by encrypted restore, restored invariant verification, signed portable export, file-inventory integrity and independent verification of restored/exported capital, action and accounting records.
- Full-platform rights/licensing/federation qualification remains governed by the separate ENTITY system-level E2E and release gates; this subsystem qualification SHALL NOT be used to imply those gates have passed.
- Not enabled: legally effective securities issuance by ENTITY core, broker/dealer execution, transfer-agent authority, custody, market-making, public trading or clearing/settlement.
- Those actions require separately authorized live external integrations, jurisdictional/legal review and qualification before activation.
