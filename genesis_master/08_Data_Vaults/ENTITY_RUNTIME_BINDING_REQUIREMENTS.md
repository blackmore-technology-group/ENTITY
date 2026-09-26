# Canonical Runtime Bindings — data_vault / data_sources
Authorities: `data_vault`, `data_sources`
Canonical owner: `08_Data_Vaults`

## Data Vault
- Raw private content remains outside public/shared evidence ledgers and encrypted at rest.
- Keys SHOULD be separated from storage-provider control and support per-asset/security-domain isolation.
- Vault state supports local/offline recovery, encrypted replicas and lifecycle-aware deletion/cryptographic erasure.

## Data Sources
- Source access is default-deny and explicitly enrolled as OFF, OBSERVE, INDEX, PROVENANCE or MANAGED.
- Credential/security locations are excluded by default; possession SHALL NOT imply licensing rights.
- C2PA/provenance verification of a local file requires applicable source enrollment/authorization.
- NIKI does not receive unrestricted vault access and metadata projection SHALL not supply raw content.

## READY Gate
- Tests cover enrollment/exclusion, encryption, unauthorized reads, deletion state and recovery.
- Each READY binding pins current `08_Data_Vaults\ENTITY_REQUIREMENTS.md` SHA-256.
