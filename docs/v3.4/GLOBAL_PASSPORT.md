# ENTITY Global Passport

ENTITY v3.4.0 introduces **one universal Global Passport envelope**. Jurisdiction, industry, privacy, trust and technical context are expressed through composable profiles rather than by creating incompatible passport systems.

## Core rule

A profile can describe, constrain, map and compose. A profile does **not** create sovereign authority merely by being installed.

The Global Passport binds existing ENTITY identity, authority, rights, evidence and provenance into a portable, verifiable envelope. It inherits the v3.3 evidence/truth distinction: passport validity is not proof that an external-world assertion is objectively true.

## v3.4 implementation surfaces

- `src/38_Global_Passports/global_passport.py`
- `src/38_Global_Passports/global_passport_profile.py`
- `src/38_Global_Passports/profile_registry.py`
- `src/38_Global_Passports/continuous_ingestion.py`
- `src/38_Global_Passports/passport_conformance.py`
- `src/39_Implementation_Packages/industry_packages.py`
- `profiles/registry.json`
- `protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json`
- `sdk/global_passport_sdk/`

## Preserved architecture

The v3.4 layer does not replace the existing data-rights lifecycle:

`DCO → Instrument → Listing → Trade → Settlement → Entitlement → Usage → Derived Output → Economic Consequence`

Nor does it replace the v3.3 reality/evidence path. It composes those layers into a deployable passport surface.

See [Domain Packages](DOMAIN_PACKAGES.md) for the six first-party implementation packages.
