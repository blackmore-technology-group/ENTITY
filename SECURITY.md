# Security Policy

ENTITY handles identity, authority, provenance, evidence, rights, cryptographic verification and portable state. Security reports should be treated as potentially high impact.

## Supported public release

The current protected public source/reference release is **ENTITY v3.3.0 — Verifiable Reality, Evidence and Economic Causality**.

Protected release commit:

`9c79f987207592cb6791e1a8956f23351cdfb2d3`

The separately published Windows x64 `1.0.0-rc2` binary remains a historical product build and should not be confused with the current v3 protocol/reference-source release line.

ENTITY Protocol 1.0 remains **FROZEN_FOR_EXTERNAL_CONFORMANCE** as its separately sealed historical conformance scope.

Current v3.3 qualification and claim boundaries are published in [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md). Independent external security review remains a separate **PENDING** milestone.

## Security model additions through v3.3

ENTITY v3.0.1 hardened operational signing-key creation, retirement/revocation cutoffs and recovery/rotation behavior while preserving valid historical signatures under the applicable signed-time semantics.

Later releases add further security-sensitive protocol surfaces, including:

- provider-neutral adoption and Rights Passport machinery;
- evidence objects and typed claim states;
- scoped and revocable attestation authority;
- external reality anchors that remain evidence rather than automatic sovereign authority;
- contestability and supersession;
- evidence-linked economic causality.

A signer-controlled timestamp is evidence from the signer, not an objective trusted timestamp. Authoritative temporal claims require the applicable independent anchoring/evidence semantics.

## Reporting a vulnerability

Do not publish exploit details, private keys, operational bindings or affected user data in a public issue.

**Private vulnerability reporting is enabled for this repository.** Use GitHub's private security reporting feature for ENTITY. If that feature is temporarily unavailable, contact Blackmore Technology Group through an official private company channel and reference the `blackmore-technology-group/ENTITY` repository.

A useful report includes:

- affected file/module and exact commit;
- attack preconditions;
- expected vs observed authorization behavior;
- reproducible steps or a minimal proof of concept;
- whether identity, signing, evidence, attestation, recovery, rights, settlement, portability or provider-independence semantics are affected;
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
- rights, usage and economic consequence transitions require the authorization/evidence the applicable protocol rules specify.

Security-critical semantic changes require an auditable protocol/governance change and, where applicable, a new protocol version.

## Disclosure and remediation

A security finding should normally progress through:

`report → reproduce → classify → contain where necessary → remediate → regression test → semantic/governance review → release or errata decision → remediation verification → disclosure`

The project may delay publication of exploit details when immediate disclosure would materially increase risk before a fix or mitigation is available.

## Security evidence boundaries

Repository CI, CodeQL, dependency review, BTG-controlled qualification, clean-room baselines and internal red-team work are valuable engineering evidence. They are **not** described as an independent external security audit.

A completed external review should identify its reviewer, scope, target commit, methodology, exclusions and remediation status so that the resulting claim remains bounded to the work actually performed.
