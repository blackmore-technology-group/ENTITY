# ENTITY Release Policy

This document defines the public release discipline for ENTITY.

ENTITY does not use a calendar promise as evidence of readiness. Releases are **evidence-gated**: a version is published when its scoped engineering, compatibility review and qualification evidence are complete enough to support the claims made for that version.

## Release classes

ENTITY uses semantic versioning as a public coordination convention:

- **PATCH** — implementation fixes, documentation corrections, tooling improvements or other changes intended to preserve published semantics and compatibility.
- **MINOR** — additive protocol/reference capabilities that preserve the stated compatibility boundary of the release line.
- **MAJOR** — changes that intentionally alter compatibility, controlling semantics or public protocol assumptions in a way that cannot be treated as an additive extension.

A version number does not override the actual protocol documents, manifests, release notes or qualification evidence. Where a frozen protocol target exists, its freeze/governance material controls that target.

## Evidence gate

A release candidate is not promoted solely because code compiles or unit tests pass. The release owner should establish, as applicable:

1. scoped requirements are identified;
2. regression tests pass;
3. targeted tests for the release feature set pass;
4. schemas/vectors/manifests are internally consistent;
5. reproducibility or sealed-kit hashes are recorded where applicable;
6. security-sensitive changes receive explicit review;
7. provider-independence and sovereignty invariants remain intact;
8. release notes describe both added capability and claim boundaries;
9. protected-branch checks pass;
10. the final release commit/tag is identified and preserved.

Some releases may require additional gates, including interoperability, migration, recovery, compatibility or performance qualification.

## Release evidence record

Each protected release should publish enough information for an external engineer to identify what was actually qualified. Depending on release scope, this may include:

- protected release commit;
- release manifest;
- exact test counts;
- vector counts;
- deterministic result hashes;
- sealed-kit hashes;
- schema hashes;
- overlay/snapshot hashes;
- CI status;
- known limitations;
- explicit external milestones that remain pending.

The public release note must distinguish BTG-controlled engineering evidence from independent third-party evidence.

## Claim discipline

The release process must not silently convert any of the following into stronger claims:

- a passing BTG-controlled test into independent validation;
- cryptographic validity into proof that an external-world claim is true;
- protocol validity into legal recognition;
- implemented market machinery into demonstrated market liquidity;
- a controlled clean-room exercise into unrelated external interoperability;
- an internal red-team result into an independent security review.

When an external milestone is pending, the release record should say so.

## Security-sensitive release changes

Changes affecting any of the following require explicit security/governance consideration before release:

- signing or canonicalization;
- root identity or authority;
- delegation/revocation;
- recovery or migration;
- provider independence;
- evidence/attestation semantics;
- external anchors;
- rights, entitlement, usage or settlement authorization;
- backward interpretation of signed historical state.

A security fix that changes published semantics may require a new protocol/version boundary rather than an implementation-only patch.

## Historical integrity

Released evidence is not rewritten merely to make later presentation cleaner.

If a signed/sealed historical kit contains a document that later appears dated or cosmetically imperfect, the preferred options are:

- publish an external clarification;
- publish an erratum where governance permits;
- issue a new release/version when semantics or target material genuinely change.

Do not weaken a verifier, rewrite a signed manifest or silently reseal historical evidence solely for presentation.

## Release cadence

ENTITY has **no fixed public release calendar**. The practical cadence is:

- development may proceed continuously on protected branches and reviewed pull requests;
- patch releases may occur when a bounded fix is qualified;
- minor/major releases occur after scoped engineering and qualification evidence are complete;
- security releases may be accelerated while still preserving evidence and governance requirements.

This policy is intended to keep public version numbers tied to engineering evidence rather than marketing deadlines.

## Current release

As of 2026-09-24, the current protected release is **ENTITY v3.3.0 — Verifiable Reality, Evidence and Economic Causality**.

Protected release commit:

`9c79f987207592cb6791e1a8956f23351cdfb2d3`

See [ROADMAP.md](../../ROADMAP.md), [docs/ENGINEERING_EVIDENCE.md](../ENGINEERING_EVIDENCE.md) and the [GitHub Releases](https://github.com/blackmore-technology-group/ENTITY/releases) page for current evidence and open external milestones.
