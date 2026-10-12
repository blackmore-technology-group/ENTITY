# ENTITY DataChip and EDP: prototype v0.1

Date: 2026-10-12. This is an experimental format; not a modification of the protected ENTITY v3.4.3 release or Protocol 1.0.

## Components

EDP (Virtual Data Processor): in-process typed interface that dispatches inspect, verify and export operations.

EDC (DataChip): offline, portable artifact containing exact content chunks and references to an optional source BTDU formula.

BTDU: retains its authoritative formula, atom-tape entropy and local storage semantics. EDC is an export copy.

ENTITY: continues to control real identities, authority, rights, consent, lineage and market events. Metadata inside a chip is not a validated authorization decision.

## Manifest

A .edc file is an uncompressed ZIP containing canonical UTF-8 JSON named manifest.json and binary files named chunks/SHA256.bin.

The manifest includes schema, format, chip_id, content_sha256, content_bytes, chunk_size, chunks, claimed_issuer, rights_passport_ref, lineage_refs, btdu_formula_object_ref and data_authority.

Chip ID is a SHA-256 of the other canonical manifest fields. It provides integrity but is not a signature.

The receiver checks the manifest, every chunk SHA-256, byte counts and overall reconstructed content SHA-256. The host application alone chooses the export destination.

## Limits and current gates

Current format permits at most 1 GiB of logical data, 1 MiB chunks, 4096 chunk references and a 256 KiB manifest. Exports require an independently supplied host authorization policy and never replace an existing file.

The portable container currently embeds exact bytes; it is not a transferable formula interpreter and does not imply greater compression. Future work requires a portable bounded formula graph, complete atom dependencies and residual entropy, signed issuer verification, policy revocation, cross-language readers and independent tests.

See sdk/datachip/README.md and tests/test_entity_datachip.py for the runnable implementation and regression cases.
