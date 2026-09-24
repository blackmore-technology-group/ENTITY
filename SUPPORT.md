# ENTITY Support and Question Routing

ENTITY is an open-source protocol/reference implementation. Different questions belong in different public surfaces so technical discussion remains useful and security-sensitive information stays private.

## I found a reproducible bug

Open a **Reproducible bug** issue using the repository issue form.

Include:

- exact release/tag/commit;
- operating system and relevant runtime/compiler versions;
- minimal reproduction steps;
- expected behavior;
- actual behavior;
- relevant test/vector IDs or hashes.

Do not include private keys, credentials, production state, recovery material or private user/business data.

## I think the specification is ambiguous or wrong

Open a **Specification ambiguity or counterexample** issue.

A concrete counterexample is useful even when you do not know the final fix. Identify the exact schema, profile, rule, transition or vector and explain how two reasonable implementations could disagree.

For v3.3, explicitly note whether the issue concerns:

- cryptographic verification;
- protocol verification;
- reality/evidence verification;
- authority/rights semantics;
- economic/market semantics.

## I have a security concern

Follow [SECURITY.md](SECURITY.md).

Do not publish exploitable credentials, private signer material or sensitive production evidence in a public issue.

## I want to contribute but do not know the whole system

Start with [START_HERE.md](START_HERE.md) and look for issues labeled:

- `good first issue`;
- `help wanted`;
- `documentation`;
- `portability`;
- `evidence`;
- `benchmark`.

Small contributions are intentionally part of the project path. You do not need to implement ENTITY or understand the entire architecture before contributing a reproducible improvement.

## I want to build an independent implementation

Read [docs/INTEROPERABILITY_CHALLENGE.md](docs/INTEROPERABILITY_CHALLENGE.md).

For work to count as independent external evidence, keep the candidate repository and authorship outside BTG control and document the public material used. BTG can clarify the published specification and vector intent without writing the independent implementation or its final qualification report.

## I want to discuss architecture before writing code

Use [GitHub Discussions](https://github.com/blackmore-technology-group/ENTITY/discussions).

For a large idea, start with the smallest architectural question or invariant you want to challenge. A focused discussion is easier to evaluate than a proposed whole-system rewrite.

## I want evidence about a release claim

Start with:

- [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md);
- the release-specific `ENTITY_V*_RELEASE_MANIFEST.json`;
- `docs/qualification/`;
- the immutable release tag;
- protected GitHub checks.

If a published hash/test count cannot be reproduced, treat it as an engineering issue and report the exact contradiction.

## I need deployment, legal or regulatory advice

ENTITY records authority, rights, evidence and protocol state; it does not determine deployment-specific law, legal title, licensing, regulatory approval, privacy compliance or accounting fair value.

Those determinations belong to the applicable organization, jurisdiction and qualified professionals. A deployment may use ENTITY records as evidence without turning ENTITY itself into the legal decision-maker.

## Commercial or organizational contact

For non-code questions about Blackmore Technology Group, use the public company website:

https://www.blackmoretechgroup.com/

For the ENTITY engineering community, prefer GitHub issues/discussions so technical answers remain publicly reusable.
