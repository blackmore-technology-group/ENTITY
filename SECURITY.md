# Security Policy

ENTITY handles identity, authority, provenance, rights, cryptographic verification, and portable state. Security reports should be treated as potentially high impact.

## Supported public release

The current public reference implementation is **1.0.0-rc2.2** and ENTITY Protocol 1.0 is **FROZEN_FOR_EXTERNAL_CONFORMANCE**.

## Reporting a vulnerability

Do not publish exploit details, private keys, operational bindings, or affected user data in a public issue.

**Private vulnerability reporting is enabled for this repository.** Use GitHub's private security reporting feature for ENTITY. If that feature is temporarily unavailable, contact Blackmore Technology Group through an official private company channel and reference the `blackmore-technology-group/ENTITY` repository.

A useful report includes:

- affected file/module and commit;
- attack preconditions;
- expected vs observed authorization behavior;
- reproducible steps or a minimal proof of concept;
- whether identity, signing, recovery, rights, portability, or provider-independence semantics are affected.

## Never include in reports or commits

- real private signing/recovery keys;
- live principal bindings;
- live authentication tokens or credentials;
- production SQLite/state databases;
- encrypted backups together with their decryption keys;
- personal/business source data not required to demonstrate the issue.

## Release-signing key lifecycle

ENTITY's public signing-key rotation, revocation, recovery and release-tag procedure is documented in:

[`docs/security/RELEASE_SIGNING_KEY_LIFECYCLE.md`](docs/security/RELEASE_SIGNING_KEY_LIFECYCLE.md)

The document publishes fingerprints/process only. Private keys and recovery codes must never be committed.

## Security invariants

A security fix must not silently weaken these protocol invariants:

- registration does not prove ownership;
- provenance does not prove rights or truth;
- provider possession does not become sovereign authority;
- applications require explicit revocable authorization;
- historical signed semantics are not silently rewritten;
- state migration/recovery preserves the same Entity root rather than manufacturing a replacement identity.

Security-critical semantic changes require an auditable protocol/governance change and, where applicable, a new protocol version.
