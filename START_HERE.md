# Start Here

ENTITY is a provider-independent authority, rights, evidence and economic-state protocol built around five primitives:

**ENTITY Â· AUTHORITY Â· RIGHT Â· EVENT Â· VALUE**

> Infrastructure possession does not become sovereign authority.

## Understand the current release

**ENTITY v3.4.0 â€” Global Passport & Continuous Provenance** is the current protected release. It retains the v3.3 evidence/truth boundaries and adds one universal Global Passport with composable jurisdiction, industry, privacy, trust and technical profiles.

Read in this order:

1. [README](README.md)
2. [v3.4.1 portal](docs/v3.4/README.md)
3. [Global Passport architecture](docs/v3.4/GLOBAL_PASSPORT.md)
4. [Six domain packages](docs/v3.4/DOMAIN_PACKAGES.md)
5. [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md)
6. [Sovereign Authority Doctrine](docs/architecture/ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md)

## Run ENTITY

```bash
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

For v3.4.1 inspect `src/38_Global_Passports/`, `src/39_Implementation_Packages/`, `profiles/registry.json`, `protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json`, `sdk/global_passport_sdk/` and `tests/test_v3_global_passports.py`.

## Deploy a domain package

Choose Healthcare, Finance, Manufacturing, AI, Robotics or Defence/Public-Unclassified from [Domain Packages](docs/v3.4/DOMAIN_PACKAGES.md), configure organization-specific facts, connect governed systems/data, ingest, verify the passport and run package conformance.

## Independent implementation

Use the [Interoperability Challenge](docs/INTEROPERABILITY_CHALLENGE.md). BTG-controlled implementations are reproducibility baselines, not independent external validation.

## Evaluate the engineering

Start with [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md) and the [v3.4 post-release closure](docs/v3.4/RECURSIVE_CLOSURE.md).

## Found a problem?

Security-sensitive findings belong in private vulnerability reporting. Specification ambiguities and reproducible bugs belong in issues with the exact version/commit, expected result and actual result.
