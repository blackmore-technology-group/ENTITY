# Migration from ADAM v0.50.1 R4 to v0.51

## Frozen parent

The exact uploaded R4 wrapper is preserved at:

`lineage/v0501_r4/ADAM_V0501_R4.zip`

Its SHA-256 is:

`3c406f50710d3aad86952bf87b42ac27b5260a77f357461e21122054cb6812c4`

R4 remains the bounded Python reference and comparison oracle. v0.51 does not overwrite its authority semantics or erase its qualification evidence.

## Migration method

```text
R4 Python proposal
        ↓
R4 Python evaluation and predicted root
        ↓
Rust evaluation of the same canonical request
        ↓
compare decision, proof, worldlines and root
        ↓
record any divergence
```

Initial Rust operation is shadow-only. Promotion proceeds through:

```text
offline golden-vector conformance
        ↓
shadow evaluation
        ↓
read-only historical replay
        ↓
limited canary authority
        ↓
majority Rust authority
        ↓
Python retained as a comparison oracle
```

## No automatic promotion

Source presence, static inspection, `cargo check`, or a single-platform build cannot transfer authority. Promotion requires the complete v0.51 acceptance contract, signed evidence and independent review.
