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
