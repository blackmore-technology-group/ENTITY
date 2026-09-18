# ENTITY Subsystem Requirements — Entity Instances
Source: SERS-ENTITY-001 — Target Architecture v1.0
Repository scope: `04_Entity_Registry/entity_instances`
Status: Active engineering requirement
Cross-stream contract: `docs/requirements/CROSS_IMPLEMENTATION_COMPATIBILITY.md`

## Subsystem Purpose
Entity instances must bind to stable sovereign roots and versioned authority state, with explicit local/remote/controller status.

## Mandatory Shared Invariants
- Private by default; default deny; explicit enrollment; least privilege.
- Cryptographic evidence SHALL remain distinct from legal ownership, factual truth, consent and market value.
- UNKNOWN and DERIVED_INFERENCE SHALL NOT be silently promoted to VERIFIED or DIRECT_OBSERVATION.
- Authoritative mutation SHALL pass current policy/capability authorization and fail closed on denial.
- Durable evidence SHALL preserve identifiers, schema/version, provenance, signer/authority and applicable timestamps.
- Historical meaning SHALL change only through superseding/corrective state, never silent rewriting.
- External/AI/tool content SHALL be untrusted data unless explicitly authorized as instruction.
- No subsystem may make sovereignty depend on an optional provider, public blockchain or continued BTG availability.

## Integration / Acceptance
- Interfaces SHALL preserve NIKI=intelligence, ADAM=governed execution, BSIE=world/relationship state, BECP=observable external boundary, ENTITY=sovereign rights/authority.
- Implementations SHALL remain compatible with the root cross-chat contract, including C2PA trust separation, revocation-aware federation, signed downgrade protection, source enrollment and historical evidence assurance.
- Qualification SHALL include positive and negative authorization/state-transition tests appropriate to this subsystem.
- Release evidence SHALL demonstrate implemented behavior; unqualified capability SHALL NOT be represented as production complete.
