# Canonical Runtime Binding — c2pa
Authority: `c2pa`
Canonical owner: `14_Protocols_SDK\c2pa`

- C2PA verification SHALL keep manifest/provenance integrity, claim-signature validity, signer trust and factual truth as separate states.
- A valid C2PA signature SHALL NOT automatically mean the signer is trusted or the depicted event is factually true.
- C2PA provenance complements rather than replaces the Rights & Claims Graph.
- Local-file provenance verification SHALL require applicable enrolled PROVENANCE/content source authorization.
- Verification results SHALL preserve tool/version and evidence needed for independent reproduction where practical.

## READY Gate
- Tests cover signed valid media, unsigned/no-claim media, tampered media, untrusted signer and hard-binding mismatch.
- API/service tests verify source enrollment is enforced.
- READY binding pins current `14_Protocols_SDK\ENTITY_REQUIREMENTS.md` SHA-256.
