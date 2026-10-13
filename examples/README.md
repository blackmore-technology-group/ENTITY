# Examples

Examples in this directory are synthetic and contain no live Entity credentials, principal bindings, private keys, or production identifiers.

The Open SDK uses hash-first envelopes. Raw source data does not need to be placed in ENTITY merely to register provenance.

See `open_sdk_asset_envelope.json` for a minimal non-authoritative asset-ingestion envelope shape.


# ENTITY Usage Receipt Verifier

A small standalone script that verifies one published ENTITY usage receipt
against its documented field set.

Schema: `entity-usage-receipt-v2`, as defined in
`src/01_Core_Runtime/usage_control/canonical_usage_control.py` (`_receipt()`).

## Usage

```bash
python3 examples/verify_receipt.py examples/fixtures/valid_usage_receipt.json
```

Exits `0` on a valid receipt, and exits non-zero otherwise.

## What It Verifies

- The file parses as JSON.
- The file's SHA-256 is reported.
- `schema` equals `entity-usage-receipt-v2`.
- The documented required fields are present with the expected types.
- The enum fields `assurance` and `evidence_origin` hold a documented value.
- `assurance_level` matches the level documented for the ``assurance`` value.
- `evidence_sha256` is 64 lowercase hex characters.

## What It Does Not Verify

- **That the receipt has not been modified.** A SHA-256 computed from the file only detects modification if compared to an independently trusted expected digest, which this script does not have.
- **That the signature is valid.** Signature verification requires the signer's manifest, a runtime dependency this example intentionally avoids.
- **That `evidence_sha256` matches any evidence payload.** The verifier only checks the field's format; it does not reconstruct or hash an evidence object.
- **Any real-world assertion.** The script does not prove that the usage occurred, that the actor is who the receipt claims, that the assurance level was actually reached, or that any descriptive field is true.

This script is a structural verifier: it only confirms that the receipt is shaped like a valid usage receipt of the documented schema.

## Tests

```bash
pytest examples/tests/test_verify_receipt.py
```