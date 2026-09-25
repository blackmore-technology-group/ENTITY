# ENTITY

[![Release](https://img.shields.io/github/v/release/blackmore-technology-group/ENTITY?sort=semver)](https://github.com/blackmore-technology-group/ENTITY/releases/latest)
[![CI](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/ci.yml/badge.svg)](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/ci.yml)
[![Dependency review](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/dependency-review.yml/badge.svg)](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/dependency-review.yml)
[![License](https://img.shields.io/github/license/blackmore-technology-group/ENTITY)](LICENSE)

**Open infrastructure for sovereign digital authority, verifiable claims, data rights, and economic state that survives providers.**

ENTITY is Blackmore Technology Group's open-source protocol and reference implementation for persistent identity, delegated authority, provenance, evidence, rights, trusted state transitions, portable recovery, and data-economic infrastructure.

> **Infrastructure possession does not become sovereign authority.**

[Documentation portal](https://blackmore-technology-group.github.io/ENTITY-DOCS/) · [Start here](START_HERE.md) · [v3.4.0 Global Passport](docs/v3.4/README.md) · [Domain packages](docs/v3.4/DOMAIN_PACKAGES.md) · [Engineering evidence](docs/ENGINEERING_EVIDENCE.md) · [Roadmap](ROADMAP.md) · [Interoperability challenge](docs/INTEROPERABILITY_CHALLENGE.md) · [Governance](GOVERNANCE.md) · [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Security](SECURITY.md) · [Releases](https://github.com/blackmore-technology-group/ENTITY/releases)

---

## ENTITY v3.4.0 — Global Passport & Continuous Provenance

ENTITY v3.4.0 turns the existing sovereign identity, authority, rights, evidence and economic architecture into a directly deployable **Global Passport** surface.

> **One ENTITY Passport. Many jurisdictions, industries, standards and contexts. No new sovereignty silos.**

The release adds:

- **Global Passport Envelope** — one portable envelope binding existing ENTITY identity, rights, evidence and provenance;
- **Composable Profile Stack** — jurisdiction, industry, privacy, trust and technical profiles compose fail-closed;
- **Versioned Global Profile Registry** — signed/profile-controlled registration without silently creating authority;
- **Standards Mapping Framework** — mappings describe correspondence and never redefine external standards;
- **Continuous Provenance** — governed ingestion and passport derivation over evolving artifacts;
- **Executable Domain Packages** — Healthcare, Finance, Manufacturing, AI, Robotics and Defence/Public-Unclassified;
- **Developer SDK/CLI** — select a package, configure organization facts, ingest, verify and deploy.

[Complete operator & developer documentation](https://blackmore-technology-group.github.io/ENTITY-DOCS/) · [In-repo v3.4 source docs](docs/v3.4/README.md) · [Global Passport](docs/v3.4/GLOBAL_PASSPORT.md) · [Six domain packages](docs/v3.4/DOMAIN_PACKAGES.md)

### Inherited v3.3 evidence layer

v3.4.0 retains v3.3's Verifiable Reality, Evidence and Economic Causality model. ENTITY still keeps cryptographic verification, protocol verification and reality/evidence verification distinct. A valid Global Passport therefore does not make an external assertion objectively true.

## The market architecture is preserved

v3.4.0 preserves ENTITY's market model:

```text
DCO
 ↓
Instrument
 ↓
Listing
 ↓
Disclosure
 ↓
Order / RFQ / Auction
 ↓
Price Discovery
 ↓
Trade
 ↓
Clearing
 ↓
Settlement
 ↓
Entitlement
 ↓
Usage
 ↓
Derived Output
 ↓
Economic Consequence
```

The evidence layer sits before and around that lifecycle so a participant can ask not only **who authorized the transition**, but also **what supports the underlying claim** and **which evidence survives into downstream economic attribution**.

---

## Core primitives and invariants

ENTITY v3 preserves five core primitives:

**ENTITY · AUTHORITY · RIGHT · EVENT · VALUE**

The implementation is built around several non-negotiable boundaries:

- Identity is not an account.
- Registration is not ownership.
- Provenance is not truth.
- A valid signature is not proof that an external-world assertion is correct.
- Possession, hosting, routing, custody and storage do not create sovereign authority.
- External registries and resolvers provide evidence or resolution; participation does not make them sovereign authority.
- Applications and agents act only through explicit, scoped, revocable authority.
- Data bytes do not need artificial scarcity; scarcity can exist in rights, entitlements, capacity, duration, jurisdiction, usage quantity, derivation and participation.
- Usage does not become realized economic value without the required evidence.
- Historical signed semantics are superseded, not silently rewritten.
- An Entity identity survives replacement of a device, host, provider or BTG infrastructure.

---

## Engineering evidence

ENTITY publishes evidence separately from claims about the project.

| Evidence boundary | Current public position |
| --- | --- |
| Current protected release | **v3.4.0 — Global Passport & Continuous Provenance** |
| Protected release commit | `2db5bff64507b8d67642122a5ff2fc73dfef9152` |
| Full regression | **177/177 PASS** |
| v3.4 targeted Global Passport/package suite | **33/33 PASS** |
| v3.4 sealed Global Passport vectors | **24/24 PASS** — 12 valid / 12 invalid |
| v3.4 sealed kit SHA-256 | `5869a3fd0ed6cb9f65bf4b20c3bd64933cad82f4aef05c5809e2e05af921f230` |
| Global Passport schema SHA-256 | `4fbfed9be1b1484bc5d28b8101d1c908b2ccced13e4e99ec896c5b054892ebdd` |
| Six-language BTG-controlled result SHA-256 | `ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba` |
| Executable domain packages | **6/6 published and verified** |
| Post-release recursive closure | **PASS** — 1,040 frozen constituents / 1,041 ENTITY records |
| Unrelated third-party implementation | **OPEN / PENDING** |
| Independent external security review | **PENDING** |
| Deployment-specific legal/regulatory determination | **Outside ENTITY protocol claims** |
| Demonstrated external market liquidity | **PENDING** |

BTG-controlled language implementations are valuable reproducibility evidence, but they are **not described as independent third-party validation**.

See [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md) for the evidence hierarchy and claim boundaries.

---

## Independent implementers wanted

The most important remaining technical credibility milestone is external:

> **Can an unrelated engineer or organization independently reproduce ENTITY semantics from the public materials without using BTG implementation code?**

ENTITY already has controlled cross-language baselines. The external challenge is intentionally different: architecture, libraries, code structure and implementation decisions belong to the independent implementer.

You do **not** need to commit to a full implementation to contribute. Useful starting points include:

- verify a sealed kit and report ambiguities;
- review one schema or canonicalization rule;
- test an invalid/tampered vector;
- review the v3.3 truth-state model;
- challenge an external-anchor threat boundary;
- benchmark evidence verification;
- improve documentation or error reporting;
- build a small candidate CLI before attempting full interoperability.

### Pick a live contributor task

If you want to evaluate the project without taking on a full implementation, these are open now:

- [Verify the v3.3 sealed reality kit on Linux](https://github.com/blackmore-technology-group/ENTITY/issues/20) — bounded portability/reproduction task.
- [Verify the v3.3 sealed reality kit on macOS](https://github.com/blackmore-technology-group/ENTITY/issues/21) — bounded portability/reproduction task.
- [Add a minimal Evidence Object and claim-transition example](https://github.com/blackmore-technology-group/ENTITY/issues/22) — small documentation/code contribution.
- [Audit the Start Here path from a fresh clone](https://github.com/blackmore-technology-group/ENTITY/issues/26) — onboarding/usability review.
- [Build a narrow independent v3.3 reality-vector classifier](https://github.com/blackmore-technology-group/ENTITY/issues/27) — clean-room interoperability evidence without implementing all of ENTITY.

A reproducible failure, counterexample or specification ambiguity is a useful result.
For the full path, see [ENTITY Interoperability Challenge](docs/INTEROPERABILITY_CHALLENGE.md).

The separately sealed [ENTITY Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit) remains the authoritative clean-room target for Protocol 1.0 campaigns.

---

## Quick start

Python 3.11+ is recommended for the reference implementation.

```bash
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

Then read [START_HERE.md](START_HERE.md) for the shortest path through the architecture and evidence.

### Developer surfaces

A minimal developer facade is available at:

```text
sdk/simple_sdk/canonical_simple_entity_sdk.py
```

The Open SDK separates producer applications from asset controllers and requires explicit principal/device/application binding before canonical ingestion. Raw content bytes are not required when a governed workflow can operate on cryptographic commitments and bounded metadata.

---

## Repository map

```text
ENTITY/
├── src/
│   ├── 01_Core_Runtime/          # identity and canonical authority primitives
│   ├── 04_Entity_Registry/      # registry surfaces
│   ├── 08_Data_Vaults/          # governed storage/vault interfaces
│   ├── 22_Sovereign_Domain/     # provider-independent domain semantics
│   ├── 31_Profiles/             # v3 profile machinery
│   ├── 33_Economic_Participation/
│   ├── 36_Adoption_Layer/       # v3.2 rights passports/adoption surfaces
│   ├── 37_Verifiable_Reality/   # v3.3 evidence, attestation, anchors and causality
│   ├── 38_Global_Passports/     # v3.4 Global Passport, profiles and continuous provenance
│   └── 39_Implementation_Packages/ # v3.4 deployable domain package machinery
├── profiles/                    # versioned global/domain profile registry
├── protocol/
│   └── v3/                      # schemas, profiles and sealed v3 materials
├── sdk/                         # public developer interfaces
├── docs/
│   ├── architecture/
│   ├── qualification/
│   └── requirements/
├── tests/                       # regression and targeted qualification tests
├── examples/
└── tools/                       # verification/release tooling
```

The repository intentionally excludes production databases, private keys, machine-specific principal bindings, recovery secrets, operational backups, BTG production state, generated installers and private qualification environments.

---

## Security and sovereignty boundary

**Never commit operational sovereignty state to this repository.**

Do not commit private signing/recovery keys, live credentials, principal/device/application binding instances, `.entitybackup` files, runtime databases, production state directories, or unredacted user/business data.

See [SECURITY.md](SECURITY.md).

---

## Protocol and governance

Key controlling documents include:

- [SERS-ENTITY-003 v2.2](docs/requirements/SERS-ENTITY-003_v2.2_COMPLETE_MASTER_ENGINEERING_DESIGN.md)
- [SERS-ENTITY-DOMAIN-001 v1.0](docs/requirements/SERS-ENTITY-DOMAIN-001_v1.0.md)
- [ENTITY Protocol 1.0 Freeze](protocol/ENTITY_PROTOCOL_1_0_FREEZE.json)
- [Protocol Governance](protocol/ENTITY_PROTOCOL_GOVERNANCE_v1.md)
- [Sovereign Authority Doctrine](docs/architecture/ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md)

Protocol 1.0 remains frozen for its external conformance campaigns. Later ENTITY versions extend the system without rewriting the evidence preserved for that frozen target.

---

## Historical builds and releases

Release history, immutable tags and downloadable artifacts are maintained on the [GitHub Releases](https://github.com/blackmore-technology-group/ENTITY/releases) page.

The older Windows `1.0.0-rc2` executable remains available as a historical product build. It should not be confused with the current v3 protocol/reference-source release line.

---

## License

ENTITY is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).

A conforming published protocol version is not intended to require BTG hosting, BTG DNS, a BTG resolver, or a paid BTG service.

---

## Project

**Blackmore Technology Group Limited**

Primary repository: `blackmore-technology-group/ENTITY`
