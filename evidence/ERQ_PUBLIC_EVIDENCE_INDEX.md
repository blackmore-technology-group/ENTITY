# ENTITY External Repository Qualification (ERQ) — Public Evidence Index

Status date: 2026-09-28

This index records the public evidence boundary for the ENTITY External Repository Qualification campaign. It does not replace sealed receipts, raw workstation evidence, Git objects, or the authoritative campaign tracker in issue #78.

## Claim boundary

```text
UPSTREAM OWNERSHIP
        !=
BTG FORK CUSTODY
        !=
BTG ENTITY METADATA OWNERSHIP
        !=
ENTITY PROTOCOL ORIGIN
        !=
AUTOMATIC ECONOMIC RIGHTS
```

Ingestion, mirroring, registration, verification and custody do not transfer upstream ownership or create automatic economic entitlement.

## Reference repository — claw-code

- Upstream: `ultraworkers/claw-code`
- BTG fork: `blackmore-technology-group/claw-code`
- Upstream commit: `08106b0c3771ef5b4a5aa176acccd460e88b7325`
- Upstream tree: `d382e2a34200de59849132f78c1ee0123ffa8122`
- MIT license blob: `28e6960dd9a2be209c308b49bc9a8973dbf4d60d`
- Tracked paths: `395`
- Unique Git objects: `375`
- Git object manifest SHA-256: `2417c8bd4a39f369bd8ef36baa7184061c5a0e04374f2bb37aa485179c6f39ff`
- Source anchor SHA-256: `d404dfed8922a3190a1d980493ed33ea96557b0018e68ad356ab1cd3313c6cd1`
- BTG publication commit: `cfcf7e968a5faf506fb6a59bf21d0e96d40b9601`
- BTG publication tree: `8e0488e3da3fb0f42b1092a8c541e984a813c877`

The BTG publication commit is one signed commit above the upstream anchor and adds only nine `.entity/` files. No upstream source path is modified by that publication commit.

## Published `.entity/` evidence

The BTG fork currently publishes:

- `.entity/ENTITY_PROVENANCE.md`
- `.entity/ERQ1_BTDU_INGEST_PUBLIC.json`
- `.entity/ERQ1_BTG_CONTRIBUTION.json`
- `.entity/ERQ1_GOVERNED_OBJECT_GRAPH.json`
- `.entity/ERQ1_GOVERNED_REPOSITORY.json`
- `.entity/ERQ1_PROVENANCE_GRAPH.json`
- `.entity/ERQ1_REPOSITORY_BTDU_OBJECT.json`
- `.entity/ERQ1_RIGHTS_MANIFEST.json`
- `.entity/PUBLICATION_MANIFEST.json`

Key published ENTITY / BTDU anchors:

- BTDU manifest ID: `btdu-repo:1621b80b8100093c68d269dab2450e647aabb6cd5bd341cc7b6ef26a69620089`
- BTDU aggregate SHA-256: `056bb283803aade8aa0c0311660d53dd67469cf38864072a6709d3ffd2d3cf70`
- BTDU atomic root: `68214f419cf5cbe44eabb75bb850e9cb2d01bab8954600ad9da4f7f4fd306fff`
- Governed object graph SHA-256: `599baa14fcdf0961d072d97153ec347d5655a2386f3125e5f7c831027090cf27`
- Provenance graph SHA-256: `9ad041653e1225b09414a09b779f894ed259d3ee26beedc985477499296315e2`
- Rights manifest SHA-256: `e5c09ce61741e181a5ff9ce351536101184a94af39b117d8e5dff838e853701e`
- BTG contribution SHA-256: `aaa91176db857e0ae4546746f4468850b96064d62b7d7faf90d86b81e2579534`

## Qualification receipts

| Qualification | Status | Final receipt SHA-256 | Public raw receipt state |
| --- | --- | --- | --- |
| ERQ-1 destructive external-repository survival | PASS | `E711F1A20FCD9DB20D010179DBD392E30D2DF3854A4E504303F6E7C6172A34B0` | Hash and qualification record are public in issue #78; raw receipt file is not represented here as published bytes. |
| ERQ-2 cross-platform recovery / verification | PASS | `65CC9B5E7BFDBCE1AB439C39176FD60CA113FD398E9032FE4954B09170D733BC` | Hash and qualification record are public in issue #78; raw receipt file is not represented here as published bytes. |
| ERQ-3 multi-repository identity / dedup / provenance separation | PASS | `527A90666F4FBE19431FF90F7B2CF7256EF71333F158B6B6811F2D598CB33666` | Hash and qualification record are public in issue #78; raw receipt file is not represented here as published bytes. |
| ERQ-4 genuine upstream advance / temporal lineage | WAITING | n/a | Upstream `ultraworkers/claw-code/main` remains at the pinned baseline. No synthetic advance is permitted. |
| ERQ-5 real BTG fork divergence | PASS | `4D6091EC88D56EDAD160A5E143FAD2A78C7D448038D26460172670A366754EA0` | Hash and qualification record are public in issue #78; raw receipt file is not represented here as published bytes. |
| ERQ-6 local / provider-neutral migration | PASS | `0DA65B8D20C298FEDBAC74B8862BEE53D009BE3DDF79CA6E2F647525F14B2299` | Hash and qualification record are public in issue #78; raw receipt file is not represented here as published bytes. |
| ERQ-6 genuinely different external Git provider | PENDING | n/a | Not proven. Prior Bitbucket attempt was blocked by external workspace/account restrictions. |

A receipt hash is not a substitute for publishing the original receipt bytes. Until the original sealed receipt file is intentionally published, this index describes it as hash-addressed public evidence rather than a publicly downloadable receipt.

## ERQ-3 deduplication result

The current recorded BTG-controlled result is:

```text
UNIQUE_CONTENT_SHA256=375
PAIRWISE_EXACT_COMPOUND_REUSE=395/395
SECOND_INGEST_NEW_ATOMIC_COMPOUNDS=0
UNIQUE_OCCURRENCE_OBJECT_REFS=790
```

This supports the bounded result that identical canonical content reused content/exact-compound identity while repository occurrence, provenance, custody and rights relationships remained distinct. It is BTG-controlled evidence, not unrelated independent validation.

## Next qualification targets

1. **External-provider ERQ-6** — recover from a genuinely different external Git provider with GitHub and local migration state excluded from the recovery path.
2. **TensorFlow** — large, active, multi-language, Apache-2.0 ecosystem with third-party notices and a materially larger contributor/dependency/provenance surface.
3. Later stress targets may include Kubernetes, Linux, VS Code, React, and repositories with their own provenance/attestation systems.

For new ERQ work, the supported runtime is ENTITY v3.4.3. The BTDU component remains 3.4.2 unchanged. Historical anchors and receipts are not rewritten when the supported runtime advances.

Authoritative campaign tracker: https://github.com/blackmore-technology-group/ENTITY/issues/78
