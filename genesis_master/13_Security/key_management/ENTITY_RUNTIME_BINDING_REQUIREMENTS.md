# Canonical Runtime Bindings — key/recovery authorities
Authorities: `purpose_keys`, `recovery_custody`, `guardian_recovery`
Canonical owner: `13_Security\key_management`

## Purpose Keys
- Separate authorities SHALL exist for identity assertions, authentication, contracts, devices, encryption, payment, delegation and sessions.
- Operational key rotation/revocation SHALL not change sovereign root identity.

## Recovery
- Recovery supports configured recovery keys, guardians, multisignature/threshold, delay, organization authorities, emergency lock and device-loss recovery.
- Death, incapacity, succession and estate/corporate transitions SHALL be representable.
- Recovery cannot silently invalidate historical signatures.

## Security
- Private keys never enter ledgers, ordinary NIKI prompt context or logs.
- Root/recovery keys SHOULD use hardware-backed protection; high-value use SHOULD support step-up authentication.

## READY Gate
- Qualification proves rotation, lost-key recovery, revoked-key rejection, threshold recovery and historical verification.
- Each READY binding pins current `13_Security\ENTITY_REQUIREMENTS.md` SHA-256.
