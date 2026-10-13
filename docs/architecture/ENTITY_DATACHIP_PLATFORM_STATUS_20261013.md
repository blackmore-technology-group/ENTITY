# ENTITY DataChip platform — status and documentation lock (2026-10-13)

**Status: post-v3.4.3 engineering; not a protected release, certified production service, or Protocol 1.0 revision.** [Public guide](https://blackmore-technology-group.github.io/ENTITY-DOCS/datachips/).

## New architecture

1. **EDCF v0.2:** formula-native, independently verifiable DataChips containing exact content or bounded deterministic ATOM / ENTROPY / CONCAT / REPEAT / SLICE recipes, with irreducible entropy retained. Legacy portable `.edc` v0.1 is a different format.
2. **EDP:** bounded verification, reconstruction, dependency and optional separate shard-set packaging. SHA-256 content identity is not signer identity or legal title.
3. **Typed Universal Composer:** versioned ports, graph validation and assembly plans; draft plans are not executable native apps and do not issue permissions, financial instruments or trusted deployment receipts.
4. **Native host:** iOS/Android/Windows/Linux retains OS permissions, ARKit/Metal/camera/GPS, user consent, device enrollment, signed native code and secure sessions.
5. **Authority:** Rights Passports, issuer identity, authenticated current controller approval, scoped signed delegated grants, revocation, trusted keys, expiry and explicit export permission are separate, live checks. Signed test fixtures are not live authority.
6. **Wallet:** shift primary navigation toward Workspace, Composer, Library and Capability Exchange; retain all historical DCOs, ticker instruments, assets, authorized formula exports, market/treasury/settlement, and controller-transfer rights. Do not price every DataChip as stock.

## Engineering evidence versus release gate

| Surface | Built or tested | Still blocked |
| --- | --- | --- |
| Shared alignment | Exact EDCF v0.2 lock pinned across ENTITY, HuntAR and Command Centre | Independent production host interoperability and qualified deployment |
| Formula-native and signed rights | Bounded Python reference, native Rust/C/Swift candidate, synthetic signed grants and revocation checks, data-only atomic activation reference | Independent malicious-package review, all-OS CI, real KMS/HSM signer, secure time and hardware anti-rollback |
| Geography | 34 separately verified Boundary Country **QA** chips, source/archive parity checked off-device | Licensed geography, full physical iPhone 34-chip mount, authorized session, offline safety, real BSIE projection, map/HUD/NIKI |
| Wallet Composer | Typed non-executable graph and PySide6 UI candidate, controller-scoped read-only DCO references | Production wallet migration, authenticated chip delivery, qualified signed host/runtime |
| Live rights | Existing Rights Passport registry audited read-only; absent explicit EXPORT grants correctly deny export | Versioned explicit EXPORT policy (#155), issuer signing and fresh revocation publication |

A chip digest does not entitle a holder to export or run it, and a Composer wiring never conveys intellectual-property rights. Do not delete original source/entropy because a QA chip reconstructs once. Do not claim an approved mobile release without real-device evidence.

## Normative boundaries and links

- [Alignment lock v0.2](BTG_DATACHIP_ALIGNMENT_LOCK_V02.json)
- [Production gate checklist, dated 12 October](ENTITY_DATACHIP_PRODUCTION_GATES_20261012.md)
- [Native-host architecture v0.1, with current addendum](BTG_DATACHIP_APPLICATION_STANDARD_V0_1.md)
- [ENTITY Wallet/DataChip Workspace](../ENTITY_DATACHIP_WORKSPACE_ARCHITECTURE.md)
- [SDK and legacy-format distinction](../../sdk/datachip/README.md)
- [Rights-policy blocker #155](https://github.com/blackmore-technology-group/ENTITY/issues/155)
