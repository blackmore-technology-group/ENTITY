# ENTITY v3.4.0 Deployment Model

The v3.4 adoption path is designed so a developer configures organization-specific facts instead of redesigning ENTITY identity, authority, rights, provenance, evidence or economic semantics.

1. Clone `blackmore-technology-group/ENTITY` and run the reference implementation tests.
2. Select one or more compatible v3.4 domain packages.
3. Replace every `CONFIGURE-ME` value with real organization-specific facts.
4. Bind the deployment to its jurisdiction and authority source.
5. Connect external systems through mappings/adapters; do not make those systems ENTITY authority by implication.
6. Ingest governed objects/evidence.
7. Derive and verify the Global Passport.
8. Run the package conformance verifier.
9. Keep production state, keys and backups outside the public repository.

Composable profiles allow one asset or identity to carry multiple contexts where the registered profile parents and constraints are satisfied.

## Current target distinction (2026-10-12)

Pin the protected **v3.4.3 tag** for released semantics. The `main` branch contains later formula storage and wallet enhancements that require their own exact commit, backup, tests and recovery qualification. Industry adapters are engineering profiles/mappings, not certification that every external healthcare, financial, manufacturing or safety system is natively integrated. For status and remaining gates, see [current implementation status](../current/IMPLEMENTATION_STATUS_20261012.md).
