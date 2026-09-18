# Canonical Runtime Binding — credentials
Authority: `credentials`
Canonical owner: `04_Entity_Registry\credentials`

- Credential existence SHALL remain separate from verification/trust status.
- Credentials SHALL be issuer-signed and preserve historical signature verification across supported key rotation/revocation.
- Revocation SHALL be explicit and durable.
- Selective disclosure SHALL not silently disclose undisclosed claims.
- Trust levels SHALL be explicit rather than inferred from identity existence.

## READY Gate
- Qualification covers issue, signature verification, selective disclosure, revocation and recovery with historical key state.
- READY binding pins current `04_Entity_Registry\ENTITY_REQUIREMENTS.md` SHA-256.
