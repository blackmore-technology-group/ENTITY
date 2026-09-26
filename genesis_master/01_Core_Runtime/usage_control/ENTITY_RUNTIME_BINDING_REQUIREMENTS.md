# Canonical Runtime Binding — usage_control
Authority: `usage_control`
Canonical owner: `01_Core_Runtime\usage_control`

- Usage evidence SHALL be licence-bound, purpose-bound and scope-checked.
- Self-declared use SHALL NOT be represented as independently verified.
- Gateway-observed access SHALL NOT be represented as proof of all downstream use.
- Counterparty attestation SHALL remain distinct from independent environmental verification.
- Environment attestation SHALL fail closed when no registered verifier accepts the evidence.
- Usage/ticket nonces SHALL reject replay and duplicate receipt creation.
- Durable usage receipts SHALL be signed and evidence-hash bound.

## READY Gate
- Qualification covers all assurance classes, scope failures, replay, revocation and signature/evidence tampering.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256.
