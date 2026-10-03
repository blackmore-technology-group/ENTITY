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
