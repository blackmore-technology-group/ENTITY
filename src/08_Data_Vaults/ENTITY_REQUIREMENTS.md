# ENTITY Data Vault Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Storage Model
- Raw private content SHALL remain separate from the public/shared evidence ledger.
- Content SHALL be encrypted at rest; encryption keys SHOULD be separated from storage-provider control.
- Per-asset or per-security-domain data-encryption keys SHOULD be supported.
- Vaults SHALL support local storage, encrypted removable storage, authorized cloud storage, redundant encrypted replicas and offline recovery.

## Classification and Access
- Support PRIVATE, INTERNAL, RESTRICTED, NON_TRANSFERABLE, LICENSABLE and PUBLIC classifications.
- Source enrollment SHALL be default-deny and support OFF, OBSERVE, INDEX, PROVENANCE and MANAGED modes.
- Explicit exclusions SHALL override inherited access.
- Credentials, private keys, session cookies, API secrets and security tokens SHALL NOT be automatically ingested.

## Deletion
- Track primary objects, replicas, backups, caches, previews, indexes, embeddings, temporary files and visible export copies.
- Support cryptographic erasure where complete physical deletion cannot be guaranteed.
- Never claim remote deletion unless it can actually be verified or attested.
