# Canonical Runtime Binding — core_permissions
Authority: `core_permissions`
Canonical owner: `01_Core_Runtime\permissions`

## Required Capability
- Every authoritative operation evaluates actor, role, capability, asset, action, purpose, policy, jurisdiction/configuration, approval threshold, time and counterparty.
- Authorization failures fail closed.
- Capabilities are scoped, revocable and non-transitive unless explicitly delegated.
- AI permissions remain separate: metadata read, content read, reasoning, disclosure, proposal and execution.
- Connector or application authority SHALL NOT silently propagate to NIKI, ADAM or unrelated subsystems.

## READY Gate
- Canonical authorization decisions are enforced outside `10_NIKI`.
- Tests cover invalid signer, expired/revoked capability, wrong scope, wrong purpose and escalation attempts.
- Replayed or duplicate requests cannot duplicate protected mutations.
- NIKI proposals are non-executing until this authority and required approvals authorize execution.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256.
