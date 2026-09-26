# ENTITY Spatial / AR Dashboard Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Integration Boundary
- Spatial/AR views SHALL consume BSIE world/relationship state and SHALL NOT become authoritative for ENTITY rights or authority.
- Scene graphs, camera projections and AR-derived observations SHALL preserve provenance and evidence origin.

## Data Handling
- Spatial observations SHALL distinguish DIRECT_OBSERVATION, ENTITY_ASSERTION, COUNTERPARTY_ATTESTATION, EXTERNAL_AUTHORITATIVE_RECORD, DERIVED_INFERENCE and UNKNOWN.
- AI-derived classifications or scene interpretations SHALL remain DERIVED_INFERENCE until accepted or corroborated.
- Sensitive location or visual content SHALL respect vault classification, disclosure policy and least-privilege projection.
- Public/shared spatial events SHOULD avoid globally correlatable root identifiers where feasible.

## Actions
- Dashboard UI MAY explain Entity/BSIE state but SHALL NOT bypass policy authorization for authoritative mutation.
- Exported captures or derived media SHOULD preserve parent/ingredient provenance and C2PA-compatible credentials where supported.
- Untrusted visual/document content SHALL never directly determine Entity authority.
