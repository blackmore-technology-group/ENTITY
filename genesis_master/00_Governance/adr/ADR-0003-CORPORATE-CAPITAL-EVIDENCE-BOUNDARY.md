# ADR-0003 — Corporate Capital Evidence Boundary
Status: ACCEPTED FOR SERS-ENTITY-003 IMPLEMENTATION
Date: 2026-09-15
Baseline: SERS-ENTITY-003 / v2.1

## Decision
ENTITY adds a corporate-capital and Digital Commodity layer, but the core SHALL remain an evidence/authority system rather than an unqualified securities execution venue.

## Required Separation
- Digital Commodity usage is economic evidence, not equity issuance.
- Recognized revenue is not cash receipt.
- Internal/modelled valuation is not externally observed market price.
- Recorded cap-table/shareholder state does not override a legally controlling external register.
- Legally effective capital changes require explicit corporate authority and external authoritative evidence/integration where applicable.

## Canonical Ownership
`21_Corporate_Capital\capital_structure\canonical_corporate_capital.py` owns the current `CORPORATE_CAPITAL_EVIDENCE_AND_ANALYTICS` runtime scope.

## Excluded Execution Scope
Broker/dealer execution, public securities trading, custody, market making, clearing/settlement, and transfer-agent authority are disabled in core pending separately authorized integration and qualification.

## Rationale
This preserves the ENTITY Evidence Boundary and prevents high usage, internal accounting, or a local database mutation from being misrepresented as market value, completed financing, or legally effective securities ownership.
