# ENTITY Economic Wallet — v3.4.3 application layer

Date: 2026-10-02

ENTITY v3.4.3 now includes a repository-safe **economic wallet application layer** over the Universal Transaction Fabric, ENTITY Exchange Protocol (EEP) and Originator Participation Profile. The wallet treats controller-held Digital Commodity Objects as first-class assets, independently from any later market instruments.

This addition does **not** change the ENTITY protocol version, the EEP wire schema, the BTDU schema, or the no-token/no-protocol-tax model.

## Two wallet roles

The wallet engine supports:

1. **Participant Wallet** — bound to an ENTITY identity and presenting its EEP rights positions, entitlements, orders, usage, obligations and observed market information.
2. **Treasury Wallet** — bound to a distinct treasury ENTITY and presenting treasury reserve rights, participation policies, economic events, receivables/payables and the same market-position view.

The wallet metadata database is a presentation/application layer. Authoritative economic state remains in the existing EEP and Economic Participation databases.

## Stock-style portfolio model

"Stock-style" means the interface uses familiar portfolio concepts:

- instrument;
- quantity;
- FIFO cost basis from settled trades;
- last settled trade;
- current bid;
- current ask;
- indicative market value;
- realized change;
- unrealized change;
- open orders/offers;
- entitlements;
- usage;
- receivables and payables.

It does **not** mean ENTITY declares a DCO right, entitlement, licence or other instrument to be a corporate share, security, commodity, derivative or any other legal classification. Legal, securities, tax and accounting classification remain outside protocol inference.

## Market-value integrity

The wallet deliberately separates:

- **last settled trade** — may provide an indicative market mark;
- **bid/ask** — displayed as quotes;
- **offers** — do not create portfolio value;
- **unpriced positions** — remain unpriced.

An issuer therefore cannot create a portfolio valuation merely by publishing an arbitrary ask price.

Indicative market values are expressly not accounting fair value and are not protocol-generated value.

## Fiat and payments

The ENTITY wallet is not a bank account and does not require cryptocurrency.

The wallet records no fiat cash balance and stores no bank/payment credentials. CAD, USD and other external currencies remain in a bank or payment service. ENTITY records the instrument, trade, obligation, settlement reference and verification evidence.

Invariants retained:

- `protocol_tax_bps = 0`
- `cryptocurrency_required = false`
- `wallet_does_not_custody_fiat = true`

## Treasury separation

A production treasury should continue to use a distinct ENTITY identity from the legal/operating originator. The wallet does not weaken the treasury deployment requirements.

Treasury reserve units remain actual EEP rights positions. Contractual primary allocations, secondary royalties, derivative participation and service revenue remain issuer-defined disclosed terms rather than protocol privilege.

## BTG deployment helper

The repository includes `tools/provision_btg_wallets.py` to create or reuse the distinct BTG Treasury ENTITY, provision the existing BTG treasury profile, create Participant and Treasury Wallet metadata, and render stock-style JSON/HTML snapshots.

The helper intentionally requires the verified Blackmore Technology Group legal ENTITY ID as an explicit argument. It does not infer Shawn Blackmore's personal ENTITY, a test ENTITY, or any legacy identifier as the corporate originator.

Example:

```bash
python tools/provision_btg_wallets.py \
  --core . \
  --state /path/to/entity/state \
  --btg-entity ent2-...
```

An existing distinct treasury identity can be supplied with `--treasury-entity`. When omitted, the helper reuses an existing manifest named `Blackmore Technology Group ENTITY Treasury` or creates one.

The helper writes deployment artifacts only to the supplied runtime state/output directory. Production wallet IDs, treasury identifiers, private identity material and generated snapshots are operational state and must not be committed to the repository.

## Qualification

The wallet-specific unit campaign passed **3/3**.

The installed wallet tests were then run together with the existing v3 economic-participation suite and passed **27/27**.

The qualification covers:

- participant position rendering;
- FIFO basis and realized/unrealized calculations from settled trades;
- last/bid/ask separation;
- unpriced positions remaining unpriced;
- offer prices not manufacturing portfolio value;
- usage and entitlement visibility;
- receivable/payable visibility;
- treasury-wallet binding;
- external fiat custody boundary;
- no token balance;
- zero protocol tax;
- compatibility with the existing economic-participation tests.

## Repository boundary

This repository publishes generic wallet source, tooling, tests and qualification evidence only.

It does **not** publish production wallet databases, live wallet IDs, treasury identity material, private signing/recovery keys, local launchers, payment credentials, runtime SQLite state, bank details, production snapshots or other private operational state.


## Native desktop wallet and asset ingest

The canonical user experience is now a native desktop application, not a generated HTML page. The source entry point is `tools/entity_wallet_desktop.py`.

The native wallet provides:

- **My Digital Assets** — controller-held DCOs from the Universal Transaction Fabric;
- **Upload / Ingest Digital Asset** — select a local file, hash it, copy it into the local wallet vault and register it as a DCO;
- **Market** — live instrument bid/ask/last observations and signed Buy/Sell order submission;
- **Market Positions** — rights positions kept separate from the underlying assets;
- **Orders** — active/recent exchange orders.

Asset ingest is deliberately non-economic by default:

`UPLOAD → SHA-256 → LOCAL VAULT → DCO REGISTRATION → MY DIGITAL ASSETS`

It does **not** automatically create an EEP instrument, licence, listing, ask price or market value. The controller may later choose to create standardized tradeable rights.

Cross-platform build tooling is provided by `tools/build_entity_wallet_desktop.py` and the `ENTITY Wallet Desktop` workflow for Windows, macOS and Linux.


## ENTITY Data Economy Terminal redesign — 2026-10-03

The native wallet is implemented with **PySide6/Qt**, replacing the earlier utility-style Tkinter presentation.

The desktop experience is organized as a data-economy terminal:

- **Overview** — sovereign portfolio state, market tape, asset holdings and settled rights-market activity;
- **Digital Assets** — first-class DCO holdings with lineage, passports, BTDU status and explicit `NO TICKER` state when no instrument exists;
- **Instruments** — canonical issuer-scoped economic instruments with ticker/market identifier, rights class, supply and underlying DCO;
- **ENTITY Market** — universal multi-issuer listings with ticker, issuer, rights, bid/ask/last, settled volume, buyers, holders and integrity flags;
- **Economic Intelligence** — settlement-aware Data Value Discovery by instrument and asset class;
- **Orders** — exchange instructions kept distinct from assets and positions.

Ticker behavior is intentionally strict:

DCO → optional economic instrument → issuer namespace + display symbol → ticker/market identifier

A DCO without an issued economic instrument displays `NO TICKER`. The wallet does not manufacture a ticker or price merely because an asset exists.

Before first issuance the wallet may display a collision-checked **suggested issuer namespace** such as `BTG`, marked `RESERVED ON ISSUE`. The alias is not authority and is not persisted until an issuer explicitly creates an instrument. Canonical instrument identity remains the immutable instrument_id.

The header exposes canonical origin context separately from asset provenance:

Shawn Blackmore → Blackmore Technology Group Limited → ENTITY

Domain lineage such as `Robotics` comes from the asset Global Passport/profile stack. AI and Manufacturing remain composed profiles rather than false parent-child lineage nodes.

The PySide6 build continues to preserve:

- protocol tax = 0;
- no cryptocurrency requirement;
- external settlement evidence boundary;
- asset registration does not issue instruments;
- instrument issuance does not automatically create a listing;
- listing/market activity does not imply intrinsic DCO value;
- BTDU, ADAM and NIKI do not create ownership.

The 2026-10-03 desktop/economy/lineage regression campaign passed **84/84** before the Qt package was built. The packaged Windows executable then passed a production-state frozen-runtime self-test with exit code 0.


## Signed Asset Disclosure and Listing Information Sheet v2 — 2026-10-03

A market listing now requires a **signed, versioned Asset Disclosure** for the underlying DCO. The disclosure belongs to the asset, not to a ticker, and can therefore support multiple economic instruments without duplicating the buyer-facing description.

The production path is:

DCO → signed Asset Disclosure → Rights Passport / Global Passport → Economic Instrument → Listing → Listing Information Sheet v2

The Asset Disclosure supports:

- detailed asset description;
- purpose / problem addressed;
- key capabilities;
- included content or components;
- intended uses;
- known limitations and exclusions;
- dependencies / prerequisites;
- validation and qualification notes;
- release/version notes;
- supporting source references.

Issuer-authored disclosure fields are signed issuer statements. ENTITY records and verifies the statement but does not convert it into objective truth or independent certification. Publishing an Asset Disclosure does not expand a Rights Passport and does not create economic value.

The Listing Information Sheet v2 snapshots the current signed Asset Disclosure and combines it with canonical DCO facts from the asset record and Global Passport, including DCO ID/code, version, object type, commodity class, measurement unit, content hash, controller, jurisdiction profiles, canonical technical metadata, industry context, profile stack, standards mappings, validation/maturity flags, provenance edges and references, evidence references, BTDU binding, rights terms, market terms and the market-value boundary.

A later Asset Disclosure update does not silently rewrite an already-created listing sheet; the listing retains the disclosure/dossier hashes that were shown to the buyer.

Portable instrument packages now include `asset-dossier.json` and, when present, `asset-disclosure.json` in addition to the human Listing Information PDF/Markdown and existing canonical manifests/passports.

The wallet shows Asset Information status directly in the DCO portfolio. A DCO without a signed disclosure is marked **REQUIRED TO LIST**. The two current Robotics DCOs were issued signed Asset Disclosure v1 records using facts already present in their canonical records; no new performance claims were inferred.


## Universal first-run identity and lineage onboarding — 2026-10-03

The desktop wallet no longer assumes a BTG identity on a clean installation. A first-run setup now creates or adopts a sovereign principal ENTITY, claims a human-readable `.entity` public name, optionally creates an operating organization/business/project beneath the principal, creates or adopts a separate Device ENTITY, records explicit lineage/device relationships, creates the wallet, and authenticates through a device-bound signing-key challenge.

The wallet header now resolves the active user's lineage dynamically. For the migrated BTG installation it displays `shawn.blackmore.entity → btg.entity`; another user receives their own lineage with no BTG-specific structural privilege.

Device information may bootstrap only a system/device identity. It must never silently create a human or organization identity. Public names remain aliases; immutable Entity IDs and signatures remain authoritative. Protocol origin remains separate from user lineage and user-asset ownership.

See `docs/v3.4/ENTITY_WALLET_IDENTITY_ONBOARDING.md` for the complete first-run and login model.


## Rights-Passport-driven instrument issuance — 2026-10-03

The desktop wallet no longer defaults every new economic instrument to `COMMERCIALIZE`. Instrument issuance now reads the selected DCO's current Rights Passport and presents only actions with an explicit `ALLOW` effect as selectable economic rights.

Rules:

- the Rights Passport is the maximum authority boundary;
- the instrument may contain only a subset of currently allowed Rights Passport actions;
- prohibited actions are shown as prohibited and cannot be selected;
- non-ALLOW/non-PROHIBIT actions are shown separately and are not directly issuable;
- the backend re-validates the selected actions immediately before canonical instrument creation;
- the canonical market registry remains the final enforcement layer and rejects any instrument whose actions exceed the Rights Passport;
- ticker/right-class/name suggestions are derived from the selected authorized actions rather than a generic commercial-right default;
- canonical asset short names are preferred for ticker suggestions where present (for example, BIRFR-1 training rights suggest `BIRFR1-TRN`).

Production verification confirmed that BIRFR-1 exposes its allowed actions (BENCHMARK, CERTIFY, COMPUTE, DERIVE, EVALUATE, FINE_TUNE, INFER, OEM_DEPLOY, TRAIN) and does not expose COMMERCIALIZE, while the Blackmore Real-Time Failure Detection Engine does expose COMMERCIALIZE because that action is present in its Rights Passport.

The complete wallet/economy/lineage/onboarding/market qualification campaign passed **89/89** after this change. The installed Windows executable then passed its frozen-runtime production self-test.


## Rights-Passport-driven instrument issuance and Software Engineering domain — 2026-10-03

Economic instrument issuance in the desktop wallet is now driven by the selected DCO's current Rights Passport. The wallet no longer defaults every asset to `COMMERCIALIZE`. It loads the active Rights Passport, presents only `ALLOW` actions as selectable instrument rights, displays prohibited/non-directly-issuable actions separately, validates the selected subset again at issuance, and derives the suggested rights class / ticker suffix from the selected actions. The canonical market validator remains the final fail-closed enforcement boundary.

Example: BIRFR-1 currently exposes BENCHMARK, CERTIFY, COMPUTE, DERIVE, EVALUATE, FINE_TUNE, INFER, OEM_DEPLOY and TRAIN. `COMMERCIALIZE` is therefore not offered for BIRFR-1. Selecting TRAIN suggests `BIRFR1-TRN` and the TRAINING rights class. DCO-000002 separately allows COMMERCIALIZE because its Rights Passport explicitly grants that action.

ENTITY now also includes a built-in `entity-profile:software-engineering@1.0` domain/profile and a `software-engineering` implementation package. This domain supports software repositories, source code, libraries, applications, algorithms, build artifacts, test evidence and engineering-control DCOs. It maps SPDX-3, CycloneDX and SLSA as non-normative interoperability mappings; the profile does not create authority or regulatory status.

Ten active legacy ENGINEERING_CONTROL DCOs that previously carried only the Global profile were migrated by issuing new immutable Global Passport versions with the Software Engineering profile. Existing passports remain preserved. The migration did not change DCO IDs, controllers, Rights Passport IDs/hashes, evidence, provenance or economic state. The wallet now resolves all 12 current BTG assets to explicit domains: 10 Software Engineering and 2 Robotics.

The Software Engineering profile is distributed as a pre-signed canonical profile record under `protocol/profiles`. Clean installations verify its `entity.entity` signature and import it at runtime; they do not mint or re-sign canonical profiles locally. This preserves the public-key-only trust boundary on new devices.
