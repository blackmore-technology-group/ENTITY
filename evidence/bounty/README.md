# Bounty Lineage Evidence

This directory stores evidence produced when a real external bounty contribution is recorded through an installed ENTITY system.

It is **not** a protocol extension and does not define new ENTITY semantics.

Each bounty run should be stored in its own immutable-style directory:

```text
evidence/bounty/
  bounty-YYYYMMDD-HHMMSS-owner-repo-issue-N/
    INDEX.json
    bounty_record.json
    evidence_hashes.json
    ...optional installed-ENTITY export/receipt/seal files...
```

## Evidence rules

- Never record a bounty as settled without payment evidence.
- Never record a contribution as accepted without upstream acceptance/merge evidence.
- Preserve the upstream repository, issue, commit/PR and licence/CLA context.
- Preserve hashes of the work evidence and installed ENTITY export.
- Do not place private keys, access tokens, passwords, API secrets or confidential third-party source in this public repository.
- Do not copy upstream source into this directory merely to prove authorship; prefer commit/diff identifiers and hashes unless publication is permitted and necessary.
- ENTITY evidence documents provenance/rights assertions; it does not override the external project's licence or contributor terms.

The companion PowerShell scripts under `tools/bounty/` are designed to prepare and push only this evidence while leaving ENTITY protocol, schema and implementation paths untouched.
