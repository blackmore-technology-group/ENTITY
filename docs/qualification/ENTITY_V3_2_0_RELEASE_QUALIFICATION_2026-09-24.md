# ENTITY v3.2.0 — Internal Release Qualification

**Date:** 2026-09-24  
**Status:** BTG internal qualified adoption release candidate  
**Base release:** v3.1.0  
**Protected base commit:** `b985b7cf875bdeeadb228d4d1885395cbcaf19f1`  
**Qualified source/kit commit:** `ee3587a6e65c2565eaab2e815e85415ab705ea47`

## Release result

ENTITY v3.2.0 extends the qualified v3.1.0 architecture with an adoption layer while preserving the five core primitives and the existing Exchange Protocol market lifecycle.

### Regression

- Official v3 regression: **128/128 PASS**
- Targeted adoption tests: **12/12 PASS**
- Adoption vectors: **8 valid + 8 invalid = 16/16**

### Sealed adoption campaign

- Vector manifest SHA-256: `40b081b3a5099aed375ad2f1095e589e56847f32790f40a30a864f45e4b9b093`
- Adoption schema SHA-256: `d474f1262166a4518399c841da93a806f5d849949f17005699200e37bcf7c321`
- Compact sealed-kit SHA-256: `44e7a00f910c89aced3b3c1b5e9cba486809ca313e9bfb4b7bc9266095c10c14`
- Required common result SHA-256: `1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18`

### Native clean-room evidence

| Runtime | Commit | GitHub Actions run | Result |
|---|---|---:|---|
| Rust | `13787e20dd9b52cf34c7bcc6262863a2a62b2a4e` | 35957428814 | PASS |
| TypeScript | `2766c68dec8914ce000123ea3281cf190dddadfc` | 35957273170 | PASS |
| C# | `9f4d33c5b5c553644cd9c73a5c9cf09040083fe3` | 35957627266 | PASS |
| Go | `ff8a733b8271ac655eac8a3302b4f6cd9acadacf` | 35957338729 | PASS |
| Swift | `f55809a85cc763d2430b046b3a60f177b30de6d8` | 35957491341 | PASS |
| Java | `ea58105b6c90a5b7bb5169cdf8701c880822bdae` | 35957541838 | PASS |

Every native implementation consumed the same pinned v3.2 compact kit, verified its SHA-256, independently classified all 16 cases, and required the same canonical result hash.

## Preserved market model

`DCO → Instrument → Listing → Disclosure → Order/RFQ/Auction → Price Discovery → Trade → Clearing → Settlement → Entitlement → Usage → Derived Output → Economic Consequence`

The v3.2 tests execute a real inherited EEP listing/order/match/settlement/entitlement/AI-training-usage path and verify that ownership of the underlying information is not silently transferred.

## Added adoption capabilities

- signed immutable Rights Passports;
- provider-neutral custody connectors;
- ODRL / W3C VC / DID / Gaia-X / IDS adapters;
- developer adoption SDK;
- jurisdiction and rights-ontology composition;
- federated resolver deployment profile;
- legal-classification assertion envelopes;
- six-language adoption conformance kit.

## Permanent boundaries

ENTITY v3.2.0 does not claim that cryptographic records determine legal title, market/accounting fair value, objective bank truth or regulatory classification. Custody does not create authority. Standards mappings do not create authority. Information itself does not have to be scarce; bounded rights and interests provide the economic scarcity where appropriate.

## External work still required

BTG-controlled conformance is not unrelated third-party verification. Independent implementation/interoperability, independent security/cryptographic review, deployment-specific legal/regulatory treatment, and real external market adoption/liquidity remain outside the internal qualification claim.
