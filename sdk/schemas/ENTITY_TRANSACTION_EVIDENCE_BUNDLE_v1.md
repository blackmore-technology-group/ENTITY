# ENTITY Transaction Evidence Bundle v1
Status: Normative interoperability and qualification specification
Architecture baseline: SERS-ENTITY-003 v2.2, Sections 171–172
Schema identifier: `entity-transaction-evidence-bundle-v1`

## 1. Purpose
An ENTITY Transaction Evidence Bundle (TEB) SHALL package the minimum complete evidence needed for an implementation-independent verifier to reproduce a declared economic/corporate transaction conclusion without executing the originating BTG application.

A conforming bundle SHALL preserve the distinction between cryptographic validity, factual truth, legal rights, external authority, accounting state and market/economic interpretation.

## 2. Canonical transaction chain
The v1 qualified profile SHALL support this evidence chain:

`Entity identity → asset provenance → rights claim → signed licence → usage receipt → external settlement evidence → accounting/value state → Digital Commodity contribution → corporate authorization → share issuance → capitalization/shareholder state → capital accounting → disclosure snapshot → event-ledger checkpoint`.

Each link SHALL reference the same transaction-scoped identifiers used by adjacent links. A verifier SHALL fail closed on broken or contradictory cross-links.
## 3. Top-level bundle object
A bundle SHALL contain:

- `schema` = `entity-transaction-evidence-bundle-v1`;
- `transaction_id` — collision-resistant transaction evidence identifier;
- `issuer_entity_id` — Entity that signs the bundle header;
- `transaction_root_sha256` — deterministic SHA-256 commitment over the complete `evidence` object;
- `generated_at_ms` — export-generation time, excluded from the transaction root;
- `evidence` — canonical evidence object defined below;
- `signature` — ENTITY signature over the bundle header `{schema, transaction_id, issuer_entity_id, transaction_root_sha256}`;
- `evidence_boundary` — declarations preventing unsupported legal/factual interpretation.

The transaction root SHALL be `SHA-256(canonical_json(evidence))`, where canonical JSON uses UTF-8, lexicographically sorted object keys, no insignificant whitespace, JSON separators `,` and `:`, and deterministic string conversion for supported scalar values.

A change to any rooted evidence value SHALL change the transaction root and invalidate the original bundle signature.
## 4. Required evidence sections
The `evidence` object SHALL contain:

- `transaction_record`;
- `manifests`;
- `asset_provenance`;
- `rights`;
- `licence`;
- `usage_receipt`;
- `license_settlement`;
- `value_record`;
- `digital_commodity`;
- `corporate_authorization`;
- `capital`;
- `share_settlement`;
- `event_ledger`;
- `external_trust_anchors`.

Missing required sections SHALL make the bundle non-conformant for the v1 qualified profile.
## 5. Signature and trust rules
ENTITY-native signatures SHALL use an explicitly identified signature record and key version. Verification SHALL use the historical Entity manifest/key state needed to validate the signed payload.

External evidence SHALL identify authority ID, authority type, jurisdiction, evidence type, subject Entity, external authority reference, issue/effective time, nonce, payload and signature. External evidence is valid only when its signature verifies against a trust anchor included in or independently supplied to the verifier.

A valid external signature SHALL NOT by itself establish that the signer is legally authoritative in the real world. Trust-anchor acceptance remains an explicit verifier/deployment decision.

## 6. Evidence-boundary rules
A conforming verifier SHALL NOT infer:

- `valid signature = legal ownership`;
- `provenance = factual truth`;
- `possession/custody/storage = sovereign authority`;
- `processing access = consent or licensing authority`;
- `usage = equity`;
- `accounting entry = external cash movement`;
- `internal/modelled valuation = market price`.

Unsupported or unavailable facts SHALL remain assertion, inference or unknown state.
## 7. Cross-link invariants
A conforming verifier SHALL confirm at minimum:

- provenance asset ID/hash matches the registered asset;
- rights claim asset ID matches the asset and its claimant signature verifies;
- licensing authority references the qualifying rights basis used to create the licence;
- licence grantor/licensee identities match the transaction parties;
- usage receipt references the same licence and asset and its purpose/use are authorized by the licence;
- license settlement obligation references the licence and its payer/payee direction is correct;
- realized value references a verified external settlement where `realized_external=true`;
- Digital Commodity evidence references the same asset, usage receipt, licence and settlement;
- recognized Digital Commodity revenue/obligation does not exceed or contradict the referenced settlement evidence in the v1 qualified profile;
- corporate authorization applies to the exact share class and issuance request;
- externally attested post-capitalization state reconciles to share positions and outstanding shares;
- capital accounting references the same capital event and balances by currency;
- share-subscription settlement references the same capital event;
- disclosure capitalization/economic values are consistent with the rooted evidence;
- ledger/checkpoint continuity validates independently.
## 8. Sovereign recovery package
A sovereign v1 export SHALL contain:

- `TRANSACTION_BUNDLE.json`;
- `TRANSACTION_ROOT.sha256`;
- `RECOVERY_MANIFEST.json`;
- encrypted `STATE_BACKUP.enc` or another explicitly versioned encrypted state package.

`RECOVERY_MANIFEST.json` SHALL bind the transaction root, transaction-bundle SHA-256, encrypted-state SHA-256, encryption/cipher identifier and recovery-key fingerprint. The recovery decryption key SHALL NOT be stored inside the public export package.

The recovery manifest SHALL be signed by the Entity identified as issuer/controller for the declared package. A third party without the recovery key SHALL still be able to validate the manifest signature and hashes of the public bundle and encrypted state object.

## 9. Destructive reproducibility requirement
Qualification SHALL verify the bundle before live-state loss, verify the same bundle while the original ENTITY/BTG live state is unavailable, restore the sovereign state into a clean path/environment, regenerate the transaction evidence, and verify again.

The pre-loss and post-restore transaction roots SHALL be identical for the same rooted evidence. The independent verifier result SHALL be semantically identical; the reference implementation additionally requires an identical deterministic `result_sha256`.
## 10. Independent verifier requirements
A conforming independent verifier SHALL be able to run without importing the ENTITY production runtime or reading the original live state databases.

The verifier SHALL recompute the transaction root, validate required signatures and cross-links, validate accounting/capitalization invariants, reject tampering, and emit a machine-readable verification result with a deterministic result hash over its material conclusions.

The BTG reference verifier is a reference implementation only. Protocol conformance SHALL NOT require use of BTG-authored verifier code when another implementation follows this specification and produces equivalent conclusions.

## 11. Versioning
Breaking changes to rooted field meaning, canonicalization, mandatory evidence sections or verification semantics SHALL require a new bundle schema/version. Historical v1 bundles SHALL remain interpretable under v1 rules.

## 12. v1 qualification boundary
TEB v1 demonstrates evidence integrity, cryptographic attribution, cross-system consistency, externally attested payment/capital evidence and sovereign reproducibility for the declared test profile. It does not itself constitute legal adjudication, securities authorization, audit opinion, payment-provider operation, transfer-agent authority or market-price certification.
