# ENTITY Archive Requirements
Source: SERS-ENTITY-001 Target Architecture v1.0
Status: Authoritative repository requirement mapping

## Historical Integrity
- Finalized historical events SHALL remain immutable except through corrective or superseding events.
- Superseded schemas, identities, nodes and releases SHALL retain enough information for independent historical verification.
- Retired operational keys SHALL preserve their historical verification and revocation timelines.

## Retention
- Retention SHALL be policy-specific.
- Provenance/evidence MAY require longer retention than underlying content where lawful and appropriate.
- Personal information SHALL not be retained merely because immutable-ledger architecture makes deletion inconvenient.
- Archived content deletion SHALL not silently rewrite surviving lawful cryptographic provenance evidence.

## Migration / Retirement
- Archived migration checkpoints SHALL preserve previous/new schema versions, migration tool version, source/result ledger roots and migration evidence.
- Retirement of BTG infrastructure SHALL not make owner-controlled sovereign records uninterpretable or unrecoverable.
- Archive state SHALL distinguish historical evidence from currently active authority.