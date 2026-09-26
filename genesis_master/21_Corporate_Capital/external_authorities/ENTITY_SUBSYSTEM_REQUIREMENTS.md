# ENTITY External Capital Authority Requirements
Source: SERS-ENTITY-003 Sections 163–170

- Trusted external capital authorities SHALL be explicitly configured with authority type, public key, jurisdiction and permitted evidence types.
- External authority evidence SHALL be cryptographically signed and bound to authority, subject Entity, jurisdiction, evidence type, external record reference, effective time and nonce.
- A valid authority signature for one subject or evidence type SHALL NOT authorize a different subject or evidence type.
- Revoked or untrusted authorities SHALL fail verification.
- A caller-supplied external record reference SHALL NOT become authoritative merely because the string is syntactically valid.
- Verification SHALL preserve the distinction between an external assertion and the underlying legal/factual truth.
