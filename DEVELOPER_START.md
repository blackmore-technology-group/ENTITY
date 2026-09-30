# ENTITY Developer Quickstart

**Target:** ENTITY v3.4.3  
**Audience:** developers who want to build before reading the entire architecture  
**Goal:** produce one small working artifact in 5–30 minutes

ENTITY separates identity, authority, evidence, provenance, rights and economic state. You do not need to understand every layer to make a useful first contribution.

## Pick one path

### A. Verify the current runtime

```bash
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
git checkout v3.4.3
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

If a step fails, report the first reproducible failure. That is useful evidence.

### B. Build a tiny verifier

Pick an open `good first issue` and implement one bounded tool or example. Good first contributions should have an objective PASS condition and should not require protocol redesign.

Useful first artifacts include:

- a Python receipt verifier;
- a TypeScript evidence verifier;
- a JSON-to-ENTITY provenance adapter;
- a GitHub Action that verifies a published ENTITY receipt;
- a CLI lineage explainer;
- a compact DCO/data-rights example.

Open tasks: https://github.com/blackmore-technology-group/ENTITY/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

### C. Reproduce a real engineering case

BTG has externally merged contributions in projects such as Memnox and Vector. Use the public evidence to inspect how external source ownership, BTG contribution authorship, test evidence and ENTITY lineage remain distinct.

Real-world ledger: https://blackmore-technology-group.github.io/ENTITY-DOCS/evidence/real-world.html

## Contribution boundary

A first contribution should not require you to accept BTG's interpretation of a result. Reproducible negative results, portability failures and counterexamples are useful.

Do not treat:

- registration as ownership;
- provenance as objective truth;
- a signature as proof an external-world claim is true;
- repository ingestion as transfer of upstream ownership;
- protocol origin as automatic economic entitlement;
- usage as realized value without the required evidence.

For deeper design questions, use GitHub Discussions. For reproducible defects, use Issues. For concrete changes, use Pull Requests. Security-sensitive findings belong under `SECURITY.md`.

## After your first artifact

If your first path works, post what you built or reproduced in Discussions. If it fails, report the exact environment, command, expected result and actual result.

The goal is a developer loop:

```text
discover → run → build → verify → discuss → contribute
```
