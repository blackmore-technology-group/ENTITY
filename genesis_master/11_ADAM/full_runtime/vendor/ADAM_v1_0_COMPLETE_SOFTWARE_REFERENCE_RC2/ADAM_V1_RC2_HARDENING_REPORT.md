# ADAM v1.0 RC2 Authority-Trust and Qualification-Integrity Hardening

## Scope

RC2 remediates every blocking defect reproduced in the deep audit of the v1.0-rc1 candidate. The original audit evidence is retained under `lineage/v1_rc1_audit/`.

## Remediations

### Restart-safe custody

The runtime resolves a stable 256-bit software-custody master key from `ADAM_V1_MASTER_KEY_HEX` or a private, atomically created state file. Release-signing and qualification-controller identities are also persisted outside release artifacts. Existing active purpose-separated keys are reused rather than silently reprovisioned on every restart.

### Trusted candidate signatures

Candidate envelopes identify a signer but do not embed a key that the verifier automatically trusts. Verification requires an explicit external signer registry and checks the pinned key fingerprint.

### Sealed wall-clock evidence

Qualification policy, start time, accumulated monotonic floor, witness registry, witness chain and invalidations are signed by a stable controller identity. Editing duration, start time, witness threshold or evidence invalidates the state. Restart cannot instantly advance elapsed time because the controller resumes from the signed monotonic floor.

### Independent daily witnesses

Daily witness records are signed by keys in a separate trusted registry. The controller key is prohibited from being registered as an independent witness. Witness signatures, candidate, deployment, day index, timestamps, metrics digest and chain links are verified.

### Trusted independent assessor

Assessor receipts are verified against an external registry that pins assessor ID, organization, key ID, public key and authorized scope. A self-generated key embedded in a receipt is rejected.

### Durable distributed certificates

Each certificate contains separate prepare and commit vote sets. Commit votes are signed only after the node fsyncs its authority record. Verification requires quorum in both phases and binds sequence, previous root, new root, payload hash, membership epoch and membership digest.

### Governed membership

Membership changes require a cryptographic quorum of current-member approvals over a deterministic proposal hash. Nodes reject stale or unknown epochs; certificate verification requires a known membership-history snapshot.

### Release integrity

The packaged verifier selects `SHA256SUMS_V1_RC2.txt`, verifies every listed file, and verifies an Ed25519 signature over the manifest before source imports execute.
