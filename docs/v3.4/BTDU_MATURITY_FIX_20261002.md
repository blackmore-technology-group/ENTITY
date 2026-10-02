# BTDU v3.4.3 Maturity Fix — 2026-10-02

This follow-up qualifies the corrected in-place ENTITY v3.4.3 BTDU build:

`v3.4.3+btdu-orientation-math-code-english.bridge-concurrency.20261002`

The public ENTITY display version remains **3.4.3** and the BTDU schema remains **3.4.2**.

## What changed

The maturity campaign after PR #120 found two real gaps: no explicit English → mathematics → code semantic bridge, and one failed transaction in an 8-writer / 120-lineage-chain raw BTDU stress test.

The corrected build adds:

- a governed, rebuildable English ↔ mathematics ↔ code semantic bridge index;
- a signed ENTITY `BTDU_WRITE` authorization receipt for bridge migration;
- in-process BTDU mutation serialization with a re-entrant write lock;
- SQLite WAL mode, `busy_timeout=30000`, and a 30-second connection timeout;
- an authority-neutral canonical replication root for proving deterministic BTDU payload convergence while preserving distinct signed ADAM authority roots.

The bridge is a derived index. It does not create rights, ownership or economic entitlement and does not rewrite the signed ADAM journal.

## Corrected qualification

The installed runtime passed **106/106** regression tests.

The maturity rerun then passed all direct gates:

- **Cross-domain reasoning:** PASS. Seven governed semantic concepts and 21 bridge relations are installed. The audit reports 20 examples because its query is capped at 20 rows. Example: `lemma:v:add → math-semantic:addition → code-token:+`.
- **Orientation/chirality:** PASS. 30,000 cases, 100% orientation-aware accuracy versus 50% direction-dropped baseline.
- **Controlled graph/RAG comparison:** PASS within the existing benchmark boundary.
- **Runtime:** PASS. 30,000/30,000 lookups returned results; median 0.0704 ms, p95 1.57234 ms; SQLite `quick_check = ok`.
- **Crash recovery:** PASS. The 846,057,472-byte copied DB returned `integrity_check = ok`; the committed transaction survived and the deliberately uncommitted transaction did not.
- **Raw concurrent lineage:** PASS. 8 writers completed all **120/120 chains**, producing exactly **360/360 nodes** and **240/240 edges**, with zero errors.
- **Replica convergence:** PASS. Both replicas produced the same semantic lineage root and the same canonical replication root `55303fa048d38908c4aef0ac39f69ba9feecf25ed780b1566b95234c0dd70c72`.

Independent signed ADAM atomic roots remain different by design because the authority envelope is local to each authority. That distinction is preserved rather than hidden.

## Signed-state and lineage preservation

The live production install retained signed ADAM sequence **75,121**, root:

`74f9c41c26f1260c01adc3db839f573cb664cbf80b84e2ba4788d7da08bbebfd`

and journal size **3,439,095,724 bytes**.

Canonical lineage guard hashes also remained unchanged.

## Repository boundary

This repository publishes source, migration tooling, tests and public qualification evidence only. It does **not** publish runtime SQLite databases, the multi-gigabyte ADAM/BTDU journal, production state, authority/private keys, credentials, bindings or backups.

See `docs/evidence/v3.4.3-btdu-maturity-fix-20261002/QUALIFICATION.json` for the machine-readable public qualification record.
