# Canonical Runtime Binding — release_attestation
Authority: `release_attestation`
Canonical owner: `17_Release\supply_chain`
Source: SERS-ENTITY-002 §§127, 140, 144

- Qualified software releases SHALL produce distinct SBOM, RBOM and PBOM artifacts.
- Unknown rights/provenance SHALL be explicit rather than guessed.
- Authorship percentages SHALL NOT be invented.
- Release manifests SHALL cryptographically bind BOMs, RTM/release-gate state and evidence references.
- Signed release manifests SHALL be independently verifiable.
- Missing evidence SHALL NOT be silently treated as passed.

## READY Gate
- BOM separation, uncertainty handling, manifest signatures and artifact hashes are qualified.
- Independent verifier rejects tampered release manifests.
- READY binding pins current `17_Release\ENTITY_REQUIREMENTS.md` SHA-256.
