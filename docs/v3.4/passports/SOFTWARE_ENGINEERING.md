# ENTITY Software Engineering Profile

**Profile reference:** `entity-profile:software-engineering@1.0`

The Software Engineering profile supplies an explicit ENTITY domain for software repositories, source code, libraries, applications, algorithms, build artifacts, test evidence and engineering-control DCOs.

It is a built-in ENTITY implementation package rather than a separate sovereignty system or a claim that an external software standard is redefined by ENTITY.

## Object scope

The profile supports Digital Commodity Objects representing:

- software;
- source repositories;
- algorithms;
- libraries and packages;
- executable/build artifacts;
- test and qualification evidence;
- documents and datasets used in software engineering;
- engineering-control DCOs.

## Standards mappings

The profile carries non-normative interoperability mappings for:

- SPDX 3;
- CycloneDX;
- SLSA.

Those mappings are correspondence metadata only. They do not create certification, regulatory status, supply-chain authority or legal rights.

## Wallet use

The ENTITY Wallet resolves the profile through the current Global Passport and displays **Software Engineering** as the DCO's primary domain where this profile is authoritative for the asset.

The 2026-10-03 production migration issued new immutable Global Passport versions for ten legacy `ENGINEERING_CONTROL` DCOs that previously carried only the Global profile.

The migration preserved:

- DCO IDs;
- controllers;
- Rights Passport IDs and hashes;
- evidence;
- provenance;
- existing economic state;
- prior Global Passport records.

It added explicit domain context; it did not rewrite the underlying DCOs or manufacture economic rights.

## Rights boundary

Software Engineering domain classification does not grant instrument actions.

Economic instruments may contain only actions already authorized by the active DCO Rights Passport. Domain profiles and Rights Passports remain separate authority surfaces.

## Distribution

The canonical signed profile record is published at:

`protocol/profiles/ENTITY_SOFTWARE_ENGINEERING_PROFILE.json`

Clean installations verify its signature and import it; they do not mint or re-sign the canonical profile locally.
