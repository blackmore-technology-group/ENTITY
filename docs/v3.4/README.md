# ENTITY v3.4 Family Runtime Portal

**Document class:** current-runtime family orientation / non-normative to Protocol 1.0
**Current supported runtime:** [ENTITY v3.4.3](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.3)
**BTDU component:** Blackmore Technology Data Universe (BTDU) 3.4.2, unchanged
**Historical v3.4.0/v3.4.1/v3.4.2 evidence:** preserved under its original release targets

This directory describes the **v3.4 runtime family**: Global Passport architecture, domain packages, deployment and historical closure material. It is not the normative ENTITY Protocol 1.0 clean-room specification.

For Protocol 1.0 independent implementation, use the separately sealed [ENTITY Protocol 1.0 External Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit).

Read [Documentation Model](../DOCUMENTATION_MODEL.md) before interpreting version labels in historical qualification material.

## Current runtime boundary

ENTITY v3.4.3 is a bounded remediation release based on immutable v3.4.2 commit `6dfa3d6cc738d9369cf092d2782676bf4f2a46e4`.

It fixes two reproduced Issue #28 defects:

1. derivative-revenue evidence substitution could create a second economic event/obligation for the same authoritative occurrence;
2. a zero-edge causal graph could return a positive self-trace for missing/empty endpoints and classify an empty path as evidence-bound.

Current v3.4.3 qualification:

| Evidence | Result |
| --- | --- |
| Issue #28 remediation module | **76/76 PASS** |
| Full repository source suite | **279/279 PASS** |
| Source-suite exit code | **0** |
| Compiled Rust qualification | **PASS — inherited unchanged scope** |
| Real-world BTDU training qualification | **PASS — inherited unchanged scope** |
| BTDU component | **3.4.2 unchanged** |

The inherited results are not described as re-executed v3.4.3 campaigns.

## Runtime architecture in this directory

The v3.4 family preserves the universal ENTITY Global Passport, composable profile stacks, versioned profile registry, standards mappings, continuous provenance, passport derivation and executable industry deployment packages.

The runtime architecture uses the five core primitives:

**ENTITY → AUTHORITY → RIGHT → EVENT → VALUE**

> One ENTITY Passport. Many jurisdictions, industries, standards and contexts. No new sovereignty silos.

These runtime primitives and packages must not be mistaken for extra Protocol 1.0 clean-room requirements.

## Start here

- [Global Passport runtime architecture](GLOBAL_PASSPORT.md)
- [Domain packages and profiles](DOMAIN_PACKAGES.md)
- [Deployment model](DEPLOYMENT_MODEL.md)
- [Historical v3.4.0 post-release recursive closure](RECURSIVE_CLOSURE.md)
- [ENTITY v3.4.3 release record](../../RELEASE_V3_4_3.md)
- [ENTITY Wallet — current application layer](ENTITY_WALLET_20261002.md)
- [Wallet identity onboarding](ENTITY_WALLET_IDENTITY_ONBOARDING.md)
- [Wallet cross-platform builds](ENTITY_WALLET_CROSS_PLATFORM_BUILDS_20261003.md)
- [Software Engineering profile](passports/SOFTWARE_ENGINEERING.md)
- [Engineering evidence](../ENGINEERING_EVIDENCE.md)

## Current wallet application layer

The current wallet is the **ENTITY Data Economy Terminal**. It includes sovereign first-run identity/lineage onboarding, Digital Asset/DCO holdings, signed asset disclosures, issuer-scoped economic instruments and tickers, Rights-Passport-driven instrument issuance, market listings/positions/orders and explicit domain lineage.

The final focused qualification completed on 2026-10-03 at **91/91 PASS**. The qualified production snapshot contained 12 current assets with no missing domains: 10 Software Engineering and 2 Robotics.

Windows, Linux and macOS are full PySide6 desktop builds of the canonical wallet. The repository also builds a native iOS Simulator portable-snapshot inspection client; native iOS write-authority parity is not claimed.

## Historical v3.4.1 qualification snapshot

The following values remain historical v3.4.1 evidence and are **not rewritten** to make them look current:

| Evidence | Historical v3.4.1 result |
| --- | --- |
| Full regression | **185/185 PASS** |
| Protocol-origin / migration / economic-lineage | **8/8 PASS** |
| v3.4 targeted tests | **33/33 PASS** |
| Sealed Global Passport vectors | **24/24 PASS** — 12 valid / 12 invalid |
| Sealed kit SHA-256 | `f95c2b347da97742fed3f20611f0eec2fd3df48694fed9494fb07163c537cfb7` |
| Global Passport schema SHA-256 | `3d72b4e67ec9929c5d960cee8fc52db35d85ba5103e361f3a61a8f5078079c5d` |
| Signed v3.4.1 release-origin sidecar SHA-256 | `d81bc3bdd6fab5acf8d923eccf24210ac1c65970826ad1f11fbe03f07aa0caa8` |
| Canonical six-language result | `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba` |
| v3.4.0 post-release constituent root | `4feb51a4bd0d958b7beb3eddbe9fd78678b7c31c2a4fe3d6cf7d9f4d87aa6e06` |

The six native implementations and domain-package qualification are BTG-controlled engineering evidence, not unrelated third-party validation.

## Sovereignty and economic boundary

Runtime packaging, repository custody, standards mapping, ingestion or provenance do not create upstream ownership or automatic economic entitlement.

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

Historical signed and sealed evidence in this directory remains bound to the version/campaign that produced it.
