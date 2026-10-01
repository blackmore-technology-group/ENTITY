# ENTITY Developer Portal

**Document class:** current-runtime developer orientation / non-normative  
**Current supported runtime:** ENTITY v3.4.3  
**BTDU component:** Blackmore Technology Data Universe (BTDU) 3.4.2, unchanged  
**Protocol 1.0:** separate frozen external clean-room target

This page is the public engineering gateway for ENTITY, an open-source project stewarded by **Blackmore Technology Group Limited (BTG)**.

Before treating a document as a protocol requirement, read [Documentation Model](docs/DOCUMENTATION_MODEL.md). ENTITY publishes several distinct layers: frozen Protocol 1.0 material, the current v3.4.3 runtime, BTDU/runtime architecture, integration/domain packages and immutable historical evidence.

ENTITY is designed so protocol conformance, verification and interoperability can be reproduced outside BTG-controlled infrastructure. BTG stewardship of the public project does not convert BTG hosting, storage, routing or software distribution into sovereign authority over conforming Entity identities or data.

## Start by objective

| Goal | Start here |
| --- | --- |
| Understand the documentation layers | [Documentation Model](docs/DOCUMENTATION_MODEL.md) |
| Understand ENTITY in 10 minutes | [START_HERE.md](START_HERE.md) |
| Run the current v3.4.3 reference runtime | [README.md](README.md#quick-start) |
| Read the v3.4.3 release boundary | [RELEASE_V3_4_3.md](RELEASE_V3_4_3.md) |
| Implement frozen Protocol 1.0 independently | [Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit) |
| Inspect public engineering evidence | [docs/ENGINEERING_EVIDENCE.md](docs/ENGINEERING_EVIDENCE.md) |
| Understand architecture decisions | [docs/architecture/README.md](docs/architecture/README.md) |
| Review project governance | [GOVERNANCE.md](GOVERNANCE.md) |
| Understand release discipline | [docs/governance/RELEASE_POLICY.md](docs/governance/RELEASE_POLICY.md) |
| Contribute code or documentation | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Find bounded starter work | [Open contributor tasks](https://github.com/blackmore-technology-group/ENTITY/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) |
| Attempt independent interoperability | [docs/INTEROPERABILITY_CHALLENGE.md](docs/INTEROPERABILITY_CHALLENGE.md) |
| Check interoperability status | [docs/interoperability/STATUS.md](docs/interoperability/STATUS.md) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |
| Read technical notes | [docs/papers/README.md](docs/papers/README.md) |
| See how contributors are recognized | [docs/community/CONTRIBUTOR_RECOGNITION.md](docs/community/CONTRIBUTOR_RECOGNITION.md) |

## Current supported runtime

**ENTITY v3.4.3** is the current supported runtime. It is a bounded remediation release based on immutable v3.4.2.

Current qualification published for v3.4.3:

- Issue #28 remediation module: **76/76 PASS**;
- full repository source suite: **279/279 PASS**;
- source-suite exit code: **0**;
- compiled Rust clean-room/conformance qualification: **PASS — inherited unchanged scope**;
- real-world BTDU training qualification: **PASS — inherited unchanged scope**.

Release merge commit: `528b70aabd05b1e930b77e4933f157731e47274f`  
Immutable v3.4.2 predecessor: `6dfa3d6cc738d9369cf092d2782676bf4f2a46e4`

BTDU remains component version **3.4.2 unchanged**. The active 30-day wall-clock campaign and immutable v3.4.2 evidence were not rewritten by v3.4.3.

## Do not mix these three targets

### ENTITY Protocol 1.0

Protocol 1.0 is the frozen external clean-room target. An unrelated implementer should use the sealed conformance-kit repository and the exact pinned material permitted by that campaign.

BTDU, ADAM, NIKI and later runtime architecture are **not automatically Protocol 1.0 requirements**.

### ENTITY runtime v3.4.3

The runtime is BTG's current supported implementation/release. It includes behavior and architecture developed after the Protocol 1.0 freeze. Runtime documentation may therefore describe concepts outside the frozen Protocol 1.0 surface.

### BTDU 3.4.2

BTDU means **Blackmore Technology Data Universe**. It is the governed information-substrate component carried unchanged into ENTITY v3.4.3. The public architecture contract identifies ENTITY for authority/rights, ADAM as deterministic state engine, NIKI as reasoning consumer and BTDU as the governed universal information substrate.

BTDU documentation does not expand the Protocol 1.0 clean-room obligation unless a normative Protocol 1.0 source explicitly does so.

## Engineering tracks

### 1. Reproduction and portability

Best for engineers who want to evaluate a published target without independently implementing the protocol.

Typical work:

- reproduce an exact historical/current campaign identified by version and hash;
- validate sealed vectors;
- identify machine-specific assumptions;
- benchmark verification;
- improve onboarding and diagnostics.

A reproduction must name the exact target. Reproducing a frozen v3.4.2 baseline is not a statement that v3.4.2 is the current runtime.

### 2. Specification and architecture review

Best for protocol, security, identity, distributed-systems and data-rights engineers.

Typical work:

- identify ambiguous semantics or undefined vocabulary;
- challenge authority transitions;
- review canonicalization and signature boundaries;
- produce counterexamples;
- review evidence, attestation, recovery and portability semantics;
- identify places where runtime examples could be mistaken for Protocol 1.0 requirements.

### 3. Independent implementation

Best for unrelated developers or organizations who want to test whether ENTITY Protocol 1.0 semantics are reproducible from permitted public material alone.

Independent implementations own their own architecture, libraries, source code, tests, repository and qualification evidence.

BTG-controlled Rust, TypeScript, C#, Go, Swift and Java repositories are reproducibility baselines, **not independent implementations**.

### 4. Live interoperability

This track begins after an independently authored implementation can classify the required public vectors correctly.

The progression is:

`sealed material → independent implementation → vector conformance → reproducible CI → bidirectional live interoperability → sovereign export/recovery survival → independently authored evidence`

Partial results remain partial. A failed vector, ambiguity or non-interoperable result is useful evidence and must not be upgraded into a success claim.

### 5. Security research

Useful targets include cryptographic misuse, canonicalization ambiguity, authority escalation, provider capture, recovery/portability failure, evidence confusion and unauthorized rights/economic-state transitions.

Use private vulnerability reporting for exploitable findings. Public architectural criticism and non-sensitive counterexamples are welcome.

## Public engineering principles

1. **Define first, bound second.** Explain what a protocol object/state is before listing what it does not imply.
2. **Evidence before claims.** Test counts and hashes remain tied to their exact target.
3. **No silent authority transfer.** Hosting, custody, routing, storage and discovery do not become sovereign authority merely because a provider performs them.
4. **No silent ownership transfer.** Registration, ingestion, provenance and custody do not create ownership.
5. **No automatic economic entitlement.** Economic participation requires explicit terms and qualified evidence.
6. **No silent semantic rewrite.** Historical signed state and sealed campaigns remain interpretable under their original target.
7. **Independent evidence stays independent.** BTG-controlled work is not relabelled third-party validation.
8. **External criticism is engineering evidence.** Reproducible failures and documentation ambiguities improve the system.

## Canonical origin versus asset provenance

The canonical ENTITY origin is:

`Shawn Blackmore → Blackmore Technology Group → ENTITY`

That identifies ENTITY's own protocol/project origin. It is not automatically the provenance root or ownership chain of unrelated upstream assets.

```text
UPSTREAM OWNERSHIP
        ≠
BTG FORK CUSTODY
        ≠
BTG-CREATED ENTITY METADATA OWNERSHIP
        ≠
ENTITY PROTOCOL ORIGIN
        ≠
AUTOMATIC ECONOMIC RIGHTS
```

## Contribution lifecycle

`issue/discussion → bounded proposal → implementation or evidence → pull request → automated checks → review → merge → release qualification where applicable`

Changes affecting identity, authority, signature meaning, provider independence, recovery, portability, evidence semantics, rights, economic state or wire compatibility require architecture/governance review in addition to ordinary code review.

## Corporate stewardship and project independence

BTG currently stewards the official specifications, reference implementation, release process and public repositories.

That stewardship is separated from protocol sovereignty. A conforming published protocol target is not intended to require BTG hosting, BTG DNS, a BTG resolver, a mandatory BTG cloud service or paid permission to implement the published protocol.

The strongest evidence for that boundary remains independently authored external implementation and interoperability.

## Where to participate

- [Issues](https://github.com/blackmore-technology-group/ENTITY/issues) — defects, portability findings, terminology/specification questions and bounded work.
- [Discussions](https://github.com/blackmore-technology-group/ENTITY/discussions) — design and implementation discussion.
- [Pull requests](https://github.com/blackmore-technology-group/ENTITY/pulls) — code, documentation and reproducible evidence.
- [Releases](https://github.com/blackmore-technology-group/ENTITY/releases) — protected public release artifacts and release notes.

If you are evaluating ENTITY for the first time, start with [START_HERE.md](START_HERE.md), then choose one bounded target and state its exact layer/version before testing it.
