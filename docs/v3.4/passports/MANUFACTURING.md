# Manufacturing — ENTITY v3.4.0 Domain Package

**Repository:** [ENTITY-MANUFACTURING](https://github.com/blackmore-technology-group/ENTITY-MANUFACTURING)  
**Core release:** [`ENTITY v3.4.0`](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.0)  
**Protected release commit:** `2db5bff64507b8d67642122a5ff2fc73dfef9152`

This package configures the **one ENTITY Global Passport** for the Manufacturing domain. It does not define a separate passport protocol and does not modify ENTITY core semantics.

## Mappings

OPC UA · Asset Administration Shell

Mappings are correspondence layers only. External standards remain externally authoritative and no normative equivalence is claimed.

## Required deployment facts

- `organization`
- `jurisdiction`
- `authority_source`
- `asset_namespace`

A deployment remains an example/non-production configuration until its `CONFIGURE-ME` values are replaced with organization-specific facts.

## Integrity

- Package SHA-256: `bc29a0de024cea22552078ff1913fa3df2b189436cb853cc2f4e08974325c4bc`
- Archive SHA-256: `f7b0e9bf563cc6cd251b21970c80d2fbafdde8b85a23dbaacb50fe73a7089851`
- Verify repository package: `python tools/verify_package.py`

## Boundaries

Package validation does not establish objective truth, legal title, regulatory compliance, independent security review, market adoption or accounting fair value. Provider custody does not create ENTITY authority.

[Back to all v3.4 domain packages](../DOMAIN_PACKAGES.md)
