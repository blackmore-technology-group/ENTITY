# ENTITY Subsystem Requirements — Relationships
Source: SERS-ENTITY-001 — Target Architecture v1.0
Repository scope: `04_Entity_Registry/relationships`
Status: Active engineering requirement
Cross-stream contract: `docs/requirements/CROSS_IMPLEMENTATION_COMPATIBILITY.md`

## Subsystem Purpose
Represent relationships independently from root identity disclosure and support pairwise identifiers, evidence origin, validity periods and revocation.

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

## SERS-ENTITY-003 v2.2 — Section 172 Sovereign Authority Doctrine
- ENTITY SHALL represent possession, custody, storage control, processing authority, sovereign authority, authorship, legal rights, consent authority, licensing authority, authorized usage, economic participation, governance authority and payment authority as distinct relationships.
- Evidence supporting one relationship SHALL NOT silently establish another relationship.
- Storage/custody/processing providers SHALL NOT acquire sovereign, licensing, consent or economic authority merely from infrastructure access.
- Provider authority SHALL be explicit, scoped, evidence-backed, time-bound where applicable and revocable.
- Provider replacement SHALL preserve the sovereign Entity root and SHALL NOT silently change authoritative rights/economic semantics.
- Economic participation SHALL require an explicit evidence-backed basis rather than infrastructure possession or usage observation alone.
- Sovereign export manifests SHALL cryptographically commit to the relationship/storage/economic-participation state needed for migration and independent verification.
