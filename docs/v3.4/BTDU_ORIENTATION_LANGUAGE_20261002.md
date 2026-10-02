# BTDU Orientation, Mathematics and Language Extension — 2026-10-02

This document describes the qualified in-place ENTITY v3.4.3 BTDU extension identified by build revision `v3.4.3+btdu-orientation-math-code-english.20261002`.

The public ENTITY display version remains **v3.4.3** and the BTDU schema version remains **3.4.2**. Historical release manifests and the canonical protocol-origin lineage are not rewritten by this extension.

## What is included

The source change adds a semantic orientation layer to BTDU, plus read/query surfaces for the qualified mathematics, programming-language and English indexes. The orientation layer distinguishes `SYMMETRIC`, `INVERSE_PAIR`, `CONTEXT_COMMUTATIVE` and `ORDERED` relations. Ordered behavior remains the default unless a mathematical profile or explicit proof permits normalization.

The qualified data state contains 246,646 mathematical declarations across 18,942 modules; 36,733 programming-language nodes with 595,898 language relations; 107,519 English synsets and 136,219 English lemmas; and 37,490 orientation topologies referenced by 180,126 occurrences.

## Programming-language source coverage

The source-acquisition manifest records pinned or curated material for Python, Java, Rust, Cargo, TypeScript, C#, Go, Kotlin and Swift. English lexical material is based on Open English WordNet 2025. Upstream provenance, commit identifiers and license information are retained in `docs/evidence/v3.4.3-btdu-20261002/SOURCE_ACQUISITION.json`.

## Rights and provenance boundary

Orientation is a derived semantic index. A normalized topology does not create ownership, usage rights or an economic entitlement. Exact source records and their provenance remain distinct from orientation topology. The build also makes no universal compression claim.

## Qualification

The installed production copy was replayed and verified against its signed journal. The final signed state is sequence **75,121** with root `74f9c41c26f1260c01adc3db839f573cb664cbf80b84e2ba4788d7da08bbebfd`. SQLite `quick_check` returned `ok`, there were zero dangling orientation occurrences, and the installed targeted regression gate completed **102/102 PASS**.

## Repository boundary

This repository contains the implementation, tests and public qualification evidence. It intentionally does **not** contain the multi-gigabyte BTDU journal, SQLite runtime databases, production state, authority keys, bindings, credentials, backups or other machine-specific mutable state.

Relevant files:

- `src/40_BTDU/canonical_btdu.py`
- `src/40_BTDU/orientation_topology.py`
- `tests/test_v343_btdu_orientation_language.py`
- `BUILD_V3_4_3_LANGUAGE_20261002.json`
- `BTDU_ORIENTATION_LANGUAGE_EXTENSION_V1.json`
- `docs/evidence/v3.4.3-btdu-20261002/QUALIFICATION.json`
- `docs/evidence/v3.4.3-btdu-20261002/COMBINED_BTDU_RESULT.json`
- `docs/evidence/v3.4.3-btdu-20261002/MATH_ORIENTATION_INGEST_RESULT.json`
- `docs/evidence/v3.4.3-btdu-20261002/SOURCE_ACQUISITION.json`

The evidence files describe a controlled, qualified representation and indexing build. They should not be read as evidence that ENTITY universally compresses arbitrary data, replaces an LLM's learned parameters, or reduces inference compute without workload-specific testing.
