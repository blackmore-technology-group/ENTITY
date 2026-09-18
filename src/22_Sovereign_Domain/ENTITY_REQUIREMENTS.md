# ENTITY Sovereign Domain Requirements
Source: SERS-ENTITY-DOMAIN-001 v1.0
Parent: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping
Source SHA-256: 38999d4fb1eebbdf1b4f9874145a1d9faed7f93f4ecd7ef0291e1768f5c4ec8f

## Sovereign domain
- ENTITY-native continued digital existence SHALL NOT require a paid registrar, DNS authority, cloud host, BTG host, paid relay, marketplace account, blockchain fee, or mandatory subscription.
- An EntityDomain SHALL bind to the sovereign Entity root and SHALL remain stable across device, IP, ISP, host, provider and geographic changes.
- ENTITY_DOMAIN SHALL NOT be interpreted as DNS_DOMAIN, HOSTING_ACCOUNT, IP_ADDRESS, DEVICE_ID, or BTG_ACCOUNT.
- Human-readable Entity names SHALL remain subordinate to cryptographic Entity identity and SHALL NOT manufacture ownership from first registration, payment, DNS possession or database order.

## Nodes and services
- Every EntityNode SHALL require explicit signed NodeAuthorization with scoped services, data, network, publication, time and delegation limits.
- Node revocation SHALL preserve the Entity root and historical evidence while preventing new authoritative publication by the revoked node.
- A ServiceManifest SHALL be signed, versioned, independently verifiable, expiry/revocation aware and bound to the Entity root, domain, node and service.
- Public presence SHALL NOT imply public access to all Entity data.
- Owner-controlled nodes SHALL be able to publish selected pages, files, APIs, datasets, software, messaging and economic services without uploading all source data to a central ENTITY service.

## Resolution and connectivity
- ENTITY-native resolution SHALL NOT require DNS and SHALL verify Entity root, name/root binding, current service manifest, NodeAuthorization, endpoint and policy before connection.
- A resolver SHALL NOT gain ownership, licensing, consent, revocation, transfer or monetization authority merely by locating an Entity.
- Multiple independent resolution sources SHALL be supported and stale/rollback state SHALL NOT override newer signed authoritative state.
- Direct authenticated connection SHALL be preferred where possible; NAT traversal and optional relays SHALL remain non-authoritative transport infrastructure.
- Relay or routing possession SHALL NOT manufacture sovereign, licensing, consent or economic authority.
## Local data and economic operation
- Core domain state SHALL remain locally inspectable and locally operable where technically possible during internet loss.
- Publishing a service SHALL NOT require surrendering owner-controlled source datasets; approved computation-to-data MAY return only permitted results.
- Economic service discovery SHALL NOT imply usage permission, licence, ownership or economic participation.
- Infrastructure providers SHALL receive fees, royalties, commissions or participation only from an explicit evidence-backed basis.

## Export, migration and recovery
- Domain export SHALL include or reference root linkage, name claims, aliases, node authorizations, service manifests, resolution state, policies, revocations, migration history, economic descriptors, schema/crypto versions and evidence roots.
- Device migration and provider migration SHALL preserve Entity root, Domain ID, rights semantics, policy semantics, provenance and economic history.
- Loss of serving nodes or BTG infrastructure SHALL NOT erase the Entity; valid sovereign recovery SHALL restore the same Entity rather than create a replacement identity.
- No proprietary BTG database SHALL be required to interpret a complete domain export.

## Qualification
- Provider-free qualification SHALL exercise no paid registrar, no DNS dependency for ENTITY-native resolution, no cloud host, no BTG host and no paid relay.
- At least two independently keyed node runtimes SHALL discover, authenticate and communicate through ENTITY-native resolution in the internal qualification environment; physical multi-device qualification SHALL remain separately identified where not executed.
- Malicious resolver, malicious relay, stale manifest, forged authorization, revoked-node replay, endpoint substitution and rollback SHALL fail closed.
- Destructive domain recovery SHALL preserve Entity root and Domain ID after original serving state is made unavailable.
- The implementation SHALL publish protocol rules, valid/invalid test vectors, an independent verifier and sealed qualification evidence.
- Open-federation qualification SHALL ultimately require an unrelated non-BTG implementation; internal reference-verifier success SHALL NOT be mislabeled as that external milestone.

## Release
- DOMAIN_IDENTITY_GATE, NAME_AUTHORITY_GATE, NODE_AUTHORIZATION_GATE, RESOLUTION_GATE, DIRECT_CONNECT_GATE, PROVIDER_INDEPENDENCE_GATE, RECOVERY_GATE, SECURITY_GATE, PRIVACY_GATE, ECONOMIC_SEMANTICS_GATE and OPEN_INTEROPERABILITY_GATE SHALL be evaluated separately.
- Any hidden mandatory registrar, DNS, BTG, cloud or paid-relay dependency SHALL block full sovereign-domain qualification.
- Future ENTITY architecture, RTM, release and CHAOS qualification SHALL treat SERS-ENTITY-DOMAIN-001 as normative unless formally superseded.
