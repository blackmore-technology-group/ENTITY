# Canonical Runtime Binding — protocol_conformance
Authority: `protocol_conformance`
Canonical owner: `14_Protocols_SDK\reference_clients`

- Reference clients SHALL independently verify identifiers, signatures, schema versions, event chains/checkpoints and declared authority boundaries.
- Protocol/schema negotiation SHALL fail closed on incompatible or security-downgrade conditions unless explicit policy permits otherwise.
- Signed downgrade history SHALL be retained so a peer cannot silently advertise an older protocol after a higher version was established.
- Conformance tests SHALL distinguish transport success from authenticated/trusted/authorized state.
- BTG extensions SHALL remain documented/versioned.

## READY Gate
- Known-answer/interoperability tests cover supported cryptographic and schema suites.
- Independent client verification reproduces authoritative validation without NIKI-specific state.
- READY binding pins current `14_Protocols_SDK\ENTITY_REQUIREMENTS.md` SHA-256.
