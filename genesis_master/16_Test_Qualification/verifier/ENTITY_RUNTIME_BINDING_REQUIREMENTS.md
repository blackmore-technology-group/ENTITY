# Canonical Runtime Binding — independent_verifier
Authority: `independent_verifier`
Canonical owner: `16_Test_Qualification\verifier`
Source: SERS-ENTITY-003 §134 and §170

- Core evidence SHALL be verifiable without trusting the production application that created it.
- Verifier SHALL check hashes, signatures, key versions/revocation timing, hash chains and Merkle proofs within implemented scope.
- External payment assurance SHALL distinguish provider-confirmed evidence from weaker evidence.
- Release evidence signatures and artifact inventories SHALL be independently checkable.
- Corporate-capital verification SHALL independently check cap arithmetic, ENTITY signatures, trusted external-authority signatures, valuation evidence classes, disclosure hashes, corporate-action evidence and balanced capital-accounting batches.
- Verification failures SHALL fail closed and identify the failed invariant without exposing secrets.

## READY Gate
- Real canonical identity/signature records verify independently.
- Tampered signatures, hash chains, Merkle proofs and release manifests are rejected.
- READY binding pins current `16_Test_Qualification\ENTITY_REQUIREMENTS.md` SHA-256.
