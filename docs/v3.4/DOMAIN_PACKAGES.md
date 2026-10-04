# ENTITY v3.4 Domain Packages

ENTITY uses **one Global Passport** with composable domain profiles and implementation packages. Domain packages do not create separate passport protocols or separate sovereignty systems.

## Public domain packages and built-in profiles

| Domain | Distribution | Included mappings | Status |
| --- | --- | --- | --- |
| [Healthcare](passports/HEALTHCARE.md) | [ENTITY-HEALTHCARE](https://github.com/blackmore-technology-group/ENTITY-HEALTHCARE) | HL7 FHIR · DICOM | first-party package |
| [Finance](passports/FINANCE.md) | [ENTITY-FINANCE](https://github.com/blackmore-technology-group/ENTITY-FINANCE) | ISO 20022 · FIX · LEI | first-party package |
| [Manufacturing](passports/MANUFACTURING.md) | [ENTITY-MANUFACTURING](https://github.com/blackmore-technology-group/ENTITY-MANUFACTURING) | OPC UA · Asset Administration Shell | first-party package |
| [AI](passports/AI.md) | [ENTITY-AI](https://github.com/blackmore-technology-group/ENTITY-AI) | NIST AI RMF · SPDX 3 · CycloneDX | first-party package |
| [Robotics](passports/ROBOTICS.md) | [ENTITY-ROBOTICS](https://github.com/blackmore-technology-group/ENTITY-ROBOTICS) | ROS 2 · Open-RMF | first-party package |
| [Defence / Public-Unclassified](passports/DEFENCE_PUBLIC.md) | [ENTITY-DEFENCE](https://github.com/blackmore-technology-group/ENTITY-DEFENCE) | Public Data Governance · Originator Control | first-party package |
| [Software Engineering](passports/SOFTWARE_ENGINEERING.md) | core ENTITY repository | SPDX 3 · CycloneDX · SLSA | built-in profile/package |

The six historical external domain repositories retain their sealed package evidence. Software Engineering was added on 2026-10-03 as a built-in signed profile and implementation package so software repositories, algorithms, build artifacts, test evidence and engineering-control DCOs no longer fall back to an unspecified/global-only domain.

## Deployment model

**Select package/profile → configure organization facts → connect systems/data → ingest → verify passport → run conformance → deploy.**

Every domain mapping remains subordinate to the registered profile and underlying ENTITY authority/rights state. External standards remain externally authoritative: ENTITY mappings describe correspondence under a mapping version and do not claim normative equivalence.

## Wallet domain behavior

The ENTITY Wallet resolves the current Global Passport/profile stack for each DCO. Domain presentation does not create economic rights.

The 2026-10-03 production migration issued new immutable Global Passport versions for ten legacy `ENGINEERING_CONTROL` DCOs while preserving prior passports and underlying DCO state. The qualified production wallet then resolved all 12 current assets to explicit domains:

- 10 Software Engineering;
- 2 Robotics;
- 0 missing domains.

## Qualification boundary

Package/profile verification demonstrates internal integrity and binding to ENTITY release/runtime material. It does not establish regulatory compliance, legal title, objective external truth, accounting fair value, independent security review or unrelated third-party interoperability.
