# ENTITY v3.4.0 — Global Passport & Continuous Provenance

ENTITY v3.4.0 turns the existing sovereign authority, rights, evidence and economic architecture into a more directly deployable developer surface without changing the five core primitives:

**ENTITY → AUTHORITY → RIGHT → EVENT → VALUE**

The release introduces one universal **ENTITY Global Passport** that can carry a composable stack of jurisdiction, industry, privacy, trust and technical profiles. Industry packages populate that passport; they do not create incompatible industry-specific passports.

## Primary additions

1. Global Passport Envelope.
2. Fail-closed Composable Profile Stack.
3. Signed, immutable Versioned Global Profile Registry.
4. Versioned Standards Mapping Framework.
5. Continuous Provenance and Passport Derivation.
6. Executable Industry Implementation Packages and deployment SDK/CLI.

The operational adoption concept is simple: **give this digital or physical asset an ENTITY Passport.**
## Executable implementation packages

The first v3.4 package families are:

- Healthcare — HL7 FHIR and DICOM mappings.
- Finance — ISO 20022, FIX and LEI mappings.
- Manufacturing — OPC UA and Asset Administration Shell mappings.
- AI — NIST AI RMF, SPDX 3 and CycloneDX mappings.
- Robotics — ROS 2 and Open-RMF mappings.
- Defence-public — public/unclassified asset, originator, custody and provenance patterns; classified material is explicitly rejected by this package.

Packages include pre-engineered object types, profile composition, rights defaults, evidence expectations, privacy defaults, mapping rules, templates, configuration schemas, positive/negative conformance fixtures and quick-start material. Developers configure organization-specific facts rather than redesigning ENTITY.

The deployment model is:

**Select package → configure organization facts → connect systems/data → ingest → verify passport → run conformance → deploy.**

External standards remain externally authoritative. ENTITY mappings state correspondence under a mapping version; they do not redefine those standards or claim normative equivalence.
## Qualification

- Full ENTITY regression: **177/177 PASS**.
- v3.4 Global Passport/package targeted tests: **33/33 PASS**.
- Sealed v3.4 conformance campaign: **24/24 PASS** — 12 valid and 12 invalid vectors.
- Sealed kit SHA-256: `5869a3fd0ed6cb9f65bf4b20c3bd64933cad82f4aef05c5809e2e05af921f230`.
- Global Passport schema SHA-256: `4fbfed9be1b1484bc5d28b8101d1c908b2ccced13e4e99ec896c5b054892ebdd`.
- Canonical cross-language result SHA-256: `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba`.
- Rust, TypeScript, Go, C#, Java and Swift BTG-controlled native implementations all passed the same campaign in protected repositories.
- Clean CLI deployment smoke test passed through initialization, package planning, ingestion and Global Passport verification.

## Permanent boundaries

A passport is not proof that an external assertion is objectively true. Cryptographic verification proves integrity and attribution within its scope. Profiles do not create sovereign authority. Package validation does not establish regulatory compliance. Provider custody does not create ENTITY authority. Market observations do not become accounting fair value. Information bytes remain nonrival; economic scarcity resides in explicitly bounded rights or interests.

The six native implementations are **BTG-controlled interoperability evidence**, not unrelated third-party independence. Unrelated external implementation/live interoperability, independent security review, deployment-specific legal/regulatory treatment, and real external market adoption remain external milestones.
