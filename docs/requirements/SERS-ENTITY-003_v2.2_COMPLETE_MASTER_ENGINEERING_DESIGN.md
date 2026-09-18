# ENTITY SOVEREIGN DIGITAL RIGHTS PLATFORM
## Complete System Engineering Requirements Specification
### SERS-ENTITY-003 — Complete Master Engineering Design v2.2

**Baseline lineage:** Incorporates SERS-ENTITY-001 — Target Architecture v1.0 and SERS-ENTITY-002 — Complete Master Engineering Design v2.0 in full.  
**Engineering expansion:** Integrates the 10/10 architecture, assurance, qualification, interoperability and production-maturity plan; the corporate-capital and digital-commodity economy architecture; the independently reproducible transaction milestone; and the Sovereign Authority Doctrine governing platform non-authority, provider replaceability and continuity of lawful Entity control.  
**Normative scope:** Sections 1–172. Sections 1–120 remain the architectural baseline; Sections 121–150 make the baseline executable, traceable, adversarially testable and independently verifiable; Sections 151–170 add corporate Entity capitalization, productive digital-commodity aggregation, share governance, disclosure, transfer control and capital-market evidence boundaries; Section 171 defines the independently reproducible ENTITY transaction as the transformational proof of sovereign, machine-verifiable economic infrastructure; Section 172 elevates sovereign authority, platform non-authority, provider replaceability and continuity of lawful digital control into an explicit cross-cutting doctrine and qualification target.

**System:** ENTITY  
**Integration Environment:** NIKI + ADAM + BSIE + BECP  
**Classification:** Core Platform Architecture  
**Document Status:** Authoritative Target Engineering Requirement  
**Purpose:** Design, build, qualify and operate a sovereign digital identity, data, provenance, rights, consent, licensing, usage-control and economic-participation infrastructure.


## v2.0 INTEGRATION NOTE

This master document preserves the original 120-section ENTITY architecture and integrates the production-assurance plan as normative engineering requirements. The expansion does not declare the system production-ready; it defines what must be implemented and evidenced before such a claim is justified.

The controlling engineering chain is:

**REQUIREMENT → DESIGN → CODE/CONFIGURATION → TEST → RESULT → EVIDENCE → HASH → RELEASE**

The controlling maturity rule is:

**Specified is not implemented. Implemented is not verified. Verified is not qualified. Qualified claims require reproducible evidence.**

## v2.1 CORPORATE-CAPITAL INTEGRATION NOTE

This revision adds a corporate-capital layer above ENTITY's existing asset, usage, licensing, settlement and accounting architecture.

The corporate-capital layer SHALL preserve a strict separation among:

**productive digital-commodity activity** — verified access, usage, licensing, subscriptions, royalties, services and other attributable activity of lawful digital assets;

**corporate economic state** — accounting, assets, liabilities, recognized revenue, cash flows, obligations, retained earnings and other properly classified economic facts of a corporate Entity;

**corporate equity** — legally authorized shares or equivalent equity interests issued by the corporate Entity; and

**market valuation** — externally observed or explicitly modelled valuation evidence that SHALL NOT be manufactured merely by internal ledger activity.

The governing causal model is:

`DIGITAL COMMODITY → RIGHTS/POLICY → AUTHORIZED USE → USAGE EVIDENCE → CONTRACT/OBLIGATION → SETTLEMENT/ACCOUNTING → CORPORATE ECONOMIC STATE → DISCLOSURE/METRICS → CAPITAL-MARKET INTERPRETATION`

Usage SHALL NOT automatically issue shares, create profit, create cash, or set a share price.

Share issuance, transfer, repurchase, cancellation, conversion, dividend/distribution and other corporate actions SHALL occur only through explicitly authorized corporate-capital state transitions.

The term **Digital Commodity** in this specification is an internal ENTITY economic/engineering classification for a lawfully controlled digital asset or service capable of measurable commercial use. It SHALL NOT by itself assert that the item is legally classified as a commodity, security, derivative, currency, financial instrument or other regulated product in any jurisdiction.

## v2.2 SOVEREIGN AUTHORITY DOCTRINE INTEGRATION NOTE

This revision elevates an architectural consequence already present throughout ENTITY into an explicit normative doctrine:

**the party that possesses, hosts, stores, transports, indexes, processes or monetizes access to digital information does not thereby become the sovereign authority over the person or organization to whom the lawful authority, rights, consent powers or economic interests belong.**

ENTITY is not designed around the proposition that an Entity automatically owns every byte it can observe or possess. It is designed to preserve machine-verifiable distinctions among possession, custody, storage control, sovereign authority, authorship, legal rights, consent authority, licensing authority, authorized usage and economic participation.

The intended architectural inversion is:

**platform-centric model**

`PLATFORM → stores data → decides access → defines platform rights → monetizes usage → retains history → controls practical export`

becomes, within the lawful and contractually permitted scope of ENTITY:

**Entity-authority model**

`ENTITY OWNER/CONTROLLER → controls authority → chooses storage → sets policy → records provenance → grants licences → observes/attests usage → records economic participation → exports/migrates sovereign state`

Storage providers, cloud services, connectors, marketplaces, AI providers, network operators, payment providers and BTG infrastructure MAY perform authorized roles, but those roles SHALL remain explicit, scoped, revocable where applicable and evidentially distinct from sovereign authority.

The governing design question is therefore not:

**Who currently has the bytes?**

It is:

**Which Entity or authorized party has which evidence-backed authority, right, duty, consent power, licence, custody role, processing permission or economic participation interest — and can those relationships survive replacement or loss of the platform currently providing infrastructure?**

This note does not assert legal ownership where law, contract or evidence does not establish it. ENTITY sovereignty SHALL operate only over the identity, state, permissions, records, content and rights that the Entity is lawfully entitled to control.

---

# 1. SYSTEM MISSION

ENTITY SHALL provide a person, company, organization, collective or other authorized digital principal with maximum lawful control over its digital identity, information, creative assets, knowledge capital, provenance, rights, permissions, licensing relationships and economic participation.

ENTITY SHALL preserve the principle that custody, storage, hosting, transport, indexing, processing or observation of data does not by itself make the custodian, storage provider, platform, connector, AI provider, network operator or BTG the authoritative controller, owner or rights-holder of that data or of the Entity's digital existence.

ENTITY SHALL NOT claim that possession of a file automatically establishes copyright, ownership, consent, authenticity, monetary value or unrestricted commercialization rights.

ENTITY SHALL distinguish cryptographic evidence from legal claims, legal claims from verified facts, and market value from arbitrary internally assigned numbers.

ENTITY SHALL operate according to the principle:

**Private by default.  
Default deny.  
Explicit enrollment.  
Least privilege.  
Provenance before valuation.  
Rights before licensing.  
Usage before settlement.  
Settlement before realized monetary value.**

ENTITY SHALL NOT require public blockchain participation, cryptocurrency ownership, gas fees, exchange accounts or payment to establish an identity or participate in basic sovereign-data functionality.

---

# 2. SYSTEM DEFINITION

ENTITY is the sovereign identity, authority, digital-rights and data-economy substrate of the Blackmore architecture.

The separation of responsibilities SHALL be:

**NIKI** — intelligence, reasoning, explanation and user interaction.

**ADAM** — governed execution and agent action.

**BSIE** — authoritative entity/world relationship and state substrate.

**BECP** — governed communication and externally observable transaction boundary.

**ENTITY** — identity, authority, data rights, provenance, consent, policy, contract, usage and economic state.

ENTITY SHALL remain authoritative for rights and authority even when NIKI, ADAM or another AI system performs reasoning or execution.

No AI model SHALL become the authoritative owner of ENTITY state merely because it reasoned about that state.

---

# 3. CORE ARCHITECTURAL PRINCIPLES

## 3.1 Sovereignty

The owner/controller SHALL retain the ability to export their complete Entity state in documented interoperable formats.

BTG SHALL NOT architect ENTITY so that the continued existence of Blackmore Technology Group is required to recover or interpret a user's own sovereign records.

Critical identity, rights and provenance records SHALL have defined migration and recovery formats.

## 3.2 Separation of content and evidence

Raw private content SHALL NOT normally be written to the distributed ledger.

The ledger SHALL contain commitments, identifiers, signatures, provenance events, rights events, contract events, usage evidence, settlement evidence and other minimum necessary state.

Actual content SHALL remain in owner-authorized storage.

## 3.3 Claims are not facts

ENTITY SHALL NOT interpret:

`valid signature = legal ownership`

or:

`earliest timestamp = creator`

or:

`registered asset = authentic event`

or:

`file possession = commercialization right`.

All such statements SHALL be modeled as claims supported by defined evidence.

## 3.4 No silent rights transfer

Exporting an Entity asset to an external platform SHALL NOT alter the authoritative Entity source-asset record.

When an external platform requires contractual rights, ENTITY SHALL record those rights as a separate external-platform grant, agreement or export state.

## 3.5 No automatic monetization by discovery

Finding, hashing, indexing or registering a file SHALL NOT mint currency or create realized monetary value.

Realized value SHALL require a legitimate economic event such as a completed licence, authorized usage obligation, royalty, sale, service, contribution agreement or externally evidenced settlement.

## 3.6 Sovereign authority, custody and storage separation

ENTITY SHALL treat **authority over a sovereign digital domain** as distinct from the location or service that stores, hosts, transports, indexes, processes or observes its data.

The mere fact that a party possesses, stores, hosts, transmits, indexes, processes, backs up, caches or can technically access data SHALL NOT by itself establish that the party owns the data, controls the Entity, holds commercialization rights, may grant licences, may consent on behalf of the Entity, or may capture the resulting economic participation.

ENTITY SHALL model and preserve machine-verifiable distinctions among at least:

`POSSESSION`;

`CUSTODY`;

`STORAGE_CONTROL`;

`SOVEREIGN_AUTHORITY`;

`AUTHORSHIP`;

`CREATORSHIP`;

`LEGAL_RIGHTS`;

`CONSENT_AUTHORITY`;

`LICENSING_AUTHORITY`;

`AUTHORIZED_USAGE`;

`ECONOMIC_PARTICIPATION`.

Evidence supporting one relationship SHALL NOT silently establish another relationship.

A transfer or delegation of custody, storage, processing, hosting, platform access or technical possession SHALL NOT silently transfer sovereign authority, authorship, ownership, consent authority, licensing authority or economic rights.

The Entity owner/controller SHALL be able, subject to lawful rights, contractual obligations and configured policy, to:

choose where authorized content is stored;

change storage providers without changing the sovereign Entity root;

retain authoritative policy and rights state independently of the storage provider;

revoke or alter future access where legally and contractually permitted;

export and migrate the complete sovereign state without requiring the continued operation or permission of the previous storage or platform provider;

verify which external parties possess, custody, process, access, license or use data to the extent supported by available evidence; and

preserve the distinction between internal Entity authority and external legal or contractual rights that ENTITY cannot unilaterally override.

No platform or provider SHALL become the authoritative source of the Entity's identity, rights, consent, provenance or economic state merely because that platform or provider stores or processes Entity-controlled data.

---

# 4. SYSTEM TRUST MODEL

ENTITY SHALL formally distinguish six evidence origins:

`DIRECT_OBSERVATION`

`ENTITY_ASSERTION`

`COUNTERPARTY_ATTESTATION`

`EXTERNAL_AUTHORITATIVE_RECORD`

`DERIVED_INFERENCE`

`UNKNOWN`

Every material claim SHALL record its evidence origin.

Every material claim SHOULD additionally carry:

confidence;

evidence references;

signatures;

timestamps;

claimant;

verification status;

dispute status;

jurisdiction where relevant.

ENTITY SHALL never silently convert `UNKNOWN` into `VERIFIED`.

---

# 5. ENTITY EVIDENCE BOUNDARY

ENTITY SHALL maintain an explicit Evidence Boundary.

The Evidence Boundary defines what ENTITY itself could actually observe or cryptographically validate.

For AI interactions through ChatGPT, BECP or another model provider, ENTITY MAY evidence:

the outbound user/system request exposed to the integration;

the visible provider response;

response metadata actually exposed;

files created from the response;

source changes;

hashes;

commands;

build results;

test results;

user approvals;

subsequent revisions;

repository state;

release state.

ENTITY SHALL NOT claim access to:

hidden model reasoning;

undisclosed model state;

provider-internal routing;

internal safety processing;

undisclosed server logs;

undisclosed model training activity;

provider infrastructure events not exposed through an integration.

Unknown platform-internal activity SHALL remain explicitly marked `UNKNOWN`.

---

# 6. SOVEREIGN ROOT IDENTITY

## ID-001 — Stable root

An Entity identity SHALL be persistent independently of any individual operational cryptographic key.

The architecture SHALL NOT permanently equate:

`Entity identity = one Ed25519 public key`.

## ID-002 — Key hierarchy

An Entity SHALL support separate cryptographic authorities for:

root recovery;

identity assertions;

authentication;

contract signing;

device authorization;

data encryption;

payment authorization;

agent delegation;

temporary sessions.

## ID-003 — Rotation

All operational keys SHALL support rotation without changing the sovereign Entity root.

## ID-004 — Revocation

Compromised, retired or superseded keys SHALL be revocable.

Historical signatures SHALL remain verifiable with the historical key state and revocation timeline.

## ID-005 — Recovery

The system SHALL support configurable recovery including:

recovery key;

trusted guardians;

multisignature recovery;

time-delayed recovery;

organization recovery authorities;

emergency account lock;

device-loss recovery.

## ID-006 — Succession

The system SHALL support death, incapacity, corporate succession, dissolution and authorized estate transition.

## ID-007 — Organizational control

Organizations SHALL support threshold authority rather than relying on a single private key.

Examples include:

CEO OR CFO for low-risk operations;

CEO AND CFO for higher-value commitments;

board threshold for intellectual-property transfer;

multi-director threshold for root recovery change.

Authority policies SHALL be machine-enforceable.

---

# 7. PRIVACY-PRESERVING RELATIONSHIP IDENTITIES

The root Entity identifier SHALL normally remain private.

ENTITY SHALL support pairwise or purpose-specific identifiers.

One external relationship SHALL NOT necessarily expose the same public identifier used in another relationship.

Example:

`relationship:youtube:<opaque-id>`

`relationship:retailer:<opaque-id>`

`relationship:researcher:<opaque-id>`

may privately resolve to the same root Entity without exposing that correlation publicly.

ENTITY SHALL support selective disclosure.

A service requesting proof of a characteristic SHOULD receive only the minimum information required.

Where technically appropriate ENTITY SHOULD support standardized Verifiable Credentials.

ENTITY SHOULD support privacy-preserving proof schemes capable of demonstrating statements such as:

verified organization;

authorized director;

age threshold met;

verified human;

licensed professional;

membership;

without unnecessary disclosure of unrelated identity attributes.

---

# 8. ENTITY TRUST LEVELS AND SYBIL RESISTANCE

Free creation of a sovereign identity SHALL remain possible.

Verification status SHALL be separate from identity existence.

ENTITY SHALL support trust levels such as:

`SELF_CREATED`

`CONTACT_VERIFIED`

`DEVICE_ATTESTED`

`HUMAN_VERIFIED`

`ORGANIZATION_VERIFIED`

`PROFESSIONAL_CREDENTIAL_VERIFIED`

`AUTHORITY_ATTESTED`.

A higher trust level SHALL NOT automatically expose the real-world identity behind the credential.

Marketplace, governance and anti-fraud functions MAY require higher verification levels.

ENTITY SHALL implement controls against unlimited fake Entity creation being used to manipulate:

reputation;

marketplace demand;

data pools;

governance;

usage statistics;

value transfers;

ratings;

recommendation systems.

---

# 9. PERMISSIONED DATA SOURCE GATEWAY

ENTITY SHALL NOT require unrestricted access to every disk, folder, document repository or connected platform.

All sources SHALL be explicitly enrolled.

The source-access model SHALL be default deny.

A source SHALL support at least five modes:

**OFF** — no Entity access.

**OBSERVE** — metadata/change observation without ordinary content inspection.

**INDEX** — content may be inspected for private classification/indexing.

**PROVENANCE** — content may be hashed and lineage/history monitored.

**MANAGED** — full authorized Entity lifecycle management, subject to rights and governance policy.

Permissions SHALL be configurable at:

drive;

folder;

subfolder;

file;

repository;

application;

cloud source;

connector;

data class.

ENTITY SHALL support explicit exclusions that override inherited permissions.

Sensitive operating-system and credential locations SHOULD default to excluded.

---

# 10. HARD PROHIBITED / RESTRICTED SOURCE CLASSES

ENTITY SHALL NOT automatically ingest or expose:

password vaults;

authentication secrets;

private cryptographic keys;

browser session cookies;

OS credential stores;

API secrets;

security tokens;

unrelated users' protected directories;

system security databases.

Highly sensitive categories SHALL require explicit enrollment and additional policy.

Possession SHALL NOT imply economic licensing permission.

A received email, confidential customer record, employee file, medical record, copyrighted third-party document or private message SHALL NOT become commercially licensable merely because it exists on an Entity-controlled computer.

---

# 11. ENCRYPTED DATA VAULT

The Data Vault SHALL store content separately from the public/shared ledger.

Content SHALL be encrypted at rest.

Encryption keys SHALL be separated from storage-provider control wherever practical.

ENTITY SHOULD support per-asset or per-security-domain data encryption keys.

A compromised storage provider SHALL not automatically gain plaintext access.

The vault SHALL support:

local storage;

encrypted removable storage;

owner-authorized cloud storage;

redundant encrypted replicas;

offline recovery.

Metadata minimization SHALL apply.

Highly sensitive filenames and paths SHOULD be conceal-able from remote ledger participants.

---

# 12. CRYPTOGRAPHIC ERASURE AND DELETION

Deletion SHALL be modeled as an asset lifecycle operation rather than a simple filesystem delete.

ENTITY SHALL track known:

primary objects;

replicas;

backups;

caches;

derived previews;

indexes;

embedding caches;

temporary files;

export copies where visible.

Where complete physical deletion cannot be guaranteed, ENTITY SHOULD support cryptographic erasure by destroying applicable content-encryption keys.

The system SHALL distinguish:

`LOCAL_DELETED`

`CRYPTographically_ERASED`

`REMOTE_DELETION_REQUESTED`

`REMOTE_DELETION_ATTESTED`

`REMOTE_DELETION_UNVERIFIED`

`RETENTION_LEGALLY_REQUIRED`.

ENTITY SHALL never claim remote deletion when it cannot verify that deletion.

---

# 13. ASSET REGISTRY

Each registered asset SHALL receive an Entity Asset ID independent of its filename.

An asset record SHALL support:

asset ID;

asset class;

controlling Entity;

claimants;

content commitment;

content location reference;

security classification;

creation/observation time;

lineage;

provenance;

rights state;

policy state;

derivatives;

external exports;

economic history.

The local pathname MAY remain private.

---

# 14. HARD AND SOFT ASSET IDENTITY

ENTITY SHALL maintain exact cryptographic identity using strong hashes.

ENTITY SHALL also support derivative identification for media and transformed content.

Exact-hash mismatch SHALL NOT automatically mean the content is unrelated.

The system SHOULD support appropriate soft-binding mechanisms such as:

media fingerprints;

perceptual hashes;

watermarks;

provenance ingredient relationships;

other domain-specific similarity evidence.

Cryptographic equality and derivative similarity SHALL be reported separately.

---

# 15. C2PA CONTENT CREDENTIAL SUPPORT

ENTITY media provenance SHOULD be C2PA-compatible.

For supported media, ENTITY SHOULD be capable of generating, preserving, verifying and associating Content Credentials.

C2PA provenance SHALL complement rather than replace the Entity Rights & Claims Graph.

ENTITY SHALL distinguish:

**provenance verified**

from:

**content factually true**.

A cryptographically valid provenance chain SHALL NOT automatically certify that the depicted event is genuine.

---

# 16. SOFTWARE AND AI-ASSISTED DEVELOPMENT PROVENANCE

ENTITY SHALL support software and knowledge-development assets as first-class assets.

For AI-assisted engineering, the system SHOULD be able to represent:

human requirement;

architecture decision;

AI request;

visible AI response;

generated code;

human modification;

compiler output;

test result;

commit;

release;

qualification evidence.

The provenance system SHALL permit a record such as:

`Human originated requirement`

`AI provider assisted generation`

`Human selected/modified/integrated`

`Build verified`

`Tests passed`

`Released by organization`.

The system SHALL NOT misrepresent AI-generated text as wholly human-generated where provenance is known.

Conversely, use of AI assistance SHALL NOT cause ENTITY to erase the human or organizational contribution.

---

# 17. KNOWLEDGE CAPITAL

ENTITY SHALL recognize Knowledge Capital as a first-class asset class.

Knowledge Capital MAY include:

engineering discussions;

requirements;

architecture decisions;

source-code lineage;

bug/fix histories;

research;

test campaigns;

human/AI collaboration histories;

operational procedures;

validated datasets;

domain knowledge graphs.

The system SHALL support value analysis at three distinct layers:

**Asset Value** — usefulness of an individual asset.

**Relationship Value** — usefulness of provenance and relationships between assets.

**Corpus Value** — usefulness of an organized collection or verified dataset.

ENTITY SHALL NOT assume that volume alone creates value.

---

# 18. RIGHTS & CLAIMS GRAPH

The existing single-owner concept SHALL be superseded by a many-to-many Rights & Claims Graph.

One asset MAY simultaneously involve multiple rights and stakeholders.

Rights relationships SHALL support at minimum:

author;

creator;

copyright claimant;

copyright owner;

controller;

custodian;

personal-data subject;

depicted person;

trademark interest;

patent interest;

confidentiality interest;

licensee;

licensor;

royalty participant;

employee/employer interest;

collective owner;

guardian;

estate;

platform-license holder;

authorized agent.

Claims SHALL be independent of the content asset itself.

---

# 19. RIGHTS CLAIM DATA MODEL

A Rights Claim SHALL support:

claim ID;

asset or asset-set reference;

claimant Entity;

right type;

share/percentage where relevant;

scope;

territory;

jurisdiction;

legal basis;

effective date;

expiry;

evidence references;

signature;

verification level;

status;

challenge/dispute state;

superseding claim.

Claim status SHALL include:

`SELF_ASSERTED`

`CORROBORATED`

`VERIFIED`

`AUTHORITATIVELY_VERIFIED`

where appropriate.

Separate dispute state SHALL include:

`ACTIVE`

`CHALLENGED`

`DISPUTED`

`SUPERSEDED`

`ADJUDICATED`.

---

# 20. COLLECTIVE AND MULTI-PARTY RIGHTS

ENTITY SHALL support assets that cannot be represented by one owner.

The system SHALL support:

joint creators;

families;

research groups;

corporations;

communities;

data cooperatives;

collective datasets;

trusts;

estates;

other multi-party governance structures.

A collective policy SHALL support voting, thresholds, delegated representatives and other defined decision mechanisms.

---

# 21. RESTRICTED / NON-COMMODITIZABLE DATA

ENTITY SHALL support the classifications:

`PRIVATE`

`INTERNAL`

`RESTRICTED`

`NON_TRANSFERABLE`

`LICENSABLE`

`PUBLIC`.

The economic system SHALL respect those classifications.

An asset MAY be usable internally while explicitly prohibited from sale or third-party AI training.

ENTITY SHALL support cases where a user has lawful control over information but is not legally entitled to sell or sublicense all of it.

---

# 22. POLICY AND CONSENT ENGINE

ENTITY SHALL implement machine-readable rights policy.

The internal policy model SHOULD be interoperable with W3C ODRL concepts rather than creating an incompatible proprietary policy language.

Policies SHALL support:

permissions;

prohibitions;

duties;

constraints;

parties;

assets;

purposes;

territory;

duration;

payment;

attribution;

retention;

deletion;

audit;

sublicensing.

ENTITY MAY define an Entity-specific ODRL profile.

---

# 23. REQUIRED POLICY ACTION VOCABULARY

The system SHALL be extensible and SHALL support policy concepts including:

`VIEW`

`COPY`

`DOWNLOAD`

`PUBLIC_DISPLAY`

`COMMERCIAL_REUSE`

`DERIVATIVE_WORK`

`AI_TRAINING`

`AI_EVALUATION`

`AI_INFERENCE`

`MODEL_TUNING`

`EMBEDDING`

`INDEXING`

`SEARCH`

`AD_TARGETING`

`PROFILE_BUILDING`

`FACIAL_RECOGNITION`

`LOCATION_ANALYSIS`

`RESEARCH`

`SUBLICENSE`

`REDISTRIBUTE`.

Unknown purposes SHALL NOT be silently considered permitted.

---

# 24. CONSENT

Consent SHALL be:

specific;

purpose-bound;

versioned;

timestamped;

revocable where legally/contractually possible;

cryptographically attributable to the authorizing party.

A policy change SHALL NOT retroactively rewrite historical consent.

Historical events SHALL preserve which policy version was active.

---

# 25. EXTERNAL PLATFORM TERMS INTELLIGENCE

ENTITY SHALL support a Platform Terms Intelligence subsystem.

Before governed export to a configured external platform, ENTITY SHOULD determine or request the applicable terms version.

The system SHOULD communicate material rights effects to the user.

A platform-impact record SHALL be capable of representing:

ownership retained;

licence granted;

exclusivity;

transferability;

sublicensing;

commercial use;

advertising rights;

AI-related provisions;

retention;

termination effect;

jurisdiction;

terms version;

terms retrieval date;

unknown/unresolved clauses.

If terms cannot be confidently interpreted, the result SHALL be marked `REVIEW_REQUIRED` rather than fabricated.

---

# 26. EXTERNAL EXPORT STATE

Export SHALL be its own event.

Required fields SHALL support:

asset;

destination platform;

exporting Entity;

timestamp;

policy snapshot;

terms snapshot/hash;

rights-impact result;

human/organizational approval;

external content ID where returned;

export success/failure.

The source asset SHALL remain governed by its Entity provenance record.

ENTITY SHALL NOT claim that its internal rights policy overrides external contractual terms accepted by the user.

---

# 27. CONTRACT AND LICENSING ENGINE

Licensing SHALL be bilateral or multi-party where applicable.

A licence SHALL have explicit:

grantor;

licensee;

assets;

rights;

purpose;

scope;

territory;

duration;

price/consideration;

usage requirements;

reporting requirements;

retention requirements;

derivative rules;

revocation rules;

termination rules;

signatures.

A proposed licence SHALL NOT become active merely because the grantor created an offer.

The accepting party SHALL explicitly accept unless another legally valid mechanism is configured.

---

# 28. LICENCE STATE MACHINE

The minimum licence lifecycle SHALL be:

`DRAFT`

`OFFERED`

`COUNTERED`

`ACCEPTED`

`ACTIVE`

`SUSPENDED`

`REVOKED_FOR_FUTURE_USE`

`EXPIRED`

`TERMINATED`

`DISPUTED`

`CLOSED`.

Transitions SHALL be validated.

An invalid transition SHALL fail closed.

---

# 29. REVOCATION SEMANTICS

ENTITY SHALL NOT present revocation as magical remote erasure.

The system SHALL distinguish:

access revoked;

future use prohibited;

new downloads prohibited;

retention expired;

deletion requested;

deletion attested;

model unlearning requested;

model unlearning attested;

historical authorized use remains lawful;

derivative rights survive;

contract terminated.

The exact consequence SHALL derive from policy and contract.

---

# 30. USAGE CONTROL

Usage evidence SHALL have explicit assurance levels.

Minimum levels:

**DECLARED** — recipient states that use occurred.

**ENTITY_GATEWAY_OBSERVED** — use passed through an Entity-controlled access gateway.

**COUNTERPARTY_ATTESTED** — recipient cryptographically attests.

**ENVIRONMENT_ATTESTED** — trusted execution/controlled compute environment provides evidence.

ENTITY SHALL never present self-reported usage as independently verified usage.

---

# 31. DATA ACCESS GATEWAY

High-value licensed data SHOULD support access without unrestricted raw-file transfer.

ENTITY SHOULD support controlled APIs capable of:

authentication;

authorization;

rate limiting;

policy evaluation;

usage metering;

purpose binding;

receipt issuance;

access termination.

For higher-assurance use cases ENTITY SHOULD support clean-room or computation-to-data models.

---

# 32. COMPUTATION-TO-DATA

ENTITY SHOULD support a future mode where approved algorithms execute against protected data while raw data remains inside an authorized environment.

The environment SHALL restrict outbound results according to policy.

This subsystem MAY be used for:

AI training;

AI evaluation;

statistics;

research;

analytics;

aggregate queries.

Usage SHALL produce auditable evidence.

---

# 33. DATA POOLS

ENTITY SHALL support governed aggregation of many contributors' assets.

A data pool SHALL define:

pool ID;

purpose;

eligible assets;

contributors;

licensing policy;

governance;

quality rules;

revenue allocation;

privacy requirements;

withdrawal/revocation conditions;

aggregation policy.

Contributor rights SHALL not disappear when data joins a pool unless an explicit lawful agreement states otherwise.

---

# 34. DATA POOL ECONOMIC DISTRIBUTION

Pool revenue allocation SHALL be deterministic and auditable.

Possible distribution inputs MAY include:

equal contribution;

asset count;

quality;

usage;

uniqueness;

measured contribution;

contractual percentages.

The selected allocation algorithm SHALL be versioned and recorded.

Retroactive algorithm changes SHALL NOT silently rewrite finalized settlements.

---

# 35. QUALITY, FRAUD AND SYNTHETIC DATA CONTROLS

Once data can create revenue, ENTITY SHALL assume adversaries will manufacture low-quality or fraudulent data.

ENTITY SHALL support:

duplicate detection;

near-duplicate detection;

synthetic-content declarations;

provenance validation;

quality scoring;

spam detection;

reputation;

fraud signals;

pool admission criteria.

AI-generated or synthetic content SHALL not automatically be considered fraudulent, but its provenance SHOULD be represented where known.

---

# 36. ENTITY EVENT LEDGER

ENTITY SHALL maintain tamper-evident event history.

Material events SHALL include:

identity changes;

key changes;

asset registration;

provenance events;

claim events;

policy events;

consent events;

licence events;

usage events;

export events;

settlement events;

dispute events;

recovery events;

authority changes;

digital-commodity registration/status events;

corporate-capital authorization events;

share-class creation/amendment events;

share issuance, transfer, conversion, repurchase and cancellation events;

shareholder-register events;

corporate-action events;

dividend/distribution declaration and payment events;

valuation/disclosure snapshot events;

capital-market evidence events.

Events SHALL be immutable once finalized except through superseding/corrective events.

---

# 37. HASH CHAIN AND EQUIVOCATION PROTECTION

A per-Entity hash chain alone SHALL NOT be treated as sufficient proof of one globally authoritative history.

ENTITY SHALL protect against fork/equivocation.

High-value events SHOULD support:

counterparty signatures;

Merkle commitments;

independent witnesses;

transparency logs;

trusted timestamping;

optional public-chain anchoring.

The system SHALL define which event classes require external witnessing.

---

# 38. PUBLIC BLOCKCHAIN POLICY

Public blockchain anchoring SHALL be optional.

Private content SHALL NOT be written to public blockchain merely for convenience.

Public anchors SHOULD contain only minimum cryptographic commitments.

ENTITY participation SHALL not require gas tokens.

A failure of a public anchor provider SHALL not invalidate locally verifiable Entity history.

---

# 39. DISTRIBUTED CONSISTENCY

ENTITY SHALL explicitly define consistency requirements by subsystem.

Rights/provenance records MAY use eventual reconciliation where safe.

Exclusive rights and value transfer SHALL require stronger finality.

The protocol SHALL define:

network partition behavior;

duplicate event handling;

conflict detection;

replay protection;

offline operation;

rejoin/reconciliation;

clock uncertainty;

finality;

event ordering.

---

# 40. VALUE SYSTEM

The value subsystem SHALL distinguish:

**Potential Value**

**Offer Value**

**Contracted Value**

**Accrued Value**

**Settled Value**

**Realized Value**.

Only actual contracted/settled obligations SHALL affect realized economic accounting.

Potential value SHALL NOT be represented as cash.

---

# 41. VALUE PROFILE

Assets and corpora MAY have non-monetary value profiles including:

rights certainty;

provenance strength;

uniqueness;

quality;

verification depth;

commercial usefulness;

sensitivity;

scarcity;

observed demand;

historical revenue;

transferability.

Scoring methodology SHALL be transparent and versioned.

ENTITY SHALL not claim that such scoring establishes objective market price.

---

# 42. PRICE DISCOVERY

ENTITY SHOULD support market-driven mechanisms including:

fixed-price offers;

negotiated licences;

auctions;

subscriptions;

usage royalties;

revenue share;

exclusive licences;

non-exclusive licences;

data-pool agreements.

Actual transactions SHALL become market evidence that may inform future valuation.

---

# 43. ACCOUNTING

The economic subsystem SHALL use double-entry accounting principles for finalized value movement.

Every settled value event SHALL have balanced entries.

Balances SHALL NOT be calculated merely from unvalidated unilateral settlement inserts.

A financial event SHALL have:

transaction ID;

payer;

payee;

amount;

unit/currency;

authorization;

obligation reference;

execution state;

external payment reference where applicable;

timestamp;

signatures;

reconciliation state.

---

# 44. SETTLEMENT STATE MACHINE

Settlement SHALL support:

`CREATED`

`AUTHORIZED`

`RESERVED`

`EXECUTING`

`CONFIRMED`

`FAILED`

`REVERSED`

`REFUNDED`

`DISPUTED`

`RECONCILED`.

Payment direction SHALL be explicit.

A licence's licensee/grantor roles SHALL not be validated using only unordered party-set equality.

Replay protection SHALL be mandatory.

Transaction identifiers SHALL incorporate a unique immutable nonce/event identifier.

---

# 45. ENTITY VALUE CREDIT

An internal unit such as Entity Value Credit MAY exist as an accounting or closed-loop settlement unit.

Its existence SHALL NOT imply a freely transferable cryptocurrency.

The initial implementation SHOULD avoid speculative token mechanics.

Architecture MAY support future regulated interoperability with:

fiat payment providers;

bank rails;

payment processors;

regulated virtual-currency providers;

other authorized settlement rails.

Any freely transferable cryptocurrency functionality SHALL be separately qualified for financial, tax and regulatory obligations before production activation.

---

# 46. EXTERNAL PAYMENT EVIDENCE

A settlement record SHALL NOT assert that external money moved solely because an internal database row exists.

External settlement SHALL require appropriate payment evidence from the integrated payment system.

ENTITY SHALL record whether payment evidence is:

provider-confirmed;

counterparty-attested;

manually entered;

unverified.

---

# 47. NIKI ACCESS MODEL

NIKI SHALL not receive unrestricted vault access.

AI permissions SHALL be separate capabilities including:

`AI_METADATA_READ`

`AI_CONTENT_READ`

`AI_REASON_OVER`

`AI_DISCLOSE`

`AI_PROPOSE_ACTION`

`AI_EXECUTE_ACTION`.

A NIKI request SHALL receive the smallest context projection required for the task.

Sensitive content SHALL not enter AI context merely because ENTITY has filesystem access.

---

# 48. NIKI READ/WRITE SEPARATION

Read-only reasoning SHALL remain separated from authoritative mutation.

NIKI MAY explain:

assets;

rights;

licences;

usage;

exports;

balances;

risks;

platform rights implications.

NIKI SHALL NOT directly alter authoritative rights or economic state without a governed execution path.

---

# 49. ADAM CAPABILITY-BASED AUTHORITY

ADAM and other agents SHALL operate under explicit capabilities.

A capability SHALL define:

agent;

permitted operation;

asset scope;

counterparty scope;

financial limit;

time limit;

approval requirements;

delegation rights;

revocation.

A compromised agent SHALL NOT inherit unlimited authority from the user's root identity.

---

# 50. HUMAN APPROVAL

High-impact actions SHALL support mandatory human or organizational approval.

High-impact operations SHOULD include:

IP assignment;

exclusive licence;

high-value contract;

sensitive data export;

root recovery changes;

key authority changes;

large settlements;

irreversible public publication;

AI-training licence of restricted corporate data.

Approval threshold SHALL be policy-driven.

---

# 51. BECP ROLE

BECP SHALL be treated as a governed external communications and observation boundary.

For transactions passing through BECP, the system SHOULD be capable of recording:

outbound commitment;

destination;

declared purpose;

timestamp;

response commitment;

provider metadata exposed;

transport result;

resulting asset relationships.

BECP SHALL not claim observation of provider-internal events that were not exposed.

---

# 52. EXTERNAL AI PROVIDER PROVENANCE

An AI interaction provenance record SHOULD support:

provider;

provider/model identifier if exposed;

request commitment;

response commitment;

time;

session/response identifier if exposed;

derived assets;

human review state;

provider attestation where available.

Hidden chain-of-thought SHALL NOT be required for provenance.

---

# 53. PLATFORM AND CONNECTOR PERMISSIONS

Every connected application SHALL have explicit scopes.

Scopes SHALL be revocable.

Connector authority SHALL not automatically propagate to NIKI, ADAM or unrelated subsystems.

A connector SHALL NOT be able to access arbitrary Entity content unless its scope requires that access.

---

# 54. PROVENANCE GRAPH

ENTITY SHALL represent derivation.

An asset MAY identify:

parent assets;

ingredients;

source datasets;

AI interactions;

human edits;

conversion steps;

build inputs;

export derivatives.

A transformed asset SHALL not erase its parent provenance.

---

# 55. SOFTWARE BILL OF MATERIALS / RIGHTS BILL OF MATERIALS

Software assets SHOULD integrate SBOM information.

ENTITY SHALL additionally support a Rights Bill of Materials identifying:

BTG-originated code;

AI-assisted code;

third-party libraries;

licence obligations;

commercial SDKs;

attributions;

redistribution constraints;

known provenance.

AI generation SHALL not erase third-party licensing obligations.

ENTITY SHALL additionally generate a **Provenance Bill of Materials (PBOM)** for qualified software and knowledge releases.

The PBOM SHALL identify, where evidence exists:

human-originated requirements;

architecture decisions;

AI-assisted generation events;

human modifications and approvals;

source inputs;

build inputs and toolchain versions;

test and qualification evidence;

release signatures;

known unknown-provenance elements.

SBOM, RBOM and PBOM SHALL be cryptographically bound to the release evidence manifest. Unknown provenance SHALL be disclosed rather than guessed.

---

# 56. DISPUTE SYSTEM

ENTITY SHALL support disputes as first-class state.

An ownership or authorship conflict SHALL not be automatically resolved by earliest Entity registration time.

Dispute records SHALL support:

challenger;

claim challenged;

counter-evidence;

authority/arbitrator;

status;

interim restrictions;

resolution;

resolution evidence;

appeal/supersession.

Court, arbitration or agreed-authority decisions MAY be attached as authoritative external evidence.

---

# 57. REPUTATION

Reputation SHALL be contextual rather than one global social score.

Separate reputation domains MAY include:

identity verification;

contract performance;

dataset quality;

payment reliability;

provenance accuracy;

professional credentials.

Negative reputation SHALL not silently contaminate unrelated domains without policy justification.

---

# 58. PORTABILITY

ENTITY SHALL implement full owner-controlled export.

An export SHALL be capable of containing:

identity metadata;

DID/credential state where applicable;

asset registry;

rights/claims graph;

policies;

contracts;

ledger events;

provenance;

usage receipts;

economic records;

configuration;

portable encrypted content where requested.

Export formats SHALL be documented.

No proprietary database SHALL be the sole authoritative interpretation format.

---

# 59. FEDERATION

ENTITY SHOULD support independently operated compatible nodes.

Federated nodes SHALL verify protocol version and cryptographic compatibility.

No node SHALL be trusted merely because it claims to be an Entity node.

Federation SHALL support:

peer authentication;

capability negotiation;

schema/version negotiation;

event validation;

rate limits;

abuse controls.

---

# 60. CRYPTOGRAPHIC ARCHITECTURE

Cryptographic algorithms SHALL be versioned and identified explicitly.

The architecture SHALL be crypto-agile.

Ed25519 MAY remain an operational signing algorithm.

The architecture SHALL permit post-quantum or hybrid signatures without changing sovereign identity.

ML-DSA support SHOULD be planned into cryptographic interfaces.

Hash algorithms SHALL likewise be algorithm identified.

No database schema SHALL permanently assume exactly one signature or hash algorithm.

---

# 61. KEY PROTECTION

Private keys SHALL never be written to event ledgers.

Root/recovery keys SHOULD support hardware-backed protection where available.

Key-use operations SHALL be logged.

High-value signing SHOULD support step-up authentication.

Secrets SHALL be excluded from ordinary NIKI prompt context and logs.

---

# 62. AUTHENTICATION AND SESSION SECURITY

ENTITY SHALL implement:

strong local authentication;

session expiration;

device authorization;

revocation;

rate limits;

CSRF protection where applicable;

secure cookie/token handling;

mutual authentication for high-trust peer operations.

Authentication token scope SHALL follow least privilege.

---

# 63. AUTHORIZATION

All authoritative operations SHALL pass policy authorization.

Authorization SHALL evaluate:

actor;

role;

capability;

asset;

action;

purpose;

current policy;

jurisdiction/configuration;

approval threshold;

time;

counterparty.

Authorization failure SHALL be fail closed.

---

# 64. PRIVACY

ENTITY SHALL minimize collection.

Metadata itself SHALL be treated as potentially sensitive.

The system SHALL avoid placing globally correlatable root identifiers in public events wherever possible.

Public/shared ledger entries SHOULD use blinded, pairwise or context-specific identifiers where feasible.

Hashes of low-entropy sensitive values SHALL not be assumed private.

Appropriate keyed commitments or other privacy-preserving methods SHOULD be used when ordinary hashes permit enumeration attacks.

---

# 65. ADVERTISING / PRIVATE MATCHING

If ENTITY supports advertising matching, raw user profiles SHOULD remain local/private.

An advertiser MAY submit targeting criteria.

The system MAY return a permitted match result without revealing the full profile.

The design SHALL protect against reconstruction attacks caused by repeated narrow queries.

Controls SHOULD include:

query budgets;

rate limiting;

minimum cohort sizes;

sensitive-trait exclusions;

privacy-preserving aggregation;

other statistical/privacy protections.

---

# 66. CLASSIFICATION ENGINE

ENTITY SHALL support automated classification, but automated classification SHALL be reviewable.

Classification MAY include:

content type;

sensitivity;

likely owner/claimants;

potential personal information;

commercial/licensing suitability;

synthetic content;

external rights concerns.

AI-generated classification SHALL be tagged as derived inference rather than authoritative fact until accepted or corroborated.

---

# 67. API ARCHITECTURE

Authoritative operations SHALL be accessible through versioned APIs.

The API SHALL separate:

identity;

sources;

vault;

assets;

claims;

policies;

licensing;

usage;

ledger;

settlement;

exports;

disputes;

agent capabilities;

digital commodities;

corporate economics;

capital structures;

share classes;

share ledger/shareholder register;

corporate actions;

disclosures and valuation evidence;

regulated-instrument classification/transfer controls;

authority relationships;

custody and storage bindings;

processing/hosting grants;

provider migration and substitution;

sovereign export and recovery;

administration.

API versions SHALL support controlled migration.

Breaking schema changes SHALL not silently reinterpret signed historical events.

---

# 68. API IDEMPOTENCY

State-changing network APIs SHOULD support idempotency keys.

Repeated delivery of the same signed request SHALL not cause duplicate licence acceptance, duplicate usage charges or duplicate settlement.

---

# 69. API ERROR MODEL

Errors SHALL be structured.

Security-sensitive failures SHALL not leak secrets.

Errors SHOULD distinguish:

authentication failure;

authorization failure;

policy denial;

invalid state transition;

signature failure;

conflict;

duplicate/replay;

dependency unavailable;

unverified external state.

---

# 70. DATA MODEL VERSIONING

All durable signed records SHALL include schema/version identification.

Schema migration SHALL preserve historical verification.

Old signatures SHALL not require rewriting simply because the current application schema changed.

---

# 71. TIME

ENTITY SHALL record high-resolution timestamps where useful.

The system SHALL distinguish:

local observed time;

counterparty time;

trusted timestamp authority time;

ledger witness/checkpoint time.

Clock disagreement SHALL not be silently ignored for high-value events.

---

# 72. OFFLINE OPERATION

Core owner-controlled functionality SHOULD continue offline.

Offline-created events SHALL be signed locally.

Synchronization SHALL occur once connectivity returns.

Conflicts SHALL be detected and surfaced.

Value double-spend or exclusive-right conflicts SHALL fail closed until reconciliation.

---

# 73. BACKUP AND DISASTER RECOVERY

Critical identity and rights records SHALL have backup requirements.

Backups SHALL be encrypted.

Recovery SHALL be tested.

A successful backup job without a tested restore SHALL not satisfy production qualification.

The system SHALL define recovery-point and recovery-time objectives.

---

# 74. AVAILABILITY

Loss of one optional external provider SHALL not destroy sovereign identity.

External platform, cloud, blockchain anchor, AI-provider or payment-provider outage SHALL degrade only dependent features where architecturally possible.

---

# 75. AUDITABILITY

All high-impact actions SHALL create audit events.

Audit records SHALL include sufficient information to determine:

who;

under what authority;

performed what action;

against what object;

under what policy;

at what time;

with what outcome.

Audit data SHALL itself be protected against unauthorized modification and disclosure.

---

# 76. OBSERVABILITY

Production services SHALL expose operational metrics.

Metrics SHOULD include:

API availability;

latency;

authorization denials;

signature verification failures;

ledger conflicts;

synchronization delay;

vault errors;

connector failures;

usage-meter errors;

settlement reconciliation errors.

Sensitive identifiers SHALL be minimized in operational telemetry.

---

# 77. PERFORMANCE

Performance targets SHALL be formally established during qualification.

As initial engineering targets:

local metadata lookup SHOULD generally complete interactively;

local authorization decisions SHOULD not depend on public blockchain latency;

ledger append SHOULD remain usable offline;

ordinary asset registration SHOULD not require remote consensus;

large corpus indexing SHALL be asynchronous internally while clearly reporting progress/state.

Economic finality MAY take longer than local operations where external payment rails are involved.

---

# 78. SCALE

The architecture SHALL be capable of handling:

millions of assets per organization;

large provenance graphs;

high-volume filesystem event streams;

large data pools;

high-volume usage receipts.

No design SHALL require loading an entire Entity history into memory for ordinary operations.

Indexes, pagination and incremental processing SHALL be implemented.

---

# 79. EVENT RETENTION

Retention SHALL be policy-specific.

Immutable provenance evidence may require longer retention than content itself.

Deletion of content SHALL not necessarily require deletion of non-personal cryptographic proof where lawful and appropriate.

Personal information SHALL not be retained merely because ledger architecture makes deletion inconvenient.

---

# 80. SECURITY THREAT MODEL

Qualification SHALL include at minimum:

stolen device;

stolen operational key;

malicious recovery guardian;

malicious peer;

malicious marketplace participant;

Sybil attack;

replay attack;

ledger fork/equivocation;

duplicate settlement;

agent compromise;

prompt injection;

connector compromise;

data-exfiltration attempt;

malicious external document;

ransomware;

vault theft;

metadata correlation;

fake provenance;

synthetic dataset fraud;

unauthorized sublicensing;

payment reversal;

network partition.

---

# 81. AI PROMPT-INJECTION DEFENCE

Untrusted content SHALL never directly determine Entity authority.

Instructions found inside:

documents;

websites;

emails;

files;

external tool results;

third-party data

SHALL be treated as untrusted data unless explicitly promoted to authorized instructions.

NIKI/ADAM SHALL not grant a licence, expose private assets or transfer value because an ingested document instructed them to do so.

---

# 82. AI EXFILTRATION PROTECTION

Before sensitive information is passed to an AI model, ENTITY SHALL evaluate:

AI read permission;

data classification;

provider;

requested purpose;

minimum necessary context;

external-disclosure policy.

The system SHOULD support local redaction/projection before external model calls.

---

# 83. HUMAN-FACING EXPLANATIONS

ENTITY SHALL make machine policy understandable.

NIKI SHOULD be able to answer:

Who can use this?

For what?

Until when?

For how much?

Can they train AI with it?

Can they sublicense it?

What happens if I revoke it?

What rights did I give this platform?

Why was this request denied?

What evidence supports this ownership claim?

---

# 84. HIGH-RISK USER WARNINGS

ENTITY SHALL warn before actions with materially irreversible or broad consequences.

Warnings SHOULD clearly distinguish:

loss of privacy;

broad platform licence;

exclusive licence;

perpetual licence;

AI training rights;

sublicensing;

public disclosure;

high-value transfer;

unverified ownership claim.

Warnings SHALL describe consequences rather than merely display generic confirmation dialogs.

---

# 85. LEGAL / JURISDICTION ENGINE

Legal rules SHALL be modular and versioned.

ENTITY SHALL not hardcode one jurisdiction as universal truth.

Records SHALL support applicable jurisdiction.

Legal-policy modules MAY assist with compliance but SHALL distinguish engineering enforcement from legal advice/adjudication.

Changes in law SHALL be handled by policy/version updates rather than rewriting historical events.

---

# 86. STANDARDS INTEROPERABILITY

The target architecture SHOULD use or interoperate with appropriate open standards including:

W3C Decentralized Identifiers;

W3C Verifiable Credentials 2.x;

W3C ODRL;

C2PA Content Credentials;

standard SBOM formats;

standard cryptographic identifiers;

standard secure transport protocols.

BTG-specific extensions SHALL be documented.

ENTITY's competitive differentiation SHALL come primarily from integration, governance and usability rather than unnecessary reinvention of established interoperability standards.

---

# 87. MINIMUM DOMAIN OBJECTS

The authoritative domain model SHALL include at least:

Entity;

RelationshipIdentity;

KeyAuthority;

Credential;

Source;

VaultObject;

Asset;

AssetVersion;

ProvenanceEvent;

RightsClaim;

Policy;

Consent;

Licence;

UsageEvent;

UsageReceipt;

ExportEvent;

TermsSnapshot;

Settlement;

AccountingEntry;

DataPool;

PoolContribution;

Dispute;

Attestation;

WitnessCheckpoint;

AgentCapability;

Approval;

RecoveryPolicy;

AuthorityRelationship;

CustodyRelationship;

StorageBinding;

ProcessingGrant;

SovereignDelegation;

EconomicParticipationRight;

ProviderMigrationRecord;

SovereignExportManifest;

CorporateEntityProfile;

DigitalCommodity;

DigitalCommodityEconomicEvent;

CorporateEconomicSnapshot;

CapitalStructure;

ShareClass;

SharePosition;

ShareLot;

ShareLedgerEvent;

ShareholderRegisterEntry;

TransferRestriction;

CorporateAction;

DividendOrDistribution;

CapitalAuthorization;

InstrumentClassification;

ValuationSnapshot;

MarketPriceObservation;

DisclosureSnapshot.

---

# 88. MANDATORY IDENTIFIER PROPERTY

Every durable high-value domain object SHALL have a collision-resistant unique identifier.

Identifiers SHALL not be derived only from fields that can legitimately repeat.

Transaction IDs SHALL include unique nonces or equivalent unique material.

---

# 89. MANDATORY SIGNATURE PROPERTY

Where an event has legal/economic/security significance, ENTITY SHALL identify:

signer;

signing authority;

algorithm;

key version;

signature;

signed payload schema;

time.

Verification SHALL be reproducible independently.

---

# 90. MANDATORY LINEAGE PROPERTY

Derived assets SHOULD reference immediate parent(s).

Where provenance is unknown, parent state SHALL be marked unknown rather than fabricated.

---

# 91. BASELINE MIGRATION REQUIREMENT

Existing `entity_identity.py`, `bsie_entity_world.py`, `data_universe.py`, service and NIKI integration work SHALL be migrated rather than discarded.

Migration SHALL preserve valid existing signed/evidentiary records.

The old owner-centric schema SHALL be upgraded to Rights & Claims Graph semantics.

The existing settlement logic SHALL be replaced or corrected to enforce directional payment roles, unique transaction identity, state transitions and true settlement evidence.

---

# 92. EXISTING LEDGER MIGRATION

Existing local signed hash-chain events SHALL remain verifiable.

A migration checkpoint SHALL record:

previous schema/version;

new schema/version;

migration tool version;

source ledger root;

result ledger root;

migration evidence.

Migration SHALL not silently change historical meaning.

---

# 93. EXISTING NIKI INTEGRATION MIGRATION

Current read-only Data Universe awareness SHALL remain.

It SHALL be extended with explicit information-projection permissions.

NIKI SHALL not automatically receive full content access merely because an asset is visible in the Entity summary.

---

# 94. EXISTING PLATFORM EXPORT MIGRATION

Existing export recording SHALL evolve into full Platform Terms Intelligence.

Historical exports MAY remain with terms status `UNKNOWN` where the applicable terms snapshot was not captured.

ENTITY SHALL not fabricate historical terms.

---

# 95. IMPLEMENTATION PHASE 1 — SOVEREIGN CORE

Phase 1 SHALL deliver a production-quality sovereign foundation consisting of:

stable root identity;

key hierarchy/rotation/recovery;

pairwise identities;

permissioned source gateway;

encrypted vault;

asset registry;

provenance;

Rights & Claims Graph;

policy/consent;

C2PA support where applicable;

read-only NIKI reasoning projection;

governed ADAM capability execution;

event ledger;

authority/custody/storage relationship model;

provider-independent storage substitution and migration;

backup/recovery;

sovereign export manifest;

portability.

Phase 1 SHALL NOT require public cryptocurrency.

---

# 96. IMPLEMENTATION PHASE 2 — ENTITY-TO-ENTITY ECONOMY

Phase 2 SHALL add:

peer discovery;

trust credentials;

licence negotiation;

bilateral signing;

usage receipts;

controlled access;

external payments;

double-entry settlement;

disputes;

royalties;

platform terms intelligence;

corporate Entity profiles where enabled;

digital-commodity economic attribution;

capital-structure records;

share-class and shareholder-register support;

authorized corporate-action workflows;

corporate economic aggregation and disclosure snapshots;

regulated-instrument classification and transfer controls for enabled equity functions.

Corporate-capital functionality MAY be deployed as a separately qualified Phase 2 scope. Enabling the Entity-to-Entity economy SHALL NOT automatically enable public share issuance or trading.

---

# 97. IMPLEMENTATION PHASE 3 — DATA SPACES

Phase 3 SHOULD add:

data pools;

collective governance;

AI training pools;

secure compute;

data clean rooms;

computation-to-data;

automated revenue sharing;

enterprise federation.

---

# 98. IMPLEMENTATION PHASE 4 — OPEN FEDERATION

Phase 4 SHOULD enable independent compatible implementations.

The protocol and schemas required for independent verification SHALL be documented.

BTG MAY operate reference infrastructure, marketplace, enterprise management and trust services without requiring BTG to control every Entity node.

---

# 99. UNIT TEST REQUIREMENTS

Every security-sensitive state transition SHALL have positive and negative tests.

Tests SHALL include:

valid operation;

invalid signer;

expired capability;

revoked key;

wrong party;

wrong direction;

replay;

duplicate ID;

policy prohibition;

unauthorized AI access;

network interruption;

invalid signature;

tampered event;

invalid state transition.

---

# 100. PROPERTY / INVARIANT TESTING

The system SHALL test invariants including:

ledger history cannot be silently altered;

unauthorized actor cannot mutate protected state;

accounting remains balanced;

revoked key cannot authorize future transactions;

duplicate message does not duplicate settlement;

asset deletion does not rewrite historical provenance;

policy denial fails closed;

NIKI read access cannot mutate state.

---

# 101. ADVERSARIAL TESTING

Qualification SHALL include deliberate attempts to:

forge ownership;

forge usage;

forge settlement;

create ledger forks;

replay licence acceptance;

reverse payer/payee roles;

exfiltrate vault content through NIKI;

inject instructions through a document;

link pairwise identities;

submit fraudulent data-pool assets;

use revoked keys;

double-spend value.

---

# 102. ENTITY GOLDEN END-TO-END QUALIFICATION SCENARIO

Before production certification the system SHALL successfully complete at least one fresh test scenario:

Entity A creation;

Entity B creation;

identity verification;

asset enrollment;

asset hash/provenance;

rights claims;

policy assignment;

licence offer;

licence acceptance;

controlled access or transfer;

usage;

usage receipt;

settlement authorization;

external/internal settlement evidence;

double-entry accounting;

balance verification;

revocation/expiry;

ledger verification;

backup;

restore;

independent evidence validation.

No manual database edits may be required to make the scenario pass.

---

# 103. PLATFORM EXPORT QUALIFICATION

A test SHALL verify:

asset remains in Entity registry;

external export creates separate event;

rights-impact warning appears;

terms snapshot/hash is retained where available;

user approval is captured;

external content identifier is associated;

source rights are not silently overwritten.

---

# 104. IDENTITY RECOVERY QUALIFICATION

Qualification SHALL prove:

operational-key rotation;

lost-key recovery;

revoked-key rejection;

guardian/threshold recovery where configured;

organization authority transition;

historical signature verification after rotation.

---

# 105. EVIDENCE BOUNDARY QUALIFICATION

Tests SHALL prove that ENTITY distinguishes:

locally observed event;

counterparty attestation;

derived inference;

unknown provider-internal activity.

The UI/API SHALL not label unknown hidden AI reasoning or undisclosed provider actions as verified.

---

# 106. PRIVACY QUALIFICATION

Tests SHALL verify:

root identity is not unnecessarily exposed;

pairwise identities cannot trivially be linked from ordinary public records;

private file paths are not leaked by default;

sensitive content is not written to the shared ledger;

AI context projection respects permission;

connector permissions respect scope.

---

# 107. CRYPTOGRAPHIC QUALIFICATION

Qualification SHALL verify:

signature creation;

signature verification;

tamper detection;

key rotation;

revocation;

algorithm identifiers;

hash-chain verification;

checkpoint/Merkle verification;

crypto-agility interface.

Where implemented, ML-DSA/hybrid support SHALL have known-answer and interoperability tests.

---

# 108. DATA LOSS QUALIFICATION

Production readiness SHALL require demonstrated restoration from backup.

The test SHALL include:

identity state;

asset metadata;

rights graph;

policies;

ledger;

contracts;

economic records.

Content recovery SHALL be verified according to configured storage policy.

---

# 109. PERFORMANCE QUALIFICATION

A representative corpus SHALL be used to establish:

registration throughput;

indexing throughput;

provenance event throughput;

authorization latency;

ledger append latency;

query latency;

synchronization performance;

memory usage;

storage growth.

Results SHALL be recorded as evidence rather than assumed.

---

# 110. SECURITY RELEASE GATE

Production release SHALL fail if any unresolved critical defect permits:

unauthorized rights mutation;

unauthorized asset disclosure;

root identity takeover;

settlement creation without authorization;

signature bypass;

ledger tampering without detection;

agent capability escalation;

unrestricted connector escalation.

---

# 111. ECONOMIC RELEASE GATE

No transferable value system SHALL enter production until:

accounting invariants pass;

replay protection passes;

settlement direction passes;

reversal/refund logic passes;

reconciliation passes;

external payment evidence passes;

applicable compliance review is completed.

---

# 112. PROVENANCE RELEASE GATE

ENTITY SHALL NOT advertise “verified ownership” unless the verification level actually supports that statement.

UI terms SHALL distinguish:

registered;

claimed;

provenance verified;

rights verified;

externally attested;

disputed.

---

# 113. TRL DEFINITION FOR ENTITY

TRL claims SHALL be evidence-based.

A local prototype with passing unit tests SHALL not be labelled TRL 9.

A production-level claim SHALL require demonstrated operation in the intended environment with representative users, security controls, recovery, real integrations and operational evidence.

Economic, identity, provenance and AI-governance subsystems MAY have different TRLs and SHALL be reported separately when appropriate.

---

# 114. REQUIRED SYSTEM DOCUMENTATION

Production qualification SHALL include:

architecture specification;

threat model;

trust model;

evidence-boundary specification;

cryptographic design;

key-management procedure;

data classification policy;

rights ontology;

ODRL profile;

API specification;

ledger/event schemas;

backup/recovery procedure;

incident response;

privacy design;

platform-export model;

settlement/accounting model;

corporate-capital architecture where enabled;

capital-structure and share-class specification;

corporate-action authorization procedure;

shareholder-register and transfer-control procedure;

digital-commodity economic-attribution methodology;

valuation/disclosure methodology and evidence-boundary policy;

regulated-instrument classification matrix and jurisdictional compliance configuration;

operator manual;

user manual;

developer integration guide;

qualification evidence package.

---

# 115. REQUIRED MACHINE-READABLE EVIDENCE

Each qualified release SHOULD produce a signed release evidence package containing:

source commit;

build hashes;

dependency/SBOM records;

test result hashes;

qualification result;

schema versions;

cryptographic-suite versions;

migration versions;

artifact hashes;

release signer;

timestamp;

Requirement Traceability Matrix snapshot;

SBOM;

RBOM;

PBOM;

red-team/adversarial campaign summary;

property/invariant test summary;

release-gate decisions;

independent-verification result where applicable;

capital-structure schema/version where corporate-capital scope is enabled;

corporate-capital invariant test summary where applicable;

share-ledger reconciliation result where applicable;

digital-commodity economic-attribution reconciliation result where applicable;

valuation/disclosure evidence-boundary test result where applicable.

---

# 116. DESIGN PROHIBITIONS

The completed system SHALL NOT:

require complete administrator access to every drive;

place all raw user data on a blockchain;

assume possession equals ownership;

assume signature equals truth;

expose one universal public identifier everywhere;

make identity permanently dependent on one key;

let NIKI autonomously rewrite rights;

let arbitrary discovered files mint value;

claim self-reported usage is independently verified;

claim an internal settlement row proves external payment;

pretend licence revocation erases remote copies;

assume platform terms are overridden by Entity policy;

make sovereignty dependent on BTG remaining online forever.

---

# 117. FINAL TARGET ARCHITECTURE

The complete platform SHALL therefore consist of these major production subsystems:

**Sovereign Root Identity**

**Privacy / Relationship Identity**

**Credential & Trust System**

**Permissioned Data Source Gateway**

**Encrypted Data Vault**

**Asset Registry**

**Knowledge Capital Registry**

**Provenance / C2PA Engine**

**Rights & Claims Graph**

**Policy & Consent Engine**

**Platform Terms Intelligence**

**Contract & Licensing Engine**

**Usage-Control Gateway**

**Secure Compute / Data Space Layer**

**Distributed Evidence Ledger**

**Witness / Transparency Layer**

**Economic & Settlement Engine**

**Data Pool / Collective Economy**

**Dispute & Resolution System**

**NIKI Governance Projection**

**ADAM Capability Executor**

**BECP Evidence Gateway**

**Federation / Portability Layer**

**Security, Recovery, Audit & Qualification Framework**

**Requirements Traceability & Architecture Change-Control Plane**

**Information Projection / Minimum-Disclosure Engine**

**Evidence Assertion & Confidence Envelope**

**SBOM / RBOM / PBOM Release Attestation Pipeline**

**Independent Verification & Interoperability Harness**

**ENTITY Red-Team & Property-Based Assurance Framework**

**Corporate Entity & Digital-Commodity Economy Layer**

**Corporate Capital Structure & Share Ledger**

**Shareholder Register & Transfer-Control Engine**

**Corporate Action / Distribution Engine**

**Corporate Economic Aggregation & Disclosure Engine**

**Capital-Market Evidence & Valuation Boundary**

**Regulated-Instrument Classification & Compliance Control Layer**

---

# 118. SYSTEM ACCEPTANCE DEFINITION

ENTITY shall be considered architecturally complete only when a user or organization can:

create and recover a sovereign identity;

authorize only selected data sources;

choose or change authorized storage without changing the sovereign Entity root or silently transferring Entity authority;

distinguish possession, custody, storage control, sovereign authority, authorship, legal rights, consent authority, licensing authority, authorized usage and economic participation as separate evidence-backed relationships;

prove that a storage provider, platform, connector, AI provider or BTG service does not acquire sovereign authority merely by storing, transporting, indexing, processing or observing Entity data;

move a complete sovereign state to a replacement authorized environment without changing the Entity root, silently changing rights/policy semantics, or assigning the former provider continuing authority it does not hold;

prove that loss or replacement of the current storage/hosting provider does not by itself alter identity, provenance, rights claims, consent state, licensing authority or economic-participation records;

register an asset without exposing its contents publicly;

prove the asset's recorded provenance;

represent multiple competing or complementary rights claims;

apply machine-readable permissions and prohibitions;

allow NIKI to reason about the asset without granting NIKI unrestricted authority;

authorize ADAM through a limited capability;

negotiate and sign an Entity-to-Entity licence;

meter or attest permitted use;

collect valid settlement evidence;

maintain balanced accounting;

revoke future use according to contract semantics;

record external-platform rights effects;

detect disputes and conflicting claims;

recover from device loss;

export the Entity to interoperable formats;

independently verify historical evidence;

where corporate-capital scope is enabled, register productive digital commodities without treating ordinary usage as equity issuance;

aggregate verified asset-level economic activity into corporate economic state without double counting;

maintain authorized, issued, outstanding, treasury/reserved and cancelled equity quantities consistently;

maintain share classes and shareholder positions under explicit rights and restrictions;

execute authorized corporate actions without permitting unauthorized dilution or ownership mutation;

separate book/economic metrics, modelled valuation and externally observed market price;

produce an evidence-backed corporate economic/disclosure snapshot;

apply transfer restrictions and jurisdictional/regulatory controls before enabled share transfers;

independently verify the capital structure and share-ledger history from signed evidence.

---

# 119. ENGINEERING DEFINITION OF THE COMPLETED SYSTEM

When the requirements in this specification are implemented and qualified, ENTITY is not merely a blockchain, wallet, file index, DRM system, AI assistant or data marketplace.

It is:

**a sovereign digital rights operating system, machine-verifiable data-economy infrastructure and, where explicitly enabled and legally configured, evidence-backed corporate-capital infrastructure.**

It gives a human or organization an authoritative digital domain in which identity, authority, data, knowledge capital, provenance, claims, consent, licensing, AI permissions, external-platform rights, usage evidence and economic participation are governed together without allowing a centralized platform, storage provider, custodian, connector, AI provider or BTG service to become the ultimate authority merely because it stores, transports, processes, indexes or observes the data.

NIKI supplies intelligence.

ADAM supplies governed execution.

BSIE supplies authoritative relationship/world state.

BECP supplies controlled communication and observable external evidence.

ENTITY supplies sovereignty.

---

# 120. NON-NEGOTIABLE CORE PRINCIPLE

The system's ultimate engineering invariant SHALL be:

**ENTITY may help a person discover, prove, protect, license and realize value from lawful digital rights, but ENTITY must never manufacture certainty, ownership, consent, privacy, usage, or monetary value that the evidence does not actually establish.**

A second non-negotiable sovereignty invariant SHALL be:

**Custody is not authority. Storage is not ownership. Possession is not authorship. Processing is not consent. Access is not a licence. Usage is not ownership. Economic participation must follow evidence-backed rights, authorization, contract and settlement.**

These invariants shall override convenience, automation and marketing claims.

---

# 121. AUTHORITATIVE ARCHITECTURE BASELINE AND CHANGE CONTROL

The complete SERS SHALL be managed as an explicit architecture baseline.

The initial 120-section specification SHALL be treated as **ENTITY Architecture Baseline 1.0**. This v2.0 master design SHALL preserve that baseline while adding executable engineering control, assurance and production qualification requirements.

No developer, automated agent, NIKI-assisted workflow, ADAM action, migration utility or release process SHALL silently change fundamental semantics of:

identity;

authority;

rights;

claims;

consent;

licensing;

usage evidence;

settlement;

provenance;

evidence origin;

recovery;

portability;

federation.

Any fundamental semantic change SHALL require an Architecture Decision Record (ADR).

Each ADR SHALL record at minimum:

ADR identifier;

problem statement;

current baseline behavior;

proposed behavior;

security impact;

privacy impact;

rights/legal-model impact;

economic impact where applicable;

interoperability impact;

migration impact;

backward-compatibility impact;

rejected alternatives;

approver(s);

effective version;

implementation references;

verification evidence.

A signed historical event SHALL never be reinterpreted silently because an ADR changes current semantics.

---

# 122. REQUIREMENT IDENTIFICATION, TRACEABILITY AND ENGINEERING STATE

Every normative `SHALL` requirement SHALL have a stable machine-readable requirement identifier.

Recommended identifier form:

`ENTITY-<DOMAIN>-<NUMBER>`

Examples:

`ENTITY-ID-003`

`ENTITY-SETTLEMENT-044`

`ENTITY-AI-081`

Each requirement SHALL map to:

requirement text;

source section;

risk classification;

phase;

implementation owner/module;

code or configuration reference;

unit-test reference;

integration-test reference;

adversarial-test reference where applicable;

qualification-test reference;

evidence artifact;

evidence hash;

release(s) containing the implementation;

current engineering state;

open defects/exceptions.

The authoritative traceability chain SHALL be:

`REQUIREMENT → DESIGN → CODE/CONFIGURATION → TEST → RESULT → EVIDENCE → HASH → RELEASE`

The requirement lifecycle SHALL support at least:

`SPECIFIED`

`DESIGNED`

`IMPLEMENTED`

`UNIT_VERIFIED`

`INTEGRATION_VERIFIED`

`ADVERSARIAL_VERIFIED`

`QUALIFIED`

A requirement SHALL NOT be reported as `QUALIFIED` merely because source code exists or a unit test passes.

A Master Requirement Traceability Matrix (RTM) SHALL cover every normative requirement in this document.

The RTM SHALL be exportable in a documented machine-readable format and SHALL be cryptographically bound to qualified releases.

No qualified release SHALL contain an unreviewed `SHALL` requirement whose implementation state is unknown.

---

# 123. FORMAL SUBSYSTEM AUTHORITY CONTRACTS

The following authority boundaries SHALL be treated as enforceable contracts, not documentation conventions:

**ENTITY** owns sovereign identity, authority, rights, consent, policy, licensing, usage-evidence interpretation and economic state.

**NIKI** owns reasoning, explanation and user-facing intelligence.

**ADAM** owns governed execution under explicit capabilities.

**BSIE** owns authoritative world/entity relationship state within its defined spatial/relationship scope.

**BECP** owns governed external communication and externally observable integration evidence.

No subsystem SHALL bypass another subsystem's authority boundary merely because it has technical access to the same machine, database, process or transport.

ENTITY SHALL maintain a machine-readable **Privilege Graph** defining allowed and denied cross-subsystem operations.

At minimum, qualification SHALL prove these negative authority cases:

`NIKI → authoritative rights mutation = DENIED`

`NIKI → settlement mutation = DENIED unless routed through governed execution`

`ADAM without capability → protected asset export = DENIED`

`ADAM without settlement authority → value transfer = DENIED`

`BECP response → authority escalation = DENIED`

`BSIE observation → ownership claim = NOT AUTOMATICALLY VERIFIED`

`document/email/web/tool instruction → ADAM authority = DENIED`

`connector scope → unrelated vault scope = DENIED`

The Privilege Graph SHALL itself be versioned and tested.

---

# 124. INFORMATION PROJECTION AND MINIMUM-DISCLOSURE ENGINE

All sensitive information movement from ENTITY to NIKI, ADAM, BECP, connectors, external AI providers, federated peers or external services SHALL pass through a governed **Information Projection Engine** or an equivalent enforceable control path.

The required decision flow SHALL be:

`requesting actor + purpose + capability + target + policy + classification → authorization → minimum projection → redaction/transformation → disclosure decision → disclosure evidence`

The engine SHALL evaluate at minimum:

requesting subsystem;

identity/capability;

requested purpose;

asset/data classification;

rights and consent state;

provider/counterparty;

jurisdiction/configuration;

minimum necessary fields;

redaction rules;

retention/disclosure restrictions;

whether external transmission is permitted.

The engine SHALL support deny, allow, redact, aggregate, pseudonymize, transform-to-derived-answer and review-required outcomes.

Sensitive content SHALL not be disclosed merely because metadata visibility was granted.

A disclosure event SHALL record enough evidence to determine what class of information was disclosed, to whom, under what authority and for what purpose without unnecessarily duplicating the disclosed sensitive content into logs.

---

# 125. EVIDENCE ASSERTION ENVELOPE

Every material assertion produced, stored or displayed by ENTITY SHALL be capable of carrying an explicit **Evidence Assertion Envelope**.

The envelope SHALL support:

claim identifier;

claim;

claimant;

evidence origin;

evidence references;

confidence where applicable;

verification level;

timestamp(s);

signature(s) where applicable;

jurisdiction where relevant;

dispute state;

supersession relationship;

schema/version.

ENTITY SHALL enforce the semantic distinction:

**observed ≠ asserted ≠ inferred ≠ counterparty-attested ≠ externally verified ≠ unknown.**

The user interface, APIs, reports and NIKI explanations SHALL NOT collapse these states into a stronger statement than the evidence supports.

For AI-assisted engineering provenance, the platform SHALL be able to represent the observable chain:

`human requirement → model request → visible response → generated artifact → human edit/review → source → build → tests → signed release`

Hidden provider reasoning or unexposed provider-internal events SHALL remain outside the Evidence Boundary and SHALL be represented as `UNKNOWN` where relevant.

---

# 126. FORMAL ENTITY RIGHTS ONTOLOGY

The Rights & Claims Graph SHALL be governed by a formal versioned **ENTITY Rights Ontology**.

The ontology SHALL represent rights and interests as relationships rather than a single `asset.owner` field.

It SHALL support at minimum all stakeholder and right types already defined by Sections 18–20, and SHALL permit extension without rewriting historical records.

Verification status SHALL remain separate from dispute state.

Verification states SHALL support at minimum:

`SELF_ASSERTED`

`CORROBORATED`

`VERIFIED`

`AUTHORITATIVELY_VERIFIED`

Dispute/lifecycle states SHALL support at minimum:

`ACTIVE`

`CHALLENGED`

`DISPUTED`

`ADJUDICATED`

`SUPERSEDED`

The ontology SHALL define cardinality, scope, territory, duration, legal basis, evidence, delegation, inheritance/succession and supersession behavior where applicable.

Registration time SHALL NOT automatically resolve ownership, authorship or priority disputes.

Mappings to external rights, policy and credential standards SHALL be documented where feasible. ENTITY-specific extensions SHALL be explicit.

---

# 127. SBOM, RBOM AND PBOM RELEASE ATTESTATION

Every qualified software release SHALL produce three complementary machine-readable inventories:

**SBOM — Software Bill of Materials:** components, packages, versions and dependency relationships.

**RBOM — Rights Bill of Materials:** known rights, licences, obligations, restrictions, attributions, redistribution constraints, commercial SDK obligations and training/data-use restrictions where relevant.

**PBOM — Provenance Bill of Materials:** observable origin and transformation history of the release and its material components.

The PBOM SHOULD connect:

human requirements;

architecture decisions;

AI-assisted generation;

human edits/reviews;

source revisions;

datasets or source inputs where relevant;

toolchains;

build products;

test campaigns;

qualification evidence;

release signatures.

The release system SHALL NOT invent authorship percentages or provenance certainty. Quantitative authorship/contribution metrics MAY be reported only when a documented method and evidence support them.

Unknown provenance SHALL be explicit.

SBOM, RBOM and PBOM artifacts SHALL be hashed and referenced from the signed release evidence manifest.

---

# 128. ECONOMIC CORRECTNESS AND ACCOUNTING ASSURANCE

The economic architecture SHALL preserve the value ladder:

`POTENTIAL → OFFER → CONTRACTED → ACCRUED → SETTLED → REALIZED`

No transition SHALL be inferred solely from file discovery, indexing, hashing, internal scoring or unilateral database insertion.

Every settlement SHALL identify at minimum:

payer;

payee;

amount;

unit/currency;

obligation;

authorization;

execution evidence;

transaction identifier;

immutable nonce/event identifier;

state;

reconciliation state;

balanced accounting entries.

Qualification SHALL cover at minimum:

duplicate payment events;

retries;

failed payments;

partial payments;

refunds;

reversals;

chargebacks where applicable;

disputes;

royalties;

multi-party distributions;

currency conversion where supported;

expired licences;

revoked licences;

incorrect payer/payee direction;

forged payment confirmations;

provider-confirmed versus manually entered payment evidence.

ENTITY SHALL never display potential or estimated value as settled or realized money.

Closed-loop Entity Value Credit, if implemented, SHALL remain semantically distinct from fiat money and freely transferable cryptocurrency unless separately qualified and legally/compliantly enabled.

---

# 129. STANDARDS CONFORMANCE AND INDEPENDENT INTEROPERABILITY

Standards support SHALL be demonstrated through executable conformance rather than documentation claims alone.

For every supported external standard or interoperable format, the preferred qualification sequence SHALL be:

`GENERATE → EXPORT → INDEPENDENTLY VALIDATE → IMPORT FROM ANOTHER IMPLEMENTATION → VERIFY SEMANTIC EQUIVALENCE`

Conformance suites SHOULD cover, where implemented:

W3C Decentralized Identifiers;

W3C Verifiable Credentials;

W3C ODRL;

C2PA Content Credentials;

standard SBOM formats;

standard cryptographic identifiers and encodings;

TLS/mTLS and secure transport profiles;

portable serialization/export formats.

BTG-specific extensions SHALL be namespaced/versioned and SHALL not cause standards-compliant fields to change meaning silently.

Interoperability evidence SHALL identify the external implementation or independent validator used, version, test vectors, result and any permitted deviations.

---

# 130. ENTITY RED TEAM AND CONTINUOUS ADVERSARIAL CAMPAIGNS

ENTITY SHALL maintain an executable adversarial assurance program called the **ENTITY Red Team** or an equivalent continuous attack framework.

The framework SHALL repeatedly attempt at minimum:

identity takeover;

recovery manipulation;

key theft/use of revoked keys;

signature forgery;

rights forgery;

provenance forgery;

usage forgery;

ledger fork/equivocation;

duplicate settlement;

licence replay;

privilege escalation;

prompt injection;

connector exploitation;

NIKI data exfiltration;

ADAM capability bypass;

pairwise identity correlation;

malicious data-pool contribution;

ransomware/data-loss simulation;

offline double-spending;

forged external payment confirmation;

malicious migration input;

schema downgrade/compatibility abuse.

Each campaign SHALL report:

attacks executed;

attacks blocked;

unexpected successes;

severity;

evidence;

remediation;

retest result;

release impact.

A known unresolved critical exploit against a production release gate SHALL block release.

---

# 131. PROPERTY-BASED AND MODEL-BASED INVARIANT CAMPAIGNS

The invariants defined in Section 100 SHALL be tested beyond hand-written examples.

Property-based or model-based testing SHALL generate large numbers of valid and invalid state transitions against critical state machines.

Mandatory invariants SHALL include at minimum:

unauthorized actors can never mutate protected rights;

revoked keys cannot authorize later operations;

duplicate signed requests cannot create duplicate settlements;

finalized double-entry accounting always balances;

asset deletion cannot rewrite historical provenance;

policy denial fails closed;

NIKI read access cannot imply mutation authority;

capability scope cannot expand without a new authorized capability;

historical signatures remain verifiable across supported migrations;

unknown evidence cannot become verified without a qualifying evidence transition.

For security- and value-critical invariants, qualification SHOULD exercise thousands or millions of generated transitions where practical and SHALL record the executed seed/corpus so failures can be reproduced.

---

# 132. FAILURE, DEGRADATION AND RECOVERY STATE MACHINES

Every production service SHALL explicitly define behavior for:

`NORMAL`

`DEGRADED`

`OFFLINE`

`DEPENDENCY_UNAVAILABLE`

`MALICIOUS_INPUT`

`CONFLICTING_STATE`

`RECOVERY`

and any service-specific terminal/quarantine state.

Each state machine SHALL define:

entry condition;

allowed operations;

denied operations;

user-visible status;

evidence/audit behavior;

recovery action;

exit condition;

fail-open or fail-closed policy.

High-impact authority, rights, exclusive licensing and value-transfer operations SHALL fail closed when required dependencies or state certainty are unavailable.

Loss of optional AI, blockchain-anchor, cloud, payment-provider or BTG-hosted services SHALL not destroy sovereign identity or locally verifiable owner records.

---

# 133. DESTRUCTIVE SOVEREIGNTY QUALIFICATION

The term **sovereign** SHALL be backed by destructive recovery evidence.

At least one qualification campaign SHALL assume that all BTG-hosted infrastructure needed by the tested deployment becomes unavailable.

Using only the documented recovery/export package and independently documented schemas/tools, the test SHALL determine whether an authorized owner can recover and interpret, as applicable:

root identity state;

key/revocation history;

credentials;

asset registry;

rights/claims graph;

policies and consent;

provenance;

contracts/licences;

usage receipts;

ledger/checkpoint evidence;

economic/accounting history;

configuration needed for migration.

The test SHALL distinguish data that is locally recoverable from data that depended on an unavailable external provider.

A sovereignty claim SHALL fail qualification if the owner's authoritative state can only be interpreted by an unavailable proprietary BTG service with no documented migration or verification path.

---

# 134. INDEPENDENT VERIFIER AND REFERENCE VALIDATION TOOLING

ENTITY SHALL provide or specify enough independent verification logic that core evidence can be checked without trusting the production application that created it.

The verifier SHALL be capable, within the scope implemented, of checking:

schema/version identifiers;

hashes/commitments;

signatures and key versions;

revocation state at event time;

ledger/hash-chain continuity;

Merkle/checkpoint evidence;

selected provenance links;

rights-claim signatures;

licence signatures/state;

usage-receipt signatures;

settlement evidence classifications;

release manifest signatures.

The independent verifier SHALL NOT require access to private content when verification can be performed using commitments and evidence records alone.

Verification failures SHALL be explicit and machine-readable.

---

# 135. OPEN FEDERATION QUALIFICATION

Phase 4 federation SHALL not be considered qualified solely because two BTG-controlled nodes communicate.

The target qualification SHALL demonstrate protocol compatibility with at least one independently operated or independently implemented verifier/node, when such an implementation is available for the declared scope.

Federation qualification SHALL cover:

peer authentication;

protocol/version negotiation;

schema negotiation;

cryptographic-suite negotiation;

capability negotiation;

valid event exchange;

invalid event rejection;

replay rejection;

rate/abuse controls;

partition/rejoin behavior;

conflict detection;

portable verification of credentials, claims, licences, provenance events, receipts and checkpoints within supported scope.

BTG MAY retain proprietary hosted services, enterprise management, marketplaces and advanced integrations while keeping the core evidence formats independently interpretable.

---

# 136. FIVE-GATE RELEASE MODEL

Every production release SHALL receive an explicit decision for five top-level gates:

**Functional Gate** — declared requirements and end-to-end behavior work for the release scope.

**Security Gate** — threat-model tests, negative authorization tests and adversarial campaigns satisfy release policy.

**Sovereignty Gate** — recovery, export, offline behavior and independence from optional providers satisfy the declared sovereign scope.

**Evidence Gate** — claims, provenance, signatures, evidence origin and independent verification remain reproducible and correctly represented.

**Economic Gate** — when economic functions are enabled, accounting, authorization, replay protection, settlement direction, reversals/refunds and reconciliation satisfy release policy.

A gate result SHALL be one of:

`PASS`

`FAIL`

`NOT_APPLICABLE_TO_DECLARED_SCOPE`

`CONDITIONALLY_ACCEPTED` only when policy explicitly permits the condition and no critical invariant is violated.

Sections 110–112 SHALL remain mandatory sub-gates within this model.

A later phase or unrelated passing gate SHALL NOT compensate for a failed gate in the release's declared scope.

---

# 137. ENTITY GOLDEN SCENARIO — AUTHORITATIVE END-TO-END TEST

Section 102 SHALL be treated as the **ENTITY Golden Scenario**.

The Golden Scenario SHALL execute on fresh test environments with:

fresh Entity A;

fresh Entity B;

fresh key material;

no manual database edits;

no hidden pre-seeded state required for success;

normal public APIs/control paths only.

The minimum chain SHALL be:

`Entity A → Entity B → identity → asset → provenance → rights → policy → licence → controlled usage → receipt → settlement → accounting → expiration/revocation → dispute → backup → total loss → restore → independent validation`

The campaign SHALL produce a machine-readable timeline linking each step to requirement IDs, test IDs and evidence hashes.

A Golden Scenario failure SHALL identify the first violated invariant or unmet requirement rather than merely reporting a generic end-to-end failure.

---

# 138. MALICIOUS ENTITY C QUALIFICATION SCENARIO

A second end-to-end campaign SHALL introduce a hostile **Entity C** attempting to compromise every material stage of the Golden Scenario.

The scenario SHALL attempt, as applicable:

identity impersonation;

credential abuse;

rights forgery;

conflicting claims;

policy bypass;

licence replay;

unauthorized content access;

usage-receipt forgery;

settlement redirection;

duplicate settlement;

prompt injection;

connector escalation;

capability escalation;

evidence tampering;

backup poisoning;

migration manipulation.

Success criteria SHALL require that attacks are either rejected, contained, quarantined or surfaced according to policy without silently corrupting authoritative state.

---

# 139. CATASTROPHIC PROVIDER-LOSS QUALIFICATION SCENARIO

A third end-to-end campaign SHALL remove critical external dependencies during active operation.

At minimum, test campaigns SHALL cover loss of:

BTG-hosted services;

AI provider;

cloud storage provider where configured;

public blockchain anchor provider where configured;

payment provider where configured;

federation peer;

network connectivity.

The system SHALL prove which functions remain available, which enter degraded state, which fail closed and how synchronization/reconciliation proceeds after restoration.

Sovereign identity, local rights/provenance records and owner-controlled recovery SHALL not be destroyed by failure of an optional provider.

---

# 140. SECURE SOFTWARE SUPPLY CHAIN AND BUILD ENGINEERING

ENTITY production software SHALL use a controlled build and release pipeline.

The pipeline SHALL support:

source revision pinning;

dependency/version pinning where feasible;

SBOM generation;

RBOM generation;

PBOM generation;

secret scanning;

static analysis appropriate to the implementation;

dependency/vulnerability review appropriate to the implementation;

test execution;

property/invariant campaigns;

adversarial campaigns;

artifact hashing;

release signing;

provenance/evidence manifest generation;

release-gate evaluation.

Production signing keys SHALL be separated from ordinary developer credentials.

A release artifact SHALL be traceable back to its source revision and evidence package.

Manual emergency builds SHALL be separately identified and SHALL not bypass mandatory critical security/evidence gates.

---

# 141. DEPLOYMENT TOPOLOGY AND ENVIRONMENT SEPARATION

Development, test, qualification/staging and production environments SHALL be logically separated.

Production secrets, root authorities and payment credentials SHALL NOT be copied into development or ordinary test environments.

Environment configuration SHALL be version-controlled or otherwise auditable without storing secrets in source control.

Deployment topology SHALL document:

service boundaries;

network trust zones;

data stores;

key stores;

external dependencies;

federation endpoints;

backup targets;

observability paths;

administrative paths;

recovery paths.

High-value administrative operations SHALL use least privilege and auditable step-up controls.

Changes to production schemas or cryptographic behavior SHALL use controlled migrations with rollback/recovery procedures.

---

# 142. OPERATIONAL SLO, OBSERVABILITY AND INCIDENT READINESS

The metrics in Sections 75–78 SHALL be tied to operational objectives for each production deployment class.

Before production qualification, each critical service SHALL define:

availability target;

latency target where relevant;

error-budget or equivalent reliability threshold;

recovery-point objective;

recovery-time objective;

maximum tolerated synchronization lag where relevant;

alert thresholds;

owner/on-call responsibility;

runbook.

Operational telemetry SHALL minimize sensitive content and shall not become a hidden secondary data store of private asset information.

Incident procedures SHALL cover containment, evidence preservation, key compromise, credential revocation, user notification requirements where applicable, recovery, root-cause analysis and verified remediation.

---

# 143. PRIVACY LEAKAGE AND DATA-EXFILTRATION ASSURANCE

ENTITY SHALL maintain automated privacy-leakage tests in addition to ordinary authorization tests.

The tests SHALL attempt to cause sensitive information leakage through:

NIKI prompts/responses;

ADAM tool inputs/outputs;

BECP messages;

connectors;

logs;

errors;

telemetry;

exports;

federation messages;

malicious documents;

metadata correlation;

pairwise identifier correlation.

The test suite SHALL distinguish direct content leakage, metadata leakage, linkage leakage and inference leakage.

A passing test SHALL demonstrate that minimum-disclosure policy is enforced at the actual information boundary, not merely configured in a database.

---

# 144. QUALIFICATION EVIDENCE PACKAGE

Every qualified release SHALL generate a self-contained evidence package sufficient for internal audit and, where authorized, independent review.

The package SHALL contain or reference by immutable hash:

release manifest;

source revision;

build artifacts;

build hashes;

RTM snapshot;

ADR set applicable to the release;

schema versions;

migration versions;

cryptographic-suite versions;

SBOM;

RBOM;

PBOM;

unit-test results;

integration-test results;

property/invariant results;

adversarial/red-team results;

Golden Scenario result;

Malicious Entity C result where in scope;

provider-loss/destructive-sovereignty results where in scope;

performance results;

backup/restore result;

interoperability result;

release-gate decisions;

known residual risks;

release signer;

timestamp.

The evidence manifest SHALL itself be signed.

Missing evidence SHALL be represented as missing, not implicitly treated as passed.

---

# 145. SUBSYSTEM TRL AND MATURITY REPORTING

ENTITY maturity SHALL be reported by subsystem and declared scope.

The report SHALL include at minimum, when present:

Identity TRL;

Vault TRL;

Rights/Claims TRL;

Provenance TRL;

AI Governance TRL;

Agent Governance TRL;

Licensing TRL;

Usage-Control TRL;

Settlement/Accounting TRL;

Data Space TRL;

Federation TRL;

Independent Verification maturity;

overall qualified maturity for the declared release scope.

A high maturity level in one subsystem SHALL NOT be used to hide a lower maturity level in another subsystem that is required for the declared product claim.

TRL evidence SHALL identify the operational environment, representative users/integrations, security evidence, recovery evidence and duration/extent of demonstrated operation appropriate to the claimed level.

---

# 146. PHASE ENTRY AND EXIT GATES

Implementation SHALL continue to follow the four phases defined in Sections 95–98.

A later phase SHALL NOT compensate for an unqualified earlier-phase dependency.

**Phase 1 — Sovereign Core** exit criteria SHALL include qualified identity/recovery, source permissions, vault, asset registry, provenance, rights graph, policy/consent, NIKI projection, ADAM capability boundaries, ledger, backup/restore, portability and the applicable security/sovereignty/evidence gates.

**Phase 2 — Entity-to-Entity Economy** SHALL not be considered production-ready until Phase 1 dependencies are qualified and the economic gate passes for the enabled scope. If corporate-capital functions are enabled, Phase 2 exit criteria SHALL additionally include qualified capital authorization, capitalization arithmetic, share-ledger integrity, shareholder-register reconciliation, corporate-action controls, valuation/disclosure separation, instrument classification and applicable transfer restrictions.

**Phase 3 — Data Spaces** SHALL require qualified contributor rights, governance, privacy, quality/fraud controls, usage evidence and deterministic/auditable allocation for enabled revenue-sharing functions.

**Phase 4 — Open Federation** SHALL require protocol documentation, independent verification and federation conformance evidence.

Exceptions SHALL be explicit engineering waivers with scope, risk, approver, expiry and remediation plan; waivers SHALL NOT override non-negotiable core invariants.

---

# 147. EXTERNAL REVIEW AND ASSURANCE READINESS

The architecture, threat model, cryptographic interfaces, rights ontology, economic model and evidence package SHALL be structured so that an authorized independent reviewer can evaluate them without access to undocumented tribal knowledge.

Review materials SHALL identify:

security assumptions;

trust assumptions;

out-of-scope threats;

known residual risks;

cryptographic dependencies;

external providers;

legal/compliance boundaries;

privacy boundaries;

evidence limitations;

open defects/exceptions.

An external review SHALL NOT be represented as a guarantee of legal ownership, security perfection or factual truth beyond the review scope.

---

# 148. MASTER ENGINEERING ARTIFACT STRUCTURE

A complete implementation SHOULD organize authoritative engineering artifacts under a deterministic structure comparable to:

```text
ENTITY/
  docs/
    architecture/
    adr/
    threat_model/
    trust_model/
    privacy/
    rights_ontology/
    policy_odrl/
    economics/
    corporate_capital/
    digital_commodities/
    disclosures/
    instrument_classification/
    federation/
    recovery/
    operations/
  requirements/
    sers/
    rtm/
  schemas/
    identity/
    rights/
    provenance/
    policy/
    licensing/
    usage/
    settlement/
    digital_commodities/
    corporate_economics/
    capital_structure/
    shares/
    corporate_actions/
    disclosures/
    instrument_classification/
    ledger/
    evidence/
  src/
  migrations/
  verifier/
  tests/
    unit/
    integration/
    property/
    adversarial/
    e2e/
    interoperability/
    recovery/
    performance/
  supply_chain/
    sbom/
    rbom/
    pbom/
  evidence/
    releases/<version>/
  runbooks/
  tools/
```

Equivalent structures MAY be used, but the same artifact classes SHALL remain discoverable and traceable.

Generated evidence SHALL not be mixed with editable source requirements in a way that permits test results to be silently altered.

---

# 149. COMPLETE 10/10 ENGINEERING ACCEPTANCE TARGET

The phrase **10/10 engineering target** SHALL refer to evidence-backed completion criteria, not marketing language.

The target is reached only when the declared production scope demonstrates:

**Architecture breadth:** formal subsystem contracts and complete domain coverage.

**Systems engineering:** invariants, state machines, failure modes, dependency boundaries and controlled migrations.

**Privacy/security:** threat-modelled, adversarially tested, recovery-tested and independently reviewable controls.

**AI governance:** bounded NIKI/ADAM authority, minimum-disclosure projection, prompt-injection resistance and exfiltration testing.

**Rights/provenance:** formal ontology, dispute awareness, evidence-origin integrity, SBOM/RBOM/PBOM and independent verification.

**Economic architecture:** accounting correctness, authorization, real payment evidence, replay protection, reversals/refunds, royalties/distribution and reconciliation for enabled scope.

**Corporate-capital architecture (when enabled):** lawful/authorized issuance controls, capitalization invariants, share-ledger/shareholder-register integrity, corporate-action governance, dilution correctness, digital-commodity economic attribution, valuation/market-price separation, disclosure evidence and transfer/regulatory controls.

**Standards/interoperability:** executable conformance and semantic round-trip tests.

**Sovereignty:** destructive recovery/export testing that does not depend on BTG remaining online.

**Qualification discipline:** complete RTM, signed evidence package, five release gates and successful authoritative end-to-end scenarios.

No assessment category SHALL be declared complete merely because the design document contains the requirement.

---

# 150. FINAL COMPLETE-SYSTEM ENGINEERING PRINCIPLE

The v2.0 complete master design added one engineering rule to the non-negotiable principle in Section 120. The v2.1 corporate-capital extension preserves that rule and applies it equally to capital structure, share ownership, corporate economics, valuation and market-price claims:

**Every important architectural claim SHALL be backed, at the maturity level being claimed, by reproducible implementation evidence.**

Therefore ENTITY SHALL progress from:

**comprehensive architecture**

to:

**implemented architecture**

to:

**verified architecture**

to:

**adversarially tested architecture**

to:

**independently reproducible, qualified operation.**

The completed ENTITY system is accepted only when its claims about identity, authority, privacy, rights, provenance, usage, value, recovery, interoperability and enabled corporate-capital state are no stronger than the evidence that can be reproduced for them.


---

# 151. CORPORATE ENTITY AND DIGITAL-COMMODITY ECONOMY

ENTITY SHALL support a corporate Entity as a sovereign organizational principal whose productive digital assets, contractual rights, liabilities, usage evidence, settlements, accounting records and capital structure can be governed within one evidence architecture.

A corporate Entity MAY control large portfolios of software, datasets, AI models, APIs, media, knowledge corpora, digital services, licences and other lawfully commercializable digital assets.

For this architecture, a **Digital Commodity** is an ENTITY asset classification representing a digital asset or service that is capable of measurable economic use under defined rights, policy and contract.

A Digital Commodity SHALL have an Entity Asset ID and SHALL remain subject to the existing Rights & Claims Graph, policy/consent, licensing, usage-control, settlement and provenance requirements.

A Digital Commodity record SHOULD support:

commodity ID;

underlying asset/version IDs;

controlling Entity;

rights state;

commercialization authority;

licensing model;

usage-meter model;

revenue-recognition mapping;

cost/royalty-obligation mapping;

availability/status;

jurisdiction/restrictions;

provenance/evidence strength;

external identifiers;

current economic-attribution state.

The Digital Commodity classification SHALL NOT imply:

legal commodity status;

security status;

transferability;

public tradability;

objective market value;

unrestricted ownership;

unrestricted sublicensing.

The legal/regulatory classification of any instrument or asset SHALL remain a separate evidence-backed determination.

---

# 152. DIGITAL-COMMODITY ECONOMIC ATTRIBUTION

ENTITY SHALL attribute economic activity to Digital Commodities using independently identifiable events rather than aggregate estimates where evidence is available.

Attributable activity MAY include:

licensed access;

API requests;

subscriptions;

software seats;

compute consumption;

dataset queries;

model inference;

AI training/evaluation access;

royalty-bearing use;

sales;

service delivery;

authorized derivative exploitation;

other contractually defined use.

A DigitalCommodityEconomicEvent SHALL identify at minimum:

event ID;

commodity/asset ID;

corporate Entity;

counterparty or privacy-preserving relationship identifier where applicable;

usage/transaction class;

usage assurance level;

contract/licence reference where required;

quantity/unit;

economic obligation generated, if any;

currency/unit of account;

settlement relationship;

cost/royalty attribution where known;

evidence origin;

timestamp;

signatures/attestations where required.

ENTITY SHALL distinguish **activity**, **billable activity**, **contracted value**, **accrued value**, **settled value**, **recognized accounting revenue** and **cash receipt**.

A usage event SHALL NOT automatically be represented as revenue, profit, cash or market value.

Economic attribution logic SHALL be versioned, deterministic for the same inputs where practical, auditable and protected against duplicate counting.

Corrections SHALL occur through corrective/superseding events rather than silent history rewriting.

---

# 153. CORPORATE CAPITAL STRUCTURE

A corporate Entity MAY maintain a machine-verifiable CapitalStructure.

The CapitalStructure SHALL represent, where applicable:

authorized share classes/series;

authorized quantity;

issued quantity;

outstanding quantity;

treasury quantity where the jurisdiction/entity structure permits it;

reserved/unissued quantity;

cancelled quantity;

conversion rights;

options/warrants/convertible rights where explicitly supported;

voting rights;

dividend/distribution rights;

liquidation or redemption rights;

transfer restrictions;

jurisdiction;

governing corporate documents;

effective dates;

approvals/resolutions;

external register references where applicable.

ENTITY SHALL maintain arithmetic invariants appropriate to the configured corporate structure.

At minimum, no issuance SHALL cause issued shares to exceed the amount lawfully authorized under the active capital authorization unless an authorized amendment takes effect first.

CapitalStructure history SHALL be append-only through signed corporate-capital events and SHALL remain reproducibly reconcilable at any historical checkpoint.

---

# 154. SHARE CLASSES, SERIES AND RIGHTS

Each ShareClass or series SHALL have explicit machine-readable rights and restrictions.

A ShareClass SHALL support, where applicable:

class/series identifier;

issuer Entity;

authorized quantity or unlimited status where legally configured;

voting weight;

voting scope;

dividend rights;

participation rights;

liquidation preference;

redemption rights;

conversion rights;

pre-emption/participation rights;

transfer restrictions;

holder eligibility restrictions;

vesting/escrow restrictions;

priority/ranking;

jurisdiction;

governing-document reference;

effective version.

ENTITY SHALL NOT infer equal economic, voting or liquidation rights merely because two instruments are both called shares.

Amendment of class rights SHALL require the configured corporate approvals and SHALL produce a new effective version without rewriting historical rights.

---

# 155. SHAREHOLDER REGISTER AND SHARE POSITIONS

ENTITY SHALL support an authoritative shareholder register for corporate Entities that enable corporate-capital functionality.

A ShareholderRegisterEntry SHALL support:

issuer;

holder Entity or permitted legal identity reference;

registered-holder status;

beneficial-owner information where lawfully available and required;

share class/series;

quantity;

acquisition/issuance basis;

restrictions/encumbrances;

certificate or electronic-record reference where applicable;

acquisition/effective date;

status;

jurisdictional/compliance attributes;

supporting share-ledger events.

ENTITY SHOULD support privacy-preserving disclosure so that public/federated evidence need not expose private shareholder identity when disclosure is not required.

The private authoritative register and any public disclosure view SHALL be separate projections.

A shareholder register SHALL be reproducible from authorized share-ledger events plus permitted migration checkpoints.

---

# 156. SHARE LEDGER AND SHARE STATE MACHINE

Corporate equity SHALL have a distinct ShareLedger separate from ordinary usage, asset and settlement events while remaining cryptographically linked to the Entity event ledger.

Supported share events MAY include:

`CLASS_AUTHORIZED`

`CLASS_AMENDED`

`ISSUANCE_AUTHORIZED`

`SHARES_ISSUED`

`TRANSFER_PROPOSED`

`TRANSFER_APPROVED`

`TRANSFER_REJECTED`

`TRANSFER_SETTLED`

`SHARES_CONVERTED`

`SHARES_REPURCHASED`

`SHARES_REDEEMED`

`SHARES_CANCELLED`

`SHARES_RESTRICTED`

`SHARES_RELEASED`

`CORRECTION_SUPERSEDED`.

Every material transition SHALL verify:

authority;

share availability;

class rights;

transfer restrictions;

required approvals;

jurisdiction/compliance state;

unique transaction/event identifier;

signature(s);

idempotency/replay status;

resulting capitalization invariants.

Invalid transitions SHALL fail closed.

Usage activity SHALL NOT directly invoke `SHARES_ISSUED` or alter shareholder ownership percentages.

---

# 157. SHARE ISSUANCE, TREASURY, REPURCHASE AND CANCELLATION

Share issuance SHALL be a governed corporate action.

An issuance SHALL identify:

issuer;

share class/series;

quantity;

recipient(s);

consideration or issuance basis;

currency/value description where applicable;

corporate authorization;

board/shareholder approval where configured;

subscription/issuance agreement where applicable;

instrument classification;

jurisdiction;

transfer restrictions;

settlement/consideration evidence where required;

effective time.

ENTITY SHALL distinguish:

new issuance;

transfer of existing outstanding shares;

treasury/reserved issuance where legally configured;

repurchase;

redemption;

cancellation.

Repurchased shares SHALL NOT be silently treated as cancelled or treasury shares; the configured jurisdictional/corporate rule SHALL determine the resulting state.

Issuance consideration SHALL NOT be represented as paid merely because the issuance was authorized.

---

# 158. DILUTION AND CAPITALIZATION MATHEMATICS

ENTITY SHALL calculate capitalization effects deterministically from the authoritative share ledger.

The system SHALL be able to calculate, where applicable:

pre-transaction shares outstanding;

new shares issued;

post-transaction shares outstanding;

holder percentage before and after transaction;

fully diluted quantity under an explicitly defined method;

option/warrant/convertible effects where supported;

class-level and consolidated voting power;

dividend/distribution participation base.

Every dilution calculation SHALL identify the denominator and methodology used.

ENTITY SHALL NOT represent an ownership percentage without identifying whether it is based on:

issued shares;

outstanding shares;

voting shares;

fully diluted shares;

another explicitly defined capitalization basis.

No increase in Digital Commodity usage SHALL by itself increase the number of outstanding shares or alter ownership percentages.

---

# 159. CORPORATE ACTIONS, DIVIDENDS AND DISTRIBUTIONS

ENTITY SHALL support governed corporate actions as first-class events.

CorporateAction types MAY include:

share issuance;

class amendment;

stock split/consolidation;

conversion;

repurchase/redemption;

cancellation;

dividend declaration;

distribution declaration;

rights offering;

merger/reorganization event;

spinout or asset transfer;

other jurisdictionally permitted actions.

A corporate action SHALL identify:

authority;

approvals;

affected classes;

record/effective dates;

calculation methodology;

holder eligibility;

financial/accounting consequences;

supporting resolutions/agreements;

regulatory/compliance state where applicable.

A dividend or distribution SHALL not become payable merely because the corporation generated usage or revenue.

Declaration, payable amount, eligibility, payment evidence and accounting recognition SHALL remain distinct states.

---

# 160. CORPORATE ECONOMIC AGGREGATION

ENTITY SHALL support a Corporate Economic Aggregator that consolidates asset-level economic evidence into corporate-level reporting without treating internal estimates as accounting facts.

The aggregator MAY combine, subject to configured accounting/reporting policy:

recognized revenue;

contracted backlog;

accrued receivables;

settled receipts;

cash balances;

digital-asset carrying values where properly supported;

capitalized development assets where permitted/configured;

royalty obligations;

licensing liabilities;

operating costs;

debt;

other assets/liabilities;

retained earnings/deficit;

Digital Commodity utilization metrics.

Each aggregate SHALL retain lineage to source accounting/evidence records.

The same economic event SHALL not be counted more than once merely because it appears in usage, licensing, settlement and accounting subsystems.

The aggregator SHALL expose reconciliation controls capable of identifying duplicate attribution and unmatched economic events.

---

# 161. CORPORATE ECONOMIC STATE AND PER-SHARE METRICS

ENTITY MAY compute corporate and per-share metrics for explanation, reporting and analysis.

Metrics MAY include:

revenue per share;

recognized earnings per share where an approved accounting methodology is configured;

book value per share;

net-asset-value-style metrics where the underlying valuation methodology is explicitly identified;

cash flow per share;

settled-value-per-share indicators;

Digital Commodity usage per share;

Digital Commodity revenue contribution;

asset concentration;

customer/revenue concentration;

royalty burden;

contracted backlog per share.

Every per-share metric SHALL identify:

numerator;

denominator;

share basis;

period;

accounting/valuation method;

data/evidence completeness;

currency/unit;

timestamp/version.

ENTITY SHALL NOT label an internal economic metric as **share price** unless it is supported by an applicable market-price observation under Section 162.

---

# 162. VALUATION AND MARKET-PRICE SEPARATION

ENTITY SHALL maintain strict semantic separation among:

**Par/Stated Value** — a legal/accounting attribute where applicable;

**Book Value** — accounting-derived equity value under the configured accounting basis;

**NAV/Asset-Based Estimate** — a methodology-dependent estimate;

**Modelled Indicative Value** — an analysis or inference;

**Transaction-Implied Value** — value implied by a specific financing or arm's-length transaction;

**Externally Observed Market Price** — price observed from an authorized external market/venue/data source;

**Offer/Ask/Bid** — a market indication not necessarily a completed transaction.

ENTITY SHALL NOT automatically recalculate an externally observed share price because Digital Commodity usage changes.

Internal modelled valuation SHALL be marked `DERIVED_INFERENCE` unless independently established otherwise.

A MarketPriceObservation SHALL record:

instrument/share class;

source/venue;

price;

currency;

bid/ask/trade classification;

quantity where known;

timestamp;

source confidence;

verification state.

A modelled value SHALL identify the valuation methodology, assumptions and input evidence.

ENTITY SHALL never present a modelled or internally calculated value as an executed market price.

---

# 163. SHARE TRADING, TRANSFER AND MARKET INTEGRATION

ENTITY MAY support authorized share transfers and integrations with lawful external transfer agents, registrars, broker/dealer systems, exchanges, alternative trading systems, private-market platforms or other permitted venues.

ENTITY SHALL NOT assume that a share may be publicly traded merely because it exists in the share ledger.

Before an enabled transfer, ENTITY SHALL evaluate applicable:

instrument classification;

issuer restrictions;

class restrictions;

holder eligibility;

contractual restrictions;

lockups/vesting;

jurisdiction;

required approvals;

transfer-agent/registrar controls;

market/venue status;

identity/KYC/AML or other compliance controls where required by the configured integration.

A transfer SHALL distinguish contractual agreement, clearing/settlement where applicable, payment settlement, and final shareholder-register update.

Failed or reversed settlement SHALL not silently create final ownership.

ENTITY SHOULD prefer integration with appropriately authorized external market infrastructure rather than attempting to create an unqualified public securities exchange inside the core protocol.

---

# 164. REGULATED-INSTRUMENT CLASSIFICATION BOUNDARY

ENTITY SHALL maintain an explicit InstrumentClassification for corporate shares and other capital/economic instruments.

Possible engineering classifications MAY include:

`CORPORATE_EQUITY`

`DEBT_INSTRUMENT`

`OPTION_OR_WARRANT`

`CONVERTIBLE_INSTRUMENT`

`ROYALTY_INTEREST`

`CONTRACTUAL_REVENUE_INTEREST`

`NON_TRANSFERABLE_PARTICIPATION`

`INTERNAL_ACCOUNTING_UNIT`

`REGULATED_SECURITY`

`POTENTIALLY_REGULATED`

`CLASSIFICATION_UNKNOWN`.

These labels SHALL be configuration/evidence states and SHALL NOT replace legal advice, regulator determinations or authoritative external classifications.

Where classification is uncertain and the proposed action could constitute issuance, public offering, trading, transfer, market-making, custody or another regulated activity, ENTITY SHALL fail closed or require configured authorized review before execution.

Jurisdiction modules SHALL be versioned and effective-dated.

Historical transactions SHALL retain the classification/ruleset used at the time.

---

# 165. CORPORATE DISCLOSURE AND INVESTOR EVIDENCE

ENTITY SHOULD support evidence-backed corporate disclosure snapshots without forcing confidential corporate data onto a public ledger.

A DisclosureSnapshot MAY include:

capitalization table summary;

share classes and rights;

shares issued/outstanding;

material transfer restrictions;

Digital Commodity count by category;

active commercial Digital Commodities;

usage metrics;

licence/customer metrics;

contracted/accrued/settled economic metrics;

recognized accounting metrics;

material royalty/obligation metrics;

asset/revenue concentration;

valuation methodology where provided;

market-price source where provided;

data freshness;

assurance/evidence level;

scope exclusions;

known limitations.

Disclosure SHALL distinguish public, investor-confidential, board-confidential, regulator-only and internal information classes where applicable.

A public disclosure SHALL not expose private customer, employee, personal or trade-secret information merely to prove aggregate corporate metrics.

ENTITY SHOULD support cryptographic commitments and auditor/verifier attestations that allow aggregate claims to be checked without disclosing unnecessary underlying content.

---

# 166. CAPITAL-MARKET EVIDENCE BOUNDARY

ENTITY SHALL extend the Evidence Boundary to corporate-capital assertions.

The system SHALL distinguish at minimum:

corporate assertion;

board/shareholder authorization;

internal accounting record;

externally confirmed payment;

transfer-agent/registrar attestation;

auditor/independent reviewer attestation;

market-venue price observation;

modelled valuation;

regulator/authority record;

unknown/unverified state.

ENTITY SHALL NOT infer:

`high usage = high share price`;

`revenue growth = guaranteed appreciation`;

`internal valuation = market price`;

`share issuance = successful financing`;

`subscription agreement = cash received`;

`payment received = legally completed share issuance`;

`ledger ownership = external register ownership` where an external authoritative register controls.

UI, API and reports SHALL preserve those distinctions.

---

# 167. CORPORATE-CAPITAL AUTHORITY AND GOVERNANCE

Corporate-capital actions SHALL operate under stricter authority controls than ordinary asset usage.

ENTITY SHALL support policy-driven approval thresholds for:

creating/amending share classes;

increasing authorized capital where applicable;

issuing shares;

repurchasing/redeeming/cancelling shares;

converting shares;

changing transfer restrictions;

declaring dividends/distributions;

major asset transfers affecting capital economics;

publishing investor disclosures;

enabling market/transfer integrations.

Thresholds MAY require combinations of:

officer approval;

director approval;

board threshold;

shareholder class approval;

external counsel/compliance approval;

transfer-agent/registrar approval;

other configured authority.

NIKI MAY explain, simulate and propose corporate-capital actions but SHALL NOT directly mutate capitalization.

ADAM MAY execute only under explicit corporate-capital capabilities whose scope identifies the issuer, action, share class, quantity/value limits, approvers, counterparties and expiry.

---

# 168. ACCOUNTING AND EQUITY-LEDGER INTEGRATION

The corporate-capital subsystem SHALL integrate with but remain semantically distinct from double-entry accounting.

Share issuance, repurchase, redemption, dividends/distributions and related transactions SHALL create accounting entries only according to the configured accounting treatment and actual economic evidence.

ENTITY SHALL maintain links among:

share-ledger event;

corporate authorization;

subscription/transfer agreement;

payment/consideration evidence;

accounting journal entry;

shareholder-register update;

external transfer-agent/registrar record where applicable.

A share-ledger event SHALL NOT itself prove cash movement.

An accounting entry SHALL NOT itself prove legal share ownership.

The system SHALL reconcile capital accounts and share quantities independently and surface mismatches.

---

# 169. CORPORATE-CAPITAL ADVERSARIAL AND INVARIANT TESTING

Qualification of corporate-capital scope SHALL include property and adversarial tests.

Mandatory invariants SHALL include, as applicable:

unauthorized actor cannot issue shares;

issued quantity cannot exceed authorized limits under the configured model;

cancelled shares cannot later transfer without a new lawful issuance path;

one transfer cannot credit two recipients;

replayed issuance/transfer requests are idempotently rejected;

shareholder-register totals reconcile to outstanding shares by class;

corporate actions preserve arithmetic invariants;

dilution calculations use declared denominators;

usage events cannot directly mutate share ownership;

modelled valuation cannot overwrite externally observed market price;

market-price data cannot be fabricated from internal usage;

payment failure cannot silently finalize paid issuance when payment is required;

restricted shares cannot transfer through an unrestricted path;

NIKI read/explanation rights cannot mutate capital structure;

ADAM cannot exceed a corporate-capital capability.

Adversarial campaigns SHALL attempt:

unauthorized dilution;

share over-issuance;

duplicate issuance;

forged board approval;

forged shareholder approval;

holder substitution;

transfer-restriction bypass;

register/ledger divergence;

payment-for-share mismatch;

market-price spoof ingestion;

valuation-label confusion;

usage-to-price manipulation;

unauthorized disclosure of shareholder/private financial information.

---

# 170. CORPORATE-CAPITAL GOLDEN SCENARIO AND ACCEPTANCE

A production scope that includes corporate-capital functionality SHALL complete a fresh end-to-end qualification scenario in addition to the general ENTITY Golden Scenario.

The minimum Corporate-Capital Golden Scenario SHALL include:

create/verify Corporate Entity A;

register multiple lawful Digital Commodities;

record rights/policy/licensing status;

generate controlled usage events;

produce usage receipts;

generate contractual obligations;

settle selected obligations with evidence;

post/reconcile accounting events;

aggregate corporate economic state;

create authorized share classes;

record authorized/issued/outstanding quantities;

issue shares through an approved workflow;

verify consideration/payment evidence where applicable;

update shareholder register;

perform a second issuance and calculate dilution;

execute an authorized share transfer subject to restrictions;

execute one corporate action such as dividend/distribution, split, conversion, repurchase or cancellation within the enabled scope;

produce a DisclosureSnapshot;

produce book/economic per-share metrics;

ingest or simulate a separately classified external market-price observation for test purposes;

prove that internal usage/valuation does not overwrite market price;

attempt unauthorized issuance/transfer and demonstrate denial;

backup and restore capital state;

independently verify share-ledger history, capitalization arithmetic, economic attribution and disclosure evidence.

The scenario SHALL prove the core v2.1 invariant:

**productive Digital Commodity activity may contribute evidence to corporate economic performance, but only authorized corporate actions may change share ownership or share count, and only valid market/valuation evidence may support claims about share value.**

Corporate-capital scope SHALL NOT be declared qualified if the system can silently convert usage into equity issuance, internal valuation into market price, or accounting records into unsupported legal ownership.


---

# 171. INDEPENDENTLY REPRODUCIBLE ENTITY TRANSACTION — TRANSFORMATIONAL SOVEREIGNTY MILESTONE

ENTITY SHALL define an **Independently Reproducible ENTITY Transaction** as a transformational system-level qualification milestone.

The purpose of this milestone is to prove that ENTITY's claims of sovereignty, machine-verifiable rights, economic evidence and corporate-capital integrity can be reproduced by an independent party without trusting or executing the BTG production application that originally created the records.

A qualifying campaign SHALL provide an independent verifier or third party with a complete documented sovereign export and the public/documented schemas, verification rules and tools required to interpret the evidence.

The independent verifier SHALL be able, within the declared qualified scope, to reproduce and validate the following evidence chain:

**Entity identity**

→ **asset provenance**

→ **rights claim**

→ **signed licence**

→ **usage receipt**

→ **settlement evidence**

→ **accounting entries**

→ **Digital Commodity economic contribution**

→ **corporate authorization**

→ **share issuance**

→ **capitalization table / shareholder-register state**

→ **disclosure snapshot**.

The verifier SHALL reach the same material conclusions as the authoritative ENTITY implementation for every evidence-backed fact in the tested chain, subject only to explicitly documented permitted differences in representation, ordering or presentation that do not change semantics.

The qualification SHALL then perform a destructive sovereignty phase in which all BTG-hosted infrastructure required by the tested deployment is treated as unavailable.

Using only the sovereign export, documented recovery material, independent verification tooling and any external authoritative evidence explicitly identified by the export, an authorized owner SHALL restore the applicable ENTITY state into a clean environment.

After restoration, the independent verifier SHALL execute the same verification chain again.

The pre-destruction and post-restoration verification results SHALL be compared for semantic equivalence.

The milestone SHALL PASS only if, for the declared scope:

- the independent verifier does not require the original BTG production application to establish the verified conclusions;
- identity, provenance, rights, licence, usage, settlement, accounting, Digital Commodity attribution, corporate authorization, capital state and disclosure evidence remain interpretable according to documented schemas;
- cryptographic signatures, commitments, key-version history, revocation state and ledger/checkpoint continuity remain independently verifiable where applicable;
- accounting and capitalization invariants reproduce correctly;
- no unsupported fact is promoted from assertion, inference or unknown state to verified state during export, restoration or independent validation;
- the restored state produces materially equivalent verification results to the pre-destruction state;
- any dependency on unavailable external providers is explicitly identified rather than silently fabricated or ignored; and
- the complete campaign produces machine-readable evidence linking requirement IDs, verifier version, input export hash, verification results, restoration evidence, output state hash and final gate decision.

The milestone SHALL FAIL if any material authoritative conclusion can only be reproduced by an unavailable proprietary BTG service for which no documented independent interpretation or migration path exists.

The milestone SHALL also FAIL if restoration changes the semantic meaning of historical identity, rights, provenance, licence, usage, settlement, accounting, capitalization or disclosure records.

A successful result SHALL establish evidence that ENTITY is operating as **sovereign, machine-verifiable economic infrastructure** rather than merely asserting that architectural property.

This milestone SHALL extend and unify the qualification intent of Sections 102, 133, 134, 137, 139 and 170. Passing any one of those sections individually SHALL NOT substitute for this complete independent reproducibility campaign when Section 171 is included in the declared release scope.

---

# 172. SOVEREIGN AUTHORITY DOCTRINE — PLATFORM NON-AUTHORITY, PROVIDER REPLACEABILITY AND DIGITAL-EXISTENCE CONTINUITY

Section 172 SHALL define the cross-cutting doctrine governing the relationship among an Entity, its information, its lawful rights and authorities, and the external platforms or infrastructure providers that may possess, store, host, transport, index, process, observe or monetize authorized access to that information.

This doctrine SHALL be read together with Sections 1, 3.6, 18–30, 36–46, 58–63, 73–75, 85–90, 118–120, 123–125, 132–139, 149–150 and 171.

The purpose of this section is to make the following architectural proposition machine-enforceable and independently testable:

> **Infrastructure possession SHALL NOT silently become sovereign authority.**

ENTITY SHALL NOT be described or implemented as a mechanism for declaring that an Entity owns every item of data it can access. ENTITY SHALL instead preserve the evidence-backed authority, rights, duties, consent powers, custody roles, processing permissions, licences, usage relationships and economic participation interests that actually exist.

## 172.1 Foundational authority doctrine

**ENTITY-SOV-AUTH-001 — Authority is distinct from possession.**  
The fact that a party possesses a copy of data SHALL NOT by itself establish sovereign authority, authorship, ownership, consent authority, licensing authority or economic participation.

**ENTITY-SOV-AUTH-002 — Authority is distinct from custody.**  
A custodian MAY hold protected data or records for another Entity while remaining unable to alter the Entity's root authority, rights state, policy state, licensing authority or economic-participation state except through an explicitly authorized operation.

**ENTITY-SOV-AUTH-003 — Authority is distinct from storage control.**  
The ability to create, read, modify, replicate, back up, encrypt, decrypt, delete or relocate storage objects SHALL NOT by itself establish lawful authority to change the meaning of the sovereign records represented by those objects.

**ENTITY-SOV-AUTH-004 — Authority is distinct from processing.**  
A platform, connector, AI provider, analytics provider or compute service MAY receive processing authority without receiving ownership, authorship, licensing authority, consent authority or economic participation.

**ENTITY-SOV-AUTH-005 — Authority is evidence-backed and scoped.**  
Every material authority asserted by ENTITY SHALL identify its subject, actor, authority type, scope, evidence origin, applicable policy or legal/contractual basis where known, effective state, revocation/expiry state and provenance.

## 172.2 Mandatory relationship separation

ENTITY SHALL be capable of representing at minimum the following relationships independently:

`POSSESSION`;

`CUSTODY`;

`STORAGE_CONTROL`;

`PROCESSING_AUTHORITY`;

`SOVEREIGN_AUTHORITY`;

`AUTHORSHIP`;

`CREATORSHIP`;

`LEGAL_RIGHTS`;

`CONSENT_AUTHORITY`;

`LICENSING_AUTHORITY`;

`AUTHORIZED_USAGE`;

`ECONOMIC_PARTICIPATION`;

`GOVERNANCE_AUTHORITY`;

`PAYMENT_AUTHORITY`.

**ENTITY-SOV-AUTH-006 — No relationship implication by default.**  
Evidence of one relationship SHALL NOT automatically create another relationship.

**ENTITY-SOV-AUTH-007 — Explicit relationship edges.**  
Each durable relationship SHALL be represented as an explicit typed edge, record or signed assertion rather than inferred solely from a filename, host, account, possession state or storage location.

**ENTITY-SOV-AUTH-008 — Relationship provenance.**  
Each relationship SHOULD identify the evidence and event history that caused the relationship to exist, change, expire, be revoked, become disputed or be superseded.

**ENTITY-SOV-AUTH-009 — Legal uncertainty preservation.**  
Where legal rights are unresolved, contested or outside ENTITY's evidence boundary, the system SHALL represent that uncertainty rather than promoting technical control into a legal conclusion.

## 172.3 Provider role and delegation model

External infrastructure providers MAY be used for storage, hosting, transport, indexing, compute, backup, content delivery, AI processing, payments, market access, transfer-agent services or other defined functions.

**ENTITY-SOV-AUTH-010 — Provider role declaration.**  
A provider relationship SHALL state the exact role or roles the provider is authorized to perform.

**ENTITY-SOV-AUTH-011 — Scoped delegation.**  
A provider delegation SHALL identify operation scope, data/asset scope, purpose, counterparty scope where relevant, time limit, retention conditions, onward-transfer/sublicensing permissions where relevant, revocation rules and applicable evidence.

**ENTITY-SOV-AUTH-012 — No transitive authority.**  
A provider receiving one capability SHALL NOT silently receive unrelated ENTITY capabilities.

**ENTITY-SOV-AUTH-013 — No provider self-promotion.**  
A provider SHALL NOT be able to promote itself from custodian, processor, storage host, connector, marketplace or observer into sovereign controller, licensor, rights-holder or economic participant merely by submitting an internal platform assertion.

**ENTITY-SOV-AUTH-014 — External contract separation.**  
Where platform terms or external contracts grant the provider rights, those rights SHALL be recorded as distinct external contractual or legal relationships and SHALL NOT be conflated with mere infrastructure possession.

**ENTITY-SOV-AUTH-015 — Delegation revocation.**  
Where revocation is legally and contractually permitted, future provider authority SHALL be revocable without requiring the Entity to abandon its root identity.

## 172.4 Provider replaceability

A core sovereignty property of ENTITY SHALL be the ability to replace infrastructure without silently replacing the Entity.

**ENTITY-SOV-AUTH-016 — Stable sovereign root across providers.**  
Changing an authorized storage, cloud, hosting, backup, indexing, AI or infrastructure provider SHALL NOT require creation of a new sovereign Entity root.

**ENTITY-SOV-AUTH-017 — Semantic continuity.**  
Provider migration SHALL preserve the semantic meaning of historical identity, provenance, rights, policies, consent, licences, usage, settlements, corporate-capital evidence and economic-participation records.

**ENTITY-SOV-AUTH-018 — Provider-independent interpretation.**  
No proprietary provider database, API or account SHALL be the only possible means of interpreting the Entity's authoritative sovereign records.

**ENTITY-SOV-AUTH-019 — Migration record.**  
A provider substitution SHALL generate a machine-readable ProviderMigrationRecord identifying source provider, destination provider, data/state scope, export commitments, import commitments, excluded state, unresolved dependencies, verification result and authorization.

**ENTITY-SOV-AUTH-020 — No silent continuing authority.**  
After a provider relationship ends, ENTITY SHALL NOT treat the former provider as retaining future authority unless a surviving contract, legal requirement, licence, retention duty or other evidence-backed relationship actually establishes that continuing authority.

**ENTITY-SOV-AUTH-021 — Provider-loss degradation.**  
Loss of one optional provider SHALL degrade only functions dependent on that provider where architecturally possible and SHALL NOT erase the sovereign interpretation of surviving identity, rights and evidence.

## 172.5 Owner/controller choice of storage and infrastructure

Subject to lawful rights, contractual restrictions, security policy and technical feasibility, the Entity owner/controller SHALL be able to choose where Entity-controlled content and sovereign state are stored.

**ENTITY-SOV-AUTH-022 — Storage-choice policy.**  
Storage location SHALL be governed by explicit Entity policy and security classification.

**ENTITY-SOV-AUTH-023 — Split storage permitted.**  
Content, keys, metadata, evidence, backups and public commitments MAY be placed with different authorized providers.

**ENTITY-SOV-AUTH-024 — Provider-neutral identifiers.**  
Durable Entity, asset, rights, licence, receipt and economic identifiers SHOULD remain meaningful independently of a provider-specific pathname, account ID or object key.

**ENTITY-SOV-AUTH-025 — Provider metadata is not authority metadata.**  
Cloud ownership fields, filesystem ACL ownership, SaaS account ownership or similar technical metadata SHALL NOT silently replace ENTITY's authority model.

## 172.6 Policy, consent and licensing independence

**ENTITY-SOV-AUTH-026 — Policy remains Entity-governed.**  
An infrastructure provider MAY enforce or mirror policy but SHALL NOT become the authoritative policy source merely because it performs enforcement.

**ENTITY-SOV-AUTH-027 — Consent remains attributable.**  
Consent authority SHALL remain attributable to the lawful authorizing party and SHALL NOT be inferred from platform possession.

**ENTITY-SOV-AUTH-028 — Licence authority follows rights.**  
Licensing authority SHALL derive from evidence-backed rights/claims, delegated authority and applicable contract/legal state rather than storage location.

**ENTITY-SOV-AUTH-029 — Access is not a licence.**  
A party that can technically read or retrieve content SHALL NOT be presumed to have authorization for commercial reuse, redistribution, AI training, sublicensing or other use beyond the applicable policy/licence.

**ENTITY-SOV-AUTH-030 — Provider export does not rewrite source authority.**  
Exporting content to a platform SHALL create an external relationship/export state; it SHALL NOT silently rewrite the source Entity's rights graph.

## 172.7 Economic participation doctrine

ENTITY SHALL preserve a distinction between economic participation and infrastructure possession.

**ENTITY-SOV-AUTH-031 — Custody does not create revenue rights.**  
A provider SHALL NOT automatically receive royalties, revenue share, equity, Digital Commodity participation or other economic interests merely because it stores, transports, processes, indexes or observes data.

**ENTITY-SOV-AUTH-032 — Economic participation requires basis.**  
Economic participation SHALL require an explicit evidence-backed basis such as a contract, licence, corporate right, royalty plan, contribution agreement, fee agreement, settlement obligation or other lawful economic relationship.

**ENTITY-SOV-AUTH-033 — Usage evidence does not establish ownership.**  
High usage MAY contribute evidence to demand, economic performance or contractual obligations, but SHALL NOT create ownership or sovereign authority.

**ENTITY-SOV-AUTH-034 — Platform monetization is separately recorded.**  
Where an external platform lawfully monetizes access under accepted terms, ENTITY SHOULD represent the platform's contractual/economic relationship separately from the Entity's sovereign source rights.

**ENTITY-SOV-AUTH-035 — Economic lineage.**  
Where economic participation is attributed to an Entity-controlled asset or Digital Commodity, the attribution SHOULD be traceable through rights/policy, licence or other authority, usage evidence, obligation, settlement/accounting and final allocation.

## 172.8 Sovereign export and digital-existence continuity

The complete sovereign state SHALL be capable of existing independently of the provider currently operating the live service.

**ENTITY-SOV-AUTH-036 — SovereignExportManifest.**  
A complete owner-controlled export SHALL contain or reference a machine-readable SovereignExportManifest describing the exported domains, schema versions, cryptographic algorithms, evidence roots, exclusions, dependencies and recovery requirements.

**ENTITY-SOV-AUTH-037 — No provider permission required for interpretation.**  
After a lawful export has been obtained, interpretation and verification of that export SHALL NOT require continued permission from the former storage/hosting provider except where an external authoritative dependency is explicitly unavoidable and documented.

**ENTITY-SOV-AUTH-038 — Independent verification.**  
High-value sovereign exports SHALL be independently verifiable using documented formats and public/portable verification rules.

**ENTITY-SOV-AUTH-039 — Restore into clean environment.**  
Qualification SHALL prove that exported sovereign state can be restored into a clean authorized environment without silently changing Entity identity or historical record meaning.

**ENTITY-SOV-AUTH-040 — Provider-independent authority continuity.**  
A successful restore SHALL preserve applicable authority relationships, rights claims, policy/consent state, licences, evidence history and economic-participation state without relying on the former provider as the authoritative source.

**ENTITY-SOV-AUTH-041 — Unknown dependency disclosure.**  
Dependencies that cannot be carried, verified or restored SHALL be declared explicitly as unresolved/externally dependent rather than fabricated.

## 172.9 Platform-centric versus Entity-authority operating model

The system SHALL be designed to replace the practical dependency pattern:

`PLATFORM → stores data → decides practical access → defines platform-scoped rights → monetizes platform usage → retains platform history → controls practical export`

with the target ENTITY pattern, to the extent lawful and technically qualified:

`ENTITY OWNER/CONTROLLER → controls sovereign authority → chooses authorized storage → sets policy → records provenance → grants licences → observes/attests usage → records economic participation → exports/migrates sovereign state`

This target pattern SHALL NOT be interpreted as a claim that the Entity can unilaterally override:

law;

court orders;

valid third-party ownership rights;

contractual obligations;

regulatory retention;

lawful platform rights already granted;

rights of other data subjects;

rights of co-creators or co-owners;

rights of employees/employers;

rights of licensees;

other independently valid interests.

The architecture SHALL therefore maximize **lawful sovereign control**, not fictional absolute ownership.

## 172.10 Required qualification campaign

A release that declares Section 172 qualified SHALL execute a fresh scenario containing at least:

1. creation of a sovereign Entity root;
2. registration of an asset in provider A storage;
3. explicit recording of provider A as custodian/storage host without sovereign authority;
4. provenance and rights records independent of provider A;
5. policy and consent state independent of provider A;
6. a valid licence and observed/attested usage relationship;
7. economic-participation evidence where applicable;
8. an attempted unauthorized provider mutation of rights, consent, licence or economic state that fails closed;
9. a possession/custody test proving provider A cannot license the asset solely because it has the bytes;
10. export of the complete qualified sovereign state;
11. removal or unavailability of provider A;
12. restoration into provider B or a clean owner-authorized environment;
13. verification that the sovereign Entity root is unchanged;
14. verification that historical signatures and provenance remain valid;
15. verification that rights/policy/licence semantics are unchanged;
16. verification that provider A does not retain undeclared future authority;
17. verification that economic-participation records reproduce correctly;
18. independent verification of the pre-migration and post-migration evidence roots/results; and
19. machine-readable qualification evidence linking requirement IDs, source/export hashes, migration evidence, verifier results and final gate decision.

## 172.11 Required adversarial cases

Qualification SHALL deliberately attempt:

- storage-provider impersonation of the sovereign Entity;
- custodian self-assignment of licensing authority;
- possession-based ownership escalation;
- processing-grant escalation into AI-training rights;
- expired provider delegation reuse;
- revoked provider delegation reuse;
- provider migration rollback;
- stale provider state overriding newer sovereign state;
- provider-specific identifier substitution;
- hidden retention of provider authority after migration;
- unauthorized economic-participation insertion;
- provider-created royalty or revenue share without contractual basis;
- external terms being misrepresented as source ownership transfer;
- incomplete export being represented as complete;
- restore changing historical rights meaning;
- restore changing economic balances or share/capital evidence;
- former-provider outage preventing otherwise independent verification.

Each attack SHALL fail closed or be explicitly surfaced as an unresolved external dependency.

## 172.12 Sovereign Authority acceptance invariant

Section 172 SHALL PASS only when the implementation can demonstrate, with reproducible evidence, that:

**custody is not authority;**

**storage is not ownership;**

**possession is not authorship;**

**processing is not consent;**

**access is not a licence;**

**usage is not ownership;**

**platform monetization is not automatic sovereign entitlement;**

**economic participation follows evidence-backed rights, authorization, contract and settlement;**

**provider replacement does not silently replace the Entity;** and

**the Entity can move the qualified sovereign state to another authorized environment without losing the machine-verifiable meaning of the lawful authority and history it is entitled to control.**

A release SHALL NOT claim the Sovereign Authority Doctrine is qualified merely because export files exist. Qualification requires successful provider-substitution, authority-escalation resistance, sovereign restore and independent semantic verification.

A successful Section 172 campaign, combined with Section 171, SHALL provide evidence that ENTITY's sovereignty claim is not merely that the user can download a copy of data. It SHALL demonstrate that the **meaning, authority relationships, rights evidence, policy, licence state, usage history, economic participation and verification logic of the qualified sovereign domain remain portable and independently interpretable when the infrastructure provider changes or disappears.**


---

# APPENDIX A — MASTER SECTION INDEX

1. SYSTEM MISSION
2. SYSTEM DEFINITION
3. CORE ARCHITECTURAL PRINCIPLES
4. SYSTEM TRUST MODEL
5. ENTITY EVIDENCE BOUNDARY
6. SOVEREIGN ROOT IDENTITY
7. PRIVACY-PRESERVING RELATIONSHIP IDENTITIES
8. ENTITY TRUST LEVELS AND SYBIL RESISTANCE
9. PERMISSIONED DATA SOURCE GATEWAY
10. HARD PROHIBITED / RESTRICTED SOURCE CLASSES
11. ENCRYPTED DATA VAULT
12. CRYPTOGRAPHIC ERASURE AND DELETION
13. ASSET REGISTRY
14. HARD AND SOFT ASSET IDENTITY
15. C2PA CONTENT CREDENTIAL SUPPORT
16. SOFTWARE AND AI-ASSISTED DEVELOPMENT PROVENANCE
17. KNOWLEDGE CAPITAL
18. RIGHTS & CLAIMS GRAPH
19. RIGHTS CLAIM DATA MODEL
20. COLLECTIVE AND MULTI-PARTY RIGHTS
21. RESTRICTED / NON-COMMODITIZABLE DATA
22. POLICY AND CONSENT ENGINE
23. REQUIRED POLICY ACTION VOCABULARY
24. CONSENT
25. EXTERNAL PLATFORM TERMS INTELLIGENCE
26. EXTERNAL EXPORT STATE
27. CONTRACT AND LICENSING ENGINE
28. LICENCE STATE MACHINE
29. REVOCATION SEMANTICS
30. USAGE CONTROL
31. DATA ACCESS GATEWAY
32. COMPUTATION-TO-DATA
33. DATA POOLS
34. DATA POOL ECONOMIC DISTRIBUTION
35. QUALITY, FRAUD AND SYNTHETIC DATA CONTROLS
36. ENTITY EVENT LEDGER
37. HASH CHAIN AND EQUIVOCATION PROTECTION
38. PUBLIC BLOCKCHAIN POLICY
39. DISTRIBUTED CONSISTENCY
40. VALUE SYSTEM
41. VALUE PROFILE
42. PRICE DISCOVERY
43. ACCOUNTING
44. SETTLEMENT STATE MACHINE
45. ENTITY VALUE CREDIT
46. EXTERNAL PAYMENT EVIDENCE
47. NIKI ACCESS MODEL
48. NIKI READ/WRITE SEPARATION
49. ADAM CAPABILITY-BASED AUTHORITY
50. HUMAN APPROVAL
51. BECP ROLE
52. EXTERNAL AI PROVIDER PROVENANCE
53. PLATFORM AND CONNECTOR PERMISSIONS
54. PROVENANCE GRAPH
55. SOFTWARE BILL OF MATERIALS / RIGHTS BILL OF MATERIALS
56. DISPUTE SYSTEM
57. REPUTATION
58. PORTABILITY
59. FEDERATION
60. CRYPTOGRAPHIC ARCHITECTURE
61. KEY PROTECTION
62. AUTHENTICATION AND SESSION SECURITY
63. AUTHORIZATION
64. PRIVACY
65. ADVERTISING / PRIVATE MATCHING
66. CLASSIFICATION ENGINE
67. API ARCHITECTURE
68. API IDEMPOTENCY
69. API ERROR MODEL
70. DATA MODEL VERSIONING
71. TIME
72. OFFLINE OPERATION
73. BACKUP AND DISASTER RECOVERY
74. AVAILABILITY
75. AUDITABILITY
76. OBSERVABILITY
77. PERFORMANCE
78. SCALE
79. EVENT RETENTION
80. SECURITY THREAT MODEL
81. AI PROMPT-INJECTION DEFENCE
82. AI EXFILTRATION PROTECTION
83. HUMAN-FACING EXPLANATIONS
84. HIGH-RISK USER WARNINGS
85. LEGAL / JURISDICTION ENGINE
86. STANDARDS INTEROPERABILITY
87. MINIMUM DOMAIN OBJECTS
88. MANDATORY IDENTIFIER PROPERTY
89. MANDATORY SIGNATURE PROPERTY
90. MANDATORY LINEAGE PROPERTY
91. BASELINE MIGRATION REQUIREMENT
92. EXISTING LEDGER MIGRATION
93. EXISTING NIKI INTEGRATION MIGRATION
94. EXISTING PLATFORM EXPORT MIGRATION
95. IMPLEMENTATION PHASE 1 — SOVEREIGN CORE
96. IMPLEMENTATION PHASE 2 — ENTITY-TO-ENTITY ECONOMY
97. IMPLEMENTATION PHASE 3 — DATA SPACES
98. IMPLEMENTATION PHASE 4 — OPEN FEDERATION
99. UNIT TEST REQUIREMENTS
100. PROPERTY / INVARIANT TESTING
101. ADVERSARIAL TESTING
102. ENTITY GOLDEN END-TO-END QUALIFICATION SCENARIO
103. PLATFORM EXPORT QUALIFICATION
104. IDENTITY RECOVERY QUALIFICATION
105. EVIDENCE BOUNDARY QUALIFICATION
106. PRIVACY QUALIFICATION
107. CRYPTOGRAPHIC QUALIFICATION
108. DATA LOSS QUALIFICATION
109. PERFORMANCE QUALIFICATION
110. SECURITY RELEASE GATE
111. ECONOMIC RELEASE GATE
112. PROVENANCE RELEASE GATE
113. TRL DEFINITION FOR ENTITY
114. REQUIRED SYSTEM DOCUMENTATION
115. REQUIRED MACHINE-READABLE EVIDENCE
116. DESIGN PROHIBITIONS
117. FINAL TARGET ARCHITECTURE
118. SYSTEM ACCEPTANCE DEFINITION
119. ENGINEERING DEFINITION OF THE COMPLETED SYSTEM
120. NON-NEGOTIABLE CORE PRINCIPLE
121. AUTHORITATIVE ARCHITECTURE BASELINE AND CHANGE CONTROL
122. REQUIREMENT IDENTIFICATION, TRACEABILITY AND ENGINEERING STATE
123. FORMAL SUBSYSTEM AUTHORITY CONTRACTS
124. INFORMATION PROJECTION AND MINIMUM-DISCLOSURE ENGINE
125. EVIDENCE ASSERTION ENVELOPE
126. FORMAL ENTITY RIGHTS ONTOLOGY
127. SBOM, RBOM AND PBOM RELEASE ATTESTATION
128. ECONOMIC CORRECTNESS AND ACCOUNTING ASSURANCE
129. STANDARDS CONFORMANCE AND INDEPENDENT INTEROPERABILITY
130. ENTITY RED TEAM AND CONTINUOUS ADVERSARIAL CAMPAIGNS
131. PROPERTY-BASED AND MODEL-BASED INVARIANT CAMPAIGNS
132. FAILURE, DEGRADATION AND RECOVERY STATE MACHINES
133. DESTRUCTIVE SOVEREIGNTY QUALIFICATION
134. INDEPENDENT VERIFIER AND REFERENCE VALIDATION TOOLING
135. OPEN FEDERATION QUALIFICATION
136. FIVE-GATE RELEASE MODEL
137. ENTITY GOLDEN SCENARIO — AUTHORITATIVE END-TO-END TEST
138. MALICIOUS ENTITY C QUALIFICATION SCENARIO
139. CATASTROPHIC PROVIDER-LOSS QUALIFICATION SCENARIO
140. SECURE SOFTWARE SUPPLY CHAIN AND BUILD ENGINEERING
141. DEPLOYMENT TOPOLOGY AND ENVIRONMENT SEPARATION
142. OPERATIONAL SLO, OBSERVABILITY AND INCIDENT READINESS
143. PRIVACY LEAKAGE AND DATA-EXFILTRATION ASSURANCE
144. QUALIFICATION EVIDENCE PACKAGE
145. SUBSYSTEM TRL AND MATURITY REPORTING
146. PHASE ENTRY AND EXIT GATES
147. EXTERNAL REVIEW AND ASSURANCE READINESS
148. MASTER ENGINEERING ARTIFACT STRUCTURE
149. COMPLETE 10/10 ENGINEERING ACCEPTANCE TARGET
150. FINAL COMPLETE-SYSTEM ENGINEERING PRINCIPLE
151. CORPORATE ENTITY AND DIGITAL-COMMODITY ECONOMY
152. DIGITAL-COMMODITY ECONOMIC ATTRIBUTION
153. CORPORATE CAPITAL STRUCTURE
154. SHARE CLASSES, SERIES AND RIGHTS
155. SHAREHOLDER REGISTER AND SHARE POSITIONS
156. SHARE LEDGER AND SHARE STATE MACHINE
157. SHARE ISSUANCE, TREASURY, REPURCHASE AND CANCELLATION
158. DILUTION AND CAPITALIZATION MATHEMATICS
159. CORPORATE ACTIONS, DIVIDENDS AND DISTRIBUTIONS
160. CORPORATE ECONOMIC AGGREGATION
161. CORPORATE ECONOMIC STATE AND PER-SHARE METRICS
162. VALUATION AND MARKET-PRICE SEPARATION
163. SHARE TRADING, TRANSFER AND MARKET INTEGRATION
164. REGULATED-INSTRUMENT CLASSIFICATION BOUNDARY
165. CORPORATE DISCLOSURE AND INVESTOR EVIDENCE
166. CAPITAL-MARKET EVIDENCE BOUNDARY
167. CORPORATE-CAPITAL AUTHORITY AND GOVERNANCE
168. ACCOUNTING AND EQUITY-LEDGER INTEGRATION
169. CORPORATE-CAPITAL ADVERSARIAL AND INVARIANT TESTING
170. CORPORATE-CAPITAL GOLDEN SCENARIO AND ACCEPTANCE
171. INDEPENDENTLY REPRODUCIBLE ENTITY TRANSACTION — TRANSFORMATIONAL SOVEREIGNTY MILESTONE
172. SOVEREIGN AUTHORITY DOCTRINE — PLATFORM NON-AUTHORITY, PROVIDER REPLACEABILITY AND DIGITAL-EXISTENCE CONTINUITY
