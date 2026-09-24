# Start Here

If you are new to ENTITY, do not begin by reading the entire requirements corpus.

Start with the question you want to answer.

## I want to understand ENTITY in 10 minutes

ENTITY is a provider-independent authority and rights protocol built around five primitives:

**ENTITY · AUTHORITY · RIGHT · EVENT · VALUE**

The core design rule is:

> Infrastructure possession does not become sovereign authority.

In v3.3, ENTITY also distinguishes a signed assertion from evidence about external reality:

```text
Reality → Observation → Claim → Evidence → Attestation → Verification
        → Authoritative ENTITY State → Right → Usage → Economic Consequence
```

Read next:

1. [README](README.md)
2. [Sovereign Authority Doctrine](docs/architecture/ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md)
3. `protocol/v3/ENTITY_VERIFIABLE_REALITY.schema.json`
4. [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md)

## I want to run the project

```bash
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

For v3.3 specifically, inspect:

```text
src/37_Verifiable_Reality/
tests/test_v3_verifiable_reality.py
protocol/v3/ENTITY_VERIFIABLE_REALITY.schema.json
protocol/v3/ENTITY_V3_3_REALITY_CLEANROOM_KIT.min.json
```

## I want a small contribution first

You do not need to implement ENTITY from scratch.

Good first contributions include:

- reproduce a documented setup on another OS;
- review one schema for ambiguity;
- test a valid or invalid vector;
- improve an error message;
- add a minimal example;
- benchmark a verification path;
- challenge a truth/authority boundary with a concrete counterexample;
- improve developer documentation.

Open an issue before large changes when scope is uncertain. Questions about the published semantics are welcome.

## I want to attempt independent implementation

Use the [Interoperability Challenge](docs/INTEROPERABILITY_CHALLENGE.md).

For an implementation to count as **independent external evidence**, do not copy, port or inspect BTG-controlled implementation code while building the candidate. The independent repository should document the exact public specification/kit it used.

BTG can clarify public specifications and vector intent, but should not write the independent implementation or its final qualification report.

## I want to evaluate the engineering

Start with [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md), then inspect the release manifests, qualification records, protected release commits, tests and sealed kits directly.

Do not infer external validation from BTG-controlled evidence. ENTITY explicitly distinguishes internal qualification from unrelated third-party validation.

## I found a problem

That is useful.

- Security-sensitive issue: follow [SECURITY.md](SECURITY.md).
- Specification ambiguity: open an issue with the exact section/vector involved.
- Reproducible bug: include environment, command, expected behavior and actual behavior.
- Contributor idea: open a discussion or a narrowly scoped issue before investing in a large implementation.

The project values reproducible criticism. A failing vector or ambiguous rule is more useful than a generic endorsement.
