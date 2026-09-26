# Security Policy

ENTITY handles identity, authority, provenance, evidence, rights, cryptographic verification, portable state, economic state, and BTDU-governed information topology. Security reports should be treated as potentially high impact.

## Supported public release

The sole current supported canonical release is **ENTITY v3.4.2 — Canonical BTDU Release**.

Protected release commit: `6dfa3d6cc738d9369cf092d2782676bf4f2a46e4`

Release tree: `f90bf74e29899f82d0a4ee321604346241bba4de`

Release-origin attestation SHA-256: `0ba4b0cc8c34688d98ef3c3425fbd70ff5b59d26183a18a15506bbad3adea0c1`

ENTITY v3.4.1 and earlier releases remain immutable historical provenance and are **superseded / unsupported for current deployment and conformance purposes**. Historical tags are not rewritten when a security issue is found; release-critical fixes produce a new candidate/release and affected qualification gates are rerun.

The current release and claim boundaries are published in the [v3.4.2 release](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.2), [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md), and the [ENTITY documentation portal](https://blackmore-technology-group.github.io/ENTITY-DOCS/). Independent external security review remains a separate post-release qualification gate and is not claimed complete by v3.4.2.

## Security-sensitive surfaces

Security review should consider, at minimum:

- sovereign identity and authority roots;
- signing-key lifecycle, revocation, rotation and recovery;
- delegated/scoped authorization;
- provenance, evidence and typed claim states;
- Global Passport and Rights Passport verification;
- protected-state backup, destructive recovery and sovereign export;
- DCO rights, settlement and economic-state transitions;
- canonical protocol-origin verification;
- BTDU mutation authorization, source/controller/rights-holder separation and repository manifests;
- ADAM deterministic atom/bond state integration;
- provider-independence and anti-capture boundaries;
- dependency integrity and release provenance.

A signer-controlled timestamp is evidence from the signer, not an objective trusted timestamp. Authoritative temporal claims require the applicable independent anchoring/evidence semantics.

## Reporting a vulnerability

Do not publish exploit details, private keys, operational bindings, protected state, credentials, or affected user data in a public issue.

**Private vulnerability reporting is enabled for this repository.** Prefer GitHub's private security reporting feature for sensitive ENTITY findings. If that feature is temporarily unavailable, contact Blackmore Technology Group through an official private company channel and reference the `blackmore-technology-group/ENTITY` repository.

A useful report includes:

- affected release/file/module and exact commit;
- attack preconditions;
- expected versus observed authorization or verification behavior;
- reproducible steps or a minimal proof of concept;
- whether identity, signing, evidence, attestation, recovery, rights, settlement, portability, BTDU state, canonical origin, or provider-independence semantics are affected;
- known impact and constraints;
- whether public disclosure before remediation would create additional risk.

## Never include in reports or commits

- real private signing/recovery keys;
- live principal bindings;
- live authentication tokens or credentials;
- production SQLite/state databases;
- encrypted backups together with their decryption keys;
- personal/business source data not required to demonstrate the issue;
- unrelated third-party secrets or data.

## Independent security review

The public pathway for external focused reviews, release reviews and broader protocol/implementation assessments is documented in:

[`docs/security/INDEPENDENT_SECURITY_REVIEW_PROGRAM.md`](docs/security/INDEPENDENT_SECURITY_REVIEW_PROGRAM.md)

That program defines review scope and evidence expectations. It does not claim that an independent external audit has already been completed.

## Release-signing key lifecycle

ENTITY's public signing-key rotation, revocation, recovery and release-tag procedure is documented in:

[`docs/security/RELEASE_SIGNING_KEY_LIFECYCLE.md`](docs/security/RELEASE_SIGNING_KEY_LIFECYCLE.md)

The document publishes fingerprints/process only. Private keys and recovery codes must never be committed.

## Security invariants

A security fix must not silently weaken these protocol invariants:

- registration does not prove ownership;
- provenance does not prove rights or external truth;
- a valid signature does not make an external-world assertion objectively true;
- provider possession does not become sovereign authority;
- applications and agents require explicit scoped revocable authorization;
- external evidence sources do not silently acquire general ENTITY authority;
- historical signed semantics are not silently rewritten;
- state migration/recovery preserves the same Entity root rather than manufacturing a replacement identity;
- protocol origin does not transfer downstream user asset ownership;
- canonical protocol origin does not create an automatic BTG royalty;
- rights, usage and economic consequence transitions require the authorization/evidence the applicable protocol rules specify;
- BTDU topology or ingest does not itself create authority, ownership, or economic entitlement.

Security-critical semantic changes require an auditable protocol/governance change and, where applicable, a new release.

## Disclosure and remediation

A security finding should normally progress through:

`report → reproduce → classify → contain where necessary → remediate → regression test → semantic/governance review → release or errata decision → remediation verification → disclosure`

The project may delay publication of exploit details when immediate disclosure would materially increase risk before a fix or mitigation is available.

## Security evidence boundaries

Repository CI, dependency review, OpenSSF Scorecard, CodeQL/SARIF results, BTG-controlled qualification, controlled clean-room baselines and internal red-team work are valuable engineering evidence. They are **not** described as an independent external security audit.

A completed external review should identify its reviewer, scope, target commit, methodology, exclusions and remediation status so that the resulting claim remains bounded to the work actually performed.
