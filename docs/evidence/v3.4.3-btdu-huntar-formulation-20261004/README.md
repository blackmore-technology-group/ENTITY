# HUNTAR BTDU reconstructive formulation qualification — 2026-10-04

The defined HUNTAR script/config/validation corpus contained **762 files / 10,103,319 bytes** and was sealed by tree-manifest SHA-256 `e2d6100f157226a74082b76139a58d89a60657e2bf876094a53e81f5f6416b47`.

BTDU formulated the corpus against the already-qualified shared English, programming-language and mathematics basis. The optimized recipe is **1,021,315 bytes** with SHA-256 `d9eeb282e1d83febd27c24a28c3aa3655ca9ee95b4138ec87013d99e1bd060ef`.

That reduces per-asset retained storage from **10,103,319 bytes to 1,021,315 bytes**, a saving of **9,082,004 bytes (89.8913%)**. The retained representation is **10.1087%** of the original raw source corpus.

Before the final reconstruction, the temporary source staging tree, the older recipe and the ZIP control were absent. A fresh decoder reconstructed **762/762 files and 10,103,319/10,103,319 bytes** from the optimized recipe plus the pre-existing BTDU basis. The reconstructed tree root exactly matched the original sealed tree root, and **491/491 reconstructed Python files compiled syntactically**.

The formulation referenced 2,288,388 original bytes through the shared BTDU basis, represented 6,715,517 bytes through reusable local formulation tokens, and carried 1,099,414 bytes as residual literal information before physical recipe compression.

## Control comparison

- ZIP/Deflate-9: 1,947,036 bytes (80.7287% reduction)
- Whole-corpus Zlib-9: 1,550,004 bytes (84.6585% reduction)
- Whole-corpus raw LZMA-9: 898,768 bytes (91.1042% reduction)
- BTDU shared-basis formulation + LZMA physical encoding: 1,021,315 bytes (89.8913% reduction)

The BTDU formulation therefore beats ZIP and whole-stream Zlib for this corpus, but **does not beat raw whole-stream LZMA** on byte count. The significance of this result is exact reconstruction from a governed shared semantic basis plus a compact asset-specific recipe, not a claim of universal compression superiority.

## Claim boundary

This proves that the defined HUNTAR software corpus can use a BTDU recipe as its primary reconstructive representation instead of persisting the conventional script files byte-for-byte. It does **not** prove equivalent savings for model weights, imagery, DEMs, videos, encrypted data, compressed archives or arbitrary high-entropy assets. Unique information has not disappeared; it is represented by the pre-existing shared BTDU basis, the local formulation dictionary and residual literal information.

The targeted BTDU regression gate after the optimized codec change completed **16 passed, 11 skipped, 0 failed**.


## Primary-storage production promotion — 2026-10-07

The migrated BTDU state completed at **4,933/4,933 formula bindings with 0 legacy objects remaining**. Post-migration closeout preserved the atomic root, sequence and formula root through compaction and a cold restart, with protected-table equality against the canonical post-migration baseline.

The qualified source was then installed into the v3.4 production runtime after a rollback snapshot was created. All five critical production source files matched the qualified candidate byte-for-byte. SQLite `quick_check` returned `ok` for the BTDU, formula and storage indexes in both the qualification state and the installed production state, with clean WAL checkpoints.

A true production cold open completed **PASS** from the installed source and installed state. It recovered atomic root `f4edfd57142e7d345b487db34fd39bd46023ff1e1112f53e3c2f86d6f148ff4b`, sequence/checkpoint **78382**, formula root `2d361acbfbc256e826bfbc84a0882b7c04949e788c8822809150d233751db07d`, and verified **4,933 objects / 4,933 formula bindings / 0 legacy**.

The final pre-clone regression recorded **23 passed, 0 failed**, and the bounded ADAM recovery regression recorded **3 passed, 0 failed**. This qualifies the reconstructive/formula BTDU storage model as the installed primary-storage path for this ENTITY v3.4.3 build. ADAM v1.0 external certification/promotion gates remain a separate program and are not claimed by this BTDU deployment result.
