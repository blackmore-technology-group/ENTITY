# Canonical Runtime Binding — adam_capabilities
Authority: `adam_capabilities`
Canonical owner: `11_ADAM\approval_gates`

- AgentCapability SHALL define agent, permitted operation, asset/counterparty scope, financial/time limit, approval requirements, delegation and revocation.
- A compromised agent SHALL NOT inherit sovereign root authority.
- High-impact actions support policy-driven human/organizational approval.
- NIKI proposals are `PROPOSED_NOT_EXECUTED`; requested actor/capability/purpose metadata SHALL NOT constitute authorization by itself.
- ENTITY authorization remains authoritative before ADAM execution.

## READY Gate
- Tests cover expired/revoked capability, wrong actor/scope, missing approval, delegation escalation and replay.
- Approval evidence is auditable and bound to the authorized operation.
- READY binding pins current `11_ADAM\ENTITY_REQUIREMENTS.md` SHA-256.
