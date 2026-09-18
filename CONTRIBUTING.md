# Contributing to ENTITY

Contributions are welcome where they preserve ENTITY's published authority and evidence boundaries.

## Before opening a pull request

1. Read `protocol/ENTITY_PROTOCOL_GOVERNANCE_v1.md`.
2. Read the relevant requirements under `docs/requirements/`.
3. Keep authoritative state separate from adapters, user interfaces, and provider infrastructure.
4. Add or update tests for behavior changes.
5. Run:

```bash
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

## Required design discipline

Changes must not silently turn:

- registration into ownership;
- provenance into truth;
- custody into authority;
- a provider into a sovereign controller;
- application events into rights/economic authority;
- usage into realized value without required evidence;
- aliases into cryptographic identity.

## Protocol changes

ENTITY Protocol 1.0 is frozen for external conformance. Security-critical or semantic changes to frozen behavior require an erratum or a new protocol version. Historical signed records must remain interpretable under the semantics that applied when they were created.

## Pull requests

A pull request should identify:

- requirement(s) addressed;
- affected authority boundary;
- implementation change;
- test/evidence added;
- compatibility impact;
- whether the change is protocol-semantic or implementation-only.

Do not include production state, credentials, private bindings, recovery keys, or real user/business data.
