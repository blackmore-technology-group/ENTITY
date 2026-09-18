# Architecture Overview

ENTITY separates sovereign authority from infrastructure custody.

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

The reference implementation is divided into:

- `01_Core_Runtime` â€” identity, policy, permissions, contracts, usage, canonical APIs.
- `04_Entity_Registry` â€” assets, event ledger, provenance, relationships, rights claims, credentials.
- `15_Operations` â€” portable state, recovery/migration, runtime state machinery.
- `22_Sovereign_Domain` â€” Entity-native domains, nodes, presence, resolution, portability and verification.
- `sdk/` â€” provider-neutral application integration and principal/device/application binding.

The controlling authority doctrine is recorded in `ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md`.
