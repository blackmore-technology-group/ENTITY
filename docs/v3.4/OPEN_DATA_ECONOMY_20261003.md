# ENTITY Open Data Economy Application Layer

Date: 2026-10-03  
ENTITY display version: **3.4.3**  
Application profile: **ENTITY_OPEN_DATA_ECONOMY 1.0.0**

## What was corrected

The DCO Factory had begun to be framed as a BTG mass-production system.

The corrected architecture treats it as a universal issuance capability for any participant with legitimate authority over an asset.

BTG's first 100 assets remain valuable as seed inventory, but market scale is expected to come from unrelated people and organizations.

## 1. Create My DCO

`CreateMyDCOService` records a human-facing issuance plan for any caller-supplied issuer/controller identity.

It captures:

- asset name/class;
- content hash;
- provenance root;
- authority evidence hash;
- privacy profile;
- rights retained;
- rights offered;
- quantity;
- duration;
- jurisdiction;
- transferability;
- commercial-use and derivation bounds;
- raw-transfer permission;
- conditions and obligations.

The planner explicitly records:

- registration is not ownership;
- authority evidence is required;
- the underlying bytes do not need to move;
- rights are the economic object;
- no protocol tax;
- no mandatory cryptocurrency;
- no gas;
- no automatic BTG royalty;
- issuer neutrality;
- provider neutrality.

It intentionally creates a **draft plan**, not an ownership claim. Canonical registration/passports/instruments still occur through the existing ENTITY stores and the passport-first production pipeline.

## 2. My Data Portfolio

`ParticipantPortfolioView` transforms the existing participant Economic Wallet into a consumer-facing view.

It summarizes:

- rights held;
- rights currently offered;
- rights licensed/entitled;
- observed bid/ask/last;
- usage;
- receivables/payables;
- indicative portfolio observations.

Treasury is not the default consumer experience. A normal participant wallet is.

Unpriced positions remain unpriced and observed market value is not accounting fair value.

## 3. Open Data Rights Exchange search

`RightsMarketDiscovery` searches active EEP listings by desired **rights**, not preferred issuer.

Current searchable criteria include:

- required actions;
- commercial-use requirement;
- derivative-model requirement;
- raw-transfer requirement;
- region;
- asset/product family.

Results expose:

- active listing;
- instrument;
- issuer;
- rights;
- venue;
- supply;
- last settled trade;
- bid;
- ask.

Issuer is explicitly not a ranking factor.

Buyer actions are:

- BUY;
- BID;
- REQUEST QUOTE.

The search layer does not declare fair value or legal classification.

## 4. Data pools

`DataPoolManager` provides provider-neutral aggregation for many small contributors.

Each contribution retains:

- contributor identity;
- DCO reference;
- contribution reference;
- provenance hash;
- rights summary;
- deterministic weight units.

Revenue allocation uses deterministic integer largest-remainder allocation so the full externally evidenced gross amount is assigned exactly to contributors.

The pool:

- creates no ownership by registration;
- takes no protocol tax;
- creates no automatic BTG royalty;
- does not itself settle fiat.

## 5. Competitive optional service providers

`OptionalServiceProviderRegistry` supports competing providers for:

- market hosting;
- certification;
- verification;
- managed infrastructure;
- enterprise APIs;
- analytics;
- custody/connectivity;
- market data;
- specialized tooling.

BTG and competitors use the same registry. No provider can acquire protocol privilege through registration.

## Immediate operating priorities

The corrected application priority is:

1. maintain enough BTG seed DCOs to prove all market paths;
2. make **Create My DCO** usable by unrelated holders;
3. make **My Data Portfolio** the normal wallet experience;
4. make the **Data Rights Exchange** rights-searchable from the buyer side;
5. support contributor **Data Pools**;
6. prove unrelated participants can originate, buy, sell, hold and benefit without BTG controlling their assets.

## Scope boundary

This release is an application layer above current v3.4.3 protocol primitives.

It does not:

- change EEP classes;
- create a token;
- impose gas;
- impose a protocol tax;
- declare a DCO to be a security/commodity/share;
- transfer ownership merely by registration;
- make BTG a privileged issuer/provider.
