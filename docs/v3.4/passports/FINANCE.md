# Finance — ENTITY v3.4.0 Domain Package

**Repository:** [ENTITY-FINANCE](https://github.com/blackmore-technology-group/ENTITY-FINANCE)  
**Core release:** [`ENTITY v3.4.0`](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.0)  
**Protected release commit:** `2db5bff64507b8d67642122a5ff2fc73dfef9152`

This package configures the **one ENTITY Global Passport** for the Finance domain. It does not define a separate passport protocol and does not modify ENTITY core semantics.

## Mappings

ISO 20022 · FIX · LEI

Mappings are correspondence layers only. External standards remain externally authoritative and no normative equivalence is claimed.

## Required deployment facts

- `organization`
- `jurisdiction`
- `authority_source`
- `settlement_policy`

A deployment remains an example/non-production configuration until its `CONFIGURE-ME` values are replaced with organization-specific facts.

## Integrity

- Package SHA-256: `768dd87fd5a29c7e2679fc2b0d4b172b8613712b148336d8fba91a3b92d0d466`
- Archive SHA-256: `43ee8464b055d68e5ebc50259eeebedac3551bcc047ec33b84f59de364e98210`
- Verify repository package: `python tools/verify_package.py`

## Boundaries

Package validation does not establish objective truth, legal title, regulatory compliance, independent security review, market adoption or accounting fair value. Provider custody does not create ENTITY authority.

[Back to all v3.4 domain packages](../DOMAIN_PACKAGES.md)
