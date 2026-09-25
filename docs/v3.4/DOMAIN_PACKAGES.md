# ENTITY v3.4.0 Domain Packages

The six repositories below are **deployable domain packages for the one ENTITY Global Passport**. They are not six separate passport protocols.

| Domain | Repository | Included mappings | Package SHA-256 |
| --- | --- | --- | --- |
| [Healthcare](passports/HEALTHCARE.md) | [ENTITY-HEALTHCARE](https://github.com/blackmore-technology-group/ENTITY-HEALTHCARE) | HL7 FHIR · DICOM | `b4e901ce37f696fa…` |
| [Finance](passports/FINANCE.md) | [ENTITY-FINANCE](https://github.com/blackmore-technology-group/ENTITY-FINANCE) | ISO 20022 · FIX · LEI | `768dd87fd5a29c7e…` |
| [Manufacturing](passports/MANUFACTURING.md) | [ENTITY-MANUFACTURING](https://github.com/blackmore-technology-group/ENTITY-MANUFACTURING) | OPC UA · Asset Administration Shell | `bc29a0de024cea22…` |
| [AI](passports/AI.md) | [ENTITY-AI](https://github.com/blackmore-technology-group/ENTITY-AI) | NIST AI RMF · SPDX 3 · CycloneDX | `4877cb5bc76ef080…` |
| [Robotics](passports/ROBOTICS.md) | [ENTITY-ROBOTICS](https://github.com/blackmore-technology-group/ENTITY-ROBOTICS) | ROS 2 · Open-RMF | `3a0e68fa6c63b2ef…` |
| [Defence / Public-Unclassified](passports/DEFENCE_PUBLIC.md) | [ENTITY-DEFENCE](https://github.com/blackmore-technology-group/ENTITY-DEFENCE) | Public Data Governance · Originator Control | `7edc52344822e370…` |

## Deployment model

**Select package → configure organization facts → connect systems/data → ingest → verify passport → run conformance → deploy.**

Every package contains schemas, mappings, templates, conformance fixtures, SDK material and a package verifier. External standards remain externally authoritative: ENTITY mappings describe correspondence under a mapping version and do not claim normative equivalence.

The sealed package contents are intentionally preserved. Additional documentation and GitHub wiki material may be published without modifying the sealed package hashes.

## Qualification boundary

Package verification demonstrates internal package integrity and binding to the v3.4 release materials. It does not establish regulatory compliance, legal title, objective external truth, accounting fair value, independent security review or unrelated third-party interoperability.
