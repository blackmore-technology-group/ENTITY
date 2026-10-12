# ENTITY implementation and qualification status — 2026-10-12

**Document class:** non-normative, current engineering status snapshot; not a protocol amendment, release manifest, certification, financial statement or independent attestation.

**Release of record:** [ENTITY v3.4.3](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.3), release commit `528b70aabd05b1e930b77e4933f157731e47274f`. **Immutable predecessor:** v3.4.2 (`6dfa3d6cc738d9369cf092d2782676bf4f2a46e4`). **BTDU component carried by the v3.4.3 tag:** 3.4.2 unchanged. **Current development branch:** `main` includes later additive BTDU storage, wallet, market and developer tooling. These changes do not retroactively modify the signed v3.4.3 tag or its frozen evidence.

## Implementation-status matrix

| Surface | What is implemented / evidenced | Boundary still open |
| --- | --- | --- |
| Identity, scope, signatures, rights, provenance and events | Python reference runtime, schemas, tests and signed release/origin record | Independent protocol and cryptographic assessment; delegated-key custody and multi-tenant operational qualification |
| v3.4.3 remediation | Issue #28 occurrence-identity/evidence replay and causal zero-edge corrections; **76/76 targeted** and **279/279 release source-suite** tests recorded | Those counts apply to the protected release, not an assertion that every later `main` change has been rerun under the same release test set |
| Universal transaction fabric and market | DCOs, Rights Passports, bounded instruments, listings, trading/settlement records, explicit transfer and wallet flows in the reference code and local deployment | External settlement is not bank payment; no independent liquidity, legal-title recognition, market surveillance certification or live exchange approval claimed |
| Wallet | Python/PySide6 desktop implementation, built Windows PyInstaller folder application; Oct 7 local wallet transfer and formula-export source exists | Desktop package qualification cannot be inferred from file existence; desktop/mobile full platform parity, distribution/signing and independent field acceptance remain open |
| BTDU reconstructive storage | `src/40_BTDU/storage_kernel.py` and `formula_kernel.py` on `main`; local migration receipt reports **4,933/4,933 formula bindings, zero legacy remaining**, signed journal sequence **78,382**, deep exact verification PASS | Local receipt is not an independently reproduced production benchmark. Irreducible entropy must remain represented. The object count in formula-node statistics may differ from total bindings because these are different scoped counters |
| BTDU measured storage | In one local qualification: 31,419,718 logical object bytes; 15,915,702 primary authoritative bytes (**49.34% reduction for that metric**); 25,004,726 operational formula/entropy bytes. The full observed local BTDU subtree occupied about **1.26 GB** including indexes and atomic state | Do not advertise universal compression, no-data storage, or the 49.34% as total-system disk savings. A separate controlled Level-3 vs vector-baseline comparison is *not* an apples-to-apples arbitrary-file compression claim |
| Formula graph composition | Measured qualification shows **4,811 LITERAL nodes and 2 CONCAT nodes** in the reported node-kind summary | Indicates opportunity to improve reusable semantic formulations; not evidence that arbitrary files reconstruct without stored irreducible information |
| ADAM and NIKI | Deterministic reference atom/bond state and governed analytical integration; AI is not authority | Hardware custody, physical multi-host, real-world-certified pilots, independent external audit and trusted assessor receipt remain unqualified in reviewed local ADAM evidence |
| Developer SDKs | Python open-entity, simple, global-passport, principal-binding and BTG-application SDK source; portable JSON schemas and reference examples | `sdk/apple_sdk`, `sdk/android_sdk`, `sdk/web_sdk` and `sdk/windows_sdk` currently include requirement documents; they are **not** independently qualified native authority SDKs |
| Independent node program | Public two-device test harness and receipt format, explicitly a test network | Independent end-to-end bidirectional interoperability + portable recovery qualification is pending |
| External security | Private vulnerability reporting, OpenSSF/dependency checks, documented external-review programme | External security audit is pending; internal CI, controlled clean rooms and self-tests are not a substitute |

## Distinguish these four targets

1. **ENTITY Protocol 1.0** is a separately frozen external clean-room conformance target. Its sealed kit controls its normative requirements. BTDU, ADAM, NIKI and the newer wallet are not implicit extra Protocol 1.0 requirements.
2. **ENTITY v3.4.3 tag** is the current supported versioned reference release. It contains a bounded remediation of the prior v3.4.2 release and inherits specified, unchanged-scope evidence only.
3. **`main` after v3.4.3** is an evolving source line with newer BTDU reconstructive storage and wallet/market work. Users must pin a specific commit and rerun the relevant qualification suite rather than calling these changes part of the old signed tag.
4. **BTG local installed state** is separate operational evidence. Read-only inspection of files and Oct 7 local test receipts is not a fresh exhaustive cold-restart qualification or independent audit.

## Integration contract for BTG apps and external teams

- Authenticate the human/organization Entity root explicitly; device metadata does not silently establish a person or transfer rights.
- Use scoped, revocable application capabilities. HuntAR, SearchAR, HikeAR, GuideProof, FraudStrike and other apps should use one versioned SDK event format and consented evidence API rather than direct SQLite editing.
- Submit source hashes and permission/rights references through a verified adapter; separate facts from inferred claims and signatures from objective truth.
- Validate Rights Passport action scope before issuance, use, trade or export. Never infer rights from ingestion or registration.
- Preserve offline queues, idempotency, conflict/replay detection and export/recovery verification; avoid permanent dependence on BTG-operated servers.
- For BTDU, verify exact reconstruction and hashes before deleting a source file. Keep encrypted independent recovery copies until real disaster recovery and total-cost benchmarks pass.
- Treat external payments and regulated or legal statuses as verifiable outside-world events, not automatic software-derived settlement.
- Keep production keys, personal data, private runtime paths and database snapshots out of public repositories.

## Next evidence gates, in priority order

1. **Release-document and compatibility CI**: assert every active page names v3.4.3 as the current tagged release, records post-tag features separately, and protects old frozen artifacts.
2. **Versioned integration SDK**: release Python, Swift, Kotlin, TypeScript and .NET clients with negative authorization vectors, offline/recovery examples and device-level tests.
3. **BTDU benchmark suite**: on independently chosen corpora, report exactness, logical bytes, all physical state/index/checkpoints, write/read latency, peak RAM, GPU/CPU, cold recovery and cost against Zstd/LZMA, filesystem CAS and comparable stores.
4. **Independent network/security qualification**: signed transport, bidirectional external nodes, HSM/secure-enclave custody, replay/revocation/rollover, threat modeling, red-team review and publishable external failures.
5. **App integration and operator pilots**: measure time to onboard, rights-consistent transfers, offline survival, rollback-safe updates and safety/regulated-context review in at least two unrelated external organizations.

## Source and claim discipline

This snapshot was prepared from [public ENTITY source](https://github.com/blackmore-technology-group/ENTITY), the protected [v3.4.3 release](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v3.4.3), [engineering evidence](../ENGINEERING_EVIDENCE.md), and read-only BTG local inspection of Oct 4–7 qualification receipts and current installed paths. Reproduction of results must identify the exact target, state and test method. **No production database, signed historical receipt, private key or immutable release content is changed by this documentation update.**
