# DCO Production Pipeline and Shared Bridges

ENTITY display version: **3.4.3**

The DCO Factory now defines an asset-first application-layer production path for serious digital assets:

`BUILD ASSET → QUALIFY → SEAL PROVENANCE → REGISTER DCO → RIGHTS PASSPORT → GLOBAL PASSPORT → PROFILE + BTDU BINDING → PUBLIC-SAFE EVIDENCE`\n\nOptional after the asset exists: `ECONOMIC INSTRUMENTS / MARKET LISTING` and `SHARED BRIDGE EXPOSURE`.

## Why the order matters

A DCO must not reach factory-managed economic issuance merely because an identifier and supply exist.

The production-pipeline registry blocks optional `ECONOMIC_INSTRUMENTS_ISSUED` unless:

- the underlying asset exists;
- qualification evidence exists;
- provenance is sealed;
- the DCO is registered;
- a Rights Passport is issued;
- a Global Passport is issued;
- profile and BTDU binding is complete.

This is an application-layer asset qualification gate. It does not replace the canonical Universal Transaction Fabric, Rights Passport, Global Passport, BTDU, EEP, wallet or settlement stores. **Ingesting or registering a DCO does not automatically issue a licence, create market supply, list an instrument or establish a price.**

## Rights Passport

Each serious DCO should have an immutable Rights Passport version describing allowed, required and prohibited actions; conditions; obligations; authority and jurisdiction references; custody references; provenance/disclosure references; privacy profile; and economic terms.

Custody is explicitly not authority.

## Global Passport

The Global Passport binds the verified Rights Passport to evidence, provenance, jurisdiction, industry profiles, standards mappings, economic state and—where appropriate—the canonical BTDU object binding.

Robotics/AI DCOs may compose:

- `entity-profile:global@1.0`
- `entity-profile:robotics@1.0`
- `entity-profile:ai@1.0`
- `entity-profile:manufacturing@1.0`

Profiles constrain interpretation; they do not create authority.

## Shared bridge rule

**Do not create one software bridge per DCO.**

`ENTITY_ROBOTICS_INTEGRATION` is a shared bridge family with reusable correspondence for:

- ENTITY API
- ROS 2
- Open-RMF
- external custody/data systems

Many DCOs bind to the same bridge definition. A per-DCO binding only records which interfaces are enabled and the exposure mode.

A bridge never creates rights or authority. Rights/entitlements must be verified separately.

## Public-safe manifest

The pipeline provides a public-manifest builder limited to:

- DCO ID;
- name;
- asset class;
- content SHA-256;
- controller/originator;
- version;
- public rights summary;
- Rights Passport hash;
- Global Passport hash;
- qualification hash;
- benchmark summary;
- public provenance references;
- economic state.

It rejects operational keys including wallet IDs, instrument IDs, venue IDs, treasury IDs, runtime paths/databases, credentials, private keys, private settlement details and customer entitlements.

## Qualification

The test campaign proves:

- economic issuance is rejected before the passport/profile/BTDU gate;
- a full required production-stage sequence can complete;
- public-safe manifests reject live operational identifiers;
- thirty DCOs can bind to one shared Robotics bridge definition without creating thirty bridge implementations;
- a non-exposed DCO cannot route an external bridge request.

This architecture remains an ENTITY **v3.4.3 application layer** and does not add a new protocol instrument class.
