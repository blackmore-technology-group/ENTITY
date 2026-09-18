# ENTITY Protocol Governance v1

## Purpose
ENTITY 1.0 is frozen for external conformance work. The freeze stabilizes wire semantics, authority boundaries, cryptographic meaning and portability behavior while independent implementations are developed.

The freeze does not claim external interoperability has passed. The current full external release remains blocked until the sovereign-domain external qualification is executed.

## Governance rules
1. A published protocol version is immutable. Corrections are issued as errata or a new version; historical signed evidence is never silently reinterpreted.
2. Blackmore Technology Group may steward specifications and publish new versions, but it cannot make an already published conforming implementation depend on BTG hosting, DNS, a BTG resolver or a paid BTG service.
3. Provider possession, storage custody and transport never become sovereign authority merely because infrastructure changes.
4. Conformance is determined by public specifications, schemas, vectors and reproducible tests rather than access to private BTG code.
5. BTG extensions must be namespaced and must not change the meaning of core protocol records.
6. Security-critical semantic changes require a new protocol version and an auditable architecture decision.
7. Implementations may continue supporting an older protocol version; forced silent upgrades are prohibited.
8. Human-readable name disputes remain governance/legal-evidence matters. Alias visibility never overrides cryptographic Entity-root authority.

## Version lifecycle
`DRAFT -> FROZEN_FOR_EXTERNAL_CONFORMANCE -> QUALIFIED -> SUPERSEDED`

A version reaches `QUALIFIED` only after required internal gates and the applicable independent external interoperability gates pass.
