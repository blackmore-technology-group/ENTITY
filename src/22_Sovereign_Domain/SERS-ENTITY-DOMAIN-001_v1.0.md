# ENTITY SOVEREIGN DOMAIN, DEVICE-NATIVE PRESENCE AND DECENTRALIZED SERVICE RESOLUTION
## Complete Engineering Requirements Specification
### SERS-ENTITY-DOMAIN-001 — v1.0

**System:** ENTITY  
**Parent architecture:** SERS-ENTITY-003 — Complete Master Engineering Design v2.2  
**Classification:** Foundational Sovereign-Network Architecture  
**Status:** Authoritative Target Engineering Requirement  
**Purpose:** Preserve the original ENTITY premise that a person, company, organization or other lawful Entity must not be required to rent its continued digital existence, domain identity, data custody, digital presence or economic participation from a registrar, cloud host, platform, marketplace or other infrastructure provider.

---

# 0. CONTROLLING DOCTRINE

The architecture SHALL treat the following as non-negotiable:

> **No Entity SHALL be required to rent continued digital existence from an infrastructure provider.**

> **An Entity domain identifies the sovereign Entity, not the computer, registrar, host, cloud account or service provider currently serving it.**

> **Infrastructure SHALL connect Entities. Infrastructure SHALL NOT become the sovereign authority over them merely because it carries, stores, indexes, resolves, relays or processes their information.**

> **The Entity survives the device. The Entity survives the host. The Entity survives the provider. The Entity survives BTG.**

The system SHALL enforce the following distinctions:

```text
ENTITY EXISTENCE            ≠ DOMAIN REGISTRAR ACCOUNT
ENTITY NAME                 ≠ RENTED DNS RECORD
ENTITY PRESENCE             ≠ CLOUD HOSTING ACCOUNT
ENTITY ROOT                 ≠ DEVICE
ENTITY NODE                 ≠ ENTITY
STORAGE                     ≠ OWNERSHIP
HOSTING                     ≠ AUTHORITY
ROUTING                     ≠ AUTHORITY
RELAY                       ≠ AUTHORITY
INDEXING                    ≠ AUTHORITY
DISCOVERY                   ≠ AUTHORITY
PROCESSING                  ≠ CONSENT
ACCESS                      ≠ LICENCE
USAGE                       ≠ OWNERSHIP
NETWORK AVAILABILITY        ≠ SOVEREIGN EXISTENCE
LOSS OF HOST                ≠ LOSS OF ENTITY
LOSS OF BTG                 ≠ LOSS OF ENTITY
DEVICE REPLACEMENT          ≠ IDENTITY REPLACEMENT
PROVIDER REPLACEMENT        ≠ ENTITY REPLACEMENT
```

---

# 1. ORIGINAL PURPOSE

ENTITY SHALL be engineered around the premise that modern digital participation unnecessarily centralizes practical control in intermediaries.

The conventional pattern is commonly:

```text
PERSON / COMPANY
      ↓
RENTS DOMAIN
      ↓
DEPENDS ON REGISTRAR
      ↓
DEPENDS ON DNS PROVIDER
      ↓
DEPENDS ON HOST / CLOUD
      ↓
UPLOADS DATA
      ↓
PLATFORM CONTROLS PRACTICAL ACCESS
      ↓
ACCOUNT / BILLING / TERMS CONTROL CONTINUED PRESENCE
```

ENTITY SHALL invert this relationship:

```text
ENTITY OWNER / CONTROLLER
      ↓
SOVEREIGN ENTITY ROOT
      ↓
SOVEREIGN ENTITY NAME
      ↓
AUTHORIZED ENTITY NODE(S)
      ↓
OWNER-CONTROLLED DATA / SERVICES
      ↓
ENTITY-NATIVE RESOLUTION
      ↓
DIRECT OR RELAYED CONNECTION
      ↓
POLICY-GOVERNED ACCESS
      ↓
RIGHTS / USAGE / ECONOMIC PARTICIPATION
```

The human-readable experience MAY resemble a website, application, profile, marketplace, service portal or data service.

The underlying sovereignty SHALL NOT depend on a traditional rented domain, DNS registrar, mandatory cloud host or centrally controlled platform account.

---

# 2. RELATIONSHIP TO SERS-ENTITY-003 v2.2

This specification is a dedicated engineering expansion of the following parent-architecture principles:

- sovereign identity independent of one operational key;
- owner-controlled storage;
- provider-independent interpretation;
- provider replaceability;
- portability;
- independently operated compatible nodes;
- peer discovery;
- offline operation;
- authority/custody/storage separation;
- sovereign export and recovery;
- independent verification;
- Section 171 independently reproducible transaction;
- Section 172 Sovereign Authority Doctrine.

This specification SHALL NOT weaken those requirements.

Where this specification conflicts with an implementation assumption that requires a mandatory registrar, mandatory DNS authority, mandatory BTG host or mandatory cloud account for continued Entity existence, this specification SHALL control for ENTITY-native operation.

---

# 3. SYSTEM DEFINITION

An **ENTITY Domain** is the persistent machine-verifiable digital presence of an Entity.

An ENTITY Domain SHALL be rooted in the sovereign Entity identity and SHALL be capable of publishing authorized services from one or more owner-authorized nodes.

The ENTITY Domain SHALL NOT be defined as:

- a DNS name;
- an HTTP host name;
- an IP address;
- a BTG account;
- a cloud account;
- a device serial number;
- a blockchain token;
- a registrar record;
- a subscription;
- a hosting contract.

The ENTITY Domain SHALL be a sovereign identity-bound namespace object whose current authorized service locations can change without replacing the Entity.

---

# 4. CORE ARCHITECTURAL OBJECTS

The authoritative model SHALL include at minimum:

```text
EntityRoot
EntityDomain
EntityName
EntityNameClaim
EntityAlias
EntityNode
NodeAuthorization
NodeCapability
ServiceManifest
ServiceDescriptor
ServiceEndpoint
ResolutionRecord
ResolutionProof
RouteAdvertisement
RelayAuthorization
RelayRecord
PresenceRecord
AvailabilityRecord
LocalDiscoveryRecord
FederationDiscoveryRecord
ConnectionPolicy
AccessPolicy
PublicationPolicy
DataLocationBinding
ServiceVersion
NodeMigrationRecord
DomainRecoveryRecord
DomainExportManifest
NameConflictRecord
NameDisputeRecord
RevocationRecord
EconomicServiceDescriptor
```

All durable high-value objects SHALL have unique identifiers and versioned schemas.

---

# 5. SOVEREIGN ENTITY ROOT

The Entity root SHALL remain the ultimate identity anchor for the ENTITY Domain.

A domain SHALL remain valid across:

- device replacement;
- operating-system replacement;
- IP-address change;
- ISP change;
- network change;
- storage-provider change;
- hosting-provider change;
- relay-provider change;
- geographic relocation;
- local-to-remote migration;
- BTG infrastructure loss.

A domain SHALL NOT require creation of a new Entity root merely because its serving infrastructure changes.

---

# 6. ENTITY-NATIVE NAME

ENTITY SHALL support a human-usable Entity name layer that is distinct from DNS.

The canonical cryptographic Entity identity SHALL remain authoritative even if human-readable names conflict, change or become unavailable.

An Entity name SHALL resolve to the Entity root and current authorized service state, not directly to one permanent machine.

Conceptual examples MAY resemble:

```text
entity:shawn
entity:blackmore
entity:blackmore.technology
entity:gf-sar
```

These examples are illustrative only. Final syntax SHALL be defined by the protocol specification.

No name syntax SHALL imply dependence on ICANN DNS.

---

# 7. NAME OWNERSHIP AND AUTHORITY

An Entity name SHALL NOT be treated as property merely because it was observed first.

Name control SHALL be represented as an evidence-backed namespace relationship.

The namespace SHALL distinguish:

```text
NAME_CLAIM
NAME_CONTROL
NAME_DELEGATION
NAME_ALIAS
NAME_DISPUTE
NAME_SUPERSESSION
NAME_REVOCATION
```

A valid name claim SHALL bind:

- claimant Entity root;
- normalized name;
- namespace;
- claim identifier;
- claim time;
- evidence;
- signature;
- status;
- conflict state;
- applicable governance rule.

---

# 8. GLOBAL NAME COLLISION

ENTITY SHALL assume that multiple parties may seek the same human-readable name.

The protocol SHALL define deterministic conflict behavior.

The system SHALL NOT silently choose a winner using only:

- earliest timestamp;
- first local registration;
- highest payment;
- possession of a matching DNS domain;
- BTG preference;
- local database order.

The system SHOULD support:

- cryptographic canonical identifiers;
- disambiguated names;
- aliases;
- organizational credentials;
- verified-name attestations;
- dispute records;
- jurisdiction-aware external evidence where relevant.

A name conflict SHALL NOT destroy either Entity's cryptographic identity.

---

# 9. NO DOMAIN RENT REQUIREMENT

Basic ENTITY-native identity and domain operation SHALL NOT require:

- payment to a registrar;
- annual domain renewal;
- mandatory hosting subscription;
- mandatory DNS subscription;
- mandatory BTG subscription;
- cryptocurrency;
- gas fees;
- marketplace membership.

Optional providers MAY charge for optional services.

Failure to pay an optional provider SHALL NOT erase the sovereign Entity root or domain state.

---

# 10. ENTITY NODE

An **EntityNode** is an authorized device or runtime permitted to serve one or more services for an Entity.

An EntityNode MAY be:

- desktop computer;
- laptop;
- phone;
- tablet;
- home server;
- NAS;
- workstation;
- enterprise server;
- datacenter host;
- embedded device;
- authorized virtual machine;
- authorized hosted instance.

The node SHALL NOT become the Entity merely because it serves the Entity.

---

# 11. NODE AUTHORIZATION

Every serving node SHALL require explicit authorization.

A NodeAuthorization SHALL identify:

```text
entity_root
node_id
public_key
permitted_services
network scopes
publication scopes
data scopes
time limits
delegation limits
recovery behavior
revocation status
authorization signatures
```

A node SHALL NOT be permitted to publish arbitrary services merely because it possesses Entity data.

---

# 12. NODE REVOCATION

A lost, compromised, retired or replaced node SHALL be revocable.

Revocation SHALL NOT change the Entity root.

A revoked node SHALL not remain an authoritative service endpoint after revocation becomes effective.

Historical evidence created while the node was valid SHALL remain independently verifiable under historical key and authorization state.

---

# 13. MULTI-NODE ENTITY

One Entity MAY authorize multiple simultaneous nodes.

Example:

```text
ENTITY ROOT
├── Desktop Node
├── Phone Node
├── Home Server Node
├── NAS Storage Node
└── Optional Relay / Availability Node
```

Different nodes MAY serve different functions.

The architecture SHALL NOT assume one machine contains all Entity state.

---

# 14. SERVICE MANIFEST

Every public or shared ENTITY Domain SHALL be capable of publishing a signed machine-readable ServiceManifest.

The ServiceManifest SHALL identify:

```text
entity_root
domain_id
manifest_version
service_id
service_type
node_id
endpoint information
protocol version
capabilities
access class
required credentials
policy references
data classifications
economic terms reference where applicable
availability metadata
expiry
revocation status
signature
```

The ServiceManifest SHALL be independently verifiable.

---

# 15. SERVICE TYPES

The protocol SHALL be extensible and SHALL support service classes including:

```text
PRESENCE
PUBLIC_PROFILE
CONTENT
FILES
APPLICATION
API
MESSAGING
SEARCH
SOFTWARE
DATASET
DATA_OFFER
MARKETPLACE
LICENSING
PAYMENT
VERIFICATION
CREDENTIALS
AI_SERVICE
COMPUTE_TO_DATA
STREAM
NOTIFICATION
DISCOVERY
ECONOMIC_SERVICE
```

A human-facing site is therefore one presentation/service of an Entity Domain, not the domain itself.

---

# 16. DEVICE-NATIVE PRESENCE

An authorized Entity device SHALL be capable of publishing an Entity presence directly.

The owner SHALL NOT be required to first upload that presence to a third-party website platform.

The presence MAY include:

- human-readable pages;
- machine-readable data;
- products;
- software;
- media;
- credentials;
- public records;
- APIs;
- licensable assets;
- economic offers;
- messaging endpoints.

---

# 17. ENTITY-NATIVE RESOLUTION

ENTITY SHALL define a native resolution process.

Resolution SHALL conceptually perform:

```text
ENTITY NAME / ENTITY ID
        ↓
RESOLVE ENTITY ROOT
        ↓
VERIFY NAME / ROOT BINDING
        ↓
FETCH CURRENT SIGNED SERVICE MANIFEST
        ↓
VERIFY NODE AUTHORIZATION
        ↓
SELECT VALID SERVICE ENDPOINT
        ↓
APPLY CONNECTION / ACCESS POLICY
        ↓
CONNECT
```

Resolution SHALL NOT require DNS for ENTITY-native operation.

---

# 18. RESOLUTION PROOF

A resolver SHALL return verifiable evidence sufficient to determine:

- which Entity root is being resolved;
- which name or identifier was requested;
- which manifest version is current;
- which node is authorized;
- which service is being requested;
- expiry/revocation state;
- relevant signatures;
- relevant federation/witness evidence where applicable.

A resolver SHALL NOT be trusted merely because it returned an address.

---

# 19. DISTRIBUTED RESOLUTION

The resolution architecture SHOULD support multiple independent resolution sources.

No single BTG resolver SHALL be required for Entity existence.

Resolution MAY use a combination of:

- local cache;
- trusted peer;
- federated node;
- replicated directory;
- witness network;
- signed advertisements;
- local network discovery;
- user-authorized resolver.

The final authority SHALL derive from signed Entity state, not resolver ownership.

---

# 20. RESOLVER NON-AUTHORITY

A resolver:

```text
CAN FIND
```

but SHALL NOT thereby:

```text
OWN
CONTROL
LICENSE
REVOKE
TRANSFER
MONETIZE
```

the Entity.

Resolver unavailability SHALL degrade discovery, not erase identity.

---

# 21. DIRECT CONNECTION

Where network conditions permit, ENTITY SHOULD connect requesting devices directly to the authorized EntityNode.

The system SHALL authenticate the Entity and node cryptographically rather than trusting only an IP address.

A connection SHALL bind:

```text
requesting Entity/device
target Entity
target node
service
purpose
policy
session
protocol version
```

where applicable.

---

# 22. NETWORK ADDRESS INDEPENDENCE

An ENTITY Domain SHALL not be permanently bound to one:

- IPv4 address;
- IPv6 address;
- MAC address;
- ISP;
- router;
- subnet;
- physical location.

Address changes SHALL be reflected through signed current presence/resolution state.

---

# 23. NAT AND FIREWALL TRAVERSAL

ENTITY SHALL support connection establishment where nodes are behind common NAT/firewall configurations.

The architecture MAY include:

- peer-assisted traversal;
- rendezvous services;
- hole punching where safe;
- authorized relay services;
- local network routing;
- overlay networking.

No traversal provider SHALL become sovereign authority over the Entity.

---

# 24. OPTIONAL RELAY

Relays MAY be used when direct connectivity is unavailable.

A relay SHALL be treated as transport infrastructure only unless separately delegated additional authority.

A relay SHALL NOT automatically gain:

```text
CONTENT_OWNERSHIP
SOVEREIGN_AUTHORITY
LICENSING_AUTHORITY
CONSENT_AUTHORITY
ECONOMIC_PARTICIPATION
```

Relay authorization SHALL be explicit, scoped and revocable.

---

# 25. RELAY PRIVACY

Where technically feasible, relay infrastructure SHOULD be unable to read protected payload contents.

ENTITY SHOULD support end-to-end encrypted service sessions.

Relays MAY observe minimum routing metadata necessary to perform their authorized role.

Metadata exposure SHALL be documented and minimized.

---

# 26. OPTIONAL HIGH-AVAILABILITY MIRRORS

An Entity MAY authorize mirrors for availability.

Mirrors SHALL NOT become authoritative merely because they contain copies.

Mirror state SHALL identify:

- source Entity;
- replication scope;
- allowed services;
- freshness;
- signatures;
- expiry;
- revocation;
- conflict state.

---

# 27. LOCAL-FIRST OPERATION

Core Entity state SHALL remain usable locally where technically possible.

An Entity SHALL be able to:

- inspect identity;
- inspect rights;
- inspect policies;
- manage local services;
- sign local events;
- serve local-network services;
- create pending changes;

without mandatory internet connectivity.

---

# 28. LOCAL NETWORK DISCOVERY

ENTITY SHOULD support local discovery among authorized devices.

A local network MAY discover an Entity service without querying a global provider.

Local discovery SHALL still authenticate the Entity and node.

Physical proximity or network presence SHALL NOT be treated as authorization.

---

# 29. OFFLINE IDENTITY CONTINUITY

Internet loss SHALL NOT destroy Entity identity.

Previously obtained verifiable state SHOULD remain usable within policy and freshness limits.

Operations requiring fresh global state or exclusive finality SHALL fail closed or enter explicit pending state.

---

# 30. DATA LOCALITY

An Entity SHALL be able to keep data on owner-controlled devices.

Publishing a service SHALL NOT require copying all underlying data to a central ENTITY service.

A service MAY expose:

- selected content;
- transformed output;
- metadata;
- API result;
- streamed data;
- computation result;

without surrendering the source dataset.

---

# 31. COMPUTATION-TO-ENTITY DATA

ENTITY SHOULD support requests where approved computation executes against locally held data.

Conceptual flow:

```text
REQUESTER
   ↓
SIGNED REQUEST / PURPOSE / LICENCE
   ↓
ENTITY POLICY
   ↓
OWNER NODE
   ↓
LOCAL COMPUTATION
   ↓
PERMITTED RESULT ONLY
```

Raw source data need not leave the owner-controlled environment.

---

# 32. PUBLIC / PRIVATE / RESTRICTED SERVICES

Each service SHALL declare an access class.

At minimum:

```text
PUBLIC
RELATIONSHIP_ONLY
CREDENTIAL_REQUIRED
LICENSE_REQUIRED
PAID
PRIVATE
LOCAL_ONLY
DISABLED
```

A public Entity presence SHALL NOT imply all Entity data is public.

---

# 33. ACCESS POLICY

Access SHALL evaluate where applicable:

- requesting Entity;
- requesting device;
- trust level;
- credential;
- service;
- purpose;
- licence;
- policy;
- jurisdiction/configuration;
- payment state;
- rate limit;
- time;
- revocation;
- consent.

Failure SHALL default deny.

---

# 34. ECONOMIC SERVICES

An EntityNode MAY publish economic services including:

- licensable datasets;
- software;
- media;
- APIs;
- AI access;
- subscriptions;
- compute services;
- professional services;
- digital goods;
- data-pool participation.

Economic discovery SHALL NOT imply permission to use.

---

# 35. DATA ECONOMY WITHOUT CENTRAL DATA OWNERSHIP

ENTITY SHALL support economic interaction without requiring BTG or another intermediary to own the underlying data.

A valid economic flow MAY be:

```text
BUYER ENTITY
    ↓
DISCOVERS OFFER
    ↓
VERIFIES PROVIDER ENTITY
    ↓
REVIEWS RIGHTS / POLICY / TERMS
    ↓
NEGOTIATES OR ACCEPTS LICENCE
    ↓
AUTHORIZED ACCESS / COMPUTE / DELIVERY
    ↓
USAGE EVIDENCE
    ↓
SETTLEMENT
    ↓
ACCOUNTING
    ↓
ECONOMIC PARTICIPATION
```

The data MAY remain on the owner-controlled node throughout the interaction.

---

# 36. ECONOMIC NON-CUSTODY PRINCIPLE

BTG, a resolver, relay, marketplace or discovery provider SHALL NOT automatically acquire an economic interest merely because it facilitates discovery or transport.

Any fee, royalty, revenue share or commission SHALL require an explicit basis.

---

# 37. ENTITY DOMAIN EXPORT

An Entity Domain SHALL be exportable.

A DomainExportManifest SHALL include or reference:

```text
entity_root
domain_id
name claims
aliases
node authorizations
service manifests
resolution records
policies
revocations
migration history
economic service descriptors
schema versions
cryptographic algorithms
evidence roots
known external dependencies
```

No proprietary BTG database SHALL be required to interpret the export.

---

# 38. DEVICE MIGRATION

A user SHALL be able to move serving responsibility from Device A to Device B without changing the Entity.

Required invariant:

```text
ENTITY_ROOT_A == ENTITY_ROOT_B
DOMAIN_ID_A    == DOMAIN_ID_B
```

The migration SHALL:

1. authorize Device B;
2. transfer or reconstruct required state;
3. verify state;
4. publish updated service manifests;
5. revoke or retire Device A as appropriate;
6. preserve history.

---

# 39. PROVIDER MIGRATION

A hosted Entity node MAY be moved between providers without changing the Entity Domain.

Provider migration SHALL preserve:

- Entity root;
- name bindings;
- service identity;
- rights semantics;
- policy semantics;
- economic history;
- provenance;
- signed historical records.

---

# 40. LOSS OF SERVING NODE

Loss of all currently serving nodes SHALL NOT erase the Entity.

The Entity SHALL remain recoverable from valid sovereign backup/export mechanisms.

After recovery, new nodes MAY be authorized and the same domain restored.

---

# 41. LOSS OF BTG

Qualification SHALL include a scenario in which BTG-operated:

- resolver;
- relay;
- directory;
- hosting;
- marketplace;
- verification service;

are unavailable.

The sovereign Entity SHALL remain recoverable and independently interpretable.

Where independent network infrastructure exists, the Entity SHOULD remain resolvable without BTG.

---

# 42. NO SILENT CENTRAL FALLBACK

Implementations SHALL NOT advertise decentralized or sovereign operation while silently requiring a central BTG service for:

- name authority;
- root identity;
- service authorization;
- domain renewal;
- recovery;
- interpretation;
- transaction verification.

Any mandatory dependency SHALL be explicitly declared and treated as an architectural blocker against full sovereign qualification.

---

# 43. NODE COMPROMISE

A compromised node SHALL NOT automatically compromise the sovereign Entity root.

Node authority SHALL be scoped.

High-impact actions SHOULD require stronger authority than ordinary service publication.

Root/recovery authority SHOULD use separate protected keys.

---

# 44. CONTENT INTEGRITY

Published content and service responses MAY be cryptographically committed or signed where appropriate.

ENTITY SHALL distinguish:

```text
served by authorized node
content integrity verified
provenance verified
rights verified
factual truth established
```

These states SHALL NOT be conflated.

---

# 45. SERVICE VERSIONING

Service manifests and descriptors SHALL be versioned.

Historical versions SHALL remain interpretable where retained.

Breaking changes SHALL not silently reinterpret signed historical transactions.

---

# 46. CACHE SEMANTICS

Caches MAY improve performance.

Cached state SHALL include:

- source;
- version;
- expiry;
- signature;
- freshness;
- revocation reference where applicable.

A stale cache SHALL NOT override newer authoritative signed state.

---

# 47. ANTI-ROLLBACK

ENTITY SHALL detect attempts to present an older valid domain/service state as current when newer state is known.

Rollback handling SHALL be explicit.

Older valid history SHALL remain verifiable without becoming current authority.

---

# 48. FEDERATION

Independent ENTITY implementations SHALL be able to participate in domain resolution and service discovery.

Federation SHALL negotiate:

- protocol version;
- schema version;
- supported cryptography;
- service types;
- capability extensions.

A federation operator SHALL not become the owner/controller of the participating Entity.

---

# 49. PROTOCOL OPENNESS

The protocol, schemas and verification rules required to:

- create a compatible Entity Domain;
- resolve an Entity;
- verify a ServiceManifest;
- authorize a node;
- verify a node;
- publish a service;
- revoke a node;
- migrate a domain;
- verify an export;

SHALL be publicly documented for qualified open-federation operation.

---

# 50. OPEN-SOURCE REFERENCE IMPLEMENTATION

BTG SHOULD provide an open-source reference implementation for the sovereign core sufficient for an owner to:

- create or import an Entity;
- operate a local node;
- publish an ENTITY-native domain;
- resolve other Entities;
- verify signed service state;
- export and recover the domain.

Commercial services MAY exist around the open sovereign core.

The open sovereign core SHALL NOT intentionally require a paid BTG service for continued Entity existence.

---

# 51. INDEPENDENT IMPLEMENTATION

Open-federation qualification SHALL ultimately include at least one non-BTG implementation that can:

- resolve the same Entity Domain;
- verify the same root;
- interpret the same ServiceManifest;
- connect to a compatible service;
- reproduce the same authorization meaning.

---

# 52. SECURITY THREAT MODEL

Qualification SHALL include:

- malicious resolver;
- malicious relay;
- malicious peer;
- spoofed Entity name;
- name-conflict manipulation;
- stale manifest;
- forged manifest;
- forged node authorization;
- revoked node replay;
- endpoint substitution;
- route hijack;
- service downgrade;
- replayed session;
- cache poisoning;
- malicious mirror;
- compromised node;
- compromised relay;
- metadata correlation;
- denial of service;
- Sybil discovery nodes;
- false availability advertising;
- rollback to stale domain state;
- unauthorized economic offer;
- hidden central dependency.

---

# 53. NAME-SPOOFING DEFENCE

Human-readable names SHALL never substitute for cryptographic verification.

The UI SHALL make it possible to distinguish:

```text
NAME MATCHED
ENTITY VERIFIED
ORGANIZATION VERIFIED
CREDENTIAL VERIFIED
```

A similar-looking name SHALL NOT inherit trust.

---

# 54. DISCOVERY SYBIL DEFENCE

The network SHALL assume malicious parties may advertise large numbers of fake nodes, names or services.

Discovery ranking and trust SHALL NOT be based solely on advertisement volume.

Trust MAY incorporate:

- verified credentials;
- relationship trust;
- independent witnesses;
- historical reliability;
- user policy;
- organizational attestations.

---

# 55. PRIVACY

ENTITY-native resolution SHALL minimize unnecessary disclosure.

A public name SHALL NOT require publication of:

- private root recovery keys;
- private data paths;
- private asset inventory;
- private relationships;
- full device inventory.

Pairwise or context-specific identifiers SHOULD be used where appropriate.

---

# 56. PRESENCE PRIVACY

An Entity SHOULD be able to publish different presence scopes.

Examples:

```text
PUBLIC PRESENCE
BUSINESS RELATIONSHIP PRESENCE
PRIVATE PEER PRESENCE
LOCAL DEVICE PRESENCE
```

The same sovereign Entity need not expose identical service metadata to every requester.

---

# 57. AVAILABILITY DOES NOT DEFINE EXISTENCE

An Entity may be temporarily unreachable.

`OFFLINE` SHALL NOT mean:

```text
DELETED
EXPIRED
UNOWNED
AVAILABLE_FOR_REASSIGNMENT
```

Temporary network absence SHALL not permit another party to claim the Entity identity or name automatically.

---

# 58. HUMAN EXPERIENCE

A user SHOULD be able to open an ENTITY-native client and enter or select an Entity name.

The client SHOULD:

1. resolve the Entity;
2. verify identity;
3. retrieve the signed service manifest;
4. present available services;
5. connect to the selected service;
6. apply trust and policy indicators.

The experience SHOULD NOT require the user to understand IP addresses, cryptographic keys or routing internals.

---

# 59. APPLICATION EXPERIENCE

An Entity service MAY present rich interactive applications.

ENTITY SHALL NOT limit service presentation to static pages.

Applications MAY execute on:

- requester device;
- owner node;
- both;
- authorized compute environment.

Application execution SHALL respect Entity policy and capability boundaries.

---

# 60. MESSAGING

An Entity Domain SHOULD support discoverable messaging endpoints.

Messaging endpoints SHALL be separately authorized and revocable.

A message endpoint provider SHALL not automatically own the Entity's relationship graph or message content.

---

# 61. SOFTWARE DISTRIBUTION

An Entity MAY publish software directly from authorized nodes.

Software publication SHOULD integrate:

- release identity;
- hashes;
- signatures;
- SBOM;
- RBOM;
- PBOM;
- provenance;
- version;
- rights/licence.

---

# 62. DATASET DISTRIBUTION

An Entity MAY publish dataset offers without publishing raw data publicly.

Discovery MAY expose only:

- description;
- schema;
- provenance summary;
- rights summary;
- price/terms;
- access method;
- quality evidence.

Actual access SHALL require applicable authorization.

---

# 63. AI SERVICES

An Entity MAY expose AI services without granting the AI provider sovereign authority.

A service SHALL distinguish:

```text
AI_INFERENCE
AI_EVALUATION
AI_TRAINING
MODEL_TUNING
```

Permission for one SHALL NOT imply another.

---

# 64. RECOVERY

Domain recovery SHALL reconstruct:

- Entity root linkage;
- name claims;
- node authorizations;
- service manifests;
- revocations;
- policies;
- economic service state;
- migration history.

Recovery SHALL be tested.

A backup that has never been restored SHALL not satisfy qualification.

---

# 65. DESTRUCTIVE DOMAIN RECOVERY TEST

Qualification SHALL perform:

```text
CREATE ENTITY
↓
CREATE ENTITY DOMAIN
↓
AUTHORIZE DEVICE A
↓
PUBLISH SERVICES
↓
VERIFY FROM DEVICE B
↓
GENERATE SOVEREIGN EXPORT
↓
REMOVE DEVICE A STATE
↓
REMOVE BTG OPTIONAL SERVICES
↓
RESTORE ON DEVICE C
↓
AUTHORIZE DEVICE C
↓
REPUBLISH SERVICES
↓
RESOLVE SAME ENTITY
↓
VERIFY SAME ENTITY ROOT
↓
VERIFY SAME DOMAIN ID
↓
VERIFY RIGHTS / POLICY / ECONOMIC STATE
```

Required:

```text
ENTITY_ROOT_BEFORE == ENTITY_ROOT_AFTER
DOMAIN_ID_BEFORE    == DOMAIN_ID_AFTER
```

---

# 66. PROVIDER-FREE QUALIFICATION

At least one qualification scenario SHALL operate with:

```text
NO PAID DOMAIN REGISTRAR
NO DNS DEPENDENCY FOR ENTITY-NATIVE RESOLUTION
NO CLOUD HOST
NO BTG HOST
NO PAID RELAY
```

Two user-controlled devices SHALL be able to discover, authenticate and communicate using ENTITY-native mechanisms in a supported network environment.

---

# 67. PROVIDER-REPLACEMENT QUALIFICATION

Run:

```text
ENTITY
↓
DEVICE / PROVIDER A
↓
PUBLISH SERVICES
↓
VERIFY
↓
MIGRATE
↓
DEVICE / PROVIDER B
↓
RESOLVE SAME ENTITY DOMAIN
↓
VERIFY SAME ROOT
↓
VERIFY SAME SERVICE AUTHORITY
```

Provider A SHALL retain no undeclared future authority.

---

# 68. MALICIOUS RESOLVER QUALIFICATION

A malicious resolver SHALL attempt to return:

- wrong Entity;
- wrong node;
- revoked node;
- stale manifest;
- attacker endpoint;
- modified service list.

The client SHALL reject responses that fail cryptographic or semantic verification.

---

# 69. MALICIOUS RELAY QUALIFICATION

A relay SHALL attempt:

- payload modification;
- endpoint substitution;
- replay;
- traffic redirection;
- fake completion;
- authority assertion.

The relay SHALL not be able to create valid Entity authority from transport possession.

---

# 70. DEVICE-THEFT QUALIFICATION

Assume Device A is stolen.

Required:

1. revoke Device A;
2. preserve Entity root;
3. preserve domain;
4. restore/activate Device B;
5. reject new authoritative publications from Device A;
6. preserve historical valid evidence.

---

# 71. REQUEST-STORM QUALIFICATION

The resolution and service layers SHALL be load-tested under concurrent:

- discovery;
- resolution;
- authentication;
- service requests;
- invalid requests;
- replay;
- stale manifests;
- malicious advertisements.

Security checks SHALL not be disabled under load.

---

# 72. FAILURE STATES

The domain subsystem SHALL implement explicit states including:

```text
NORMAL
LOCAL_ONLY
PARTIALLY_REACHABLE
RELAY_REQUIRED
DEGRADED
OFFLINE
RESOLUTION_CONFLICT
STALE_STATE
PROVIDER_UNAVAILABLE
RECOVERY
COMPROMISED_NODE
```

Transitions SHALL be logged and testable.

---

# 73. NO AUTOMATIC REASSIGNMENT ON OUTAGE

Network outage, device outage, failure to contact a provider or temporary inactivity SHALL NOT automatically free an Entity identity or Entity name for reassignment.

Any name-expiry policy, if one exists, SHALL be independently governed and SHALL NOT be equivalent to a commercial registrar lease by default.

---

# 74. ECONOMIC FAILURE INVARIANT

Loss of a node, relay, resolver or provider SHALL NOT silently alter:

- balances;
- rights;
- licences;
- economic participation;
- Digital Commodity state;
- corporate-capital state.

Infrastructure failure SHALL NOT manufacture or destroy economic rights.

---

# 75. AUDIT

Material domain operations SHALL create audit events including:

- name claim;
- name conflict;
- node authorization;
- node revocation;
- service publication;
- service update;
- provider migration;
- domain export;
- domain restore;
- resolver conflict;
- security rejection.

---

# 76. OBSERVABILITY

Implementations SHOULD measure:

- resolution success rate;
- resolution latency;
- direct-connect success;
- relay usage;
- node availability;
- stale-manifest rate;
- verification failure;
- malicious-response rejection;
- migration success;
- restore success.

Metrics SHALL not become a reason to centralize sovereign authority.

---

# 77. IMPLEMENTATION PHASES

## Phase A — Local Sovereign Domain

Deliver:

- EntityDomain object;
- EntityName;
- EntityNode;
- NodeAuthorization;
- signed ServiceManifest;
- local resolution;
- direct local service access;
- export/recovery.

## Phase B — Internet Peer Resolution

Deliver:

- distributed/federated discovery;
- signed resolution;
- changing network-address support;
- direct peer connection;
- NAT traversal;
- optional relays.

## Phase C — Multi-Node Presence

Deliver:

- multi-device authorization;
- service distribution;
- failover;
- mirrors;
- migration;
- node revocation.

## Phase D — Economic Entity Services

Deliver:

- data offers;
- licensing endpoints;
- payment endpoints;
- usage receipts;
- computation-to-data;
- marketplace discovery without mandatory central custody.

## Phase E — Open Federation

Deliver:

- published protocol;
- independent implementations;
- non-BTG resolution;
- interoperability qualification.

---

# 78. REQUIRED REFERENCE SOFTWARE

The reference implementation SHOULD include:

```text
entity-domain
entity-node
entity-resolver
entity-service
entity-relay
entity-export
entity-restore
entity-verify
```

Names are illustrative.

Each tool SHALL be independently testable.

---

# 79. REQUIRED PROTOCOL SPECIFICATIONS

The project SHALL publish at minimum:

```text
ENTITY Domain Identifier Specification
ENTITY Name Claim Specification
ENTITY Node Authorization Specification
ENTITY Service Manifest Specification
ENTITY Resolution Protocol
ENTITY Presence Advertisement Specification
ENTITY Direct Session Protocol
ENTITY Relay Protocol
ENTITY Domain Export Specification
ENTITY Domain Recovery Specification
ENTITY Domain Migration Specification
ENTITY Economic Service Discovery Specification
```

---

# 80. REQUIRED TEST VECTORS

Publish valid and invalid vectors for:

- Entity root;
- name binding;
- name conflict;
- node authorization;
- node revocation;
- service manifest;
- resolution proof;
- stale state;
- rollback;
- relay authorization;
- domain export;
- domain restore.

Independent implementations SHALL be able to reproduce expected results.

---

# 81. RELEASE GATES

The subsystem SHALL not be qualified until all applicable gates pass:

```text
DOMAIN_IDENTITY_GATE
NAME_AUTHORITY_GATE
NODE_AUTHORIZATION_GATE
RESOLUTION_GATE
DIRECT_CONNECT_GATE
PROVIDER_INDEPENDENCE_GATE
RECOVERY_GATE
SECURITY_GATE
PRIVACY_GATE
ECONOMIC_SEMANTICS_GATE
OPEN_INTEROPERABILITY_GATE
```

A failed gate SHALL not be offset by another gate.

---

# 82. AUTOMATIC FAIL CONDITIONS

Any of the following SHALL block qualification:

- Entity existence depends on annual domain payment;
- DNS is mandatory for ENTITY-native resolution;
- BTG resolver is the only authoritative resolver;
- BTG cloud is required to interpret the Entity;
- losing the current host destroys the Entity identity;
- device replacement changes the Entity root;
- resolver can redirect without detection;
- revoked node can still publish authoritative state;
- relay can become licensor/owner by assertion;
- provider migration silently changes rights or economic state;
- domain export omits authority state while claiming completeness;
- recovery creates a new Entity instead of restoring the existing one;
- self-hosted node operation requires hidden central permission;
- user data must be centrally uploaded merely to participate;
- optional service nonpayment destroys sovereign domain existence.

---

# 83. SYSTEM ACCEPTANCE DEFINITION

The sovereign-domain subsystem is architecturally complete only when a person or organization can:

1. create or recover a sovereign Entity;
2. establish an ENTITY-native domain without purchasing a traditional domain;
3. authorize their own computer/device as an EntityNode;
4. publish a signed service manifest;
5. expose a human-facing or machine-facing service directly from that node;
6. have another ENTITY-capable device resolve the Entity without DNS being the source of authority;
7. independently verify the Entity root, node and service;
8. apply public/private/licensed access policy;
9. migrate the domain to another device without changing the Entity;
10. revoke a lost or compromised node;
11. preserve identity, rights, provenance, policies and economic state through migration;
12. export and recover the entire domain state;
13. continue to interpret the Entity without BTG;
14. use optional relays/hosts without granting them sovereign authority;
15. participate in economic transactions without transferring ownership of all source data to a central platform;
16. pass destructive recovery and provider-replacement tests;
17. interoperate with an independent implementation.

---

# 84. ENGINEERING DEFINITION OF THE COMPLETED SUBSYSTEM

When implemented and qualified, this subsystem is not merely:

- web hosting;
- DNS;
- peer-to-peer file sharing;
- a wallet;
- a personal server;
- a distributed database.

It is:

> **a sovereign digital-presence and service layer in which a person or organization can operate a persistent machine-verifiable digital domain from authorized devices they control, publish services directly, move those services between devices and providers without changing the Entity, and participate in digital economic relationships without renting continued digital existence from an intermediary.**

---

# 85. NON-NEGOTIABLE FINAL PRINCIPLE

The architecture SHALL preserve this principle through every implementation decision:

> **Your device may host your Entity, but it does not define your Entity.**

> **Your network may carry your Entity, but it does not control your Entity.**

> **A resolver may locate your Entity, but it does not own your Entity.**

> **A relay may connect your Entity, but it does not gain rights over your Entity.**

> **A provider may assist your Entity, but it must remain replaceable.**

> **Your data, lawful rights, assets, provenance and economic participation remain governed by the Entity authority model.**

And ultimately:

> **A person or organization should not have to keep paying another company merely to continue existing digitally.**

---

# APPENDIX A — CORE INVARIANTS

```text
ENTITY_ROOT != DEVICE_ID

ENTITY_DOMAIN != DNS_DOMAIN

ENTITY_DOMAIN != HOSTING_ACCOUNT

ENTITY_DOMAIN != IP_ADDRESS

ENTITY_DOMAIN != BTG_ACCOUNT

RESOLUTION_PROVIDER != SOVEREIGN_AUTHORITY

RELAY_PROVIDER != SOVEREIGN_AUTHORITY

HOSTING_PROVIDER != SOVEREIGN_AUTHORITY

STORAGE_PROVIDER != SOVEREIGN_AUTHORITY

ENTITY_ROOT_BEFORE_DEVICE_MIGRATION
==
ENTITY_ROOT_AFTER_DEVICE_MIGRATION

DOMAIN_ID_BEFORE_PROVIDER_MIGRATION
==
DOMAIN_ID_AFTER_PROVIDER_MIGRATION

LOSS_OF_PROVIDER
!=
LOSS_OF_ENTITY

LOSS_OF_BTG
!=
LOSS_OF_ENTITY
```

---

# APPENDIX B — REQUIRED INTEGRATION INTO SERS-ENTITY-003

The master ENTITY engineering design SHALL reference this specification as a mandatory subordinate architecture for all claims involving:

- sovereign domain;
- device-native presence;
- self-operated Entity nodes;
- Entity name resolution;
- direct device access;
- provider-independent digital presence;
- open federation;
- domain recovery;
- provider-free qualification.

Future ENTITY release gates SHALL treat this document as normative unless formally superseded through architecture change control.

---

# APPENDIX C — REQUIRED QUALIFICATION EVIDENCE

A qualified implementation SHALL produce a sealed evidence package containing:

```text
ENTITY_DOMAIN_QUALIFICATION_CURRENT.json
ENTITY_DOMAIN_TEST_RESULTS.json
ENTITY_DOMAIN_RTM.json
ENTITY_DOMAIN_RTM.sha256
ENTITY_DOMAIN_RELEASE_MANIFEST.json
ENTITY_DOMAIN_RELEASE_MANIFEST.sha256
ENTITY_DOMAIN_VALID_VECTORS/
ENTITY_DOMAIN_INVALID_VECTORS/
ENTITY_DOMAIN_DESTRUCTIVE_RECOVERY/
ENTITY_DOMAIN_PROVIDER_REPLACEMENT/
ENTITY_DOMAIN_MALICIOUS_RESOLVER/
ENTITY_DOMAIN_MALICIOUS_RELAY/
ENTITY_DOMAIN_INDEPENDENT_INTEROP/
```

The evidence SHALL identify:

- repository commit;
- source hashes;
- binary hashes;
- protocol versions;
- schema versions;
- test counts;
- pass/fail status;
- random seeds;
- known limitations;
- independent-verification results;
- remaining external dependencies.

---

# APPENDIX D — FINAL RELEASE CLAIM

Only after the requirements in this specification are implemented and qualified may a release claim:

> **ENTITY provides a sovereign device-native digital domain whose continued existence, service identity, authority and economic state do not depend on a rented traditional domain, mandatory cloud host or continued operation of BTG infrastructure.**

Any such claim SHALL be bounded to the actual qualification scope and evidence.
