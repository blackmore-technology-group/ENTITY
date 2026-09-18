# Canonical Runtime Binding — transaction_evidence_bundle_v1
Authority: `transaction_evidence_bundle_v1`
Canonical owner: `15_Operations\transaction_evidence`

- Runtime SHALL implement the published ENTITY Transaction Evidence Bundle v1 specification.
- Exporter and standalone verifier implementation hashes SHALL be pinned in the READY binding.
- READY SHALL require passing `ENTITY_INDEPENDENT_TRANSACTION_CURRENT.json` with no declared limitations in the qualified scope.
- The binding SHALL preserve the evidence boundary: cryptographic verification is not legal adjudication or market certification.
- Recovery key material SHALL remain separate from the public sovereign transaction export.
