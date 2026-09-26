# Canonical Runtime Bindings — service_runtime
Authorities: `contracts`, `settlement`, `data_pools`, `data_spaces`
Canonical owner: `01_Core_Runtime\service_runtime`

## Contract / Licensing
- Bilateral or multi-party licences use validated state transitions and explicit grantor/licensee direction.
- Offers do not become active without valid acceptance.

## Settlement
- Finalized value uses balanced double-entry accounting, explicit payer/payee direction, replay protection and real external payment evidence where applicable.
- Internal database state alone SHALL NOT prove external money movement.

## Data Pools / Data Spaces
- Pools preserve contributor rights, version governance and deterministic auditable revenue allocation.
- Controlled access/compute-to-data SHALL meter use without requiring unrestricted raw-file transfer.

## READY Gate
- Each authority may qualify independently and SHALL publish its own binding only after its tests pass.
- READY bindings pin current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256.
- NIKI may reason/propose against these states but cannot create authoritative contract, settlement, pool or access state.
