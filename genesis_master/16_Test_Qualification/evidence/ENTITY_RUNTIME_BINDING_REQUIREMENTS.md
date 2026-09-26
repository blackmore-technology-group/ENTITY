# Canonical Runtime Binding — prebootstrap_evidence
Authority: `prebootstrap_evidence`
Canonical owner: `16_Test_Qualification\evidence`

- Evidence created before sovereign-controller bootstrap SHALL retain its historical evidence origin and assurance level.
- Adoption SHALL NOT retroactively claim that ENTITY directly observed events it did not observe.
- Historical external/pre-bootstrap records SHALL be integrity checked before adoption.
- Repeated adoption SHALL be idempotent/deduplicated.
- Invalid embedded hashes or unverifiable evidence SHALL be rejected or explicitly marked unverified.

## READY Gate
- Tests prove assurance preservation, integrity rejection, idempotency and no retroactive direct-observation upgrade.
- Qualification artifacts identify exactly what was tested and SHALL NOT overstate field, production or TRL evidence.
- READY binding pins current `16_Test_Qualification\ENTITY_REQUIREMENTS.md` SHA-256.
