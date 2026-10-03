# DCO-000001 Passport / Production Binding

ENTITY display version: **3.4.3**

BIRFR-1 now follows the mandatory DCO production contract.

## Rights Passport

- privacy: `SELECTIVE_DISCLOSURE`
- SHA-256: `3ae5f9ce40dba97789c7ee84973414e4c906c2fb6aa65ac925545a1419d88119`
- custody provider is not authority
- provider credentials are not passport state
- training, inference, compute, evaluation, derivation, benchmark/certification and OEM deployment require governed rights
- raw redistribution without the separate redistribution right is prohibited
- provenance removal and usage-meter bypass are prohibited

## Global Passport

SHA-256:

`d79f05074afb42859fe0ae7d3ba97ee3bed73441fcd94949e79c22ddf2ed3663`

Profile stack:

- Global
- Robotics
- AI
- Manufacturing

Economic state:

`POTENTIAL / CAD 0`

This is deliberate. Passport issuance, supply and treasury reserve do not create market value.

## BTDU reference

The Global Passport carries a content-addressed BTDU reference to the BIRFR asset bundle root.

The binding is explicitly:

`CONTENT_ADDRESSED_REFERENCE`

and:

`exact_atomization_status = DEFERRED_RESOURCE_BOUNDARY`

A full attempt to recover the existing signed ADAM/BTDU universe was stopped by available process memory. The deployment therefore does **not** claim that BIRFR-1 was exactly atomized into that universe.

The binding still preserves the required boundaries:

- protocol origin is not asset provenance;
- BTDU topology does not create ownership;
- BTDU topology does not create economic entitlement;
- automatic protocol royalty is zero.

## Shared Robotics bridge

BIRFR-1 is bound to the reusable `ENTITY_ROBOTICS_INTEGRATION` family in `NOT_EXPOSED` mode.

No BIRFR-specific ROS/Open-RMF bridge was created.

## Public-safe publication

The public-safe manifest exposes the DCO code, name, asset class, content hash, controller/originator, version, public rights summary, passport hashes, qualification hash, benchmark summary, public provenance references and economic state.

It excludes live runtime identifiers and confidential operational state.
