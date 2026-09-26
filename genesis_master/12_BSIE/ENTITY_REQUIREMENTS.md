# ENTITY / BSIE Integration Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Responsibility Boundary
- BSIE SHALL remain the authoritative entity/world relationship and state substrate.
- ENTITY SHALL remain authoritative for identity authority, data rights, provenance, consent, policy, contracts, usage and economic state.
- BSIE state SHALL NOT silently imply legal ownership, commercialization rights or verified truth.

## Graph Integration
- BSIE relationship/world objects referenced by ENTITY SHALL use stable identifiers and explicit provenance/evidence references.
- Derived world-state relationships SHALL preserve parent/ingredient lineage where applicable.
- Unknown provenance SHALL remain UNKNOWN rather than fabricated.
- Pairwise/context-specific Entity identifiers SHOULD be used where global correlation is unnecessary.

## Projection
- BSIE projections exposed to other subsystems SHALL be purpose-scoped and least privilege.
- Sensitive physical-world or relationship state SHALL respect ENTITY classification and disclosure policy.
- Migration SHALL preserve valid existing signed/evidentiary records and historical meaning.
