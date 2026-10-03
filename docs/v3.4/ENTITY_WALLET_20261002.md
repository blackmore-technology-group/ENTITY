# ENTITY Economic Wallet — v3.4.3 application layer

Status: **implemented / locally qualified / protocol version unchanged**

ENTITY v3.4.3 now includes a stock-style economic wallet application layer over the existing ENTITY Exchange Protocol (EEP), originator-participation profile and settlement records.

The wallet is **not a cryptocurrency wallet**, does not create a protocol token, and does not take custody of fiat currency. CAD, USD and other external money remain at a bank, payment service or other external settlement provider. ENTITY records the economic rights, signed market activity, obligations, external-payment evidence and settlement state.

## Two wallet roles

### Participant Wallet

A Participant Wallet is a portfolio view for an ENTITY identity. It presents:

- EEP rights-unit positions;
- instrument rights and transferability;
- entitlements and expiries;
- usage records;
- open buy/sell orders;
- last settled trade;
- bid and ask quotes;
- FIFO settled-trade cost basis when reconstructable;
- realized and unrealized change when evidence is complete;
- receivables and payables created by ENTITY economic events.

### Treasury Wallet

A Treasury Wallet binds to the separate ENTITY Treasury identity required by the existing BTG treasury deployment profile. It adds:

- treasury reserve rights positions;
- participation policies;
- reserve allocations;
- primary-issuance participation;
- secondary-transfer participation;
- derivative participation;
- service-revenue events;
- economic obligations and settlement status.

The treasury identity remains distinct from the BTG legal ENTITY.

## Stock-style presentation, not legal classification

"Stock-style" describes the portfolio and market interface:

```text
Instrument
Quantity
Cost basis
Last settled price
Bid
Ask
Indicative market value
Realized change
Unrealized change
Orders / offers
Activity
```

The wallet does **not** declare DCO/EEP rights to be corporate shares, securities, commodities, derivatives or any other legal/accounting classification. Those classifications remain outside protocol inference.

## Authoritative-state boundary

The wallet does not create a second economic ledger.

EEP remains authoritative for:

- balances;
- instruments;
- entitlements;
- orders;
- trades;
- usage;
- clearing.

The Originator Participation Profile remains authoritative for:

- treasuries;
- participation policies;
- reserve allocations;
- economic events;
- obligations.

The wallet database stores wallet configuration and watch-list data only. A wallet record is not signing authority and does not create ownership or entitlement. ENTITY/EEP signatures remain the canonical authority path for transactions.

## Market-value boundary

A sell offer is not market value. A bid is not market value. An issuer-selected offer price is not realized value.

The wallet uses the **latest settled ENTITY trade** as the observed price source for an indicative position mark.

If no settled trade exists, the position remains **unpriced**.

```text
offer / ask ──► quote only
bid         ──► quote only

settled trade
      │
      ▼
observed last price
      │
      ▼
quantity × last price
      │
      ▼
indicative portfolio mark
```

Every wallet snapshot labels these values:

- indicative only;
- not accounting fair value;
- not protocol-generated value.

## Fiat and payment custody

The wallet reports:

```text
fiat_custody = EXTERNAL_BANK_OR_PAYMENT_SERVICE
wallet_cash_balance = null
wallet_does_not_custody_fiat = true
payment_credentials_stored = false
cryptocurrency_required = false
protocol_tax_bps = 0
```

External money movement is evidenced through the existing ENTITY settlement/payment-attestation path rather than represented as fictitious wallet cash.

## DCO economy use

A single DCO can support multiple rights instruments while the underlying information remains one governed object.

Example:

```text
Industrial Robotics Dataset DCO
├── inference rights
├── AI-training rights
├── commercial-derivative rights
├── redistribution rights
└── regional-exclusive rights
```

Those instruments can appear in Participant and Treasury Wallets as positions while preserving their separate terms, quantities, duration, transferability, participation policies and settlement currency.

## Reference implementation

Core:

`src/42_ENTITY_Wallet/canonical_wallet.py`

CLI:

`tools/entity_wallet.py`

BTG deployment helper:

`tools/provision_btg_wallets.py`

Tests:

`tests/test_entity_wallet.py`

Example snapshot:

```bash
python tools/entity_wallet.py \
  --core . \
  --state /path/to/entity/state \
  --wallet-id wallet3-example \
  --html-out wallet.html
```

BTG deployment requires an explicitly supplied, verified Blackmore Technology Group legal ENTITY ID:

```bash
python tools/provision_btg_wallets.py \
  --core . \
  --state /path/to/entity/state \
  --btg-entity ent2-...
```

The helper does not infer a personal/test identity as BTG and keeps the Treasury ENTITY distinct.

## Qualification

The installed implementation was exercised together with the existing v3 economic-participation tests:

- wallet tests: **3/3 PASS**;
- combined wallet + existing economic-participation tests: **27/27 PASS**.

The production deployment confirmed that the Participant Wallet reads pre-existing EEP rights positions without copying them into a second ledger. The newly provisioned Treasury Wallet begins with no reserve positions until an explicit participation policy and reserve allocation are created.

No live SQLite databases, wallet snapshots, production identity keys, payment credentials or bank information are published in the repository.

## Version boundary

This is an application-layer addition to **ENTITY v3.4.3**. It does not change the EEP wire schemas, DCO model, settlement model or protocol tax invariant, so no ENTITY version bump is required.
