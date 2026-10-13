# Contribution Lineage Evidence

This directory stores public evidence produced when a real external contribution is recorded through an installed ENTITY system.

It is **not** a protocol extension and does not define new ENTITY semantics.

The historical directory name remains `evidence/bounty/` for compatibility, but records may represent funded, contingent/promised, or pro-bono contributions.

## Public evidence versus sealed local evidence

Installed ENTITY/BTDU receipts may legitimately contain machine-local operational paths. Those sealed receipt bytes remain authoritative in the local evidence archive and are identified by their SHA-256 and ENTITY/BTDU atomic-root lineage.

Do **not** publish a path-bearing sealed receipt directly into this repository.

When a sealed receipt contains workstation-local paths, publish a **portable public projection** instead. A public projection must:

- identify itself as a projection, not as the sealed receipt;
- record the exact sealed receipt SHA-256 and sealed receipt schema;
- preserve the relevant ENTITY/BTDU atomic root, predecessor receipt hash and external contribution identifiers;
- preserve the actual acceptance, review, CI, rights and economic state;
- omit machine-local paths, credentials, secrets and other non-portable operational fields;
- state that the sealed receipt remains unchanged and authoritative;
- never invent acceptance, ownership, payment, rights or settlement.

A public projection therefore proves what was publicly selected from the sealed evidence while keeping the original sealed bytes immutable and independently hash-addressable.

Current accepted public projections in this experiment include the Vector #26501 / PR #26504 and Memnox #46 / PR #86 cases. Both are PRO_BONO upstream-accepted contributions with realized cash preserved as `0 USD` and payment settlement preserved as false.

## Evidence rules

- Never record a contribution as settled without payment evidence.
- Never record a contribution as accepted without upstream acceptance/merge evidence.
- Preserve the upstream repository, issue, commit/PR and licence/CLA context.
- Preserve hashes of the work evidence and installed ENTITY export/receipt.
- Do not place private keys, access tokens, passwords, API secrets or confidential third-party source in this public repository.
- Do not publish absolute workstation paths such as drive-letter paths.
- Do not copy upstream source into this directory merely to prove authorship; prefer commit/diff identifiers and hashes unless publication is permitted and necessary.
- ENTITY evidence documents provenance/rights assertions; it does not override the external project's licence or contributor terms.

The companion scripts under `tools/bounty/` are evidence-capture/publication tooling only. They must leave ENTITY protocol, schema, implementation and canonical runtime paths untouched.
