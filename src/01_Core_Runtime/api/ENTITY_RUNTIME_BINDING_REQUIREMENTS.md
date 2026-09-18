# Canonical Runtime Binding — service_api
Authority: `service_api`
Canonical owner: `01_Core_Runtime\api`

## Required Capability
- Versioned authoritative APIs for identity, sources, vault, assets, claims, policy, licensing, usage, ledger, settlement, exports, disputes, capabilities and administration.
- State-changing APIs SHOULD use idempotency keys and SHALL reject replay/duplicates for high-impact operations.
- Structured errors distinguish authentication, authorization, policy denial, invalid transition, signature failure, conflict, replay and unverified external state.
- Breaking schema changes SHALL NOT reinterpret signed historical records.
- API access SHALL remain least privilege and fail closed.

## READY Gate
- Canonical API runs/persists outside `10_NIKI`; NIKI is a client/adapter, never API authority owner.
- Contract tests demonstrate required endpoints and authorization boundaries.
- Permanent bootstrap endpoint is enabled only when identity, policy_consent, core_permissions and service_api are all READY.
- Network exposure is separately qualified; local service readiness does not imply secure public exposure.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256.
