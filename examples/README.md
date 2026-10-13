# Examples

Examples in this directory are synthetic and contain no live Entity credentials, principal bindings, private keys, or production identifiers.

The Open SDK uses hash-first envelopes. Raw source data does not need to be placed in ENTITY merely to register provenance.

See `open_sdk_asset_envelope.json` for a minimal non-authoritative asset-ingestion envelope shape.

## Receipt verifier example

`verify_published_receipt.py` is a standalone stdlib script that:

- reads a published JSON receipt from disk and reports the file's SHA-256;
- checks a minimal field set for `entity-independent-node/receipt/v1` receipts (the Independent Node Program harness);
- recomputes `receipt_sha256` with the same canonical JSON rules as `independent-node/node.py`.

It does **not** verify ENTITY runtime signatures, production keys, or whether an external-world claim is true.

```bash
python examples/verify_published_receipt.py examples/fixtures/independent_node_receipt_valid.json
python examples/verify_published_receipt.py examples/fixtures/independent_node_receipt_tampered.json
```

The tampered fixture keeps the original `receipt_sha256` while mutating `object_sha256`, so verification fails closed.

All fixtures under `examples/fixtures/` are **hand-authored synthetic data** for this example. They are not real independently published or attested receipts, and the IDs in them are placeholders.

A passing run recomputes a self-hash that anyone could recompute from the same file, so it proves only that the bytes have not changed since the receipt was written. It does not prove who wrote the receipt, that an independent node produced it, or that any external-world claim is true. Treat the verifier as a format/integrity check, not an authenticity check.
