# ENTITY Canonical Binding Collision Register
Status: RESOLVED IN NIKI RESOLVER — ROOT MANIFEST ADOPTION IN PROGRESS
Scope: <LOCAL_DRIVE>/Sovereign_Entity_Network

## Resolution
The active `EntityPlatformBindingResolver` supports a multi-authority `ENTITY_RUNTIME_BINDING.json` manifest through an `authorities` object.
Each authority receives its own status, implementation file, exports, qualification evidence and optional implementation version while sharing the owner requirements SHA-256.

## Verified Evidence
- `central_runtime/tests/test_multi_authority_bindings.py` verifies two authorities can resolve from one owner manifest.
- A missing sibling authority remains embedded fallback rather than inheriting READY.
- A stale requirements hash fails closed.
- Focused validation on 2026-09-15: 6/6 binding/bootstrap tests passed.

## Shared Owner Groups
- `01_Core_Runtime\service_runtime`: contracts, data_pools, data_spaces, settlement
- `02_Peer_Network`: federation, transparency_witness
- `04_Entity_Registry`: credentials, data_universe, knowledge_capital
- `08_Data_Vaults`: data_sources, data_vault
- `13_Security\key_management`: guardian_recovery, purpose_keys, recovery_custody

## Remaining Gate
Collision resolution does NOT make any authority READY. Every authority must still satisfy implementation, requirements-hash pinning, qualification evidence and release gates before status `READY` is permitted.
