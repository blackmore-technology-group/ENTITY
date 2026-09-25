# ENTITY

[![Release](https://img.shields.io/github/v/release/blackmore-technology-group/ENTITY?sort=semver)](https://github.com/blackmore-technology-group/ENTITY/releases/latest)
[![CI](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/ci.yml/badge.svg)](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/ci.yml)
[![Dependency review](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/dependency-review.yml/badge.svg)](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/dependency-review.yml)
[![License](https://img.shields.io/github/license/blackmore-technology-group/ENTITY)](LICENSE)

**Open infrastructure for sovereign digital authority, verifiable claims, data rights, continuous provenance and economic state that survives providers.**

ENTITY is Blackmore Technology Group's open-source protocol and reference implementation for persistent identity, delegated authority, provenance, evidence, rights, trusted state transitions, portable recovery and data-economic infrastructure.

> **Infrastructure possession does not become sovereign authority.**

[Documentation portal](https://blackmore-technology-group.github.io/ENTITY-DOCS/) · [Start here](START_HERE.md) · [Developer portal](DEVELOPERS.md) · [v3.4.0 Global Passport](docs/v3.4/README.md) · [Domain packages](docs/v3.4/DOMAIN_PACKAGES.md) · [Engineering evidence](docs/ENGINEERING_EVIDENCE.md) · [Interoperability challenge](docs/INTEROPERABILITY_CHALLENGE.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Releases](https://github.com/blackmore-technology-group/ENTITY/releases)

---

## Choose your path

| You want to… | Start here |
| --- | --- |
| Understand ENTITY quickly | [START_HERE.md](START_HERE.md) |
| Run the reference implementation | [Quick start](#quick-start) |
| Build with ENTITY v3.4.0 | [v3.4 Global Passport](docs/v3.4/README.md) |
| Start from a healthcare, finance, manufacturing, AI, robotics or defence package | [Domain packages](docs/v3.4/DOMAIN_PACKAGES.md) |
| Inspect qualification evidence | [Engineering evidence](docs/ENGINEERING_EVIDENCE.md) |
| Contribute without implementing the whole protocol | [Live contributor tasks](#pick-a-live-contributor-task) |
| Attempt an unrelated clean-room implementation | [Interoperability challenge](docs/INTEROPERABILITY_CHALLENGE.md) |
| Review architecture/governance | [Architecture](docs/architecture/README.md) · [Governance](GOVERNANCE.md) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |

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

[Complete operator & developer documentation](https://blackmore-technology-group.github.io/ENTITY-DOCS/) · [In-repo v3.4 docs](docs/v3.4/README.md) · [Global Passport](docs/v3.4/GLOBAL_PASSPORT.md) · [Six domain packages](docs/v3.4/DOMAIN_PACKAGES.md)

### What can I build or evaluate?

ENTITY is designed for systems that need portable authority, rights, provenance or evidence to survive changes in provider, host, application or custody. Examples include governed data workflows, rights-bearing digital assets, evidence-backed claims, continuous provenance chains, interoperable identity/authority state and domain-specific Global Passport deployments.

ENTITY v3.4.0 also exposes six public domain packages:

- [Healthcare](https://github.com/blackmore-technology-group/ENTITY-HEALTHCARE) — HL7 FHIR and DICOM mapping context;
- [Finance](https://github.com/blackmore-technology-group/ENTITY-FINANCE) — ISO 20022, FIX and LEI mapping context;
- [Manufacturing](https://github.com/blackmore-technology-group/ENTITY-MANUFACTURING) — OPC UA and Asset Administration Shell mapping context;
- [AI](https://github.com/blackmore-technology-group/ENTITY-AI) — NIST AI RMF, SPDX 3 and CycloneDX mapping context;
- [Robotics](https://github.com/blackmore-technology-group/ENTITY-ROBOTICS) — ROS 2 and Open-RMF mapping context;
- [Defence/Public-Unclassified](https://github.com/blackmore-technology-group/ENTITY-DEFENCE) — public/unclassified originator, custody and provenance patterns.

Each package configures the **same Global Passport**. The packages do not create separate sovereignty systems and do not redefine external standards.

### Inherited v3.3 evidence layer

v3.4.0 retains v3.3's Verifiable Reality, Evidence and Economic Causality model. ENTITY keeps cryptographic verification, protocol verification and evidence supporting external-world claims distinct. A valid Global Passport therefore does not make an external assertion objectively true.

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

Then read [START_HERE.md](START_HERE.md).

For v3.4.0 inspect:

```text
src/38_Global_Passports/
src/39_Implementation_Packages/
profiles/registry.json
protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json
protocol/v3/ENTITY_V3_4_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json
sdk/global_passport_sdk/
tests/test_v3_global_passports.py
```

Useful v3.4 verification tools include:

```text
tools/verify_v3_4_global_passport_release.py
tools/verify_v3_4_implementation_packages.py
tools/verify_v3_4_0_release_manifest.py
```

### Developer surfaces

A minimal developer facade is available at:

```text
sdk/simple_sdk/canonical_simple_entity_sdk.py
```

The v3.4 Global Passport SDK is available under:

```text
sdk/global_passport_sdk/
```

The Open SDK separates producer applications from asset controllers and requires explicit principal/device/application binding before canonical ingestion. Raw content bytes are not required when a governed workflow can operate on cryptographic commitments and bounded metadata.

---

## Public cross-language baselines

BTG publishes controlled native implementations so developers can inspect cross-language reproducibility and CI evidence:

| Language | Repository | v3.4 command |
| --- | --- | --- |
| Rust | [ENTITY-RUST-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-RUST-CLEANROOM) | `cargo run --locked --release --bin passport_v34` |
| TypeScript | [ENTITY-TYPESCRIPT-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-TYPESCRIPT-CLEANROOM) | `node dist/passport_v34.js` after build |
| C# / .NET | [ENTITY-CSHARP-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-CSHARP-CLEANROOM) | `dotnet run --project passport-v34/PassportV34.csproj -c Release` |
| Go | [ENTITY-GO-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-GO-CLEANROOM) | `go run ./cmd/passport-v34` |
| Swift | [ENTITY-SWIFT-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-SWIFT-CLEANROOM) | `swift run -c release PassportV34` |
| Java | [ENTITY-JAVA-CLEANROOM](https://github.com/blackmore-technology-group/ENTITY-JAVA-CLEANROOM) | `mvn ... exec:java -Dexec.mainClass=org.btg.entity.cleanroom.PassportV34` |

These repositories are **BTG-controlled reproducibility evidence, not independent third-party validation**.

The stronger external milestone is an implementation authored and controlled by an unrelated engineer or organization using the public specifications and sealed material rather than BTG implementation code.

---

## Engineering evidence

ENTITY publishes engineering evidence separately from claims about the project.

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

See [Engineering Evidence](docs/ENGINEERING_EVIDENCE.md) for the evidence hierarchy and claim boundaries.

---

## Pick a live contributor task

You do **not** need to understand or implement all of ENTITY before contributing. A reproducible failure, counterexample, ambiguity, portability issue or onboarding problem is useful evidence.

Current bounded entry points:

- [Verify the v3.4 Global Passport kit on Linux](https://github.com/blackmore-technology-group/ENTITY/issues/20) — clean reproduction/portability task.
- [Verify the v3.4 Global Passport kit on macOS](https://github.com/blackmore-technology-group/ENTITY/issues/21) — clean reproduction/portability task.
- [Verify the v3.4 Global Passport kit on Windows](https://github.com/blackmore-technology-group/ENTITY/issues/45) — Windows reproduction/portability task.
- [Audit the v3.4 Start Here path from a fresh clone](https://github.com/blackmore-technology-group/ENTITY/issues/26) — onboarding/usability review.
- [Try one v3.4 domain package from a clean clone](https://github.com/blackmore-technology-group/ENTITY/issues/46) — bounded package-adoption test.
- [Build a narrow independent v3.4 Global Passport classifier](https://github.com/blackmore-technology-group/ENTITY/issues/27) — clean-room interoperability evidence without implementing all of ENTITY.

For the full external path, see [ENTITY Interoperability Challenge](docs/INTEROPERABILITY_CHALLENGE.md).

The separately sealed [ENTITY Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit) remains the authoritative clean-room target for Protocol 1.0 campaigns.

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

## The market architecture

ENTITY preserves the following data-rights/economic lifecycle:

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

## Repository map

```text
ENTITY/
├── src/
│   ├── 01_Core_Runtime/              # identity and canonical authority primitives
│   ├── 04_Entity_Registry/           # registry surfaces
│   ├── 08_Data_Vaults/               # governed storage/vault interfaces
│   ├── 22_Sovereign_Domain/          # provider-independent domain semantics
│   ├── 31_Profiles/                  # v3 profile machinery
│   ├── 33_Economic_Participation/
│   ├── 36_Adoption_Layer/            # v3.2 rights passports/adoption surfaces
│   ├── 37_Verifiable_Reality/        # v3.3 evidence, attestation, anchors and causality
│   ├── 38_Global_Passports/          # v3.4 Global Passport, profiles and provenance
│   └── 39_Implementation_Packages/   # v3.4 deployable domain package machinery
├── profiles/                         # versioned global/domain profile registry
├── protocol/v3/                      # schemas, profiles and sealed v3 materials
├── sdk/                              # public developer interfaces
├── docs/                             # architecture, qualification, requirements and guides
├── tests/                            # regression and targeted qualification tests
├── examples/
└── tools/                            # verification/release tooling
```

The repository intentionally excludes production databases, private keys, machine-specific principal bindings, recovery secrets, operational backups, BTG production state, generated installers and private qualification environments.

---

## Security and sovereignty boundary

**Never commit operational sovereignty state to this repository.**

Do not commit private signing/recovery keys, live credentials, principal/device/application binding instances, `.entitybackup` files, runtime databases, production state directories or unredacted user/business data.

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

## Historical builds and releases

Release history, immutable tags and downloadable artifacts are maintained on the [GitHub Releases](https://github.com/blackmore-technology-group/ENTITY/releases) page.

The older Windows `1.0.0-rc2` executable remains available as a historical product build. It should not be confused with the current v3 protocol/reference-source release line.

## License

ENTITY is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).

A conforming published protocol version is not intended to require BTG hosting, BTG DNS, a BTG resolver or a paid BTG service.

---

**Blackmore Technology Group Limited**  
Primary repository: `blackmore-technology-group/ENTITY`
