# ENTITY v3.3.0 — Six-Language Controlled Conformance Addendum

**Date:** 2026-09-24  
**Status:** PASS  
**Evidence class:** BTG-controlled cross-language reproducibility  
**Published release:** `v3.3.0`  
**Protected release commit:** `9c79f987207592cb6791e1a8956f23351cdfb2d3`

This addendum records controlled native-language qualification completed after the v3.3.0 GitHub Release was published. It does **not** move, replace or rewrite the published `v3.3.0` tag, release commit, release manifest or release snapshot.

The six campaigns consumed the same v3.3 semantics as the published release. The exact release-tag artifacts independently hash to:

- sealed reality kit SHA-256: `f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46`
- verifiable-reality schema SHA-256: `6e1c7e621e0aa84627e009febf8999503b7a61f92627b885ed10a19f2ef7d767`
- required deterministic result SHA-256: `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`
- vector campaign: **20/20 PASS** — 10 valid and 10 invalid records

## Native controlled baselines

| Runtime | Qualified commit | GitHub Actions run | Result |
| --- | --- | ---: | --- |
| Rust | `0ff638fdb0a3d7e8e061205d5b5bc2e3f1e68a31` | `36016169261` | PASS |
| TypeScript | `6582532af2af6a9bcf458aa2e80a841f64f51094` | `36016179311` | PASS |
| C# | `5a1fb61380a788b98d7fccb9f138527f063c1d9f` | `36016731801` | PASS |
| Go | `74cebdfbb0a6751ea60764e874656b119a3e2416` | `36016190096` | PASS |
| Swift | `bbc4e6e6d7cfa4517e90ca2f9477f784e29c72f1` | `36016560914` | PASS |
| Java | `1d4d717cd9f5bd93bdcf1403d86b840517c208f3` | `36016205611` | PASS |

Every runtime evaluated the same 20 public v3.3 records and independently converged on:

`82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`

The workflows preserve the earlier qualification chain: legacy ENTITY verification and the applicable v3.1/v3.2 campaigns remain gates before the v3.3 campaign. A green v3.3 workflow therefore does not replace the earlier evidence.

## What this adds to the v3.3 evidence record

This materially strengthens the reproducibility claim for the Verifiable Reality, Evidence and Economic Causality layer across six separate runtime ecosystems. It demonstrates controlled convergence for the distinctions between evidence, typed claim state, scoped attestation, external anchors and causal-economic records.

It does **not** upgrade the claim to independent external interoperability. All six repositories remain BTG-controlled.

## Permanent truth boundary

The successful campaign does not mean ENTITY makes reality indisputable. The release continues to distinguish:

1. cryptographic verification — integrity and attribution;
2. protocol verification — compliance with ENTITY semantics;
3. reality/evidence verification — the attributed evidence supporting an external-world claim.

A valid signature, a valid protocol record or an external attestation does not automatically establish objective legal or physical truth.

## External milestones still open

- unrelated third-party v3.3 implementation;
- bidirectional live interoperability with an unrelated implementation;
- independent security/cryptographic review;
- deployment-specific legal/regulatory validation where required;
- real external issuer/buyer activity, repeat transactions and demonstrated liquidity.
