# Canonical Runtime Binding — service_state_machine
Authority: `service_state_machine`
Canonical owner: `15_Operations\runtime_states`

- Production services SHALL expose NORMAL, DEGRADED, OFFLINE, DEPENDENCY_UNAVAILABLE, MALICIOUS_INPUT, CONFLICTING_STATE, RECOVERY and quarantine behavior.
- Every state SHALL define allowed/denied operations, user-visible status, audit behavior, recovery action and fail-open/fail-closed policy.
- High-impact authority, rights, exclusive-licensing and value-transfer operations SHALL fail closed outside NORMAL.
- Security/conflict/quarantine transitions SHALL require evidence.
- Unknown operations and invalid transitions SHALL fail closed.

## READY Gate
- Qualification SHALL exercise every state and negative high-impact behavior.
- READY binding pins current `15_Operations\ENTITY_REQUIREMENTS.md` SHA-256.
