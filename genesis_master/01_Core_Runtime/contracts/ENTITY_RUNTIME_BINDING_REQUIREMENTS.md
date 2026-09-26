# Canonical Runtime Binding — contracts
Authority: `contracts`
Canonical owner: `01_Core_Runtime\contracts`

- Licence lifecycle SHALL be state-machine enforced and signed.
- OFFERED state SHALL NOT be treated as an active licence.
- Grantor/licensee direction SHALL be explicit.
- Activation SHALL re-check current recorded licensing-authority claims.
- Counteroffers SHALL increment terms versions and invalidate stale authority bases.
- Revocation for future use SHALL preserve historical authorized-use evidence.
- Contract history SHALL remain independently signature-verifiable after recovery.

## READY Gate
- Qualification covers draft, offer, counter/accept, activation, scope, authority loss, invalid transitions and future revocation.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256.
