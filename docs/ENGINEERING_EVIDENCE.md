# ENTITY Engineering Evidence

**Document class:** evidence index / current-runtime orientation
**Current supported runtime:** ENTITY v3.4.3
**BTDU component:** Blackmore Technology Data Universe (BTDU) 3.4.2, unchanged
**Protocol 1.0:** separate frozen clean-room target
**Normative effect:** none; this page indexes and explains evidence rather than changing it

This document separates **what Blackmore Technology Group Limited (BTG) has directly qualified**, **what unrelated people have reproduced**, and **what still requires independent evidence outside BTG control**.

The purpose is not to turn test counts into marketing claims. It is to make each result's target, control boundary and remaining credibility gap explicit.

See [Documentation Model](DOCUMENTATION_MODEL.md) for the repository-wide version/layer rules.

## Evidence classes

ENTITY treats the following as different evidence classes. One class must not silently be relabelled as another.

1. **Protected BTG release evidence** — protected branch/release commit, release tag, manifest and qualified tests under BTG control.
2. **Sealed campaign evidence** — exact public vector/kit target with hashes and deterministic result requirements.
3. **BTG-controlled cross-language reproducibility** — separately implemented language baselines still controlled by BTG.
4. **External reproduction of a BTG target** — an unrelated person runs a published BTG-controlled campaign and reproduces the expected result.
5. **Independent implementation** — an unrelated party authors and controls an implementation from the permitted public protocol/specification material.
6. **Independent live interoperability/recovery** — independently controlled implementation exchanges required state with BTG and survives the required sovereign export/recovery path.
7. **Independent security/research/deployment evidence** — separate reviews or real deployments with their own explicitly bounded scope.

A successful result at class 4 does not automatically become class 5 or 6. A BTG-controlled language implementation does not become independent merely because it uses a different programming language.

## Current supported release — ENTITY v3.4.3

**Release:** `v3.4.3`
**Release merge commit:** `528b70aabd05b1e930b77e4933f157731e47274f`
**Immutable predecessor:** v3.4.2 commit `6dfa3d6cc738d9369cf092d2782676bf4f2a46e4`

ENTITY v3.4.3 is a bounded remediation release for the two defects reproduced in Issue #28:

1. derivative-revenue evidence substitution could create a second economic event/obligation for the same authoritative occurrence;
2. a zero-edge causal graph could return a positive self-trace for missing/empty endpoints and label an empty path evidence-bound.

### Direct v3.4.3 qualification

| Evidence | Result |
| --- | --- |
| Issue #28 remediation module | **76/76 PASS** |
| Full repository source suite | **279/279 PASS** |
| Full source-suite exit code | **0** |

### Inherited unchanged-scope qualification

The v3.4.3 release record explicitly carries forward two previously closed v3.4.2 results because the remediation did not modify those qualified components/paths:

- compiled Rust clean-room/conformance qualification — **PASS**, evidence SHA-256 `96a7b5175dc11e1d881a9a1aa53c3496dac93d182d7072e71ad4982921571754`;
- real-world BTDU training qualification — **PASS**, evidence SHA-256 `4d31bc1a3ae8c8ff6dcf096b304914808e27cc60595510cc7088b5af021931ff`.

These are **inherited records**, not re-executed v3.4.3 campaigns.

### Component/version boundary

- ENTITY runtime: **3.4.3**;
- BTDU component: **3.4.2 unchanged**;
- v3.4.2 release evidence: immutable historical evidence;
- active 30-day wall-clock campaign: not reset or rewritten by v3.4.3.

Authoritative release material: [`RELEASE_V3_4_3.md`](../RELEASE_V3_4_3.md) and [`RELEASE_V3_4_3.json`](../RELEASE_V3_4_3.json).

## Post-tag ENTITY Wallet qualification — 2026-10-03

The current main-branch wallet application layer is later than the immutable `v3.4.3` tag and is therefore recorded separately from the tagged release evidence.

Final focused wallet/economy/lineage/onboarding/global-passport campaign: **91/91 PASS**.

Wallet implementation baseline: `212ee56d34aee578e6df701ef9f9a675661b7162`.

The locally rebuilt/installed Windows package passed its frozen-runtime self-test. Qualified production-state domain resolution contained 12 current assets: 10 Software Engineering and 2 Robotics, with no missing domain.

Windows/Linux/macOS full desktop binaries are produced by the cross-platform wallet workflow. The iOS Simulator artifact is a native portable-snapshot inspection client and is not classified as an independently qualified native authority/runtime implementation.

See [wallet state](v3.4/ENTITY_WALLET_20261002.md) and [cross-platform builds](v3.4/ENTITY_WALLET_CROSS_PLATFORM_BUILDS_20261003.md).

## External reproduction evidence

An unrelated GitHub contributor reproduced the published BTG-controlled Java v3.4.2 26-vector baseline on Windows 11 / OpenJDK 21 / Maven 3.9.6 and reported:

- compilation successful;
- campaign execution successful;
- **26/26 PASS**;
- sealed-kit SHA-256 matched `ced70113f1d153627eb972b11adbf20e502ed086e0b13e8abf1dc5adc4c2e716`;
- campaign result SHA-256 matched `45af773554a7191c1b49a75c636a1106afb1de36d788bb00d7af56097b8d1b0e`;
- `overall_valid: true`.

This is meaningful **external reproduction** of a BTG-published baseline. It is not an independently designed implementation from the Protocol 1.0 specification and is not full independent interoperability qualification.

## Frozen v3.4.2 language campaigns

The BTG-controlled Rust, TypeScript, C#/.NET, Go, Swift and Java repositories retain the exact v3.4.2 Global Passport campaign as a frozen reproducibility target.

Campaign commitments include:

- vectors: **26/26 PASS**;
- sealed-kit SHA-256: `ced70113f1d153627eb972b11adbf20e502ed086e0b13e8abf1dc5adc4c2e716`;
- canonical campaign result SHA-256: `45af773554a7191c1b49a75c636a1106afb1de36d788bb00d7af56097b8d1b0e`;
- `overall_valid: true`.

The word **v3.4.2** here names the exact campaign target. It does not mean v3.4.2 is still the current supported runtime.

These six repositories remain BTG-controlled evidence.

## ENTITY Protocol 1.0 external clean-room target

ENTITY Protocol 1.0 remains a separately frozen external conformance target in the [`ENTITY-Protocol-1.0-Conformance-Kit`](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit).

Protocol 1.0 independent implementation is evaluated from the permitted public material in that sealed kit. Later runtime/component material—including BTDU, ADAM, NIKI or Global Passport implementation internals—is not silently added to the Protocol 1.0 implementation obligation.

A full external Protocol 1.0 interoperability PASS still requires the published gates, including independent implementation, valid/invalid vector behavior, bidirectional live interoperability and sovereign export/recovery verification.

**Independent external interoperability remains PENDING until an unrelated implementation satisfies the required gates.**

## v3.4.1 — historical protected release

**Release:** `v3.4.1`
**Protected release commit:** `9822b1b65f8269ebc17208a342809720729ae2f8`

Historical qualification retained exactly as v3.4.1 evidence:

- complete regression: **185/185 PASS**;
- protocol-origin / migration / economic-lineage: **8/8 PASS**;
- targeted Global Passport/package suite: **33/33 PASS**;
- sealed vectors: **24/24 PASS** — 12 valid / 12 invalid;
- sealed kit SHA-256: `f95c2b347da97742fed3f20611f0eec2fd3df48694fed9494fb07163c537cfb7`;
- schema SHA-256: `3d72b4e67ec9929c5d960cee8fc52db35d85ba5103e361f3a61a8f5078079c5d`;
- six-language BTG-controlled result SHA-256: `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`;
- six v3.4.0 executable domain package payloads requalified unchanged: **6/6 PASS**;
- `ENTITY_CURRENT_RELEASE_ORIGIN.json` SHA-256: `d81bc3bdd6fab5acf8d923eccf24210ac1c65970826ad1f11fbe03f07aa0caa8`.

Protocol origin remains separate from user/asset provenance and does not create an automatic royalty or economic entitlement.

## v3.4.0 — historical protected release and domain packages

**Release:** `v3.4.0`
**Protected release commit:** `2db5bff64507b8d67642122a5ff2fc73dfef9152`

Historical qualification:

- complete regression: **177/177 PASS**;
- targeted Global Passport/package suite: **33/33 PASS**;
- sealed vectors: **24/24 PASS** — 12 valid / 12 invalid;
- sealed kit SHA-256: `5869a3fd0ed6cb9f65bf4b20c3bd64933cad82f4aef05c5809e2e05af921f230`;
- schema SHA-256: `4fbfed9be1b1484bc5d28b8101d1c908b2ccced13e4e99ec896c5b054892ebdd`;
- six-language BTG-controlled result SHA-256: `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`;
- six executable domain package payloads published and verified;
- post-release recursive closure: **PASS**, frozen constituent root `4feb51a4bd0d958b7beb3eddbe9fd78678b7c31c2a4fe3d6cf7d9f4d87aa6e06`.

The domain-package repositories retain their exact v3.4.0 package hashes/bindings as historical evidence. Reader-facing compatibility/status language may advance only where qualification supports it; the package payload hashes themselves are not rewritten.

## v3.3.0 — historical Verifiable Reality qualification

Historical release qualification:

- complete regression: **144/144 PASS**;
- targeted v3.3 tests: **16/16 PASS**;
- sealed vectors: **20/20 PASS** — 10 valid / 10 invalid;
- sealed kit SHA-256: `f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46`;
- schema SHA-256: `6e1c7e621e0aa84627e009febf8999503b7a61f92627b885ed10a19f2ef7d767`;
- deterministic result SHA-256: `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`.

BTG later completed the same sealed campaign in six controlled language baselines. That remains controlled cross-language reproducibility, not unrelated interoperability evidence.

## v3.2.0 — historical adoption qualification

**Protected commit:** `512665096cef3771a3a8307d6dc955015ee0efbc`

Historical BTG-controlled qualification:

- regression: **128/128 PASS**;
- targeted adoption tests: **12/12 PASS**;
- sealed vectors: **16/16 PASS** — 8 valid / 8 invalid;
- sealed kit SHA-256: `44e7a00f910c89aced3b3c1b5e9cba486809ca313e9bfb4b7bc9266095c10c14`;
- six-language result SHA-256: `1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18`.

Again, this is BTG-controlled evidence.

## Real-world external-repository qualification

ENTITY also runs bounded External Repository Qualification (ERQ) campaigns against real public repositories. These campaigns test provenance, deduplication, recovery, fork divergence and provider portability while preserving upstream ownership/licence boundaries.

Current CLAW campaign status is tracked in ENTITY issue #78:

- ERQ-1 destructive external-repository survival — **PASS**;
- ERQ-2 cross-platform recovery/verification — **PASS**;
- ERQ-3 multi-repository identity/dedup/provenance separation — **PASS**;
- ERQ-4 genuine upstream advance / temporal-lineage preservation — **WAITING FOR REAL UPSTREAM ADVANCE**;
- ERQ-5 BTG fork divergence from pinned upstream anchor — **PASS**;
- ERQ-6 local/provider-neutral migration — **PASS**;
- ERQ-6 external-provider migration — **PENDING / NOT COMPLETED** because the selected external provider blocked the repository at the account/workspace plan limit.

Do not convert ERQ-4 into a synthetic pass, and do not describe the external-provider limitation as an ENTITY technical failure.

ERQ ingestion does not transfer upstream ownership or create automatic economic entitlement.

## Sovereignty, provenance and economic boundary

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

ENTITY may record attributable provenance, authorship, copyright/licence, custody, rights metadata, usage evidence and economic state. Those records establish only the protocol/evidence facts they actually verify.

The data-economic lifecycle remains:

`DCO → Instrument → Listing → Disclosure → Order/RFQ/Auction → Price Discovery → Trade → Clearing → Settlement → Entitlement → Usage → Derived Output → Economic Consequence`

A **Digital Commodity Object (DCO)** or other governed record does not acquire market value, settlement finality, royalty rights or legal title merely because ENTITY can represent it. Economic participation requires explicit rights/terms and the required evidence.

## Intentionally untouched evidence

The documentation audit does not rewrite:

- signed/sealed Protocol 1.0 artifacts;
- v3.4.2 campaign hashes or expected results;
- historical release manifests and tags;
- historical package hashes/bindings;
- ERQ receipts/hashes;
- external contributor reproduction evidence;
- the active 30-day wall-clock campaign.

When an old artifact is confusing, the fix belongs in explanatory documentation around it, not in falsifying the historical artifact.

## Remaining strongest evidence gaps

The major external milestones still include:

- an unrelated independently authored implementation from the permitted public Protocol 1.0 material;
- required bidirectional live interoperability;
- independent sovereign export/recovery survival evidence;
- genuine ERQ-4 temporal-lineage evidence after a real upstream advance;
- external-provider completion of the currently pending ERQ-6 leg;
- independent security/research assessment where claimed.

Until those occur, documentation must describe them as pending rather than inferred from BTG-controlled tests.
