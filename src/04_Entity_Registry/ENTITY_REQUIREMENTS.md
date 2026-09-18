# ENTITY Registry Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Domain Model
- Registry SHALL support Entity, RelationshipIdentity, KeyAuthority, Credential, Source, Asset, AssetVersion, ProvenanceEvent, RightsClaim, Policy, Consent, Licence, UsageEvent, UsageReceipt, ExportEvent, TermsSnapshot, Settlement, AccountingEntry, DataPool, PoolContribution, Dispute, Attestation, WitnessCheckpoint, AgentCapability, Approval and RecoveryPolicy.
- Every durable high-value object SHALL have a collision-resistant unique identifier.

## Identity and Relationships
- Root identity SHALL remain stable across operational key rotation.
- Pairwise/purpose-specific relationship identifiers SHALL be supported so external relationships need not expose one universal identifier.
- Verification status SHALL remain separate from identity existence.
- Delegations SHALL be explicit, scoped, revocable and auditable.

## Rights Graph
- Single-owner semantics SHALL be superseded by a many-to-many Rights & Claims Graph.
- Claims SHALL support claimant, right type, share, scope, territory, jurisdiction, legal basis, dates, evidence, signature, verification and dispute state.
- Competing or complementary claims SHALL coexist without fabrication or silent resolution.
## SERS-ENTITY-003 v2.2 Sovereign Authority Objects
- Registry SHALL support AuthorityRelationship, CustodyRelationship, StorageBinding, ProcessingGrant, SovereignDelegation, EconomicParticipationRight, ProviderMigrationRecord and SovereignExportManifest domain semantics.
- Provider/custodian records SHALL NOT silently become ownership, consent, licensing or governance authority.
- Sovereign authority SHALL remain stable across storage-provider substitution unless an explicit governed authority transition occurs.
