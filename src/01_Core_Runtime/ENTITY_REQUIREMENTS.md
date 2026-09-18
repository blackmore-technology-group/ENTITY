# ENTITY Core Runtime Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Core Responsibilities
- Implement stable sovereign identity independent of any one operational key.
- Provide key hierarchy, rotation, revocation, recovery, succession and threshold organizational authority.
- Provide versioned APIs for identity, sources, vault, assets, claims, policies, licensing, usage, ledger, settlement, exports, disputes, capabilities and administration.
- Implement policy authorization for every authoritative operation.

## Runtime Invariants
- Authorization SHALL evaluate actor, role, capability, asset, action, purpose, policy, jurisdiction/configuration, approval threshold, time and counterparty.
- Authorization failure SHALL fail closed.
- Durable signed records SHALL include schema/version identifiers.
- State-changing network APIs SHOULD support idempotency keys.
- Invalid state transitions, replay and duplicate operations SHALL be rejected.
- Ordinary asset registration SHALL not require remote consensus.
- Core owner-controlled functions SHOULD remain available offline where feasible.

## Security Boundaries
- Secrets SHALL not enter ordinary AI context or logs.
- No schema SHALL permanently assume a single signature or hash algorithm.
- Existing valid signed/evidentiary records SHALL remain verifiable through migration.
