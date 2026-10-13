# ENTITY DataChip Workspace + Capability Exchange — architecture v0.1

**Status: implemented graph compiler and isolated PySide6 wallet integration candidate; NOT a promoted wallet release.**

## Product change

ENTITY is no longer primarily a stock-style market for digital commodities. The primary user activity becomes *create, inspect, combine, qualify, license and deliver verifiable capabilities*. The legacy financial functions remain valid but optional.

ENTITY remains a sovereign system. It must allow open or internally controlled content reuse without requiring a DCO issuance, ticker symbol, market listing, wallet trade or cryptocurrency.

## Distinct objects — never conflate them

| Object | Authority | What it represents |
|---|---|---|
| Content DataChip (EDCF v0.2) | Exact SHA-256 bytes and pinned format | Portable reconstructed content, not automatically licensable or executable |
| Typed Module Interface | Declarative JSON; untrusted until independently qualified | Inputs/outputs, version, constraints, kind; not permission to execute |
| Assembly Draft | User-scoped deterministic JSON with checksum | Directed graph of connected interfaces; no authorization or execution |
| Compiled Assembly Plan | Canonical JSON + content digest | Dependency order and graph compatibility evidence only |
| Qualified Capability Release | **Future** signed application-host policy and native/sandbox proof | Potential deployable module requiring explicit platform/rights gates |
| Rights Passport / Usage Licence | Existing ENTITY ownership plus qualified live signer/revocation | Who may use, transfer, adapt, run or redistribute an asset |
| Exchange Listing | Existing bounded-rights market; future capability catalogue | Offer to license/deploy/buy approved bounded use without automatically selling underlying intellectual property |
| Economic Instrument / Treasury | Current DCO and exchange settlement | Optional tradable investment/usage rights with explicit issuer, payment and delivery |

A DataChip's content SHA does NOT identify its legal owner or give its user execution privileges. Dependency graph wires NEVER transfer legal rights.

## New wallet navigation

1. **Workspace** — recent chip drafts, library status, verified provenance and app integrations.
2. **Visual Composer** — typed drop-in nodes, connections, graph validation, read-only EDCF integrity import and deterministic export.
3. **Library / Digital Assets** — existing DCO assets, formula storage, passports, import, reconstruction and lineage.
4. **Rights Instruments** — existing economic instrument issuance and rights classes.
5. **Capability Exchange** — discover reusable modules and rights; existing ticker market retained as first compatibility view.
6. **Market Analytics** — optional valuation of rights (not an intrinsic asset price).
7. **Settlements** — existing authorization-and-payment-dependent delivery.
8. **Treasury** — existing market/economic overview.

Future capability-exchange listings should prioritize module name, interface contract, runtime/OS compatibility, rights classes, provenance, revocation state, supported platforms, security evidence and delivery policy. A ticker is optional for a financial instrument, not mandatory for any DataChip.

## Implemented Composer v0.1

- A bounded graph model (up to 128 nodes, 512 edges, 256 interfaces, 512KiB serialized draft).
- Versioned DataChip interface manifests with strictly typed named ports, only exact type matches and one incoming edge per input.
- Directed acyclic graph compiler; no cycle or unconnected required port accepted.
- Deterministic canonical JSON assembly plan with topological order and SHA-256.
- Local draft store scoped by active wallet entity string, separate from all economic, passport and BTDU DB files.
- Drag/drop PySide6 canvas with input/output port clicks, status/inspection, save/open, module import and plan export.
- Optional read-only EDCF archive import using ENTITY's independent formula verifier; imported archive can be represented as a content source; rights always remain unverified.
- All compilation outputs explicitly state no execution, no issuer trust, no rights, no trading, no deploy.
- Tests for malformed schema, invalid ports, cross-owner draft loading, tampering, path traversal, type mismatch, occupied ports, cycles, and illegal authority flags.

**Engineering honesty:** content checksums detect accidental modification but are not authenticated signatures. Wallet entity ID strings in local drafts are not login credentials; an authenticated host must enforce user identity before granting access. Interface manifests are not executable code. The v0.1 Composer does NOT implement a runtime, qualified deployment, real money transactions or arbitrary third-party code loading.

## Compatibility and non-destructive migration

- Preserve **all** existing Exchange, DCO, Wallet, Global Passport, BTDU formula, controller transfer, buyer activation and ledger tables; no schema changes or migrations in this phase.
- Do not rename, reset, relabel or reassign economic assets. Preserve historical ticker mappings for existing instruments.
- Move ticker/price-first UI behind "Capability Exchange" and "Treasury"; never price every content chip as a stock.
- Place Composer drafts exclusively under `<ENTITY_STATE>/wallet/composer/drafts` with canonical checksum and atomic saves.
- Maintain EDCF v0.2 as portable content identity and reuse its independently verified archive format. A Composer graph is a distinct manifest schema.
- A future signed *assembly release* needs pinned imports, trusted issuer, secure time, revocation, target host approvals, transactional activation/rollback, dependency hashes and audit receipts.
- Existing HikeAR/HuntAR consumers remain read-only and unchanged by this wallet/UI experiment.

## Next engineering gates

1. Verify and package the PySide6 candidate EXE in an **isolated** preview state; run real UI interaction tests and check drag/drop on a Windows desktop.
2. Connect the Composer catalogue to wallet-owned DCOs and actual verified EDCF archives using authenticated Passport and file/BTDU source resolvers, keeping a separate right-check call for every execution.
3. Support capability interface contracts and policy-restricted sandbox runtimes (WebAssembly/native host), with code-signing/ABI compatibility gates.
4. Create discoverable, licence-first Capability Exchange listings and conditional materialization/delivery receipts. No synthetic issuer keys for production transactions.
5. Perform DB backups, regression, explicit wallet-user migration and signed Windows EXE qualification before promoting over the existing ENTITY Wallet.

**This staged implementation is a first working Composer and wallet UI refactor; it is not the final universal application builder.**
