# Healthcare — ENTITY v3.4.0 Domain Package

**Repository:** [ENTITY-HEALTHCARE](https://github.com/blackmore-technology-group/ENTITY-HEALTHCARE)  
**Core release:** [`ENTITY v3.4.0`](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.0)  
**Protected release commit:** `2db5bff64507b8d67642122a5ff2fc73dfef9152`

This package configures the **one ENTITY Global Passport** for the Healthcare domain. It does not define a separate passport protocol and does not modify ENTITY core semantics.

## Mappings

HL7 FHIR · DICOM

Mappings are correspondence layers only. External standards remain externally authoritative and no normative equivalence is claimed.

## Required deployment facts

- `organization`
- `jurisdiction`
- `authority_source`
- `privacy_policy`

A deployment remains an example/non-production configuration until its `CONFIGURE-ME` values are replaced with organization-specific facts.

## Integrity

- Package SHA-256: `b4e901ce37f696fa10666839cb8d3cacbd1fe663070667ca1767a6245e7cf939`
- Archive SHA-256: `8384e1be86a6ca89e0eac744e5a88bcd633073c68ee46356cd4f651d695138a3`
- Verify repository package: `python tools/verify_package.py`

## Boundaries

Package validation does not establish objective truth, legal title, regulatory compliance, independent security review, market adoption or accounting fair value. Provider custody does not create ENTITY authority.

[Back to all v3.4 domain packages](../DOMAIN_PACKAGES.md)
