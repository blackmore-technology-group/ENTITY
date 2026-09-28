# Contributing to ENTITY

**Document class:** project contribution policy / non-normative to Protocol 1.0  
**Current supported runtime:** ENTITY v3.4.3  
**Documentation rules:** [docs/DOCUMENTATION_MODEL.md](docs/DOCUMENTATION_MODEL.md)

Contributions are welcome where they preserve ENTITY's published authority, evidence, sovereignty, rights and claim boundaries.

You do **not** need to understand the entire system before contributing. Small, reproducible improvements are useful: documentation corrections, portability reports, schema ambiguity reviews, failing vectors, examples, tests, benchmarks and narrowly scoped implementation work.

Start with [START_HERE.md](START_HERE.md). Before changing public documentation, read [Documentation Model](docs/DOCUMENTATION_MODEL.md). For Protocol 1.0 clean-room implementation work, also read [docs/INTEROPERABILITY_CHALLENGE.md](docs/INTEROPERABILITY_CHALLENGE.md) and use the separately sealed Protocol 1.0 Conformance Kit.

## Before opening a pull request

1. Identify the exact layer/version you are changing: Protocol 1.0, current runtime, BTDU component, integration/domain material or historical evidence.
2. Read the applicable public protocol/profile/release material for that layer.
3. Keep authoritative state separate from adapters, user interfaces and provider infrastructure.
4. Preserve historical interpretation of already-signed records and sealed campaigns.
5. Add or update tests for behavior changes.
6. Run the applicable repository tests.

For the current reference runtime:

```bash
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

If a proposed change is large or touches protocol/security semantics, opening an issue/discussion first is encouraged. That is coordination, not a request for permission to investigate the problem.

## Documentation discipline

Public documentation must not force a reader to infer which ENTITY layer is being described.

Where applicable, a standalone entry-point document should identify:

- its documentation class;
- the exact target/version;
- whether it is normative or non-normative;
- whether a cited older version is a frozen evidence target rather than the current runtime.

Define concepts positively before listing exclusions. Expand project-specific acronyms on first use.

In particular:

- **BTDU** means **Blackmore Technology Data Universe**;
- the current runtime is **ENTITY v3.4.3**;
- the BTDU component remains **3.4.2 unchanged**;
- ENTITY Protocol 1.0 remains a separate frozen external clean-room target;
- a frozen v3.4.2 language campaign remains v3.4.2 evidence and must not be rewritten to v3.4.3 merely for appearance;
- BTDU, ADAM, NIKI and later runtime examples must not be presented as Protocol 1.0 implementation requirements unless the normative Protocol 1.0 material explicitly says so.

## Required design discipline

Changes must not silently turn:

- registration into ownership;
- provenance into truth;
- a valid signature into objective external truth;
- custody, hosting or resolution into sovereign authority;
- an external evidence source into ENTITY authority;
- application events into protected rights/economic authority;
- usage into realized value without required evidence;
- aliases into cryptographic identity;
- a disputed historical claim into deleted history;
- repository ingestion into upstream ownership;
- ENTITY protocol origin into the provenance origin of unrelated assets;
- a fork, ingest or metadata record into automatic royalty/economic entitlement.

The canonical ENTITY origin and downstream asset provenance are separate relationships.

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

## Runtime evidence, passport and profile discipline

Later ENTITY runtime versions retain the distinction between:

- **cryptographic verification** — signature/commitment integrity;
- **protocol verification** — valid semantics/state transition for the specified target;
- **reality/evidence verification** — attributed evidence supporting an external-world claim.

Code or documentation that collapses these layers should be treated as a semantic defect. Profile composition must not create authority; external standards must be mapped rather than redefined; and industry packages must not create separate sovereignty silos.

## Protocol changes

ENTITY Protocol 1.0 is frozen for its external conformance campaign. Security-critical or semantic changes to frozen behavior require an erratum or a new protocol version through the applicable governance process.

Later ENTITY runtime versions may add profiles/layers/components, but historical signed records and conformance targets must remain interpretable under the semantics that applied to them.

Documentation clarification outside the sealed kit may explain Protocol 1.0 more clearly without changing the frozen target.

## Pull request description

Please identify, where applicable:

- document/runtime/protocol layer affected;
- exact version/target;
- requirement/profile addressed;
- authority, truth, provenance, rights or economic boundary affected;
- implementation/documentation change;
- test/evidence added;
- compatibility impact;
- whether the change is protocol-semantic or implementation/documentation-only;
- whether any public conformance vector/kit needs to change.

A concise PR with a clear reproduction/test path is preferable to a large narrative.

## Independent implementations

Independent clean-room implementations should live in repositories controlled by the independent implementer. BTG can clarify published specifications and vector intent, but should not author an implementation that is later presented as independent evidence.

BTG-controlled Rust, TypeScript, C#, Go, Swift and Java repositories are reproducibility baselines. External reproduction of one of those baselines is meaningful reproduction evidence, but it is not the same as an independently designed implementation.

If you are considering a full implementation, you are welcome to begin with a subset or a design question. Your architecture, libraries, repository layout and internal implementation choices remain yours.

## Security and private state

Do not include production state, credentials, private bindings, recovery keys, real user/business data or private signer material in issues, pull requests or test fixtures.

For security-sensitive reports, follow [SECURITY.md](SECURITY.md).

## Project conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Critical, reproducible feedback is welcome. Finding an ambiguity, stale version statement, incorrect assumption or failing edge case is a contribution to ENTITY.
