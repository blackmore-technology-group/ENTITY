# ENTITY v3.4.0 Release Qualification — 2026-09-24

**Status:** BTG_INTERNAL_QUALIFIED_GLOBAL_PASSPORT_CONTINUOUS_PROVENANCE_RELEASE_CANDIDATE

**Qualified source:** `854529e6cb88e77f29cce581beb74b530768224c`  
**Base:** ENTITY v3.3.0 at `9c79f987207592cb6791e1a8956f23351cdfb2d3`

## Qualification result

- Complete regression: **177/177 PASS**.
- v3.4 targeted Global Passport / implementation-package tests: **33/33 PASS**.
- Sealed Global Passport campaign: **24/24 vectors** (12 valid, 12 invalid).
- Canonical result SHA-256: `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`.
- Six BTG-controlled native implementations: **Rust, TypeScript, Go, C#, Java, Swift — PASS**.
- CLI deployment path: initialize → package plan → ingest → passport verify — **PASS**.

## Release architecture

ENTITY v3.4 preserves `ENTITY → AUTHORITY → RIGHT → EVENT → VALUE`. It adds one Global Passport, composable profiles, a versioned profile registry, explicit external-standard mappings, continuous provenance and executable implementation packages for Healthcare, Finance, Manufacturing, AI, Robotics and public/unclassified Defence.

Industry packages populate the one Global Passport. They do not define incompatible industry-specific passports, create authority, declare truth, or establish regulatory compliance.

## Evidence boundary

The six native implementations are all BTG-controlled. Their common result is meaningful controlled-interoperability evidence, but **unrelated third-party implementation/interoperability remains pending**. External security review and deployment-specific legal/regulatory determinations also remain external work.
