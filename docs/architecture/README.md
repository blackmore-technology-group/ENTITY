# ENTITY Architecture

ENTITY separates sovereign authority from infrastructure custody and keeps identity, authorization, evidence, rights, usage and economic consequence as auditable but distinct concerns.

At a high level:

```text
Entity identity
    â†“
Scoped / revocable authority
    â†“
Applications, devices, nodes
    â†“
Assets + provenance + evidence
    â†“
Rights / policy / consent
    â†“
Licensing / usage / settlement evidence
    â†“
Portable state + recovery
```

The v3.3 evidence path extends that model with:

```text
REALITY
  â†“
OBSERVATION
  â†“
CLAIM
  â†“
EVIDENCE
  â†“
ATTESTATION
  â†“
VERIFICATION
  â†“
AUTHORITATIVE ENTITY STATE
```

v3.4 adds one Global Passport over that architecture:

```text
ENTITY state + rights + evidence
        â†“
Global Passport envelope
        â†“
Composable profile stack
        â†“
Versioned profile / standards mappings
        â†“
Continuous provenance + derivation
        â†“
Domain deployment packages
```

Profiles add context and constraints; they do not create sovereign authority or redefine external standards.

The project deliberately separates **cryptographic verification**, **protocol verification** and **reality/evidence verification**. See [Technical Note 001 â€” Three Verification Boundaries](../papers/TECHNICAL_NOTE_001_THREE_VERIFICATION_BOUNDARIES.md).

## Major implementation surfaces

- `01_Core_Runtime` â€” identity, policy, permissions, contracts, usage and canonical APIs.
- `04_Entity_Registry` â€” assets, event ledger, provenance, relationships, rights claims and credentials.
- `15_Operations` â€” portable state, recovery/migration and runtime state machinery.
- `22_Sovereign_Domain` â€” Entity-native domains, nodes, presence, resolution, portability and verification.
- `31_Profiles` â€” profile machinery.
- `33_Economic_Participation` â€” economic participation and consequence surfaces.
- `36_Adoption_Layer` â€” Rights Passports and adoption-layer interfaces.
- `37_Verifiable_Reality` â€” evidence objects, attestation, external anchors, contestability and causal attribution.
- `38_Global_Passports` â€” Global Passport envelope, profiles, registry, continuous provenance and conformance.
- `39_Implementation_Packages` â€” deployable industry-package machinery and configuration planning.
- `profiles/` â€” versioned Global Passport/domain profile registry assets.
- `sdk/` â€” provider-neutral application integration, Global Passport SDK and principal/device/application binding.

See [v3.4.1 current release / v3.4 architecture and domain packages](../v3.4/README.md).

## Architecture Decision Records

Durable architecture decisions are recorded as ADRs. The process is defined in [ADR_PROCESS.md](ADR_PROCESS.md).

Current public ADRs:

| ADR | Status | Subject |
| --- | --- | --- |
| [ADR-0004](ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md) | Accepted | Sovereign Authority Doctrine â€” platform non-authority, provider replaceability and digital-existence continuity |

ADR numbers are stable and never reused. A superseded/rejected ADR remains part of the historical architecture record.

## Other architecture documents

- [ENTITY Domain Protocols v1](ENTITY_DOMAIN_PROTOCOLS_v1.md)
- [ENTITY 2 â€” Causal NIKI Integration](ENTITY_2_CAUSAL_NIKI_INTEGRATION.md)
- [ENTITY 2 â€” Full ADAM Integration](ENTITY_2_FULL_ADAM_INTEGRATION.md)

These documents should be read with their stated version/status. Their presence in the architecture directory does not automatically make every statement normative for the current protected release.

## Architecture invariants

The current architecture is intended to preserve these boundaries:

- identity is not an account;
- registration is not ownership;
- provenance is not truth;
- a valid signature is not proof that an external-world assertion is correct;
- possession, hosting, routing, custody and storage do not create sovereign authority;
- external registries and anchors can provide evidence without becoming general authority;
- applications and agents act only through explicit, scoped, revocable authority;
- recovery preserves authoritative identity continuity rather than manufacturing a new root;
- historical signed semantics are superseded explicitly, not silently rewritten;
- data bytes do not require artificial scarcity for rights, entitlements, licensing and usage to be economically governed.

## Change control

Changes affecting identity, authority, signature meaning, provider independence, recovery, portability, evidence semantics, historical interpretation, rights/settlement authorization or wire compatibility require explicit architecture/governance consideration.

See:

- [GOVERNANCE.md](../../GOVERNANCE.md)
- [Release Policy](../governance/RELEASE_POLICY.md)
- [SECURITY.md](../../SECURITY.md)
- [Engineering Evidence](../ENGINEERING_EVIDENCE.md)
