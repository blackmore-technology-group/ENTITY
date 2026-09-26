# Canonical Runtime Binding — asset_registry
Authority: `asset_registry`
Canonical owner: `04_Entity_Registry\asset_registry`

- Asset registration SHALL record controller, content commitment, metadata and classification without treating registration as legal ownership proof.
- Private locators SHALL remain separated from ordinary summaries/projections.
- Registration MAY create a DATA_CONTROLLER claim but SHALL NOT create copyright/ownership certainty.
- Provenance binding SHALL survive deactivation/deletion of the active registry state.
- NIKI projection SHALL expose minimum summary information only.
- Asset history SHALL be auditable through the canonical event ledger.

## READY Gate
- Tests prove registration, private-locator separation, rights/provenance integration and historical preservation.
- Destructive restore re-verifies asset metadata and linked provenance/ledger evidence.
- READY binding pins current `04_Entity_Registry\ENTITY_REQUIREMENTS.md` SHA-256.
