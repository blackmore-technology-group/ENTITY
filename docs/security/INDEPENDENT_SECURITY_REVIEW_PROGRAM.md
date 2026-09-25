# ENTITY Independent Security Review Program

Blackmore Technology Group Limited maintains this public program to make independent security review of ENTITY easier to scope, reproduce and evaluate.

The program does **not** claim that ENTITY has already completed an independent external security audit. Unless a specific external review is published and listed here, that milestone remains **PENDING**.

## Objectives

An independent review should test whether ENTITY's implementation and protocol boundaries preserve the project's stated security and sovereignty invariants under hostile conditions.

Priority review areas include:

1. cryptographic primitive use and key handling;
2. signature canonicalization and replay boundaries;
3. identity-root continuity;
4. delegation, attenuation and revocation;
5. authority escalation paths;
6. recovery, migration and provider replacement;
7. external evidence and attestation semantics;
8. external reality anchors and substitution attacks;
9. rights, entitlement, usage and settlement authorization;
10. portable-state integrity and rollback resistance;
11. parser/schema ambiguity and differential interpretation;
12. historical-state reinterpretation risks;
13. denial-of-service and resource exhaustion where security-relevant;
14. dependency and supply-chain exposure.

## Review levels

### Level A — focused review

A bounded review of one subsystem, invariant or attack surface.

Examples:

- signature/canonicalization review;
- recovery boundary review;
- evidence-state transition review;
- external-anchor threat model.

### Level B — release security review

A structured review of the current protected release and its release-specific security surfaces.

Expected outputs include:

- exact release commit;
- scope;
- methodology;
- findings by severity;
- reproducibility notes;
- exclusions;
- remediation status.

### Level C — protocol and implementation assessment

A broader independent assessment covering both protocol semantics and reference implementation behaviour, including cross-component attack paths and provider-independence guarantees.

This is the strongest review class described by this program, but it is still distinct from legal certification, regulatory approval or proof that every deployment is secure.

## Current review target

Current protected release: **ENTITY v3.4.0 — Global Passport & Continuous Provenance**

Protected release commit: `2db5bff64507b8d67642122a5ff2fc73dfef9152`

The review scope should include Global Passport/profile composition, profile-registry integrity, standards-mapping boundaries, continuous provenance, passport derivation, domain-package deployment semantics, and the inherited v3.3 evidence/attestation surfaces. Reviewers should pin findings to an exact commit, tag or release artifact rather than reviewing an unspecified moving branch.

## Evidence expected from reviewers

A useful independent review should publish or privately provide, as appropriate:

- reviewer identity/organization or explicit anonymous status;
- relationship to BTG and any conflicts of interest;
- exact target version/commit;
- scope and exclusions;
- methodology and tooling;
- reproducible proof-of-concept material when safe;
- severity rationale;
- affected invariants/components;
- remediation verification where performed;
- residual risk and unresolved questions.

If exploitation details would create unnecessary risk, public reports may summarize the issue while technical reproduction remains under coordinated disclosure until remediation is available.

## Security invariants reviewers should challenge

At minimum, reviewers should attempt to falsify these boundaries:

- registration does not prove ownership;
- provenance does not prove rights or external truth;
- a valid signature does not make an external-world assertion objectively true;
- provider possession does not become sovereign authority;
- applications/agents require explicit scoped revocable authorization;
- historical signed semantics are not silently rewritten;
- recovery preserves the same authoritative Entity root rather than manufacturing a replacement identity;
- external evidence sources do not silently acquire general ENTITY authority;
- rights/usage/economic consequences require the authorization/evidence the protocol says they require.

## Reporting process

Potentially exploitable vulnerabilities should be reported through the private vulnerability process described in [SECURITY.md](../../SECURITY.md).

Public issues and Discussions are appropriate for:

- non-sensitive threat models;
- specification ambiguities;
- architectural critiques;
- counterexamples that do not expose active users or secrets;
- hardening proposals after responsible disclosure requirements are satisfied.

## Remediation workflow

A security finding should move through:

`report → reproduce → classify → contain where necessary → remediate → regress-test → review semantic impact → release/errata decision → verify remediation → disclose at appropriate level`

Security fixes must not silently weaken sovereignty, portability or historical-integrity invariants merely to close an implementation defect.

If remediation changes published protocol semantics, the project should use an explicit governance/version mechanism rather than silently reinterpret existing signed state.

## Independent review status

| Review class | Status | Public evidence |
| --- | --- | --- |
| BTG-controlled CI/static analysis | **ACTIVE** | GitHub Actions / CodeQL in repository |
| BTG-controlled qualification/red-team work | **AVAILABLE AS PROJECT EVIDENCE** | See engineering evidence and qualification materials |
| Independent external focused review | **PENDING** | None claimed as complete |
| Independent external release review | **PENDING** | None claimed as complete |
| Independent external protocol + implementation assessment | **PENDING** | None claimed as complete |

BTG-controlled testing is not a substitute for an unrelated security review.

## Recognition and publication

Independent reviewers may be credited according to [Contributor Recognition](../community/CONTRIBUTOR_RECOGNITION.md), subject to security/privacy constraints.

A future completed review should be added to this document with:

- reviewer/organization;
- review date;
- target commit;
- scope;
- report link or disclosure reference;
- remediation status.

## No automatic bounty or certification claim

This document defines a review pathway. It does not itself promise a monetary bounty, procurement engagement, certification, safe-harbour contract or regulatory recognition. Any such arrangement must be separately stated by Blackmore Technology Group Limited.
