# ENTITY Economic Wallet — v3.4.3 application layer

Date: 2026-10-02

ENTITY v3.4.3 now includes a repository-safe **economic wallet application layer** over the existing ENTITY Exchange Protocol (EEP) and Originator Participation Profile.

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
