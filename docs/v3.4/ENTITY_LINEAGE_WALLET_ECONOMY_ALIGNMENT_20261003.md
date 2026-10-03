# ENTITY Lineage, Wallet, DCO and Economy Alignment

Date: 2026-10-03  
ENTITY release: v3.4.3  
Status: canonical application-layer alignment

## 1. The lineage model

ENTITY has two independent lineage planes. They must never be collapsed.

### 1.1 Protocol and domain lineage

The canonical ENTITY protocol ancestry is:

```text
Shawn Blackmore
  ↓  FOUNDER_ORIGINATOR_CONTEXT
Blackmore Technology Group Limited
  ↓  PROTOCOL_STEWARDSHIP
ENTITY
  ↓  signed release origin
ENTITY v3.4.3
  ↓  ENTITY-issued domain profile
Robotics
```

The canonical origin identifier is:

`entity-origin:shawn-btg-entity@1.0`

This lineage identifies protocol origin and domain context. It does **not** transfer ownership of a user's data or asset to Shawn, BTG, ENTITY, or a profile.

A Global Passport for a Robotics asset must therefore carry both:

- a verified protocol-origin binding to the canonical ENTITY release; and
- `entity-profile:robotics@1.0` in its resolved profile stack.

### 1.2 Profile composition is not parent/child lineage

Robotics assets may also compose profiles such as AI or Manufacturing:

```text
Primary domain: Robotics
Composed profiles: AI, Manufacturing
```

The wallet must not render this as:

`Robotics → AI → Manufacturing`

because those are composed profiles, not ancestry edges.

### 1.3 Asset provenance and control

Asset provenance is separate:

```text
BTG
  ↓ creates / controls
DCO-000001 BIRFR-1
  ↓ trained/derived relationship
DCO-000002 Failure Detection Engine
```

For another participant, that same asset plane may instead begin with that participant's ENTITY identity.

Protocol origin does not infer asset ownership. Asset provenance does not redefine protocol origin.

## 2. ENTITY, ADAM, NIKI and BTDU

The system roles remain:

- **ENTITY** — sovereign identity, authority, rights, policy, economic semantics and protocol origin.
- **ADAM** — deterministic governed execution, state transition and evidence substrate.
- **NIKI** — bounded reasoning and proposals. NIKI does not acquire sovereign authority merely by reasoning about an asset.
- **BTDU** — governed information topology and exact/semantic representation over ADAM. BTDU topology cannot create ownership, rights, royalties or economic entitlement.

For wallet display, ADAM, NIKI and BTDU are capability/evidence bindings, not ownership ancestors.

## 3. Canonical Digital Commodity ingest

The desktop wallet must use the same canonical v3.4.3 stack as the deployment CLI.

```text
SELECT / CREATE ASSET
        ↓
verify controller identity
        ↓
verify v3.4.3 release-origin attestation
        ↓
BTDU signed ingest + content hash
        ↓
register asset as DCO in Universal Transaction Fabric
        ↓
issue evidence
        ↓
grant controller rights
        ↓
issue Rights Passport
        ↓
resolve Global + domain profiles
        ↓
issue Global Passport
        ↓
embed protocol origin
        ↓
bind BTDU reference
        ↓
record zero POTENTIAL economic state
        ↓
MY DIGITAL ASSETS
```

Ingest must not automatically create:

- an EEP instrument;
- a licence;
- a market listing;
- an ask price;
- a market value;
- an originator royalty;
- a protocol fee.

The DCO is the governed digital commodity asset. Market rights are optional economic instruments created later by explicit controller action.

## 4. Wallet separation

The native wallet has two economically different holdings surfaces.

### My Digital Assets

Shows DCOs controlled by the wallet identity.

Each asset can display:

- title and content hash;
- real object type;
- commodity class;
- controller;
- canonical protocol/domain lineage;
- asset provenance parents;
- current Global Passport;
- BTDU binding state;
- whether the passport embeds current protocol origin.

### Market Positions

Shows EEP rights units that the participant owns or holds.

A market position is not the underlying DCO.

## 5. Economy

The original market lifecycle remains:

```text
DCO
 → optional EEP instrument
 → listing / disclosure
 → order, RFQ or auction
 → price discovery
 → trade
 → clearing
 → settlement
 → entitlement
 → usage
 → derived output
 → economic consequence
```

The exchange continues to use actual orders and settled trades for market observations.

Registration of a DCO does not establish market value. An offer does not establish realized value. Protocol tax remains zero and cryptocurrency is not required.

## 6. Robotics correction

The production Robotics assets are retained as the same signed objects.

- **DCO-000001 — BIRFR-1** remains the BTG-controlled Robotics failure/recovery dataset.
- **DCO-000002 — Blackmore Real-Time Failure Detection Engine** remains the BTG-created Robotics algorithm derived from DCO-000001.

Their historical Global Passport v1.0 records are preserved.

Lineage-complete Global Passport v1.1 records now bind each asset to:

- `entity-origin:shawn-btg-entity@1.0`;
- `entity-release:v3.4.3`;
- Global + Robotics + AI + Manufacturing profiles;
- the existing BTDU binding;
- the existing BTG controller and Rights Passport.

The wallet renders the primary protocol/domain path as:

`Shawn Blackmore → Blackmore Technology Group Limited → ENTITY → Robotics`

AI and Manufacturing are shown as composed profiles.

DCO-000003 is not promoted to the production asset registry while its qualification remains failed.

## 7. v3.4.3 release-origin repair

The v3.4.3 release originally lacked the post-tag `ENTITY_CURRENT_RELEASE_ORIGIN.json` sidecar required by the canonical v3.4.3 ingest path.

A signed post-tag attestation was generated with the existing canonical ENTITY protocol identity and verified against:

- release tag: `v3.4.3`
- commit: `528b70aabd05b1e930b77e4933f157731e47274f`
- tree: `f13e42f515dcc4cd985e9b832e0ecfec416ce423`
- origin lineage: `entity-origin:shawn-btg-entity@1.0`

The attestation does not contain private key material.

## 8. Locked invariants for Robotics 3 and later

Future Robotics assets must:

1. be built and qualified as actual assets before economic issuance;
2. retain their real asset type (SOFTWARE, MODEL, DATASET, DEVICE, etc.);
3. enter ENTITY through the canonical origin/passport/BTDU path;
4. use Robotics as the primary domain profile where applicable;
5. preserve explicit asset-to-asset provenance for derivations;
6. keep NIKI, ADAM and BTDU roles separate from ownership;
7. create market instruments only by explicit controller choice;
8. never invent value from registration or an asking price;
9. preserve historical signed records rather than rewriting them;
10. fail closed when required origin, identity, rights, evidence or qualification is missing.

This alignment is an application/runtime correction. It does not require a new ENTITY protocol version.


## 9. Universal issuer-neutral market

The corrected economy is not a BTG market implementation.

Any valid ENTITY controller may create a DCO under its own asset lineage and explicitly issue bounded economic rights under the same registry rules.

```text
ENTITY identity
  ↓
controlled DCO
  ↓
Rights Passport
  ↓
Global Passport / provenance
  ↓
optional canonical instrument
  ↓
optional listing
  ↓
venue-neutral EEP execution and settlement
```

BTG receives no hidden namespace, fee, market, settlement or ownership privilege.

Human symbols such as `BTG:BRC22-COM`, `ACME:VM07-TRN` or `JSMITH:PHOTO26-COM` are signed issuer-scoped aliases. The immutable canonical instrument ID is authoritative.

Instrument identity and listing identity are separate so the same canonical instrument may be published or listed through more than one approved venue.

Every new universal listing requires a Listing Information Sheet and machine listing manifest bound to the canonical instrument, DCO, issuer, Rights Passport and Global Passport.

Portable packages may be published on GitHub, websites, documentation or partner surfaces without creating duplicate instruments.

## 10. Data Value Discovery

Market identifiers become useful human measurement keys while analytics remain keyed by canonical `instrument_id`.

ENTITY may measure settled activity for each bounded rights instrument, including:

- last settled price;
- 24-hour / 30-day volume;
- unique buyers;
- trade count;
- high / low;
- active holders;
- circulating supply;
- externally verified settlement activity;
- royalties and participation actually settled.

These observations may roll upward from instrument to DCO, rights class, asset class and primary domain where explicit passport/DCO classification supports the relationship.

The wallet exposes a Data Value Discovery surface while preserving the boundary that instrument-rights prices do not establish intrinsic or accounting value for the entire underlying DCO.

Market-integrity flags include self-trading, reciprocal flows and counterparty concentration. Related-wallet detection requires authorized relationship evidence and is not inferred from identity similarity.

## 11. Robotics prelaunch economic cleanup

The three historical robotics issuance campaigns were audited before cleanup planning:

- synthetic robotics economic pilot: 21 instruments;
- DCO-000001 BIRFR-1: 20 instruments;
- DCO-000002 Failure Detection Engine: 16 instruments.

The 57 instruments were prelaunch economic experiments. The production audit found no orders, trades, clearing, buyer entitlements or usage. Non-issuer balances were internal BTG treasury reserve allocations, not external holders.

Because EEP 3.0 is already a qualified protocol component, instrument withdrawal is **not** being introduced as a new EEP signed-wire primitive merely to clean this application state.

Instead, an application-layer fail-closed migration:

1. verifies zero market/economic activity;
2. verifies every non-issuer balance is an exact internal issuer-owned treasury reserve;
3. preserves all signed historical rows;
4. marks unused instruments/listings withdrawn;
5. returns internal reserve units to the issuer;
6. supersedes the associated EOPP participation policies;
7. records DCO Factory issuance withdrawals;
8. leaves the underlying DCO assets active;
9. creates signed migration evidence and backups.

If any real market history or unexplained holder exists, the migration refuses to run.

This preserves EEP 3.0 conformance and economic history while removing the abandoned licence-oriented robotics direction from active state.
