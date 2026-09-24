# ENTITY Open-Source Governance

## Purpose

This document defines how the public ENTITY project is stewarded, how protocol-impacting decisions are handled, and how Blackmore Technology Group Limited's project stewardship is separated from protocol sovereignty.

## Stewardship

Blackmore Technology Group Limited (BTG) currently stewards the official ENTITY specifications, reference implementation, release process, project repositories and public engineering evidence.

Stewardship does **not** make BTG the sovereign authority over conforming Entity identities, rights or data merely because BTG publishes software, specifications, resolvers, repositories or infrastructure.

A conforming published protocol version is intended to remain usable without mandatory dependence on BTG-controlled hosting or services.

## Governance principles

ENTITY governance follows these principles:

1. **Published meaning is stable.** A published protocol version is not silently reinterpreted after release.
2. **Evidence is separated from claims.** BTG-controlled testing is not relabeled as unrelated external validation.
3. **Infrastructure is not sovereignty.** Hosting, routing, custody, storage, discovery and software distribution do not automatically create authority.
4. **Historical signed state is preserved.** New rules supersede or migrate old state explicitly rather than rewriting history.
5. **Security-critical semantics require explicit review.** Identity, authority, signatures, recovery, portability, evidence, rights and compatibility changes cannot be treated as ordinary refactors when their meaning changes.
6. **External criticism is useful evidence.** Reproducible failures, ambiguities and counterexamples are valid engineering outcomes.
7. **Protocol conformance should be publicly reproducible.** Public specifications, schemas, vectors and verification material should be sufficient for an unrelated implementer to test the stated target.

## Published protocol versions

A published protocol version is immutable in meaning. Corrections are handled through one or more of:

- implementation fixes that preserve semantics;
- documented errata;
- clarifying non-normative guidance;
- an explicitly versioned protocol change.

A conforming implementation of a published version must not require, as a hidden condition of core conformance:

- BTG hosting;
- BTG DNS;
- a BTG resolver;
- a mandatory BTG cloud service;
- a paid BTG subscription or licence to use the published protocol.

Optional BTG-operated services may exist, but service use must remain distinguishable from core protocol authority and conformance.

## Protocol 1.0 freeze

ENTITY Protocol 1.0 remains **FROZEN_FOR_EXTERNAL_CONFORMANCE** under its separately published freeze and conformance materials.

That historical target is not rewritten to match later ENTITY releases. Later versions may extend the system while preserving Protocol 1.0 evidence as a distinct historical conformance target.

Independent external interoperability qualification for that target remains separate from BTG-controlled testing.

## Decision classes

### Class A — implementation-preserving

Examples:

- bug fixes that preserve published semantics;
- performance improvements;
- diagnostics;
- developer tooling;
- documentation corrections that do not change normative meaning.

These changes can normally proceed through standard pull-request review and release qualification.

### Class B — architecture-sensitive

Examples:

- changes to internal boundaries that affect security or portability assumptions;
- new provider/custody integration surfaces;
- new evidence or rights-processing components;
- changes that introduce a new durable architectural dependency.

These changes should receive explicit architecture review and may require an ADR.

### Class C — protocol/security semantic

Changes affecting any of the following require explicit governance review and may require a new protocol/version boundary:

- identity-root semantics;
- authority, delegation or revocation;
- signature or canonicalization meaning;
- provider independence;
- recovery, migration or portability;
- evidence/attestation state semantics;
- external reality anchors;
- historical signed-state interpretation;
- rights, entitlement, usage or settlement authorization;
- wire compatibility or conformance behavior.

See [ADR Process](docs/architecture/ADR_PROCESS.md).

## Architecture Decision Records

Durable architecture decisions are recorded under `docs/architecture/`.

ADRs should be used when the project needs a stable public record of:

- context;
- decision;
- alternatives;
- security/sovereignty implications;
- compatibility effects;
- consequences;
- supersession history.

An ADR cannot silently override a frozen protocol target. Protocol semantics must change through the applicable version/governance mechanism.

## Release governance

ENTITY releases are **evidence-gated**, not calendar-promised.

Release readiness should be supported by the qualification appropriate to that release, including regression, targeted tests, manifests/hashes, compatibility review, security-sensitive review and protected-branch checks.

The project maintains a separate [Release Policy](docs/governance/RELEASE_POLICY.md) describing patch/minor/major expectations, evidence gates, historical-integrity rules and claim discipline.

## Conformance governance

Conformance is determined by public specifications, schemas, test vectors and reproducible verification—not by privileged access to private BTG infrastructure.

BTG-controlled cross-language implementations are controlled reproducibility evidence. They are not described as unrelated independent implementations.

External conformance evidence should identify:

- implementation repository/commit;
- authoring party and relationship to BTG;
- exact target/version;
- test command;
- public result/evidence;
- known failures or exclusions;
- whether live interoperability/recovery was attempted.

Current status is published in [Interoperability Status](docs/interoperability/STATUS.md).

## Security governance

Potentially exploitable vulnerabilities use the private reporting process in [SECURITY.md](SECURITY.md).

Security-critical changes must preserve or explicitly version changes to the project's core invariants. A security fix is not permitted to silently trade away provider independence, portability, historical integrity or scoped authority merely to close a defect.

The public external-review pathway is described in [Independent Security Review Program](docs/security/INDEPENDENT_SECURITY_REVIEW_PROGRAM.md).

## Contributor governance

Contributors retain credit for their actual work through Git/GitHub history and project recognition surfaces where appropriate.

Contribution does not automatically imply:

- employment;
- maintainer authority;
- endorsement of ENTITY or BTG;
- independent validation of areas not tested;
- legal, regulatory or certification opinion.

See [Contributor Recognition](docs/community/CONTRIBUTOR_RECOGNITION.md).

## Maintainers

BTG currently retains stewardship/merge/release authority for the official ENTITY repositories.

If formal external maintainer roles are established later, the project should document each role's:

- scope;
- review authority;
- merge authority;
- release authority;
- security responsibilities;
- conflict-of-interest expectations;
- removal/succession process.

Contributor activity alone does not silently create maintainer authority.

## Extensions

Vendor-, deployment- or application-specific extensions must be namespaced and must not silently redefine core ENTITY records or claim conformance by changing the meaning of a published core field.

An extension may add optional behavior without converting its vendor-specific dependency into a core protocol requirement.

## Historical integrity

Signed historical records, sealed conformance targets and published release evidence are not silently reinterpreted under newer policy or protocol semantics.

When presentation or documentation later improves, the project prefers:

- new explanatory material;
- explicit errata where permitted;
- a new release/version where the target genuinely changes;

rather than weakening verification or rewriting signed historical evidence for cosmetic reasons.

## Technical publications

Informative technical papers are published under [docs/papers](docs/papers/README.md). They explain architecture and threat boundaries but are not automatically normative.

Normative authority remains with the applicable protocol, schemas, freeze/governance documents, release manifests and controlling requirements.

## Public participation

Engineering participation occurs through:

- GitHub Issues for bounded work, defects and specification questions;
- GitHub Discussions for design/architecture discussion;
- Pull Requests for reviewable code/documentation/evidence;
- private security reporting for exploitable vulnerabilities.

The public developer gateway is [DEVELOPERS.md](DEVELOPERS.md).

## Governance changes

Changes to this governance document should themselves be reviewable through the protected pull-request process.

A governance edit cannot retroactively transform BTG-controlled evidence into independent validation or silently change the meaning of a previously frozen/released protocol target.
