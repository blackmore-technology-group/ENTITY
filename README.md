# ENTITY

**Open infrastructure for sovereign digital authority, verifiable claims, data rights, and economic state that survives providers.**

ENTITY is Blackmore Technology Group's open-source protocol and reference implementation for persistent identity, delegated authority, provenance, evidence, rights, trusted state transitions, portable recovery, and data-economic infrastructure.

> **Infrastructure possession does not become sovereign authority.**

[Start here](START_HERE.md) · [Engineering evidence](docs/ENGINEERING_EVIDENCE.md) · [Roadmap](ROADMAP.md) · [Interoperability challenge](docs/INTEROPERABILITY_CHALLENGE.md) · [Governance](GOVERNANCE.md) · [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Security](SECURITY.md) · [Releases](https://github.com/blackmore-technology-group/ENTITY/releases)

---

## ENTITY v3.3 — Verifiable Reality, Evidence and Economic Causality

ENTITY v3.3 adds a formal bridge between claims about the external world and authoritative ENTITY state without pretending that a signature makes a claim objectively true.

```text
REALITY
  ↓
OBSERVATION
  ↓
CLAIM
  ↓
EVIDENCE
  ↓
ATTESTATION
  ↓
VERIFICATION
  ↓
AUTHORITATIVE ENTITY STATE
  ↓
RIGHT
  ↓
USAGE
  ↓
ECONOMIC CONSEQUENCE
```

The v3.3 layer adds:

- **Evidence Objects** — signed, typed evidence that can reference sensors, documents, registries, laboratory results, receipts, APIs and institutional records.
- **Typed claim states** — `OBSERVED`, `ASSERTED`, `INFERRED`, `ATTESTED`, `EXTERNALLY_VERIFIED`, `ADJUDICATED`, `DISPUTED`, `REVOKED`, `UNKNOWN`.
- **Attestation authority** — authority can be scoped to specific classes of facts and revoked without granting general sovereignty.
- **External reality anchors** — external systems may provide attributed evidence without silently becoming ENTITY authority.
- **Contestability and supersession** — challenges, decisions and superseding claims preserve the history they replace.
- **Causal economic attribution** — evidence can be carried through derivation and economic consequence rather than stopping at provenance.

The governing thesis is deliberately bounded:

> **ENTITY does not make reality indisputable. It makes claims about reality attributable, evidentiary, contestable, machine-verifiable and economically traceable.**

### Three kinds of verification

ENTITY keeps three questions separate:

1. **Cryptographic verification** — did this key sign this exact record?
2. **Protocol verification** — does this state transition obey ENTITY rules?
3. **Reality/evidence verification** — what evidence supports the claim about the external world, who supplied it, under what authority, and what is its current status?

A successful answer to one does not silently imply the others.

---

## The market architecture is preserved

v3.3 does not replace ENTITY's market model:

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
| Current release line | **v3.3.0 — Verifiable Reality, Evidence and Economic Causality** |
| Complete v3.3 regression | **144/144 PASS** |
| v3.2 targeted adoption tests | **12/12 PASS** |
| v3.2 sealed adoption vectors | **16/16 PASS** — 8 valid / 8 invalid |
| v3.2 BTG-controlled native convergence | **Rust · TypeScript · C# · Go · Swift · Java** |
| v3.2 common result SHA-256 | `1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18` |
| v3.3 targeted verifiable-reality suite | **16/16 PASS** |
| v3.3 sealed reality vectors | **20/20 PASS** — 10 valid / 10 invalid |
| v3.3 deterministic result SHA-256 | `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d` |
| Protected predecessor | **v3.2.0** — commit `512665096cef3771a3a8307d6dc955015ee0efbc` |
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
│   └── 37_Verifiable_Reality/   # v3.3 evidence, attestation, anchors and causality
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
