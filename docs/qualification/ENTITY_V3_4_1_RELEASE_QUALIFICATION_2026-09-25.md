# ENTITY v3.4.1 Release Qualification — 2026-09-25

**Status:** BTG_INTERNAL_QUALIFIED_PROTOCOL_ORIGIN_LINEAGE_SOVEREIGN_BOOTSTRAP_PATCH

**Qualified source:** `04d7386c70ef1665ea44824d16e1bb09f5329ca8`
**Base:** ENTITY v3.4.0 at `2db5bff64507b8d67642122a5ff2fc73dfef9152`

## Qualification result

- Complete regression: **185/185 PASS**.
- Protocol-origin/migration/economic-lineage regression: **8/8 PASS**.
- v3.4 Global Passport/package tests: **33/33 PASS**.
- Sealed v3.4.1 Global Passport campaign: **24/24 vectors** (12 valid, 12 invalid).
- Canonical result SHA-256: `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`.
- Six BTG-controlled native implementations: **Rust, TypeScript, Go, C#, Java, Swift — PASS**.
- Six executable domain packages: **PASS**.

## Corrected release property

Fresh-user bootstrap no longer makes that user the issuer/originator of ENTITY's canonical profiles. Existing v3.4.0 user identity, objects, Rights Passports and signed history remain unchanged; historical profile variants remain verifiable by body hash while new issuance uses canonical ENTITY-signed profiles and explicit protocol-origin lineage.

The v3.4.1 exact release-origin anchor is generated only after the immutable tag exists and is distributed as an ENTITY-signed sidecar. New v3.4.1 issuance fails closed without that exact sidecar.
