# ENTITY Economic Constitution — Open Data Economy

Date: 2026-10-03  
ENTITY display version: **3.4.3**

## Purpose

ENTITY is infrastructure for an open market in legitimately controlled **rights**, not a system in which Blackmore Technology Group must own the assets being traded.

The scarce economic object is the bounded right or entitlement. The underlying information does not need to become artificially scarce and registration does not create ownership.

## Constitutional invariants

1. Everyone can participate.
2. Registration is not ownership.
3. Rights—not copies—are the economic object.
4. Users choose what rights they retain and what rights they offer.
5. Rights may have bounded supply, duration, jurisdiction and transferability.
6. Markets determine price. ENTITY does not declare fair value.
7. Transferability must be explicit.
8. Participants can hold rights portfolios.
9. Contributors may aggregate into governed pools.
10. Fiat settlement is supported externally.
11. Cryptocurrency is not required.
12. Gas is not required.
13. Protocol tax is zero.
14. BTG receives no automatic royalty or hidden protocol privilege.
15. BTG and other service providers compete on optional services.
16. The market is issuer-neutral and provider-neutral.
17. Protocol operation does not determine legal title, fair value or regulatory classification.

Canonical constants:

```
protocol_tax_bps = 0
cryptocurrency_required = false
gas_required = false
automatic_btg_royalty_bps = 0
issuer_neutral = true
provider_neutral = true
```

## Economic flow

```
LEGITIMATE HOLDER
      │
      ├── underlying data / algorithm / model / creative work / observations
      │
      ↓
     DCO
      │
      ↓
RIGHTS PASSPORT
      │
      ├── rights retained
      └── rights offered
              │
              ↓
      ECONOMIC INSTRUMENT
              │
              ↓
          OPEN MARKET
              │
      ┌───────┴────────┐
      ↓                ↓
   HOLDER            BUYER
      │                │
      └──── RIGHTS ────┘
```

The data itself need not move when compute-to-data or governed execution is used.

## BTG's role

BTG may originate assets and participate in the market exactly like another legitimate holder.

The first 100 BTG DCOs are **seed portfolio / proof-of-market inventory**, not the definition of ENTITY's economy.

Their purpose is to prove:

- DCO creation;
- authority and provenance;
- Rights and Global Passports;
- rights issuance;
- listing;
- price discovery;
- trading;
- settlement evidence;
- usage;
- derivative economics;
- portfolios.

The growth roadmap is therefore not "100 → 1,000 → 10,000 BTG-owned DCOs."

It is:

```
100 BTG seed DCOs
        ↓
external creators enter
        ↓
1,000 total DCOs
        ↓
10,000 total DCOs
        ↓
100,000+
        ↓
millions
```

with an increasing share controlled by unrelated participants.

## Optional services

BTG may earn revenue from optional competitive services such as:

- market hosting;
- certification;
- verification;
- managed infrastructure;
- enterprise APIs;
- analytics;
- custody/connectivity;
- market data;
- specialized tooling.

No service position is a protocol privilege. Another organization can compete.

## Consumer-facing doctrine

A normal participant should not need to understand EEP, EOPP or BTDU terminology.

The normal flow should be:

```
I HAVE DATA
   ↓
What is it?
   ↓
Do I have authority/rights?
   ↓
Prove provenance
   ↓
Choose privacy
   ↓
Choose rights I retain
   ↓
Choose rights I offer
   ↓
Choose quantity / duration / restrictions
   ↓
Review
   ↓
Create DCO / passports / instruments
   ↓
List if desired
```

The buyer side should be equally rights-first:

```
LOOKING FOR
asset type
region
period / scale
required rights
commercial permissions
derivative permissions
raw-transfer requirement
        ↓
SEARCH
        ↓
BUY / BID / REQUEST QUOTE
```

## Data pools

Individual contributors may aggregate economically useful rights into governed pools while retaining provenance and attribution.

A pool is not a transfer of ownership merely because a contribution is registered.

Pool allocations must be deterministic and evidence-backed. The protocol takes no automatic cut.

## Relationship to existing v3.4.3 components

This constitution reinforces, rather than replaces:

- the existing Data Economic Sovereignty doctrine;
- the issuer-neutral EEP exchange;
- the Economic Participation Profile;
- the Rights Passport;
- the Global Passport;
- the participant Economic Wallet;
- the DCO Factory;
- the passport-first production pipeline.

No protocol version change is required.
