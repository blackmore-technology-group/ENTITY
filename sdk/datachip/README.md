# ENTITY DataChip / EDP v0.1

Experimental source. Not a protected ENTITY protocol release, production wallet or native mobile SDK.

The .edc format is a portable content-addressed archive that a separate host can verify offline. It includes exact bytes reconstructed from an existing BTDU formula when using the optional adapter. It is an export copy, not the authoritative BTDU primary storage object. Claims in the manifest do not authenticate the owner, issuer or rights.

## Run

From ENTITY repository root, on Python 3.10 or later:

    python -m sdk.datachip.cli pack input.bin output.edc
    python -m sdk.datachip.cli inspect output.edc
    python -m sdk.datachip.cli verify output.edc
    python -m unittest discover -s tests -p "test_entity_datachip*.py" -v

Only pack, inspect and verify are CLI functions. Export requires an application-supplied authorization callback; the CLI does not expose an unverified extraction option.

## Host bus

    from sdk.datachip.bus import DataChipProcessor, BUS_SCHEMA
    edp = DataChipProcessor()
    response = edp.dispatch({
        "schema": BUS_SCHEMA,
        "operation": "edc.verify",
        "chip": "output.edc"
    })

The bus supports only edc.inspect, edc.verify and edc.export. Export is denied unless the host provides an independently trusted and action-specific authorization callback, which must validate current identity, rights and revocation. The prototype does not implement the signed authority verifier.

## BTDU

Applications may call pack_btdu_formula(kernel, object_id, target), passing the existing BTDUFormulaKernel. The adapter deep-verifies the source and streams reconstruction into an exact portable copy. It does not alter the kernel, delete source data, transfer rights, issue assets or change market state.

## Security/limits

The implementation rejects altered hashes, duplicate/unexpected ZIP members, unsupported schemas, malformed manifests and unintended output replacement. It does not execute any code from the archive, resolve network references or import paths from the manifest. Initial limits: 1 GiB logical content, 1 MiB chunks, 4096 references and a 256 KiB manifest. Independent fuzzing, hardened parsers and resource limits are still needed.

A deterministic SHA-256 chip identifier is **not** a digital signature or an authenticated issuer statement.

## Next gates

Signed issuer statements; versioned trusted Rights Passport verification; self-contained deterministic formula/atom and required entropy bundles; Rust, Swift, Kotlin and .NET readers; portable golden vectors; real-device security reviews; independent two-way interoperability.

Specification: docs/architecture/ENTITY_DATACHIP_V0_1.md
