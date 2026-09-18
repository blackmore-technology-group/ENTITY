# Architecture Overview

ENTITY separates sovereign authority from infrastructure custody.

At a high level:

```text
Entity identity
    ↓
Scoped / revocable authority
    ↓
Applications, devices, nodes
    ↓
Assets + provenance + evidence
    ↓
Rights / policy / consent
    ↓
Licensing / usage / settlement evidence
    ↓
Portable state + recovery
```

The reference implementation is divided into:

- `01_Core_Runtime` — identity, policy, permissions, contracts, usage, canonical APIs.
- `04_Entity_Registry` — assets, event ledger, provenance, relationships, rights claims, credentials.
- `15_Operations` — portable state, recovery/migration, runtime state machinery.
- `22_Sovereign_Domain` — Entity-native domains, nodes, presence, resolution, portability and verification.
- `sdk/` — provider-neutral application integration and principal/device/application binding.

The controlling authority doctrine is recorded in `ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md`.
