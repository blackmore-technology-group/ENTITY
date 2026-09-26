# Canonical Runtime Binding — event_ledger
Authority: `event_ledger`
Canonical owner: `04_Entity_Registry\event_ledger`

- Events SHALL be append-only, signed and hash-chained.
- Event payloads SHALL be represented by commitments/hashes unless disclosure policy permits content storage elsewhere.
- Ledger verification SHALL detect sequence, hash and signature tampering.
- Checkpoints SHALL bind an event range to a Merkle root and signed head hash.
- Unknown or invalid historical signatures SHALL fail verification.
- Ledger evidence SHALL not imply factual truth beyond the signed assertion/evidence origin.

## READY Gate
- Unit/integration tests prove append, signature verification, tamper detection and checkpoint verification.
- Destructive restore preserves ledger verification.
- READY binding pins current `04_Entity_Registry\ENTITY_REQUIREMENTS.md` SHA-256.
