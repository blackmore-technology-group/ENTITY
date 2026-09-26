# ADR-0002 — Legacy Data Universe to Canonical Asset Registry
Status: ACCEPTED
Effective baseline: SERS-ENTITY-002 v2.0

## Problem
The legacy `data_universe` fallback combines asset registration, licensing, usage, settlement and a legacy owner field. SERS-002 requires these authorities to be separated and prohibits registration or possession from being interpreted as ownership.

## Current baseline behavior
NIKI requests only `niki_project_data_summary_v1` from the `data_universe` authority. The embedded fallback exposes a broad legacy DataUniverse implementation.

## Decision
The canonical `data_universe` NIKI projection SHALL be served by the root-owned Asset Registry. Asset records use `controller_entity_id`; legal ownership remains exclusively a Rights & Claims assertion. Licensing, usage and economics remain separate authorities.

## Security / privacy impact
This reduces authority concentration and prevents NIKI summary access from implying rights, licensing or economic mutation authority.

## Rights / economic impact
Asset registration produces a DATA_CONTROLLER record and provenance binding but never an ownership conclusion. No economic state is created by registration.
## Interoperability / migration impact
The NIKI export name remains `niki_project_data_summary_v1`, preserving the read-only projection ABI while changing its canonical owner to the Asset Registry. Existing legacy records require explicit migration; no historical signed record is reinterpreted.

## Backward compatibility
NIKI remains compatible because the projection contract is preserved. Legacy broad DataUniverse mutation APIs are not promoted into the canonical asset authority.

## Rejected alternatives
- Promote the legacy combined DataUniverse unchanged.
- Treat asset registration as ownership.
- Keep licensing and settlement inside the NIKI-facing asset summary authority.

## Approval / implementation
Approver: repository engineering authority
Implementation: `04_Entity_Registry/asset_registry/canonical_asset_registry.py`
Verification: `16_Test_Qualification/unit/test_canonical_asset_ledger.py`
Recovery verification: `16_Test_Qualification/recovery/test_destructive_sovereignty_extended.py`
