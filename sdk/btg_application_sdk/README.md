# BTG Application SDK v1

This is an additive integration profile for existing ENTITY capabilities. It does not replace or redefine SERS-ENTITY-003, identity, sovereign authority, rights, consent, licensing, settlement, accounting, capital, recovery or provider-replacement semantics.

## Purpose

BTG applications such as HUNTAR, SearchAR, HikeAR, NIKI, BSIE, BoundarysBest and future systems may become native ENTITY data/provenance producers through application-specific Entity identities such as `huntar.entity`.

The human-readable `.entity` alias is not the cryptographic authority. The canonical Entity ID and signed manifest remain authoritative.

## Boundary

The application SDK may register SOFTWARE, DATA, MODEL, KNOWLEDGE and EVIDENCE assets; preserve source/data-subject references; add provenance derivations; create knowledge-capital receipts; and append bounded non-authoritative application events.

The SDK does not expose direct mutation of ownership verification, consent, licences, settlements, payments, Digital Commodity state, capital state or governance authority. Those operations remain exclusively in their existing canonical ENTITY subsystems.

## Security model

Application binaries SHALL NOT contain ENTITY root private keys. Application/device clients create bounded envelopes containing hashes and metadata. An authorized ENTITY-side session validates the application/device context and the canonical ENTITY runtime signs resulting records.

Authorization is default deny. Raw source content is not required in ingest envelopes. Idempotency keys prevent duplicate ingestion and reject replay with changed payloads.
