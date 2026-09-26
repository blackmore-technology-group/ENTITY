# ADAM v1.0 RC2 Final Software Status

## Classification

**ADAM v1.0.0-rc2 — Complete Bounded Artificial Living Data-Universe Software Reference / External Production Certification Required**

The internal software implementation is complete for the bounded architecture and the rc2 hardening findings are remediated. This package is not represented as hardware-certified, multi-host certified, thirty-day certified, or independently security-certified.

## RC2 blockers closed

1. Persistent custody and release identities reopen safely after restart.
2. Wall-clock state is signed and policy-bound; edited state is rejected.
3. Daily qualification witnesses must use separately trusted external keys.
4. Assessor receipts must match a pinned registry entry and key.
5. Network certificates contain both prepare and durable commit quorums.
6. Membership epoch and membership digest are verified by nodes and certificates.
7. Candidate envelopes no longer trust a public key embedded by the candidate itself.
8. The v1 manifest verifier verifies the current manifest and its Ed25519 signature before imports.

## Remaining external certification gates

- Non-exportable HSM/KMS/PKCS#11 key custody and ceremonies
- Physically independent multi-host deployment and WAN fault qualification
- Certified physical device and functional-safety pilot
- Large licensed real-world multimodal and field-sensor training
- Thirty actual wall-clock days under frozen production workload
- Independent security, safety and operational assessment
