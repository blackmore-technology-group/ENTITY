# ENTITY

[![Release](https://img.shields.io/github/v/release/blackmore-technology-group/ENTITY?sort=semver)](https://github.com/blackmore-technology-group/ENTITY/releases/latest)
[![CI](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/ci.yml/badge.svg)](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/ci.yml)
[![Dependency review](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/dependency-review.yml/badge.svg)](https://github.com/blackmore-technology-group/ENTITY/actions/workflows/dependency-review.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/blackmore-technology-group/ENTITY/badge)](https://securityscorecards.dev/viewer/?uri=github.com/blackmore-technology-group/ENTITY)
[![License](https://img.shields.io/github/license/blackmore-technology-group/ENTITY)](LICENSE)

**Open infrastructure for sovereign digital authority, verifiable claims, data rights, continuous provenance and economic state that survives providers.**

> **Run it. Verify it. Break it. Implement it independently.**

ENTITY is Blackmore Technology Group's open-source protocol and reference implementation for persistent identity, delegated authority, provenance, evidence, rights, trusted state transitions, portable recovery and data-economic infrastructure.

[**ENTITY v3.4.2 Release**](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.2) · [**External Qualification**](https://github.com/blackmore-technology-group/ENTITY/issues/55) · [**v3.4.2 + BTDU overview**](https://blackmore-technology-group.github.io/ENTITY-DOCS/v342/) · [**Documentation**](https://blackmore-technology-group.github.io/ENTITY-DOCS/) · [**Conformance Kit**](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit) · [**Interoperability Challenge**](docs/INTEROPERABILITY_CHALLENGE.md)

---

## ENTITY v3.4.2 — Canonical BTDU Release

**v3.4.2 is the sole current supported canonical ENTITY release.** Earlier releases remain immutable historical provenance and are superseded for current deployment and conformance purposes.

v3.4.2 introduces the **Blackmore Technology Data Universe (BTDU)** while preserving ENTITY authority, rights, provenance and economic semantics; ADAM deterministic state; NIKI bounded reasoning; BSIE world-state boundaries; BECP governance boundaries; and the Genesis primitives:

```text
ENTITY → AUTHORITY → RIGHT → EVENT → VALUE
```

### Published qualification

| Evidence | Result |
| --- | --- |
| Full regression | **203/203 PASS** |
| Repository safety | **3/3 PASS** |
| GitHub dependency review | **PASS** |
| Public conformance smoke | **PASS** |
| Protected-state recovery | **PASS** |
| Exact restore | **true** |
| Restored sovereign signing | **true** |
| v3.4.1 origin continuity | **true** |

Protected release commit: `6dfa3d6cc738d9369cf092d2782676bf4f2a46e4`  
Release tree: `f90bf74e29899f82d0a4ee321604346241bba4de`  
Release-origin attestation SHA-256: `0ba4b0cc8c34688d98ef3c3425fbd70ff5b59d26183a18a15506bbad3adea0c1`

Canonical lineage:

```text
Shawn Blackmore → Blackmore Technology Group → ENTITY → v3.4.2
```

A third party may fork and operate the software independently. A derivative that removes or substitutes the canonical origin lineage does not qualify as canonical ENTITY under the v3.4.2 canonical-status rules.

Protocol origin remains separate from downstream ownership: canonical origin does not automatically transfer authority over user assets, does not make BTG owner of downstream data, and does not create an automatic protocol royalty.

---

## Blackmore Technology Data Universe

BTDU adds an atomic/bonded data architecture in which reusable atoms, bonds and compounds can be connected to ENTITY provenance, authority, rights and economic state.

```text
Atoms → Bonds → Compounds → Governed Objects → Provenance / Rights / Economic Lineage
```

The architecture separates computational/temporary relationships from relationships that need persistent evidentiary, rights or economic significance.

BTDU is **not** presented as generic raw-file compression. It is a different representation model for structured, semantic and relational information.

[Explore the v3.4.2 + BTDU documentation →](https://blackmore-technology-group.github.io/ENTITY-DOCS/v342/)

---

## Data-rights economic architecture

ENTITY models explicit rights around data rather than requiring artificial scarcity in the bytes themselves.

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

Originator participation may be expressed through explicit terms such as issuance participation, retained rights, secondary participation or derivative participation. ENTITY does not require a cryptocurrency, gas token or automatic BTG tax.

---

## Quick start

Python 3.11+ is recommended for the reference implementation.

```bash
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
git checkout v3.4.2
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

Then choose a narrow path:

- [Audit the Start Here path from a clean clone](https://github.com/blackmore-technology-group/ENTITY/issues/26)
- [Reproduce the Rust vector campaign on Linux](https://github.com/blackmore-technology-group/ENTITY/issues/48)
- [Try a domain package from a clean clone](https://github.com/blackmore-technology-group/ENTITY/issues/46)
- [Attempt an independent implementation](docs/INTEROPERABILITY_CHALLENGE.md)
- [Read the Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit)

A reproducible failure, ambiguity, counterexample or portability problem is useful evidence.

---

## External promotion qualification

ENTITY v3.4.2 deliberately separates BTG-controlled evidence from qualification that should come from unrelated participants. The umbrella entry point is [External Verification Challenge #55](https://github.com/blackmore-technology-group/ENTITY/issues/55).

Current public qualification calls:

- [#58 — Hardware-backed sovereign key custody](https://github.com/blackmore-technology-group/ENTITY/issues/58)
- [#59 — Physical multi-host interoperability and recovery](https://github.com/blackmore-technology-group/ENTITY/issues/59)
- [#60 — Certified-device pilot](https://github.com/blackmore-technology-group/ENTITY/issues/60)
- [#61 — Independent security audit](https://github.com/blackmore-technology-group/ENTITY/issues/61)
- [#62 — Independent assessor evidence review and qualification receipt](https://github.com/blackmore-technology-group/ENTITY/issues/62)

Each gate has its own evidence requirements and claim boundary. Passing one gate does not imply that another gate passed. Negative findings, reproducible failures and incomplete results remain useful evidence.

---

## Public cross-language baselines

BTG publishes controlled reproducibility baselines in:

- [Rust](https://github.com/blackmore-technology-group/ENTITY-RUST-CLEANROOM)
- [TypeScript](https://github.com/blackmore-technology-group/ENTITY-TYPESCRIPT-CLEANROOM)
- [C# / .NET](https://github.com/blackmore-technology-group/ENTITY-CSHARP-CLEANROOM)
- [Go](https://github.com/blackmore-technology-group/ENTITY-GO-CLEANROOM)
- [Swift](https://github.com/blackmore-technology-group/ENTITY-SWIFT-CLEANROOM)
- [Java](https://github.com/blackmore-technology-group/ENTITY-JAVA-CLEANROOM)

These repositories are **BTG-controlled reproducibility evidence, not independent third-party validation**. The stronger external milestone remains an implementation authored and controlled by an unrelated engineer or organization using public specifications and sealed conformance material rather than BTG implementation code.

---

## Domain entry points

The same ENTITY sovereignty model is packaged for:

- [Healthcare](https://github.com/blackmore-technology-group/ENTITY-HEALTHCARE)
- [Finance](https://github.com/blackmore-technology-group/ENTITY-FINANCE)
- [Manufacturing](https://github.com/blackmore-technology-group/ENTITY-MANUFACTURING)
- [AI](https://github.com/blackmore-technology-group/ENTITY-AI)
- [Robotics](https://github.com/blackmore-technology-group/ENTITY-ROBOTICS)
- [Defence / Public-Unclassified](https://github.com/blackmore-technology-group/ENTITY-DEFENCE)

The packages configure one ENTITY sovereignty model; they do not create separate sovereignty systems or redefine external standards.

---

## Core invariants

- Identity is not an account.
- Registration is not ownership.
- Provenance is not truth.
- A valid signature is not proof that an external-world assertion is correct.
- Possession, hosting, routing, custody and storage do not create sovereign authority.
- Applications and agents act only through explicit, scoped, revocable authority.
- Data bytes do not require artificial scarcity; scarcity can exist in rights, entitlements, capacity, duration, jurisdiction, usage quantity, derivation and participation.
- Usage does not become realized economic value without the required evidence.
- Historical signed semantics are superseded, not silently rewritten.
- An ENTITY identity survives replacement of a device, host, provider or BTG infrastructure.

---

## Post-release qualification still open

v3.4.2 does **not** claim completion of the following external ADAM promotion gates:

- `RUST_COMPILED_QUALIFIED`
- `REAL_WORLD_TRAINING`
- hardware-backed key custody
- physical multi-host qualification
- certified-device pilot
- 30-day wall-clock operation
- independent security audit
- independent assessor receipt

These remain post-release qualification work and do not rewrite the immutable v3.4.2 release artifact.

If post-release training or qualification changes model weights, executables, protocol behavior or other release-critical hashed material, the result is a subsequent candidate/release rather than a modified v3.4.2.

---

## Security boundary

**Never commit operational sovereignty state to this repository.**

Do not commit private signing/recovery keys, live credentials, principal/device/application binding instances, `.entitybackup` files, runtime databases, production state directories or unredacted user/business data.

See [SECURITY.md](SECURITY.md).

---

## Documentation and governance

- [Documentation portal](https://blackmore-technology-group.github.io/ENTITY-DOCS/)
- [v3.4.2 + BTDU](https://blackmore-technology-group.github.io/ENTITY-DOCS/v342/)
- [External Verification Challenge](https://github.com/blackmore-technology-group/ENTITY/issues/55)
- [Engineering evidence](docs/ENGINEERING_EVIDENCE.md)
- [Interoperability challenge](docs/INTEROPERABILITY_CHALLENGE.md)
- [Governance](GOVERNANCE.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Citation metadata](CITATION.cff)
- [CodeMeta](codemeta.json)
- [All releases](https://github.com/blackmore-technology-group/ENTITY/releases)

ENTITY is published under the Apache License 2.0.
