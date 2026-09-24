# ENTITY Public Roadmap

This roadmap separates **released engineering** from **open external evidence milestones**.

It is not a promise that every future version will follow a fixed feature schedule. ENTITY versions are released when their scoped engineering and qualification evidence are complete.

## Current protected release

**ENTITY v3.3.0 — Verifiable Reality, Evidence and Economic Causality**

Protected release commit:

`9c79f987207592cb6791e1a8956f23351cdfb2d3`

Release qualification:

- complete regression: **144/144 PASS**;
- targeted v3.3 tests: **16/16 PASS**;
- sealed v3.3 reality vectors: **20/20 PASS** (10 valid / 10 invalid);
- canonical sealed kit SHA-256: `f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46`;
- deterministic result SHA-256: `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`;
- protected GitHub checks and CodeQL: **PASS**.

See [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md) for the evidence hierarchy and claim boundaries.

## What is already engineered

The current public release line includes:

- persistent sovereign identity and delegated authority;
- provenance and signed events;
- rights, entitlements, usage and economic consequence;
- provider-neutral custody and federated resolution;
- Rights Passports and adoption-layer interfaces;
- standards/jurisdiction adapters without silent authority transfer;
- first-class Evidence Objects;
- typed claim/truth states;
- scoped/revocable attestation authority;
- external reality anchors;
- contestability and supersession;
- evidence-backed causal economic attribution.

The existing market lifecycle remains:

`DCO → Instrument → Listing → Disclosure → Order/RFQ/Auction → Price Discovery → Trade → Clearing → Settlement → Entitlement → Usage → Derived Output → Economic Consequence`

## Highest-priority open milestone: independent implementation

BTG-controlled implementations are not independent validation.

The most important next technical credibility milestone is:

> An unrelated engineer or organization independently reproduces ENTITY semantics from public specification/clean-room material without using BTG implementation code.

A complete external qualification path should progress through:

1. public material / sealed-kit verification;
2. independently authored implementation;
3. valid-vector acceptance;
4. invalid/tampered-vector rejection;
5. reproducible CI evidence;
6. bidirectional live interoperability;
7. sovereign export/recovery survival;
8. identical authoritative result after recovery;
9. independently authored qualification evidence.

Partial independent results are useful and should be published as partial results rather than upgraded into a full interoperability claim.

See [Interoperability Challenge](docs/INTEROPERABILITY_CHALLENGE.md).

## External security review

A separate milestone is an independent review of:

- cryptographic use and canonicalization;
- trust and authority transitions;
- recovery/portability boundaries;
- evidence and attestation semantics;
- external-anchor failure modes;
- market/settlement authorization boundaries.

Repository CI, CodeQL and BTG-controlled red-team/qualification work do not replace independent review.

## Real integration evidence

The project should accumulate external integration evidence from environments BTG does not control, including where appropriate:

- issuers;
- data custodians;
- independent resolvers;
- buyers/licensees;
- registries and evidence sources;
- applications consuming Rights Passports;
- repeated usage/derivation/economic-consequence flows.

The protocol should not claim market liquidity merely because its market machinery is implemented.

## Legal and regulatory evidence

ENTITY records authority, rights, assertions and evidence; it does not determine the law.

Deployment-specific legal classification, title, licensing, recognition, privacy obligations, regulatory approval and accounting treatment remain external determinations by the relevant institutions/professionals.

## Contributor roadmap

Near-term contributor work is intentionally smaller than the external qualification milestone. Current useful tasks include:

- Linux/macOS release reproduction;
- portability fixes;
- evidence examples;
- schema and claim-state ambiguity reviews;
- external-anchor threat models;
- verifier benchmarking;
- onboarding/documentation audits;
- causal-attribution counterexamples;
- narrow independent v3.3 vector classifiers.

Open issues carrying `good first issue`, `help wanted`, `specification`, `evidence`, `portability` and `interoperability` labels are the live work queue.

## What is not on the roadmap

ENTITY does not need artificial dependence on BTG infrastructure in order to create project value.

The roadmap does **not** aim to require:

- BTG hosting for core conformance;
- BTG DNS/resolution as sovereign authority;
- a mandatory BTG cloud service;
- paid permission to use a conforming published protocol;
- artificial scarcity of data bytes;
- silent reinterpretation of historical signed records.

The project should become more credible as more of it can be reproduced outside BTG control.
