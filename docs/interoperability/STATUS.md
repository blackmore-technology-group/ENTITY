# ENTITY Interoperability Status

This page is the public status board for reproducibility, conformance and interoperability evidence.

It is intentionally conservative: a repository, implementation or test is listed only for the evidence it actually demonstrates. Controlled implementations are not promoted into independent validation merely because they are written in different languages.

## Status vocabulary

- **PASS** — the stated test/evidence requirement was completed successfully.
- **PARTIAL** — useful evidence exists, but the stated end-to-end milestone is incomplete.
- **PENDING** — no qualifying public result has yet been recorded.
- **FAILED / COUNTEREXAMPLE** — a reproducible result demonstrates non-conformance, ambiguity or failure. This is useful evidence and should remain visible until resolved or superseded.

## Current supported release and frozen campaign evidence

Supported tagged reference release: **ENTITY v3.4.3**; protected release commit `528b70aabd05b1e930b77e4933f157731e47274f`.

Direct v3.4.3 Issue #28 verification: **76/76 targeted PASS; 279/279 full source-suite PASS**. BTDU component **3.4.2 remains unchanged** within this protected tag. The latest `main` implementation adds distinct post-tag storage and application work and must be pinned to its own commit for qualification.

**Historical v3.4.1 Global Passport campaign**, not the current runtime:
- Protected historical commit: `9822b1b65f8269ebc17208a342809720729ae2f8`.
- Sealed kit SHA-256: `f95c2b347da97742fed3f20611f0eec2fd3df48694fed9494fb07163c537cfb7`.
- Deterministic result SHA-256: `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`.
- Schema SHA-256: `3d72b4e67ec9929c5d960cee8fc52db35d85ba5103e361f3a61a8f5078079c5d`.
- The historical campaign has **24 vectors (12 valid / 12 invalid)** across six BTG-controlled native implementations; this is a *historical reproducibility result*, not a new v3.4.3 or Protocol 1.0 qualification.

Separately, [engineering evidence](../ENGINEERING_EVIDENCE.md) records external reproduction of a **frozen v3.4.2 Java 26-vector** campaign. That is meaningful independent *reproduction* of a BTG target, not independently authored Protocol 1.0 conformance or end-to-end recovery qualification.

## BTG-controlled cross-language reproducibility baselines

The 24-vector results below are specifically the frozen v3.4.1 campaign, not live v3.4.3 code qualification.

These implementations are controlled by Blackmore Technology Group Limited. They demonstrate cross-language reproducibility against the stated public vector target, but **do not constitute unrelated external validation**.

| Implementation | Control | v3.4 vector target | Native CI | Evidence class |
| --- | --- | --- | --- | --- |
| Rust | BTG-controlled | 24/24 | **PASS** | Controlled cross-language reproducibility |
| TypeScript | BTG-controlled | 24/24 | **PASS** | Controlled cross-language reproducibility |
| C# | BTG-controlled | 24/24 | **PASS** | Controlled cross-language reproducibility |
| Go | BTG-controlled | 24/24 | **PASS** | Controlled cross-language reproducibility |
| Swift | BTG-controlled | 24/24 | **PASS** | Controlled cross-language reproducibility |
| Java | BTG-controlled | 24/24 | **PASS** | Controlled cross-language reproducibility |

Repositories:

- [ENTITY-RUST-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-RUST-CLEANROOM)
- [ENTITY-TYPESCRIPT-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-TYPESCRIPT-CLEANROOM)
- [ENTITY-CSHARP-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-CSHARP-CLEANROOM)
- [ENTITY-GO-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-GO-CLEANROOM)
- [ENTITY-SWIFT-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-SWIFT-CLEANROOM)
- [ENTITY-JAVA-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-JAVA-CLEANROOM)

## External milestone scoreboard

External reproduction of a frozen BTG-controlled v3.4.2 Java campaign is documented separately above. It is not evidence that the independently authored conformance or live interoperability milestones below are complete.

| Milestone | Current status | Evidence required to change status |
| --- | --- | --- |
| Unrelated developer independently authors and qualifies a v3.4 conformance implementation | **PENDING** | Public implementation designed outside BTG control, vectors and own CI |
| Unrelated implementation accepts all valid v3.4 vectors | **PENDING** | Reproducible public candidate result |
| Unrelated implementation rejects all invalid/tampered v3.4 vectors | **PENDING** | Reproducible public candidate result |
| Reproducible CI in unrelated repository | **PENDING** | Public CI tied to independently authored implementation |
| Bidirectional live interoperability with BTG reference implementation | **PENDING** | Public test evidence covering both directions |
| Sovereign export/recovery survival across independent implementation boundary | **PENDING** | Recovery evidence showing preservation of the same authoritative result/root |
| Independently authored qualification report | **PENDING** | External party's own evidence package |
| Independent external security review | **PENDING** | Public or privately verifiable independent review with defined scope |

## Protocol 1.0 historical conformance target

The separately published [ENTITY Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit) remains the authoritative sealed target for Protocol 1.0 external conformance campaigns.

That historical target must not be silently rewritten to match later ENTITY versions. Protocol 1.0, v3.3 historical evidence and current v3.4 evidence should be reported separately.

## How a new external result is added

An external result should identify at least:

1. implementation repository and commit;
2. authoring organization/developer relationship to BTG;
3. language/runtime;
4. exact target kit/version and hashes;
5. test command;
6. valid/invalid vector outcome;
7. CI evidence where available;
8. known failures, skipped cases or deviations;
9. whether live interoperability was attempted;
10. whether sovereign export/recovery was attempted.

A result may be recorded as **PARTIAL**. Partial evidence must not be upgraded to full interoperability merely because the completed portion passed.

## Challenge

For the public path from a small vector classifier through full interoperability, see [ENTITY Interoperability Challenge](../INTEROPERABILITY_CHALLENGE.md).

A reproducible failure, ambiguity or counterexample is an acceptable and useful outcome.
