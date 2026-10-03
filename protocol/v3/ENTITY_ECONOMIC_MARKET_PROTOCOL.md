# ENTITY Economic Market Protocol — Universal Instrument and Listing Registry

Status: v3.4.3 application/registry profile  
Date: 2026-10-03

## Purpose

ENTITY is a general-purpose digital asset economy. It is not a BTG-only marketplace.

Any valid ENTITY identity may control a DCO and, where its Rights Passport permits, issue an economic instrument against that DCO under the same protocol rules used by every other participant.

ENTITY owns the **protocol and registry rules**, not the assets listed through them.

## Universal market stack

```text
USER / ORGANIZATION / OTHER VALID ENTITY CONTROLLER
        ↓
ENTITY identity
        ↓
Owned / controlled DCO
        ↓
Rights Passport
        ↓
Global Passport / lineage / evidence
        ↓
Economic Instrument
        ↓
Instrument Registry
        ↓
Listing + Listing Information Sheet
        ↓
ENTITY-compatible Market / Venue
        ↓
Wallet-to-wallet trade
        ↓
Clearing / settlement / entitlement
        ↓
Economic lineage
```

The five universal market primitives are:

1. **Issuer**
2. **Instrument**
3. **Listing**
4. **Trade**
5. **Settlement**

EEP remains the execution, clearing, settlement and entitlement engine. This profile adds the universal issuer namespace, canonical instrument package, canonical listing package and buyer-facing disclosure layer above EEP.

## Issuer neutrality

BTG has no special structural market privilege.

Examples:

```text
shawn.blackmore.entity
└── btg.entity
    └── robotics.entity
        └── controller-001.entity

acme-corp.entity
└── ai.entity
    └── vision-model-07.entity

jane.smith.entity
└── photography.entity
    └── collection-2026.entity
```

These are examples of participant/domain/asset structures. Protocol-origin ancestry remains distinct from participant asset provenance and control.

## Issuer namespaces

Every issuer may register one signed market namespace alias derived from or chosen for its ENTITY identity.

Examples:

```text
BTG
ACME
JSMITH
```

A namespace is a convenience alias only. It is never authority.

The canonical issuer remains the cryptographic ENTITY ID.

A namespace is unique in one registry. If a preferred alias is already held by another verified issuer, a collision-safe alias is allocated.

## Instrument identity

A human-readable market symbol is not globally authoritative.

Example:

```text
Instrument Name:
Vision Model 07 Commercial Training Rights

Display Symbol:
VM07-TRN

Market Identifier:
ACME:VM07-TRN

Canonical Instrument ID:
entity.instrument:v1:<issuer-entity-id>:<underlying-dco-id>:training:000001
```

The three identity layers are:

```text
Friendly name
        ↓
Issuer namespace + display symbol
        ↓
Canonical immutable instrument ID
```

Two issuers may independently use the same display symbol. Resolution is issuer-scoped.

```text
ACME:SHARED-TRN
JSMITH:SHARED-TRN
```

These resolve to different canonical instrument IDs.

## Required instrument package

Every universal instrument package records at least:

- canonical instrument ID;
- issuer ENTITY ID;
- issuer namespace alias;
- underlying DCO ID;
- instrument name;
- display symbol;
- market identifier;
- EEP instrument class;
- rights class;
- series;
- fungibility;
- divisibility;
- supply;
- Rights Passport ID;
- Global Passport ID;
- jurisdiction;
- transfer rules;
- economic terms;
- royalty/participation terms;
- plain-language rights the buyer receives;
- plain-language rights the buyer does not receive;
- evidence references;
- creation time;
- current status;
- issuer signature.

The instrument package is not the underlying DCO and does not silently transfer ownership of the underlying asset.

## Listing separation

An instrument and a listing are different objects.

One instrument may be listed on more than one approved venue without creating a new instrument.

```text
DCO
   │
   └── Canonical Instrument
              │
              ├── ENTITY primary market
              ├── issuer private market
              └── partner marketplace
```

Each listing records at least:

- canonical listing ID;
- canonical instrument ID;
- venue ID;
- market ID;
- display symbol;
- quote unit;
- trade mode;
- settlement method;
- minimum quantity;
- quantity precision;
- price precision;
- pricing method;
- Listing Information Sheet hash;
- machine manifest hash;
- listing status;
- listing time;
- issuer/lister signature.

## Listing Information Sheet — REQUIRED

A buyer must not be expected to understand an instrument from a ticker alone.

Each listing therefore requires a buyer-facing **Listing Information Sheet** bound by hash to the canonical instrument and listing.

It must answer:

- What is this?
- Who is the issuer?
- What DCO is underneath it?
- What does the buyer receive?
- What does the buyer **not** receive?
- What actions are granted?
- What restrictions apply?
- Is commercial use permitted?
- Is AI training permitted?
- Are derivatives permitted?
- Is redistribution permitted?
- What is the supply?
- What is the divisibility?
- What pricing mechanism is being used?
- What royalties or participation obligations apply?
- What is the duration?
- What territory/jurisdiction applies?
- What transfer restrictions apply?
- Which Rights Passport applies?
- Which Global Passport applies?
- Which provenance/evidence references apply?
- What are the canonical instrument and listing IDs?
- What is the current status/version?

A prominent plain-language section must distinguish the underlying asset from the rights represented by the instrument.

Example:

```text
WHAT IS THIS?

VM07-TRN represents a defined commercial training right
associated with Vision Model 07.

Purchasing this instrument grants:
• the rights explicitly listed below

Purchasing this instrument does not grant:
• ownership of the underlying model
• copyright ownership
• unrestricted source redistribution
```

The Listing Information Sheet is disclosure. It does **not** substitute for the Rights Passport, Global Passport, canonical instrument record or governing terms.

## Portable publication

An instrument may be published anywhere while retaining exactly one canonical identity.

Approved publication surfaces may include:

- GitHub;
- project websites;
- API documentation;
- package metadata;
- research publications;
- product pages;
- contracts/invoices;
- QR codes;
- partner marketplaces.

External publication is a reference surface, not a minting surface.

A portable instrument package may contain:

```text
<symbol>.entity-instrument/
├── LISTING_INFORMATION.pdf
├── LISTING_INFORMATION.md
├── ENTITY_INSTRUMENT.md
├── entity-instrument.json
├── instrument.json
├── listing.json
├── rights-passport.json
├── global-passport.json
├── provenance.json
├── verification.json
└── SHA256SUMS
```

Rule:

> An instrument can be published anywhere, but it has one canonical instrument identity.

## Wallet issuance flow

The native wallet may expose:

```text
Create / ingest asset
        ↓
Create DCO
        ↓
Establish provenance + lineage
        ↓
Rights Passport
        ↓
Global Passport
        ↓
Create Economic Instrument
        ↓
Choose rights being offered
        ↓
Set supply / divisibility / transfer rules
        ↓
Create Listing Information Sheet
        ↓
Choose venue + price mechanism
        ↓
Create Listing
        ↓
LIST
```

Instrument creation and listing are always explicit controller actions. DCO ingest alone does not issue rights or create market value.

## Buyer inspection

Before purchase the wallet should expose:

- issuer;
- issuer ENTITY ID;
- market identifier;
- canonical instrument ID;
- underlying DCO;
- lineage;
- provenance;
- Rights Passport;
- Global Passport;
- rights granted;
- rights excluded;
- restrictions;
- supply/available quantity;
- price/bid/ask or pricing method;
- royalty/participation terms;
- jurisdiction;
- evidence;
- trade history.

## Trade flow

```text
BUY
 ↓
validate canonical instrument
 ↓
validate active listing
 ↓
validate buyer eligibility where required
 ↓
execute trade
 ↓
create clearing obligation
 ↓
settle payment-versus-right
 ↓
update entitlement balances
 ↓
apply bound royalty/participation rules
 ↓
generate signed ENTITY receipt
 ↓
append economic lineage
```

External payment truth remains evidence-bound. ENTITY does not claim money moved merely because a trade record exists.

## Invariants

1. ENTITY registry rules are issuer-neutral.
2. BTG is an issuer like any other issuer.
3. Symbol aliases are never authority.
4. Canonical instrument IDs are immutable.
5. One canonical instrument may have multiple listings.
6. Listings do not duplicate instruments.
7. Listing Information Sheets are required buyer-facing disclosures.
8. Rights Passports remain authoritative for rights semantics.
9. Protocol origin does not transfer asset ownership.
10. DCO creation does not create market value.
11. Instruments are optional after DCO creation.
12. Protocol tax remains 0.
13. Cryptocurrency is not required.
14. Venue operators do not become protocol or asset authority.
15. Historical signed economic records are preserved when withdrawn/superseded.


## Data Value Discovery

The canonical market identifier (for example `ACME:WX26-TRN`) is a human-readable measurement key. It is **not** the authoritative database key. All analytics resolve to the immutable `instrument_id`.

ENTITY may measure actual economic demand for each instrument from settled market activity:

- last settled price;
- 24-hour and 30-day settled volume;
- settled notional by currency;
- trade count;
- unique buyers and sellers;
- high/low settled price;
- active holder count;
- issuer inventory and open sell offers;
- settled and externally verified royalty/participation obligations;
- market-integrity indicators.

Open bids and asks are liquidity observations. They do **not** become price history, volume, realized demand or value merely because they exist.

For a DCO with several rights instruments, ENTITY keeps each right economically distinct:

```text
ACME:WX26-ACC   Access rights
ACME:WX26-QRY   Query rights
ACME:WX26-TRN   AI training rights
ACME:WX26-COM   Commercial-use rights
```

This allows ENTITY to observe whether demand is concentrated in access, query, training, commercial, derivative or other rights without assigning one arbitrary price to the underlying DCO.

### Rollups

Observed activity may roll upward through:

```text
instrument
   ↓
underlying DCO
   ↓
asset class / subtype
   ↓
primary domain / industry
   ↓
ENTITY economy
```

Rollups preserve currency boundaries. CAD, USD and other quote units are never summed into one synthetic value without a separately evidenced conversion method.

BTDU bindings may enrich semantic rollups across related assets, but BTDU topology does not create economic value, ownership or rights.

### Market-integrity safeguards

Raw volume is not proof of value. Economic intelligence therefore separates or flags:

- self-trade attempts;
- reciprocal counterparty flows;
- concentrated counterparty activity;
- unsettled executions;
- externally unverified settlement;
- related-wallet relationships only when explicit authorized relationship evidence exists.

ENTITY must not infer hidden relationships between wallets merely to strengthen a market metric.

### Valuation boundary

A settled price for a rights instrument means the market exchanged **that defined right under those terms** at that price.

It does not prove:

- intrinsic value of the underlying DCO;
- accounting fair value;
- enterprise value of the issuer;
- a universal price for all rights associated with the asset.

Data Value Discovery is therefore market evidence, not protocol-created value.
