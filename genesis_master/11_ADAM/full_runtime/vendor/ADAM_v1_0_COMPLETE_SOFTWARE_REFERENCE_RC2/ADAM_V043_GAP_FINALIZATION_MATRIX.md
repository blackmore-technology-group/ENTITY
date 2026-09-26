# ADAM v0.43 Gap Finalization Matrix

| Area | Implemented artifact | Automated evidence | Final external action |
|---|---|---|---|
| Semantic understanding | `adam_v43/semantic_world.py` | held-out and OOD audit; exact model-vault embedding | supply larger licensed multimodal corpora and production evaluation |
| Temporal/sensor learning | `adam_v43/temporal_learning.py` | 4,800 generated regimes and 85 real O1 events | connect real sensors and retain long-horizon labelled outcomes |
| Theorem proving | `adam_v43/theorem_proving.py` | Horn, symbolic and finite proofs plus counterexample | select domain proof assistants and formal specifications |
| Key custody | `adam_v43/key_custody.py` | isolated 2-of-3 quorum and rotation | provision PKCS#11 HSM or cloud KMS and capture attestation |
| Rust authority | `rust_authority_kernel/` | static contract plus compiled native protocol oracle | build with Cargo, fuzz, reproduce and review |
| 30-day SLA | `production_qualification/` | real-time early-rejection smoke | operate continuously for 30 actual days and review final certificate |
