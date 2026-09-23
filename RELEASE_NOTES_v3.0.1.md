# ENTITY v3.0.1 Release Notes

Released: 2026-09-23
Qualification: BTG internally qualified maintenance release

ENTITY v3.0.1 is a security-hardening maintenance release for the v3.0.x protocol/reference line. It preserves v3.0.0 EEP/EOPP/MSRP market semantics while strengthening signing-key lifecycle verification and publishing the completed BTG-controlled post-release qualification evidence.

## Security hardening

- Enforce signing-key `created_at_ms` for v2 signature records.
- Enforce retired/revoked key cutoffs while preserving signatures made before the cutoff.
- Remove obsolete local operational private-key material after successful key rotation/recovery.
- Add dedicated regression and randomized adversarial coverage.

## Qualification closeout

- 94/94 patched regression PASS.
- Five controlled native language implementations converge on identical v3 state/recovery/result roots.
- 1,000,000 assets + 3,000,000 events with signed Merkle evidence and destructive restore PASS.
- 4,000 fully settled scale trades PASS.
- 900-second operational soak PASS.
- Internal crypto/privacy and regulatory-engineering tracks closed for the documented scope.

Unrelated third-party interoperability, independent external security review, and deployment-specific regulatory/legal determinations remain external by definition.
