# ENTITY Developer Portal

This page is the public engineering gateway for ENTITY, an open-source project stewarded by **Blackmore Technology Group Limited (BTG)**.

ENTITY is designed so that protocol conformance, verification and interoperability can be reproduced outside BTG-controlled infrastructure. BTG stewardship of the public project does not convert BTG hosting, storage, routing or software distribution into sovereign authority over conforming Entity identities or data.

## Start by objective

| Goal | Start here |
| --- | --- |
| Understand ENTITY in 10 minutes | [START_HERE.md](START_HERE.md) |
| Run the reference implementation | [README.md](README.md#quick-start) |
| Inspect public engineering evidence | [docs/ENGINEERING_EVIDENCE.md](docs/ENGINEERING_EVIDENCE.md) |
| Understand architecture decisions | [docs/architecture/README.md](docs/architecture/README.md) |
| Review project governance | [GOVERNANCE.md](GOVERNANCE.md) |
| Understand release discipline | [docs/governance/RELEASE_POLICY.md](docs/governance/RELEASE_POLICY.md) |
| Contribute code or documentation | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Find bounded starter work | [Open contributor tasks](https://github.com/blackmore-technology-group/ENTITY/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) |
| Attempt independent interoperability | [docs/INTEROPERABILITY_CHALLENGE.md](docs/INTEROPERABILITY_CHALLENGE.md) |
| Check interoperability status | [docs/interoperability/STATUS.md](docs/interoperability/STATUS.md) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |
| Review the external security-review program | [docs/security/INDEPENDENT_SECURITY_REVIEW_PROGRAM.md](docs/security/INDEPENDENT_SECURITY_REVIEW_PROGRAM.md) |
| Read technical notes | [docs/papers/README.md](docs/papers/README.md) |
| See how contributors are recognized | [docs/community/CONTRIBUTOR_RECOGNITION.md](docs/community/CONTRIBUTOR_RECOGNITION.md) |
| Discuss engineering questions | [GitHub Discussions](https://github.com/blackmore-technology-group/ENTITY/discussions) |

## Current protected release

**ENTITY v3.4.1 — Protocol Origin Lineage & Sovereign User Bootstrap**

Protected release commit: `9822b1b65f8269ebc17208a342809720729ae2f8`

Public qualification evidence includes 185/185 regression tests, 8/8 protocol-origin/migration/economic-lineage tests, 33/33 targeted v3.4 tests, 24/24 sealed vectors, six BTG-controlled native implementations converging on `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`, six published executable domain packages, and a completed post-release recursive closure.

Start with the [v3.4.1 portal](docs/v3.4/README.md) and [Domain Packages](docs/v3.4/DOMAIN_PACKAGES.md). These results are BTG-controlled engineering evidence, not unrelated third-party validation.

## Engineering tracks

### 1. Reproduction and portability

Best for engineers who want to evaluate the project without implementing the protocol.

Typical work:

- reproduce the release on Linux or macOS;
- validate sealed vectors;
- identify machine-specific assumptions;
- benchmark verification;
- improve onboarding and diagnostics.

### 2. Specification and architecture review

Best for protocol, security, identity, distributed-systems and data-rights engineers.

Typical work:

- identify ambiguous semantics;
- challenge authority transitions;
- review canonicalization and signature boundaries;
- produce counterexamples;
- review evidence, attestation, recovery and portability semantics.

### 3. Independent implementation

Best for unrelated developers or organizations who want to test whether ENTITY semantics are reproducible from public material alone.

Independent implementations own their own:

- architecture;
- libraries;
- code structure;
- testing strategy;
- repository;
- qualification evidence.

BTG-controlled Rust, TypeScript, C#, Go, Swift and Java implementations are reproducibility baselines, **not independent implementations**.

### 4. Live interoperability

This track begins after an independently authored implementation can classify the public vectors correctly.

The target progression is:

`sealed material → independent implementation → vector conformance → reproducible CI → bidirectional live interoperability → sovereign export/recovery survival → independently authored evidence`

Partial results are published as partial results. A failed vector, ambiguity or non-interoperable result is useful evidence and must not be upgraded into a success claim.

### 5. Security research

Security research should focus on concrete boundaries such as:

- cryptographic misuse;
- signature/canonicalization ambiguity;
- authority escalation;
- provider capture;
- recovery or portability failure;
- evidence/attestation confusion;
- external-anchor substitution;
- rights/usage/settlement authorization flaws.

Use private vulnerability reporting for exploitable findings. Public architectural criticism and non-sensitive counterexamples are welcome in issues or Discussions.

## Public engineering principles

ENTITY development follows several rules that contributors should be able to audit:

1. **Evidence before claims.** Qualification artifacts and exact hashes are published separately from marketing language.
2. **No silent authority transfer.** Hosting, storage, routing, discovery and custody do not become sovereign authority merely because an infrastructure provider performs them.
3. **No silent semantic rewrite.** Historical signed state is superseded or migrated explicitly rather than reinterpreted under new rules.
4. **Independent evidence stays independent.** BTG-controlled testing is never relabeled as third-party validation.
5. **Protocol versions are reviewable public targets.** Conformance should be possible from public specifications, schemas, vectors and reproducible tooling.
6. **External-world claims remain contestable.** Cryptographic validity, protocol validity and evidence supporting a claim are separate questions.
7. **Useful failures are publishable results.** Reproducible failures, counterexamples and ambiguities improve the protocol.

## Contribution lifecycle

A typical contribution moves through:

`issue/discussion → bounded proposal → implementation or evidence → pull request → automated checks → review → merge → release qualification where applicable`

Changes that affect identity, authority, signature meaning, provider independence, recovery, portability, evidence semantics or wire compatibility receive architecture/governance review in addition to ordinary code review.

See [GOVERNANCE.md](GOVERNANCE.md) and [docs/governance/RELEASE_POLICY.md](docs/governance/RELEASE_POLICY.md).

## Corporate stewardship and project independence

Blackmore Technology Group Limited currently stewards ENTITY's specifications, reference implementation, release process and official public repositories.

That stewardship is intentionally separated from protocol sovereignty. A conforming published ENTITY version is not intended to require BTG hosting, BTG DNS, a BTG resolver, a mandatory BTG cloud service or paid permission to use the protocol.

The strongest long-term evidence for that boundary is external reproduction and interoperability by parties BTG does not control.

## Where to participate

- [Issues](https://github.com/blackmore-technology-group/ENTITY/issues) — bounded engineering work, defects, portability findings and specification questions.
- [Discussions](https://github.com/blackmore-technology-group/ENTITY/discussions) — architecture, design review, implementation questions and broader engineering discussion.
- [Pull requests](https://github.com/blackmore-technology-group/ENTITY/pulls) — code, documentation and reproducible evidence.
- [Releases](https://github.com/blackmore-technology-group/ENTITY/releases) — protected public release artifacts and release notes.

If you are evaluating ENTITY for the first time, start with [START_HERE.md](START_HERE.md), then choose one bounded task before attempting a complete implementation.
