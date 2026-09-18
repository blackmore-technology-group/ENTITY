# ENTITY Canonical Authority Handoff Requirements
Source: SERS-ENTITY-001 Target Architecture v1.0
Coordination basis: active NIKI integration-adapter workstream

## Authority Boundary
- `10_NIKI` is an integration/reasoning adapter, not the canonical authority owner.
- Canonical identity, rights, policy, permissions, vault, contracts, settlement, peer trust, recovery and BSIE world state SHALL live outside `10_NIKI`.
- NIKI MAY consume bounded projections and create proposals; it SHALL NOT become authoritative state.

## Runtime Handoff Contract
- Canonical authorities MAY publish `ENTITY_RUNTIME_BINDING.json` only after implementation and qualification.
- Binding schema SHALL be `entity-runtime-binding-v1`, ABI version `1`.
- Status SHALL be one of DEVELOPMENT, QUALIFIED, READY or RETIRED.
- READY SHALL identify the authority, implementation file, explicit exports, implementation version and qualification evidence.
- READY SHALL include `requirements_sha256`, equal to the SHA-256 of the current top-level owner `ENTITY_REQUIREMENTS.md`.
- A requirements change invalidates a stale READY binding until requalification.
- No documentation-only action SHALL create a READY binding.

## Bootstrap Gate
- Permanent sovereign bootstrap SHALL remain blocked until canonical `identity`, `policy_consent`, `core_permissions` and `service_api` authorities are READY.
- Embedded NIKI fallback persistence is development/qualification state only.
- Canonical durable persistence SHALL reside under the owning root subsystem.
