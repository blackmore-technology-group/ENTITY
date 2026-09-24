## What changed?

<!-- Describe the smallest useful summary of the change. -->

## Why?

<!-- Link the issue/specification requirement or explain the reproducible problem. -->

## Evidence

<!-- Tests, vectors, hashes, reproduction output, benchmarks, screenshots, etc. -->

- [ ] Relevant tests added or updated
- [ ] Full regression run when the change can affect protocol/runtime behavior
- [ ] No credentials, private keys, production state or private user/business data included

## Boundary check

Does this change affect any of the following?

- [ ] Identity / authority
- [ ] Rights / entitlement
- [ ] Evidence / claim-state semantics
- [ ] Provider or resolver authority boundary
- [ ] Market / settlement / economic state
- [ ] Cryptographic or canonicalization behavior
- [ ] Public conformance vectors / sealed kit
- [ ] None of the above

If checked, explain how the existing boundary is preserved or intentionally versioned:

## Compatibility

<!-- Note protocol-semantic vs implementation-only changes and compatibility impact. -->

## Claim discipline

- [ ] The PR description distinguishes implemented/tested behavior from proposed or external claims.
- [ ] If this is independently authored conformance work, BTG did not author the implementation or final qualification evidence.
