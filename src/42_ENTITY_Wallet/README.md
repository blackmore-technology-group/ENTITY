# ENTITY Economic Wallet

The ENTITY Economic Wallet is a v3.4.3 application layer over the existing ENTITY Exchange Protocol and Economic Participation state.

It supports two presentation roles:

- **Participant Wallet** — positions, entitlements, orders, usage, obligations and observed market information for an ENTITY identity.
- **Treasury Wallet** — the same position view plus treasury reserve allocations, participation policies and treasury economic events.

## Source-of-truth rule

The wallet does not create a second economic ledger.

Authoritative rights quantities come from EEP balances. Last price comes only from settled EEP trades. Orders supply bid/ask quotes. Entitlements, usage and economic obligations remain in their existing canonical stores.

The wallet's own SQLite database contains only wallet metadata and watchlists.

## Stock-style rules

The UI exposes familiar portfolio fields such as quantity, FIFO cost basis, last, bid, ask, indicative market value, realized change and unrealized change.

Offers do not create portfolio value. Unpriced positions remain unpriced.

"Stock-style" is a presentation model and does not assert a legal classification.

## Fiat boundary

The wallet does not custody fiat, has no protocol token requirement and stores no payment credentials. CAD/USD and other fiat may remain with a bank or payment provider while ENTITY records the economic rights, trade, obligation, settlement reference and evidence.

Invariants:

- `protocol_tax_bps = 0`
- `cryptocurrency_required = false`
- `wallet_does_not_custody_fiat = true`

See `docs/v3.4/ENTITY_WALLET_20261002.md` and the public qualification record under `docs/evidence/v3.4.3-entity-wallet-20261002/`.

## BTG provisioning

Use `tools/provision_btg_wallets.py` to bind the application layer to an explicitly supplied verified Blackmore Technology Group legal ENTITY and a distinct BTG Treasury ENTITY. The helper creates/reuses the treasury identity, provisions the existing treasury profile, creates both wallet roles and writes runtime snapshots outside the repository.

```bash
python tools/provision_btg_wallets.py --core . --state /path/to/entity/state --btg-entity ent2-...
```

Do not commit generated runtime wallet IDs, private identity material, wallet databases, bank/payment credentials or production snapshots.
