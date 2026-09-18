# Canonical Runtime Binding — identity
Authority: `identity`
Canonical owner: `01_Core_Runtime\identity`
NIKI embedded implementation is fallback only.

## Required Capability
- Stable sovereign Entity root independent of any operational key.
- Purpose-specific key authorities, rotation, revocation, recovery and succession.
- Historical signatures remain independently verifiable across rotation/revocation.
- Organization threshold authority SHALL be machine enforceable.
- Pairwise identity interfaces SHALL not expose the root identifier unnecessarily.

## READY Gate
- Durable identity state persists outside `10_NIKI`.
- Positive/negative tests cover creation, rotation, revoked-key rejection, recovery and authority transition.
- Export/recovery formats are documented and restore-tested.
- Runtime exports match the integration ABI expected by the adapter.
- `ENTITY_RUNTIME_BINDING.json` SHALL NOT be marked READY before qualification evidence exists.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256.
