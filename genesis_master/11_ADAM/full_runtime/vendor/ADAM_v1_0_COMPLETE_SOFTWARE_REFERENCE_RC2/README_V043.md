# ADAM v0.43 — Research Gap Closure and Production Qualification

This branch extends the v0.42 Distributed Living Recreation Universe and addresses the six remaining research or external-production areas without converting unavailable external evidence into false claims.

## Added modules

- `adam_v43.semantic_world` — evidence-linked open-world semantic model registry and OOD abstention;
- `adam_v43.temporal_learning` — multichannel temporal learning and real Operations One event corpus;
- `adam_v43.theorem_proving` — Horn, symbolic conservation and finite counterexample proofs;
- `adam_v43.key_custody` — isolated process signing, rotation, quorum and HSM/KMS provider contracts;
- `adam_v43.production_soak` — resumable real-wall-clock SLA qualification;
- `native_authority_reference/` — compiled native framing/hash-chain conformance reference (not a signing authority);
- `rust_authority_kernel/` — complete production-target Rust authority source.

## Qualification

```bash
python -m pytest -q tests tests_v43
python run_v43_gap_closure_audit.py
```

## Claim boundary

The build materially advances every remaining gap. External hardware, Rust compilation and 30 actual days remain external acceptance activities and are supplied with complete runnable programs and gates.
