# ENTITY v3.0.1 — BTG Internal Maintenance Release Qualification

Date: 2026-09-23  
Status: **BTG_INTERNAL_QUALIFIED_MAINTENANCE_RELEASE**

v3.0.1 hardens operational signing-key lifecycle semantics discovered during BTG's post-release cryptographic campaign. Retired/revoked signing keys are time-cut off for v2 signature records, signatures predating key creation fail closed, and obsolete local operational private-key material is removed after successful rotation/recovery.

## Closed BTG-controlled tracks

- Full patched regression: **94/94 PASS**.
- Five-language controlled polyglot transaction/recovery qualification: **Rust, TypeScript, C#, Go, Swift — PASS with identical state/recovery/result roots**.
- Key lifecycle crypto assurance: **10,000 randomized signature cases, 100 rotation cycles, 25 recovery cycles, no failures**.
- EEP misuse/red-team assurance: **5,400 cases PASS**.
- Privacy crypto assurance: **3,000 assertions PASS**.
- Persistent scale/destructive recovery: **1,000,000 assets + 3,000,000 events**, signed Merkle receipts and identical pre/post recovery roots.
- Market execution scale: **4,000 fully settled trades**.
- Operational soak: **900 seconds**, **7,231 settled trades**, periodic implementation reopen.
- Regulatory-engineering applicability/control mapping: **internally closed** for the documented v3.0.x baseline.

## External-only milestones

1. Unrelated third-party v3 implementation and independent live interoperability.
2. Independent external security/cryptographic review.
3. Deployment-specific legal/regulatory classification, licensing, recognition or approval where required.

## Permanent protocol truth boundaries

ENTITY does not create legal title, objective external-bank truth, market value, or accounting fair value merely by recording cryptographic evidence.
