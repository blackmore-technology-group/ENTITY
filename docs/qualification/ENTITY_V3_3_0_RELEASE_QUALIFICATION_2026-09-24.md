# ENTITY v3.3.0 — Internal Release Qualification

**Date:** 2026-09-24

**Status:** BTG internal qualified verifiable-reality release candidate

**Base release:** v3.2.0

**Protected base commit:** `512665096cef3771a3a8307d6dc955015ee0efbc`

**Qualified source/gateway commit:** `8d0d60948c584de9bdff665ed034480c08254509`

## Release result

ENTITY v3.3.0 adds a formal evidence bridge between external-world claims and authoritative ENTITY state while preserving v3.2 Rights Passports, the five core primitives and the existing market lifecycle.

### Qualification

- Complete inherited + v3.3 regression: **144/144 PASS**
- Targeted verifiable-reality tests: **16/16 PASS**
- Verifiable-reality clean-room vectors: **10 valid + 10 invalid = 20/20**
- Clean-room kit SHA-256: `f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46`
- Schema SHA-256: `6e1c7e621e0aa84627e009febf8999503b7a61f92627b885ed10a19f2ef7d767`
- Required deterministic result SHA-256: `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`

## Six-language controlled conformance

| Runtime | Commit | GitHub Actions run | Status |
|---|---|---:|---|
| Rust | `0ff638fdb0a3d7e8e061205d5b5bc2e3f1e68a31` | `36016169261` | PASS |
| TypeScript | `6582532af2af6a9bcf458aa2e80a841f64f51094` | `36016179311` | PASS |
| C# | `5a1fb61380a788b98d7fccb9f138527f063c1d9f` | `36016731801` | PASS |
| Go | `74cebdfbb0a6751ea60764e874656b119a3e2416` | `36016190096` | PASS |
| Swift | `bbc4e6e6d7cfa4517e90ca2f9477f784e29c72f1` | `36016560914` | PASS |
| Java | `1d4d717cd9f5bd93bdcf1403d86b840517c208f3` | `36016205611` | PASS |

All six native implementations accept/reject the same 20 sealed records and converge on `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`. These remain BTG-controlled implementations, not unrelated third-party interoperability evidence.

## New v3.3 layer

`Reality → Observation → Claim → Evidence → Attestation → Verification → Authoritative ENTITY State → Right → Usage → Economic Consequence`

v3.3 introduces signed Evidence Objects, typed claim states, scope-limited attestation authority, external reality anchors, contestability/supersession and evidence-backed causal economic attribution.

## Preserved market model

`DCO → Instrument → Listing → Disclosure → Order/RFQ/Auction → Price Discovery → Trade → Clearing → Settlement → Entitlement → Usage → Derived Output → Economic Consequence`

The targeted suite explicitly verifies that v3.2 Rights Passports compose without rewrite and the inherited exchange lifecycle survives v3.3.

## Three verification layers

1. **Cryptographic verification** — did this key sign this exact record?
2. **Protocol verification** — does the transition obey ENTITY semantics?
3. **Reality/evidence verification** — what evidence supports the external-world claim, under whose authority, with what status?

These are intentionally not equivalent.

## Claim boundary

ENTITY v3.3.0 does not claim to make external reality indisputable. Evidence, attestations and external records remain attributable and contestable. External systems do not automatically become ENTITY authority. Protocol records do not determine legal title or accounting/market fair value.

## External work still required

BTG-controlled qualification is not unrelated third-party verification. Independent implementation/interoperability, independent security/cryptographic review, deployment-specific legal/regulatory treatment and demonstrated external market adoption/liquidity remain outside this internal release claim.
