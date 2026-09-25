# ENTITY Engineering Evidence

This document separates **what BTG has directly qualified** from **what still requires evidence outside BTG control**.

The purpose is not to turn test counts into marketing claims. It is to make the project's evidence inspectable and the remaining credibility boundaries explicit.

## Evidence hierarchy

From strongest release evidence downward, ENTITY treats these as distinct artifacts:

1. **Protected release commit** — merged through the protected `main` branch with required checks.
2. **Immutable release tag / GitHub Release** — points at the protected release commit.
3. **Cryptographic release manifest / snapshots** — binds the qualified release material.
4. **Regression and targeted qualification tests** — exercise documented behavior and invariants.
5. **Sealed conformance vectors / clean-room kits** — give reproducible external test targets.
6. **BTG-controlled cross-language implementations** — test reproducibility across languages/runtimes while remaining BTG-controlled.
7. **Unrelated external implementation** — separate authorship/control; required before calling the result independent external interoperability evidence.
8. **Independent security review / deployment / market evidence** — separate external milestones, not implied by repository tests.

No lower layer silently upgrades itself into a higher one.

---

## v3.2.0 — protected public release

**Release:** `v3.2.0`  
**Protected commit:** `512665096cef3771a3a8307d6dc955015ee0efbc`

Documented BTG-controlled qualification:

- complete regression: **128/128 PASS**
- targeted v3.2 adoption-layer tests: **12/12 PASS**
- sealed adoption vectors: **16/16 PASS**
  - 8 valid
  - 8 invalid
- release-overlay files: **17/17 verified**
- sealed kit SHA-256: `44e7a00f910c89aced3b3c1b5e9cba486809ca313e9bfb4b7bc9266095c10c14`
- common six-language result SHA-256: `1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18`
- v3.2 overlay snapshot SHA-256: `31662691cbe3a2d08ee5bd54c72b73cf56b49acc3dd9133dc45672eff4042d36`
- inherited v3.1 release snapshot: `0241c75e7f28481db0bfdf27a67a482c431032beedb2491b13dd5927dc344255`

BTG-controlled native v3.2 baselines exist in:

| Language | Qualified commit |
| --- | --- |
| Rust | `13787e20dd9b52cf34c7bcc6262863a2a62b2a4e` |
| TypeScript | `2766c68dec8914ce000123ea3281cf190dddadfc` |
| C# | `9f4d33c5b5c553644cd9c73a5c9cf09040083fe3` |
| Go | `ff8a733b8271ac655eac8a3302b4f6cd9acadacf` |
| Swift | `f55809a85cc763d2430b046b3a60f177b30de6d8` |
| Java | `ea58105b6c90a5b7bb5169cdf8701c880822bdae` |

All six produced the same documented v3.2 result hash. Because BTG controlled the campaign, this is **controlled cross-language reproducibility evidence**, not unrelated external validation.

---

## v3.3.0 — release qualification

v3.3 introduces the Verifiable Reality, Evidence and Economic Causality layer.

The release-candidate branch is based directly on the protected v3.2.0 commit. The initial v3.3 implementation adds:

- `src/37_Verifiable_Reality/evidence_objects.py`
- `src/37_Verifiable_Reality/attestation_authority.py`
- `src/37_Verifiable_Reality/reality_anchors.py`
- `src/37_Verifiable_Reality/causal_economic_graph.py`
- `src/37_Verifiable_Reality/reality_profile.py`
- `src/37_Verifiable_Reality/reality_conformance.py`
- `protocol/v3/ENTITY_VERIFIABLE_REALITY.schema.json`
- `protocol/v3/ENTITY_V3_3_REALITY_CLEANROOM_KIT.min.json`
- `tests/test_v3_verifiable_reality.py`

Release qualification records:

- complete regression: **144/144 PASS**;
- targeted v3.3 verifiable-reality tests: **16/16 PASS**;
- sealed verifiable-reality vectors: **20/20 PASS** (10 valid / 10 invalid);
- sealed kit SHA-256: `f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46`;
- schema SHA-256: `6e1c7e621e0aa84627e009febf8999503b7a61f92627b885ed10a19f2ef7d767`;
- required deterministic result SHA-256: `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`;
- v3.3 release overlay: **22 release-critical files**.

The exact overlay and composed release snapshot hashes are recorded in `ENTITY_V3_3_0_RELEASE_MANIFEST.json`; the manifest is the machine-readable authority for those values so this human evidence page does not create a self-referential hash dependency.

The qualification JSON/manifest deliberately records the state before publication as a BTG-internal qualified release candidate. Public release status is established separately by the protected `main` merge, `v3.3.0` tag and GitHub Release; that chronology should not be rewritten after publication.

## v3.3.0 — post-release six-language controlled conformance

After the protected `v3.3.0` release was published, BTG completed the same v3.3 sealed campaign in six native clean-room baselines: Rust, TypeScript, C#, Go, Swift and Java.

All six evaluated the exact release kit (`f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46`), passed 20/20 records, and converged on result SHA-256 `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`.

The authoritative post-release records are:

- `docs/qualification/ENTITY_V3_3_0_SIX_LANGUAGE_CONTROLLED_CONFORMANCE_2026-09-24.json`
- `docs/qualification/ENTITY_V3_3_0_SIX_LANGUAGE_CONTROLLED_CONFORMANCE_2026-09-24.md`

This evidence does not move or rewrite the `v3.3.0` tag, protected release commit, release manifest or release snapshot. It is controlled cross-language reproducibility evidence, not unrelated third-party interoperability.

## ENTITY governs ENTITY — recursive sovereign provenance and economic lineage

BTG subsequently ran the released ENTITY v3.3.0 architecture against ENTITY's own development lineage. The campaign registered the v1.0 RC lineage, v2.0.0-alpha1, v3.0.0, v3.0.1, v3.1.0, v3.2.0 and v3.3.0 as ENTITY-governed digital objects, then connected the six final BTG-controlled clean-room baselines and their conformance evidence.

Qualification results:

- **9** release-stage objects registered;
- **6** clean-room result objects registered;
- **26** signed Evidence Objects;
- **9** Rights Passports;
- **42** provenance edges;
- legacy/v1 clean-room campaign retained as **PASS**;
- v3.1 result retained as `879c8e1eba2549a9a1962605760b715b0fd47d3ea640fb9c6f29be5c63cfb8c5`;
- v3.2 result retained as `1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18`;
- v3.3 result retained as `82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d`;
- backward provenance from v3.3.0 reaches the v1.0 RC lineage;
- forward provenance from v1 reaches v3.3.0, all six v3.3 clean-room results and convergence evidence;
- state semantic root before destructive recovery: `b3e4a87fc5e3790fb2fe54ee780d2fa66734b86091d2b2fba53b5cd6fb5c0f48`;
- state semantic root after destructive recovery: `b3e4a87fc5e3790fb2fe54ee780d2fa66734b86091d2b2fba53b5cd6fb5c0f48`;
- sovereign bundle semantic root: `aa81b0d1d84d70ab414183558d3ac2ce0b8204697c2fcb6914b7b91d3e3c78a6`;
- causal/economic graph root: `0de207802b2a0b3526be8269c80917c76570e135c27befa5261d5c14edb3d132`;
- all Evidence Objects and Rights Passports reverified after recovery.

The campaign deliberately records zero monetary value and zero historical contribution weight where no evidence supports a value or percentage. It therefore proves provenance/economic-lineage readiness without manufacturing royalties, market value, accounting fair value or ownership claims.

Authoritative campaign records:

- `docs/qualification/ENTITY_RECURSIVE_SOVEREIGN_PROVENANCE_QUALIFICATION_2026-09-24.json`
- `docs/qualification/ENTITY_RECURSIVE_SOVEREIGN_PROVENANCE_QUALIFICATION_2026-09-24.md`

The full local qualification harness is retained on the qualification host; its SHA-256 is `8c9efbc93dbd6e313f65011c877c34ad618578c448ce698a43848ee9ef110729`. The synthetic sovereign bundle is not committed to the public repository; its semantic root is recorded above.

---

## v3.4.0 post-publication recursive closure

A post-release closure campaign was completed against the immutable `v3.4.0` tag at `2db5bff64507b8d67642122a5ff2fc73dfef9152` plus the captured heads of the six v3.4 clean-room repositories, `ENTITY-GITHUB-APP`, and six published domain repositories. The frozen capture contains 984 exact Git blobs, 45 GitHub API evidence records and 11 release-evidence artifacts: 1,040 constituents / 5,136,474 bytes.

- frozen constituent root: `4feb51a4bd0d958b7beb3eddbe9fd78678b7c31c2a4fe3d6cf7d9f4d87aa6e06`;
- ENTITY-ingested constituent root: `4feb51a4bd0d958b7beb3eddbe9fd78678b7c31c2a4fe3d6cf7d9f4d87aa6e06`;
- 1,041 ENTITY objects, Evidence Objects, rights records, Rights Passports, Global Passports and zero-value records;
- 1,040 zero-weight closure-membership provenance edges;
- exact state tree before/after destructive recovery: `6e054beaa96c089b3958973c834b3ddb2dda2466961c7ac67a748c7813c22925`;
- canonical SQLite semantic root before/after: `9c8ed4e767adf37abad6f0a2492e8a8007126fc1264218d0d184a4f6e7fa4231`;
- content-vault root before/after: `6ffc454b88c06f9da72db5854c3018a8fc5e0f3a334d829eafafeb0f9dbd4280`;
- sovereign export tree: `ce155ac3755d37292b69dd97aa24a4e9635e23950de016529640555f23b79149`;
- all 1,041 registered objects reverified after AES-256-GCM backup, destructive state deletion and recovery.

The closure target is finite and immutable: the `v3.4.0` release plus the captured external repository heads. The later commit that publishes the closure evidence is not defined as a constituent of that already-frozen target, because requiring a record to ingest the event that publishes itself would create non-terminating self-reference. This remains BTG-controlled evidence and does not establish independent third-party validation, objective truth, legal/regulatory approval, market adoption or accounting fair value.

Authoritative records:

- `docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_2026-09-24.json`
- `docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_2026-09-24.md`
- `docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_CATALOG_2026-09-24.json`
- `tools/verify_v3_4_post_release_closure.py`

---

## What the tests are intended to prove

Tests can support claims such as:

- signatures and commitments fail on tampering;
- scoped authority is required for protected transitions;
- an external anchor does not automatically become sovereign authority;
- claim-state escalation requires governed evidence/transition semantics;
- disputes and supersession preserve history;
- causal-economic edges require evidence and satisfy graph constraints;
- inherited v3.2 rights and market semantics remain compatible;
- ENTITY can register, traverse, export, destroy, recover and reverify its own synthetic development-provenance state.

Tests do **not** by themselves prove:

- that an external-world statement is objectively true;
- legal title or regulatory status;
- the absence of every security defect;
- independent implementation reproducibility;
- market demand or liquidity;
- deployment approval in a particular jurisdiction.

---

## External milestones still open

The following should remain visibly separate from BTG-controlled release qualification:

1. **Unrelated clean-room implementation** from the public specification/kit.
2. **Bidirectional live interoperability** between BTG and independently authored implementations.
3. **Sovereign export/recovery survival** with the independent implementation reaching the same authoritative result.
4. **Independent security/cryptographic review.**
5. **Deployment-specific legal/regulatory analysis or recognition.**
6. **Real external issuer/buyer activity and repeated market transactions.**

The project should update these statuses only when corresponding evidence exists.

---

## Reporting an evidence problem

If a hash, manifest, test count, release claim or qualification statement cannot be reproduced, open an issue with:

- the exact release/tag/commit;
- the command or artifact checked;
- expected result;
- actual result;
- environment details where relevant.

A reproducible contradiction should be treated as an engineering issue, not as hostile feedback.
