# ENTITY / NIKI Integration Contract

Authoritative root: `<LOCAL_DRIVE>/Sovereign_Entity_Network`
Workstream owner: `10_NIKI` only
Canonical architecture source: root `ENTITY_REQUIREMENTS_TRACEABILITY.md` and per-directory `ENTITY_REQUIREMENTS.md` files.

## Boundary

`10_NIKI` is not the architectural owner of ENTITY identity, rights, vaults, peer networking, hosting, cryptography, recovery, federation, settlement, AR authority, ADAM action authority, or BSIE world state.

Code currently implemented under `10_NIKI\sovereign_adapted` is an **embedded integration implementation/fallback** used to develop and qualify NIKI-facing contracts while canonical root runtimes are being populated in parallel.

The parallel non-NIKI workstream owns all root directories outside `10_NIKI`. This workstream MUST NOT overwrite or relocate files into those directories without an explicit runtime-binding handoff.
## Runtime Binding Handoff

Each canonical authority may publish `ENTITY_RUNTIME_BINDING.json` inside its owner directory using schema `entity-runtime-binding-v1`.

A binding is canonical only when:
- its `authority` matches the authority declared in `10_NIKI\ENTITY_PLATFORM_BINDINGS.json`;
- its status is `READY`;
- its implementation path remains inside the declared owner directory;
- its exported symbols are explicitly declared;
- its implementation passes the root qualification/release requirements.

When a valid canonical binding appears, the canonical implementation takes precedence over the embedded NIKI fallback for that authority.

Until then, the fallback remains a development/qualification adapter and SHALL NOT be described as architectural ownership by NIKI.
## Persistence Rule

Embedded fallback databases under `10_NIKI` are development/qualification state only.

A canonical authority binding MUST own its durable persistence outside `10_NIKI` in the appropriate root authority or node/runtime location. Canonical identity, rights, policy, vault, contract, settlement and recovery state must not depend on NIKI's package directory.

The public bootstrap API therefore fails closed while the canonical core (`identity`, `policy_consent`, `core_permissions`, `service_api`) is not READY, unless the explicit development-only environment override `ENTITY_ALLOW_EMBEDDED_BOOTSTRAP=1` is set.

This prevents the first permanent sovereign Entity from being created inside a NIKI implementation tree.
## Requirement-Contract Pinning

A canonical `READY` runtime binding must include `requirements_sha256`, equal to the current SHA-256 of the top-level owner directory's `ENTITY_REQUIREMENTS.md`.

If the parallel root workstream changes that requirement contract, the prior binding becomes stale automatically and the NIKI adapter will refuse to classify it as canonical until it is requalified against the new contract.

This prevents cross-chat drift where code remains marked production-ready after its authoritative requirements changed.
## What 10_NIKI legitimately owns

The NIKI workstream may own and evolve:
- context adapters that project canonical ENTITY/BSIE state into bounded reasoning context;
- Entity-specific reasoning/orchestration logic;
- overlay/annotation generation;
- NIKI-side policy constraints and disclosure minimization;
- reasoning interfaces and proposal generation;
- compatibility shims for existing NIKI clients.

These components may consume canonical authority but SHALL NOT become the authority for identity, rights, policy, vault content, contracts, settlement, peer trust, recovery, or BSIE world state.

## ENTITY 2.0 / Full ADAM v1.0 Integration

The v2 development path adds `adam_full_runtime` as a production-required canonical authority owned by `11_ADAM\full_runtime`. ENTITY remains the sovereign authorization root. The full ADAM runtime supplies deterministic atomic information, exact evidence/reconstruction, reaction-governed transition history, aligned semantic claims, and the bounded ADAM v1.0 runtime surfaces. NIKI may project ADAM metadata for reasoning but does not execute ADAM mutations or acquire ENTITY authority.

Protocol 1.0 remains frozen. This integration is versioned as ENTITY 2.0 development because it expands evidence/state semantics rather than silently redefining Protocol 1.0.
