# ENTITY Full Engineering Corpus Ingest — 2026-09-24

**Status: PASS**

ENTITY ingested every substantive file in the protected v3.3.0 release tree and the six BTG-controlled v3.3 clean-room repositories: Rust, TypeScript, C#, Go, Swift and Java.

## Coverage

- 742 logical source/repository files
- 3,479,081 source bytes
- 466 unique SHA-256 content blobs after deduplication
- 2,530,319 bytes stored in the content-addressed vault after deduplication
- 750 ENTITY objects
- 750 signed Evidence Objects
- 750 machine-readable rights records
- 750 Rights Passports
- 750 explicit zero-value economic records
- 1,484 provenance edges

## Sovereign baseline

- root object: `obj3-c310f8de7443fdce3e5a3c3e40d1b577a4f20e0a`
- inventory SHA-256: `0d24dc5d8676d4e9fc4b8ff8151a464463dbbd6820007fe64c3f47ea954000a0`
- sovereign bundle semantic SHA-256: `00b6d157fee24f1c8aa800bebc3edc6a83c9f801fcd86180da2567e157482b92`
- full catalog file SHA-256: `94b428bda7e9581564c13a1984844bf6370b125968190e0d4663700a91aac44e`
- local sovereign bundle file SHA-256: `1423a2350a6e38a8e6334b06659bd4aa697b82d9ba10f68c17846687495ca417`

## Recovery verification

The production ingest state was encrypted with AES-256-GCM and restored into a separate verification state. The semantic database root before and after restore was identical:

`0596445056faecdf16b1ac9832b82e7308b23299ed15f297e383a9974ed0714b`

All 742 logical file records resolved to recovered vault content with matching SHA-256 hashes. All 750 Evidence Objects and 750 Rights Passports reverified after restore.

## Boundaries

No monetary value, royalty rate, historical contribution percentage, legal ownership conclusion or accounting fair value was invented during ingest. Every economic record is an explicit zero-value baseline until real evidence supports a different state.

Repository internals, dependency caches and build/test by-products were excluded: `.git`, `node_modules`, `.build`, `target`, `dist`, `bin`, `obj`, `__pycache__`, and `.pytest_cache`.

Private recovery material and raw vault bytes are not published in the repository. The public evidence contains only cryptographic commitments and the governed-result summary.
