# ENTITY Architecture Decision Record Process

Architecture Decision Records (ADRs) document decisions that affect ENTITY's durable architecture, protocol boundaries or security/governance invariants.

## When an ADR is required

An ADR should be considered when a change affects one or more of:

- root identity semantics;
- authority, delegation or revocation;
- signature/canonicalization meaning;
- provider independence;
- custody versus sovereignty boundaries;
- recovery, migration or portability;
- evidence and attestation semantics;
- external reality anchors;
- historical signed-state interpretation;
- rights, entitlement, usage or economic consequence semantics;
- compatibility or public protocol behavior.

Routine implementation detail that preserves existing architecture does not require an ADR.

## ADR states

Use one of these states:

- **PROPOSED** — under discussion; not yet authoritative.
- **ACCEPTED** — approved architecture decision.
- **SUPERSEDED** — replaced by a later ADR; retained for historical traceability.
- **REJECTED** — considered but not adopted.
- **DEPRECATED** — retained for historical reference but no longer recommended for new implementation.

## Required sections

A new ADR should include:

1. **Title and identifier**
2. **Status**
3. **Date**
4. **Context**
5. **Decision**
6. **Security/sovereignty implications**
7. **Compatibility implications**
8. **Alternatives considered**
9. **Consequences**
10. **Evidence / references**
11. **Supersedes / superseded by**, if applicable

## Review expectations

ADRs touching security- or sovereignty-critical boundaries should be reviewed against:

- [GOVERNANCE.md](../../GOVERNANCE.md)
- [SECURITY.md](../../SECURITY.md)
- [Release Policy](../governance/RELEASE_POLICY.md)
- applicable protocol governance/freeze documents
- the project's public engineering evidence and current claim boundaries.

An ADR cannot silently rewrite a frozen protocol target or historical signed semantics. If a decision changes published protocol meaning, the change must use an explicit version/governance mechanism.

## Numbering

ADRs use a stable numeric identifier, for example:

`ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md`

Numbers are never reused, even if an ADR is rejected or superseded.

## Relationship to technical papers

ADRs record a decision. Technical papers explain concepts, threat boundaries or analysis. A paper may motivate an ADR, but it does not become normative merely because it exists in the public repository.

See [docs/papers/README.md](../papers/README.md).
