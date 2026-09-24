# ENTITY v3.1.0 Release Qualification

**Date:** 2026-09-24  
**Status:** BTG INTERNAL QUALIFIED FEATURE RELEASE  
**Base:** ENTITY v3.0.1 at `a977b013cb29504f04953c4fce33d2372e91097b`

ENTITY v3.1.0 extends the security-hardened v3.0.1 release with the Global Infrastructure Profile Set and the Data Economic Sovereignty Doctrine. The five-primitives Core remains `ENTITY / AUTHORITY / RIGHT / EVENT / VALUE`; the new jurisdiction, ontology, governance, privacy/provenance, topology, cryptographic-migration and data-economic mechanisms remain profiles layered above Core.

## Qualification result

- Complete corrected-base regression: **116/116 PASS**.
- Global infrastructure + doctrine targeted campaign: **22/22 PASS**.
- Global conformance pack: **8 valid + 8 invalid vectors**.
- Feature snapshot: `a26be5480b94f7669d41158cbceb1e8d31146afbbcba88f3ee4857c323cf25fc`.
- Six-language common semantic result: `879c8e1eba2549a9a1962605760b715b0fd47d3ea640fb9c6f29be5c63cfb8c5`.

## Canonical BTG-controlled clean-room evidence

| Language | Canonical main commit | GitHub Actions run | Result |
|---|---|---:|---|
| Rust | `1dd9d4d35a5ff582f1a38ad5f2f537728c58e062` | `35950910738` | PASS |
| TypeScript | `795a15c463f6f685282892bcdea480fb79ef311d` | `35950918876` | PASS |
| C# | `e5ee834ae3b59bf28358a7279dba8a197928c107` | `35950928130` | PASS |
| Go | `5be40a675cf3bd9d7d2a6bd39d39ef437839d28c` | `35950936069` | PASS |
| Swift | `830355d2c850bec6abdd62e8274d81afa5a8101e` | `35950945169` | PASS |
| Java | `2d230ea09388149f3829275e88324616469f8e0f` | `35953170903` | PASS |
## New v3.1 qualification surface

The release qualifies signed/effective-dated jurisdiction overlays; explicit semantic registries and crosswalks; stakeholder-diverse standards governance; purpose-bound privacy and confidential provenance; partition/offline topology; cryptographic-suite migration; and rights-based data-economic semantics.

The Data Economic Sovereignty Doctrine makes the economic boundary explicit: information does not need artificial byte scarcity. Scarcity is expressed through bounded rights, entitlements, capacities, durations, jurisdictions, usage quantities, derivation rights, participation rights and transferability constraints. Originator participation must be established by valid terms; ENTITY does not infer it from mere creation or possession.

ENTITY preserves the chain from information to governing RIGHT, authorized EVENT/use, derivation and VALUE/economic consequence. It does not turn cryptographic evidence into legal title, fair value, regulatory classification or objective external-payment truth.

## Inherited v3.0.1 qualification

v3.1.0 inherits the v3.0.1 internally qualified security and production evidence: 1,000,000 assets, 3,000,000 events, destructive recovery, 4,000 settled EEP trades, 900-second / 7,231-trade continuity soak, 5,400 EEP adversarial crypto cases, 10,000 randomized key-lifecycle signature cases, 3,000 privacy assertions and 200 signed Merkle receipts.

## Remaining external milestones

1. Unrelated third-party v3 implementation and independent live interoperability.
2. Independent external security/cryptographic review.
3. Deployment-specific legal/regulatory classification, licensing, recognition or approval where required.

These are intentionally not self-certified by BTG. The six native clean-room implementations above are significant controlled reproducibility evidence, but remain BTG-controlled.
