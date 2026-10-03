> **STRATEGIC EMPHASIS CORRECTED — 2026-10-03**  
> This document originally framed 10,000 DCOs primarily as a BTG production target. The factory remains technically capable of large catalogs, but the operating objective is now an **open, issuer-neutral DCO issuance capability**. BTG's first 100 DCOs are seed/proof-of-market inventory; growth beyond that is expected increasingly from unrelated participants. See `ENTITY_ECONOMIC_CONSTITUTION_20261003.md` and `OPEN_DATA_ECONOMY_20261003.md`.

# DCO Factory — 10,000-DCO design target

Date: 2026-10-02  
ENTITY display version: **3.4.3**  
DCO Factory: **0.1.0 application layer**

## Purpose

The DCO Factory is the industrial issuance layer above the existing ENTITY v3.4.3 Universal Transaction Fabric, EEP, Economic Participation Profile and Economic Wallet.

It does not add a new protocol instrument class and does not require an ENTITY version change.

The factory exists because a catalog measured in thousands of DCOs must not be created as thousands of hand-built economic contracts.

## Design target

The factory has been qualified for a **10,000-record catalog design target**, but that is a technical capacity target—not a requirement for BTG to own 10,000 DCOs. The corrected operating roadmap is to use roughly 100 BTG seed DCOs to prove the market, then open issuance to unrelated participants and scale the **total** market catalog. Actual balances, entitlements, transactions and usage remain activity-driven.

## Commercial profiles

### Standard
3–5 product archetypes.

### Advanced
6–8 product archetypes.

### Strategic
9–12 product archetypes.

A product archetype is distinct from an EEP instrument class. ENTITY v3.4.3 still uses the existing six EEP classes:

`SPOT_LICENSE`, `SUBSCRIPTION`, `COMPUTE_TO_DATA`, `PROCUREMENT`, `CONTRIBUTION`, and `SECONDARY_LICENSE`.

Specific commercial products are expressed through actions, constraints, terms, supply, duration, variants and transferability.

## Strategic AI / robotics template

The reusable `BTG-STRATEGIC-AI-ROBOTICS-01` template contains twelve commercial archetypes:

1. Evaluation
2. Inference
3. Training
4. Compute-to-data
5. Enterprise/API
6. Commercial derivative
7. OEM/embedded
8. Field-of-use
9. Redistribution
10. Synthetic/derived data
11. Regional exclusivity
12. Contributor participation

Regional exclusivity is one commercial archetype. A concrete DCO can expand it into territory-specific physical instruments. The current robotics template uses ten regions, so the twelve archetypes produce twenty-one physical EEP instruments.

## Scarcity classes

The factory standardizes four supply philosophies:

- `OPEN_CAPACITY` — additional series may be issued under published policy;
- `CONTROLLED_CAPACITY` — additional issuance requires a disclosed policy/version;
- `FIXED_CAP` — maximum supply is defined for the DCO version;
- `UNIQUE` — one unit for a specific unique variant such as a territory.

Supply is deliberately separate from pricing. A supply record does not create market value.

## Master Economic Record

Each DCO is designed to have one authoritative application-layer management record containing:

- identity/family/version/lifecycle;
- source hash and provenance root;
- template and economic profile;
- instrument/archetype summary;
- supply and treasury reserves;
- market state;
- economic state;
- version/derivative relationships;
- duplication classification.

This record is an operating index over canonical ENTITY state, not a replacement ledger.

## Duplicate and version protection

The factory provides:

- exact source-hash duplicate rejection;
- semantic-fingerprint duplicate rejection when a fingerprint is supplied;
- provenance-root review;
- explicit `NEW_VERSION` classification;
- explicit `DERIVATIVE_OF_EXISTING_DCO` classification;
- otherwise `NEW_DCO`.

The application layer intentionally refuses to silently convert an existing-lineage candidate into a new independent DCO.

## Qualification boundary

The factory qualification inserts and summarizes **10,000 Master Economic Records** in a single SQLite-backed application registry. This qualifies the factory/catalog design path.

It does **not** claim that 10,000 DCOs were commercially issued, traded, settled or independently valued, and it does not replace separate EEP market-throughput qualification.

## Industrial Robotics reference instance

The installed Industrial Robotics DCO has been expanded to the complete twelve-archetype Strategic profile.

Its 12 archetypes map to **21 physical EEP instruments** because Regional Exclusivity has ten territory-specific variants.

Current controlled-prelaunch aggregate:

- **28,418 issued rights units**;
- **2,280 actual BTG Treasury reserve units**;
- **0 orders**;
- **0 trades**;
- **0 market marks**.

The additional archetypes were added without changing ENTITY v3.4.3.
