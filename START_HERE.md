# Start Here

**Document class:** current-runtime orientation / non-normative guide  
**Current supported runtime:** ENTITY v3.4.3  
**BTDU component:** Blackmore Technology Data Universe (BTDU) 3.4.2, unchanged  
**Frozen clean-room target:** ENTITY Protocol 1.0 / External Conformance Kit v1.0.2

ENTITY is Blackmore Technology Group Limited's open-source infrastructure for persistent identity, scoped authority, provenance, rights, evidence, portable recovery and data-economic state.

The current runtime architecture uses five core primitives:

**ENTITY · AUTHORITY · RIGHT · EVENT · VALUE**

> Infrastructure possession does not become sovereign authority.

Before going deeper, read [Documentation Model](docs/DOCUMENTATION_MODEL.md). It explains which material is Protocol 1.0, current runtime, BTDU/component architecture, integration material or frozen historical evidence.

## Understand the current runtime

**ENTITY v3.4.3** is the current supported runtime release. It is a bounded remediation release based on immutable v3.4.2 and fixes the two reproduced Issue #28 defects.

Current release qualification:

- Issue #28 remediation module: **76/76 PASS**;
- full repository source suite: **279/279 PASS**;
- source-suite exit code: **0**;
- compiled Rust qualification: **PASS — inherited unchanged scope**;
- real-world BTDU training qualification: **PASS — inherited unchanged scope**.

BTDU remains component version **3.4.2 unchanged**. v3.4.2 release evidence remains immutable historical evidence.

Read in this order:

1. [README](README.md)
2. [Documentation Model](docs/DOCUMENTATION_MODEL.md)
3. [ENTITY v3.4.3 release record](RELEASE_V3_4_3.md)
4. [v3.4 family runtime portal](docs/v3.4/README.md)
5. [Global Passport runtime architecture](docs/v3.4/GLOBAL_PASSPORT.md)
6. [Six domain packages](docs/v3.4/DOMAIN_PACKAGES.md)
7. [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md)
8. [Sovereign Authority Doctrine](docs/architecture/ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md)

## Choose the correct layer

### I want to implement Protocol 1.0 independently

Use the separately sealed [ENTITY Protocol 1.0 External Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit).

Protocol 1.0 clean-room conformance does **not** require an implementer to reproduce BTDU, ADAM, NIKI, the BTG reference runtime or later runtime-only architecture unless the sealed Protocol 1.0 material explicitly says so.

### I want to run the current ENTITY reference runtime

```bash
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
git checkout v3.4.3
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

### I want to understand BTDU

BTDU means **Blackmore Technology Data Universe**. In ENTITY v3.4.3 the BTDU component remains **3.4.2 unchanged**. It is runtime/component architecture, not an additional Protocol 1.0 clean-room requirement.

See `BTDU_ARCHITECTURE_CONTRACT.json` and the public BTDU documentation portal material.

### I want to evaluate a domain package

Choose Healthcare, Finance, Manufacturing, AI, Robotics or Defence/Public-Unclassified from [Domain Packages](docs/v3.4/DOMAIN_PACKAGES.md).

These packages configure the one ENTITY sovereignty model. They do not create separate protocols, separate sovereignty systems or replacement versions of external standards.

## Independent implementation and external evidence

Use the [Interoperability Challenge](docs/INTEROPERABILITY_CHALLENGE.md).

Keep these evidence classes separate:

- BTG-controlled qualification;
- external reproduction of a BTG-controlled target;
- unrelated independently authored implementation;
- live bidirectional interoperability;
- independent security/research review.

A lower class does not silently become a stronger class.

## Core claim boundaries

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

Registration, ingestion, mirroring, provenance, custody or verification do not themselves transfer ownership or create automatic economic entitlement.

## Found a problem?

Security-sensitive findings belong in private vulnerability reporting. Specification ambiguity, terminology confusion, stale version references, platform-specific failures and reproducible bugs belong in issues with the exact document/version/commit, expected interpretation and actual interpretation.

External documentation criticism is treated as engineering evidence, not as a reason to relax conformance or rewrite sealed historical artifacts.
