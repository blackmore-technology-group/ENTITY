# ENTITY Sovereign Domain Protocol Specifications v1

Authority: SERS-ENTITY-DOMAIN-001 v1.0
Parent: SERS-ENTITY-003 v2.2
Encoding: UTF-8 JSON; canonical signing form is JSON with lexicographically sorted keys and compact separators.
Hash: SHA-256. Entity signatures: Ed25519. Direct-session key agreement: X25519 + HKDF-SHA256. Session AEAD: AES-256-GCM.

## 1. Domain Identifier
`entity-domain-v1` binds `domain_id` to `entity_root`, namespace, version and status.
`domain_id` is not a DNS name, IP address, device identifier, provider account or BTG account.
Changing serving infrastructure MUST NOT change `entity_root` or `domain_id`.

## 2. Name Claim
`entity-name-claim-v1` contains claim ID, domain ID, Entity root, normalized name, namespace, conflict state, evidence and Entity signature.
Human-readable name matching NEVER replaces cryptographic Entity-root verification.
DNS possession, first registration and payment do not manufacture sovereign authority.

## 3. Node Authorization
`entity-node-authorization-v1` binds a node public key to domain/root, service scopes, network scopes, publication scopes, data scopes and validity window.
Authorization is Entity-signed. A revoked node cannot create new authoritative publication.
Revocation is represented separately by immutable `entity-node-revocation-v1`.

## 4. Service Manifest
`entity-service-manifest-v1` binds service ID/type, authorized node, endpoint, protocol version, capabilities, access class, credential requirements, policy references, data classifications, economic terms, expiry and status.
Manifest versions are monotonic per service. A stale valid manifest remains historical evidence but cannot override a newer known version.
Service discovery does not itself grant access, a licence, consent, ownership or economic participation.

## 5. Resolution Protocol
Input MAY be Domain ID, Entity root, or human-readable Entity name.
Resolver MUST verify root/name binding, node authorization/revocation, service signature, service/node scope, validity windows and anti-rollback state before returning an endpoint.
Resolver output is `entity-resolution-proof-v1` and explicitly records `resolver_is_authority=false` and `dns_used_as_authority=false`.
Multiple resolution sources MAY transport snapshots. Source possession does not create sovereign authority.

## 6. Presence Advertisement
`entity-presence-advertisement-v1` is signed by the currently authorized node key and contains domain/root/node binding, service IDs, scope, endpoint hints, sequence and expiry.
Scopes are PUBLIC, RELATIONSHIP, PRIVATE and LOCAL. Presence metadata MUST be minimized for the selected scope.
Presence advertisements are transport/discovery hints and MUST NOT be treated as proof of ownership, licensing authority, consent or payment authority.
Sequence rollback, expiry, revocation or signature failure MUST reject the advertisement.

## 7. Direct Session Protocol
Client sends `entity-direct-hello-v1` with target node/service, fresh nonce and ephemeral X25519 public key.
Node returns `entity-direct-server-hello-v1` containing both ephemeral keys, nonce, node/service binding and node Ed25519 signature.
Both sides derive a 256-bit session key using X25519 + HKDF-SHA256 and encrypt request/response frames using AES-256-GCM.
Client MUST verify the node key against Entity-signed NodeAuthorization before accepting service data. Replayed session nonces MUST fail.

## 8. Relay Protocol
A relay transports opaque protocol frames only. Relay metadata MUST state that relay possession is not Entity authority.
A relay cannot modify encrypted session payloads without AEAD failure, cannot substitute node/service identity without signature/binding failure, and cannot make a valid sovereign-authority assertion merely by forwarding traffic.
Replay and endpoint substitution MUST be rejected by the endpoint protocol.

## 9. Domain Export
`entity-domain-export-package-v1` contains the signed Entity identity manifest, public domain snapshot, export manifest and package SHA-256.
The export manifest commits to identity and domain-snapshot hashes, schema versions, cryptographic algorithms, state references and known external dependencies.
A complete export MUST declare whether proprietary BTG storage or DNS is required for interpretation. Qualified v1 exports require both to be false.

## 10. Domain Recovery
Recovery first validates the sovereign export and encrypted sovereign state, restores the original Entity root and domain state, then verifies `ENTITY_ROOT_BEFORE == ENTITY_ROOT_AFTER` and `DOMAIN_ID_BEFORE == DOMAIN_ID_AFTER`.
Recovery MAY authorize a replacement node after restoration. Recovery MUST NOT create a replacement Entity identity when the original valid sovereign identity is recoverable.

## 11. Domain Migration
`entity-domain-migration-v1` records old/new node and provider bindings plus sovereign semantic hashes before and after migration.
The sovereign semantic hash excludes replaceable infrastructure details such as endpoint address and node identifier while preserving domain/root/name, service identity/type, access policy references, data classification and economic terms.
Migration succeeds only when sovereign semantic hashes remain identical.

## 12. Economic Service Discovery
Economic service descriptors MAY expose offer type, rights summary, policy references, pricing/terms references and access method without publishing raw source data.
Discovery is not authorization. Licence, consent, payment, usage and economic participation remain separate evidence-backed states.
Infrastructure providers receive no economic participation absent an explicit contractual/economic basis.

## 13. Version and Failure Rules
Unknown major protocol/schema versions MUST fail closed unless an explicit compatibility rule exists.
Historical signed records remain verifiable but do not automatically regain current authority.
Temporary OFFLINE, DEGRADED, PROVIDER_UNAVAILABLE or LOCAL_ONLY state never frees Entity identity/name for reassignment.

## 14. Required Verification Order
1. Verify Entity identity manifest.
2. Verify Domain ID/root binding.
3. Verify name claim if used.
4. Verify node authorization and revocation.
5. Verify presence/service signature and expiry.
6. Apply anti-rollback state.
7. Apply access/policy/licence requirements.
8. Establish authenticated direct/relayed transport.
9. Record usage/economic evidence only after authorization.

## 15. Non-authority Invariants
`DNS != sovereign authority`; `resolver != sovereign authority`; `relay != sovereign authority`; `host != sovereign authority`; `device != Entity`.
Transport availability does not alter rights, consent, licences, Digital Commodity state, balances or corporate-capital state.

## 16. Conformance
A conforming implementation MUST reproduce the valid/invalid vectors published with the qualified release, verify the standalone domain export, reject malicious resolver/relay substitutions, preserve root/domain across migration/recovery, and expose no hidden mandatory BTG/DNS/cloud/paid-relay dependency in the qualified internal scope.
External non-BTG implementation interoperability is a separate higher-assurance milestone and MUST NOT be inferred solely from BTG-authored reference software.
