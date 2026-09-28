# ENTITY Documentation Model

**Status:** current non-normative documentation governance for the public ENTITY repository family  
**Current supported runtime:** ENTITY v3.4.3  
**BTDU component:** Blackmore Technology Data Universe (BTDU) v3.4.2, unchanged in ENTITY v3.4.3  
**Frozen clean-room protocol target:** ENTITY Protocol 1.0 / External Conformance Kit v1.0.2

This document explains how to read ENTITY documentation without confusing protocol requirements, runtime implementation details, component architecture, domain integrations or historical evidence.

It does **not** change a protocol, schema, vector, release manifest, signed record, sealed kit or historical qualification result.

## 1. Five documentation classes

Every public ENTITY document should be read as one of the following classes.

### A. Normative Protocol 1.0 / sealed conformance material

Purpose: define the frozen external clean-room target and the exact material against which an unrelated implementation can be evaluated.

Authoritative location: [`ENTITY-Protocol-1.0-Conformance-Kit`](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit).

Examples include the interoperability profile, canonicalization/cryptography rules, schemas, vectors, pass criteria and signed kit manifest.

**Rule:** later runtime or BTDU documentation must not silently add requirements to Protocol 1.0. BTDU, ADAM, NIKI, Global Passport runtime internals and current ENTITY application code are not required implementation dependencies for the Protocol 1.0 clean-room campaign unless the sealed kit itself says otherwise.

### B. Current ENTITY runtime

Purpose: describe the currently supported BTG reference/runtime release and its qualified behavior.

Current release: **ENTITY v3.4.3**.

ENTITY v3.4.3 is a bounded remediation release based on immutable v3.4.2. It fixes the two reproduced Issue #28 defects and carries forward only explicitly identified unchanged-scope v3.4.2 qualification.

**Rule:** a current-runtime document may describe implementation architecture or qualified behavior that is broader than Protocol 1.0. That does not retroactively change the frozen Protocol 1.0 target.

### C. BTDU component / runtime architecture

BTDU means **Blackmore Technology Data Universe**.

Current component version in ENTITY v3.4.3: **BTDU 3.4.2 unchanged**.

BTDU is a governed information substrate built around reusable atoms, bonds and compounds connected to ENTITY provenance, authority, rights and economic state. The public architecture contract describes:

- ENTITY — authority and rights;
- ADAM — deterministic state engine;
- NIKI — reasoning consumer;
- BTDU — governed universal information substrate.

**Rule:** BTDU architecture is not itself the Protocol 1.0 clean-room specification. References to BTDU operations or scopes are runtime/component examples unless a normative protocol source explicitly defines them.

### D. Domain, adapter and integration material

Purpose: configure or integrate ENTITY for a specific environment without creating a new sovereignty model.

Examples:

- Healthcare / Finance / Manufacturing / AI / Robotics / Defence packages;
- ENTITY GitHub App;
- external-standard mappings;
- deployment examples.

**Rule:** these materials map to or consume ENTITY semantics. They do not silently redefine ENTITY identity, authority, rights, evidence, economic state or external standards.

### E. Historical / frozen evidence

Purpose: preserve the exact record of what was released, tested or sealed at a particular point in time.

Examples include historical release notes, signed release manifests, v3.4.2 26-vector language campaigns, older domain-package payload bindings, receipts, hashes and frozen qualification artifacts.

**Rule:** historical evidence is not rewritten merely because the supported runtime advances. A document may therefore correctly contain an older version number when that number identifies the exact target that was tested.

## 2. Version map

| Layer | Current / authoritative status | Meaning |
| --- | --- | --- |
| ENTITY runtime | **v3.4.3** | Current supported reference/runtime release |
| BTDU | **3.4.2 unchanged** | Component version carried by v3.4.3 |
| ENTITY Protocol 1.0 | **Frozen external conformance target** | Independent clean-room protocol campaign |
| v3.4.2 language campaigns | **Frozen historical targets** | Exact 26-vector BTG-controlled reproducibility campaigns |
| v3.4.0 domain-package payloads | **Frozen package payloads** | Historical sealed package content; reader-facing compatibility may advance only when requalification supports it |
| Older releases | **Historical / superseded as applicable** | Preserve exact evidence; do not present as the current runtime |

The word **current** must always identify the layer it refers to. For example, “current Java campaign target” is ambiguous and should be written as “frozen v3.4.2 Java campaign target” when the repository is intentionally reproducing v3.4.2 evidence.

## 3. Define first, bound second

ENTITY documentation should define a term positively before explaining what it does not imply.

Preferred pattern:

1. **What it is** — object, state, relationship or operation;
2. **How it is established or verified**;
3. **What role it plays**;
4. **Boundary** — what separate claims do not follow automatically.

Example:

> **Protocol validity** means an input satisfies every applicable ENTITY protocol rule for the specified target, including the required structural, canonicalization, signature, authority/binding, revocation, lineage, version and semantic checks. Protocol validity does not by itself establish unrelated legal ownership or objective external-world truth.

Avoid leading with long lists of things a term is not before explaining the term itself.

## 4. Acronym rule

Project-specific acronyms are expanded on first use in every standalone entry-point document.

Important examples:

- **BTG** — Blackmore Technology Group Limited;
- **BTDU** — Blackmore Technology Data Universe;
- **DCO** — Digital Commodity Object;
- **RFQ** — Request for Quote;
- **ADAM** and **NIKI** — runtime/component names, not Protocol 1.0 conformance requirements unless a normative source explicitly says otherwise.

External-standard acronyms should be linked or expanded where doing so materially helps an implementer understand the mapping.

## 5. Sovereignty, provenance and economic claim boundaries

The following distinctions are architectural invariants and must remain visible in documentation:

```text
UPSTREAM OWNERSHIP
        ≠
BTG FORK CUSTODY
        ≠
BTG-CREATED ENTITY METADATA OWNERSHIP
        ≠
ENTITY PROTOCOL ORIGIN
        ≠
AUTOMATIC ECONOMIC RIGHTS
```

ENTITY can record and verify protocol facts about identity, provenance, custody, authorship, licences, rights metadata, usage evidence and economic state. Registration, ingestion, mirroring, verification or custody do not themselves transfer upstream ownership or create automatic economic entitlement.

The canonical ENTITY origin is a statement about ENTITY's own origin/stewardship lineage. It must not be presented as the provenance root of unrelated upstream assets.

Economic participation requires explicit terms. The existence of data, provenance, lineage, a fork, an ingest or an ENTITY record does not itself create a royalty, payment obligation, fair value or legal entitlement.

## 6. Evidence classes

Documentation must distinguish:

- **BTG-controlled qualification** — engineering evidence produced under BTG control;
- **external reproduction** — an unrelated party reproduces a published BTG-controlled target;
- **independent implementation** — separately authored implementation from permitted public material;
- **live interoperability evidence** — independently controlled systems exchange/verify the required protocol state;
- **independent security/research review** — separate external assessment with its own scope.

One class must not be relabelled as another.

## 7. Source-of-truth order

When human-facing prose and immutable evidence appear inconsistent, do not silently choose a newer-sounding statement. Identify the layer and target first.

For Protocol 1.0 clean-room work, use the sealed Protocol 1.0 conformance repository and its pinned release/tag.

For the current runtime, use the current ENTITY release, release manifest and protected main branch.

For BTDU architecture, use the current runtime's BTDU architecture contract and the explicitly stated component version.

For historical qualification, use the exact historical tag, kit, hash, receipt or signed manifest identified by that campaign.

## 8. Editing rules

Documentation-only clarification may improve wording, navigation and classification without changing normative meaning.

Do **not** edit historical evidence merely to make version labels look current. In particular, do not rewrite:

- sealed conformance vectors;
- signed kit manifests;
- release hashes or receipts;
- historical result hashes;
- exact historical package bindings;
- independent contributor evidence;
- the active 30-day wall-clock campaign record.

If a frozen artifact is difficult to understand, add or improve explanatory material outside the sealed artifact and clearly label that guidance non-normative.

## 9. Review checklist for a public document

Before merge, ask:

- Does the first screen say what layer/version this document describes?
- Are project-specific acronyms expanded on first use?
- Are concepts defined positively before exclusions?
- Could a Protocol 1.0 implementer mistakenly think a runtime/BTDU example is mandatory?
- Could an old campaign be mistaken for the current release?
- Could provenance/custody be mistaken for ownership?
- Could an evidence object be mistaken for objective truth?
- Could data ingestion be mistaken for an automatic economic right?
- Is BTG-controlled evidence clearly separated from unrelated external validation?
- Are historical hashes and sealed targets preserved exactly?

If any answer is unsafe or ambiguous, the document is not ready to publish.

## 10. Audit record

Cross-repository remediation is tracked in [ENTITY issue #91](https://github.com/blackmore-technology-group/ENTITY/issues/91). The audit was triggered by concrete external implementer feedback in Protocol 1.0 Conformance Kit issues #10 and #12.
