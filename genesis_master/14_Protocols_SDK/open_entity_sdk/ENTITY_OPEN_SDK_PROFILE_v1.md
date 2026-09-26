# ENTITY Open Developer SDK Profile v1

Authority remains the existing ENTITY core and sovereign-domain protocols; this profile is additive and does not replace them.

## Address model
1. `display_alias` is human-readable and MAY collide (example: `huntar.entity`).
2. `entity_address` is the canonical `ent1-/ent2-` Entity root and is authoritative.
3. `entity_address_sha256` is a verification/display hash of the canonical address.
4. `alias_binding_sha256` commits to namespace + normalized alias + Entity root.
5. UI MAY show `collision_safe_display` (`alias~shortfingerprint`), but verification MUST use `entity_address`.
6. Ambiguous alias resolution MUST fail closed and require Entity/domain ID disambiguation.

## Developer integration
Applications MAY register SOFTWARE, DATA, MODEL, KNOWLEDGE and EVIDENCE commitments. Raw content need not enter the ledger. Each asset records the producing Entity address, content SHA-256, source/data-subject reference when applicable, classification, provenance and derivation lineage.

Registration MUST NOT infer ownership or economic value. Rights claims require an explicit claimant, right type, legal basis and evidence and remain self-asserted until independently verified under canonical ENTITY rules.

## Economy boundary
Open-SDK application events MUST NOT directly manufacture consent, verified rights, licences, settlement, payment, Digital Commodity state, corporate capital or sovereign authority. Those transitions remain controlled by the existing canonical ENTITY subsystems.

## Portability
No BTG server, DNS registrar, proprietary cloud, paid relay or specific storage provider is required by this SDK profile. A conforming implementation reproduces the JSON envelopes and addressing rules and validates against published conformance vectors.
