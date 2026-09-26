# Canonical Runtime Binding — migration_config
Authority: `migration_config`
Canonical owner: `15_Operations\migration`

- Sovereign recovery SHALL include configuration needed to interpret and migrate owner-controlled state.
- State-domain locations SHALL be relative/portable rather than tied to one machine path.
- Configuration SHALL identify required open/common interpreters and cryptographic primitives.
- External dependencies SHALL be explicit so unavailable-provider data can be distinguished from locally recoverable data.
- Migration configuration SHALL be owner-signed and independently verifiable after destructive restore.

## READY Gate
- Qualification destroys the live state, restores it, verifies the migration configuration signature and resolves every declared state domain without a proprietary BTG service.
- READY binding pins current `15_Operations\ENTITY_REQUIREMENTS.md` SHA-256.
