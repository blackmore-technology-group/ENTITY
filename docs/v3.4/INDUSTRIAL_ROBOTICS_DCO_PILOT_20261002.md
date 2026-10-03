# Industrial Robotics DCO Product Family — Controlled Prelaunch

Date: 2026-10-02  
ENTITY display version: **3.4.3**  
DCO: `DCO-BTG-ROBOTICS-DATASET-001`

## Status

The first Industrial Robotics DCO product family has been issued into an installed ENTITY v3.4.3 runtime and surfaced through the ENTITY Economic Wallet.

This is a **controlled prelaunch qualification**, not an external sale campaign.

The underlying pilot asset is a deterministic synthetic robotics telemetry dataset containing **10,000 records**. It exists to exercise the DCO → EEP instrument → treasury reserve → wallet path without pretending that the pilot corpus itself has established commercial value.

Dataset SHA-256:

`ee246c4af5380daf178d8a85112ba5ae22b6379345e2ecfa1307fb6dcf881563`

Dataset-manifest SHA-256:

`4b3eb8edaef0aa165481d257b2525caf1ee18dcb6e45bcc7d9a2bb996cd6e2da`

## Product family

| Product | Symbol | Supply | BTG Treasury reserve | Transferable | Illustrative reference price |
| --- | --- | ---: | ---: | --- | ---: |
| Inference-use rights | `BTG-RBT-INF` | 10,000 | 2,000 | No | CAD 250 |
| AI-training rights | `BTG-RBT-TRN` | 1,000 | 250 | No | CAD 10,000 |
| Commercial-derivative rights | `BTG-RBT-DER` | 100 | 30 | Yes | CAD 100,000 |
| Redistribution rights | `BTG-RBT-RED` | 50 | 0 | No | CAD 250,000 |
| Canada exclusive | `BTG-RBT-XCA` | 1 | 0 | No | CAD 1,500,000 |
| United States exclusive | `BTG-RBT-XUS` | 1 | 0 | No | CAD 1,500,000 |
| European Union exclusive | `BTG-RBT-XEU` | 1 | 0 | No | CAD 1,500,000 |
| United Kingdom exclusive | `BTG-RBT-XUK` | 1 | 0 | No | CAD 1,500,000 |
| Japan exclusive | `BTG-RBT-XJP` | 1 | 0 | No | CAD 1,500,000 |
| South Korea exclusive | `BTG-RBT-XKR` | 1 | 0 | No | CAD 1,500,000 |
| Australia / New Zealand exclusive | `BTG-RBT-XANZ` | 1 | 0 | No | CAD 1,500,000 |
| India exclusive | `BTG-RBT-XIN` | 1 | 0 | No | CAD 1,500,000 |
| Defined Middle East exclusive | `BTG-RBT-XME` | 1 | 0 | No | CAD 1,500,000 |
| Defined Latin America exclusive | `BTG-RBT-XLAT` | 1 | 0 | No | CAD 1,500,000 |

Total issued rights units: **11,160**.

Actual rights transferred from the BTG issuer position into the distinct BTG Treasury ENTITY: **2,280 units**.

Issuer units remaining after reserve allocation: **8,880**.

## What was actually exercised

The qualification created:

- one governed DCO underlying object;
- fourteen EEP instruments;
- fourteen signed disclosures;
- fourteen active listings;
- three treasury reserve positions;
- fourteen new participant-wallet positions;
- three new treasury-wallet positions.

All fourteen instruments reference the same DCO underlying object.

The ten regional-exclusive instruments passed the deployment uniqueness check for the configured exclusivity class and territory.

## What was deliberately not activated

The prelaunch created:

- **0 orders**;
- **0 trades**;
- **0 market marks**.

The earlier example prices remain **illustrative reference prices**. They are not live asks, settled prices, accounting fair values or evidence of DCO value.

Illustrative royalty/participation examples have not been converted into contractual basis-point obligations.

External-sale activation remains a separate controlled step.

## Wallet result

The ENTITY Economic Wallet now displays the issued rights as positions.

The BTG Treasury Wallet holds the actual reserve balances for:

- `BTG-RBT-INF` — 2,000 units;
- `BTG-RBT-TRN` — 250 units;
- `BTG-RBT-DER` — 30 units.

These positions are intentionally **unpriced** because no qualifying settled trade has occurred.

This preserves the wallet rule that an issuer cannot manufacture market value simply by issuing units or publishing an illustrative price.

## Integrity

Post-issuance SQLite `quick_check` returned `ok` for:

- Universal Transaction Fabric;
- ENTITY Exchange Protocol state;
- Economic Participation state;
- ENTITY Wallet state.

## Economic boundaries

The deployment retains:

- external bank/payment-provider fiat custody;
- `cryptocurrency_required = false`;
- `protocol_tax_bps = 0`;
- no automatic legal/securities classification;
- no inference that a listing equals a sale;
- no inference that an illustrative price equals market value.

The next activation stage is to convert selected prelaunch instruments into deliberately approved live offers, then exercise primary trade, clearing, settlement evidence, entitlement delivery and later secondary/derivative economic paths.
