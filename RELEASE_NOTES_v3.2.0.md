# ENTITY v3.2.0 — Adoption Layer and Rights Passport Infrastructure

ENTITY v3.2.0 is an additive adoption release built directly on the protected v3.1.0 global-infrastructure and Data Economic Sovereignty baseline.

It does **not** redesign the five core primitives and it does **not** replace the existing ENTITY Exchange Protocol market lifecycle.

The governing abstraction remains:

`ENTITY → AUTHORITY → RIGHT → EVENT → VALUE`

The preserved economic lifecycle remains:

`DCO → Instrument → Listing → Disclosure → Order/RFQ/Auction → Price Discovery → Trade → Clearing → Settlement → Entitlement → Usage → Derived Output → Economic Consequence`

## What v3.2 adds

### ENTITY Rights Passport

A signed, immutable, versioned Rights Passport can now bind an existing ENTITY object to:

- controller and authority references;
- machine-readable rights and prohibitions;
- jurisdiction-profile references;
- semantic/ontology references;
- provider-neutral custody locators;
- provenance and disclosure references;
- privacy profile;
- economic terms;
- external legal-classification assertions.

The passport explicitly preserves these boundaries:

- custody provider is not sovereign authority;
- moving storage providers does not change the ENTITY object identity;
- underlying information is not silently transferred by a rights instrument;
- information bytes do not have to be artificially scarce;
- legal classification remains dependent on external authoritative law/evidence.

### Standards adapters

v3.2 adds explicit translation/evidence adapters for:

- W3C ODRL;
- W3C Verifiable Credentials;
- DIDs;
- Gaia-X;
- International Data Spaces.

Mappings are explicit crosswalks. ENTITY does not silently declare semantic equivalence and an external standard or credential does not automatically become ENTITY authority.

### Provider-neutral connectors

The adoption layer can describe custody in:

- AWS S3;
- Azure Blob;
- Google Cloud Storage;
- Snowflake;
- Databricks;
- PostgreSQL;
- SQL Server;
- local filesystems;
- HTTP/API endpoints.

These locators contain no provider credentials and do not grant authority to the infrastructure provider.

### Developer adoption facade

The new adoption SDK composes existing v3 rights, jurisdiction, resolution and exchange profiles through a smaller developer-facing surface. It does not acquire authority and it does not bypass the underlying profiles.

### Federated resolver deployment

v3.2 exposes a fail-closed federated resolver deployment profile requiring multiple resolvers. Resolver participation itself does not create sovereign authority.

## Market structure remains intact

The existing ENTITY Exchange Protocol remains the market engine.

v3.2 does not replace:

- Digital Commodity Objects;
- rights instruments;
- listings;
- signed orders;
- RFQs;
- auctions;
- price discovery;
- clearing;
- settlement;
- entitlements;
- usage metering;
- derivative participation;
- EOPP originator participation;
- treasury positions.

Instead, v3.2 makes those instruments easier for outside systems to understand, locate, map to standards, verify and use across providers and jurisdictions.

## Qualification

- Official v3 regression: **128/128 PASS**.
- Targeted v3.2 adoption tests: **12/12 PASS**.
- Sealed adoption conformance vectors: **8 valid + 8 invalid**.
- Sealed compact kit SHA-256: `44e7a00f910c89aced3b3c1b5e9cba486809ca313e9bfb4b7bc9266095c10c14`.
- Common six-language v3.2 result SHA-256: `1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18`.
- Native BTG-controlled implementations: **Rust / TypeScript / C# / Go / Swift / Java — PASS**.

Each clean-room repository runs its inherited v3.1 campaign and then independently evaluates the pinned v3.2 sealed kit in its native runtime.

## Release lineage

v3.2.0 is based on protected v3.1.0 commit:

`b985b7cf875bdeeadb228d4d1885395cbcaf19f1`

The qualified v3.2 source/kit point is:

`ee3587a6e65c2565eaab2e815e85415ab705ea47`

This preserves the v3.0.1 and v3.1.0 histories rather than rewriting them.

## Claim boundary

The six implementations remain BTG-controlled. This release does not claim unrelated third-party implementation, independent external cryptographic/security review, deployment-specific legal approval, or demonstrated external market liquidity.

Those remain external qualification and commercialization milestones.
